#!/usr/bin/env python3
"""
VERITAS Provenance Stack — Module 20
Full implementation of the 3-layer Provenance Layer:
  1. Archivist Node: CAS + nomic-embed-text embeddings
  2. Context Compiler: deterministic context + proof-carrying retrieval
  3. Forensic Trace Sealing: S.E.A.L. cryptographic chain

Connects to real Veritas Vault database (READ-ONLY).
Uses Ollama nomic-embed-text for semantic embeddings.
"""

import hashlib
import json
import logging
import math
import sqlite3
import struct
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import os

log = logging.getLogger('provenance')

# ══════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════

VAULT_DB_PATH = Path('/mnt/c/Users/rlope/AppData/Roaming/veritas-vault/vault_data/vault.db')
EMBED_MODEL = 'nomic-embed-text'
OLLAMA_URL = 'http://127.0.0.1:11434'
EMBED_DIM = 768  # nomic-embed-text output dimension
TOP_K = 5        # number of context fragments to retrieve
CAS_DIR = Path('/home/veritas/gravity-omega-v2/backend/data/provenance_cas')

# ══════════════════════════════════════════════════════════════
# LAYER 1: ARCHIVIST NODE (A0-A6 Ingest)
# ══════════════════════════════════════════════════════════════
# Content-Addressed Storage (CAS) with nomic-embed-text embeddings.
# Every chunk is addressed by its SHA-256 content hash.
# Embeddings are stored in a local SQLite for fast cosine retrieval.

class ArchivistNode:
    """Foundation layer: CAS + embedding index."""

    def __init__(self, cas_dir=CAS_DIR):
        self.cas_dir = cas_dir
        self.cas_dir.mkdir(parents=True, exist_ok=True)
        self.index_db = cas_dir / 'embedding_index.db'
        self._init_index()

    def _init_index(self):
        """Initialize the embedding index database."""
        db = sqlite3.connect(str(self.index_db))
        db.execute('''CREATE TABLE IF NOT EXISTS embeddings (
            content_hash TEXT PRIMARY KEY,
            title TEXT,
            source TEXT,
            doc_type TEXT,
            embedding BLOB,
            chunk_text TEXT,
            indexed_at REAL,
            tier TEXT DEFAULT 'C',
            retrieval_count INTEGER DEFAULT 0
        )''')
        # Backwards compatibility migration
        try:
            db.execute("ALTER TABLE embeddings ADD COLUMN tier TEXT DEFAULT 'C'")
        except Exception:
            pass
        try:
            db.execute("ALTER TABLE embeddings ADD COLUMN retrieval_count INTEGER DEFAULT 0")
        except Exception:
            pass
        db.execute('''CREATE TABLE IF NOT EXISTS index_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        db.commit()
        db.close()

    def content_hash(self, text):
        """SHA-256 content-addressed hash."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def _embed_text(self, text):
        """Get embedding from nomic-embed-text via Ollama."""
        try:
            payload = json.dumps({
                'model': EMBED_MODEL,
                'prompt': text[:8192],  # nomic supports up to 8192 tokens
            }).encode()
            req = urllib.request.Request(
                f'{OLLAMA_URL}/api/embeddings',
                data=payload,
                headers={'Content-Type': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            return data.get('embedding', [])
        except Exception as e:
            log.warning(f'Embedding failed: {e}')
            return []

    def _embedding_to_blob(self, embedding):
        """Pack float list into compact binary blob."""
        return struct.pack(f'{len(embedding)}f', *embedding)

    def _blob_to_embedding(self, blob):
        """Unpack binary blob to float list."""
        n = len(blob) // 4
        return list(struct.unpack(f'{n}f', blob))

    def ingest_from_vault(self, limit=500):
        """Index vault documents into CAS with embeddings (READ-ONLY on vault)."""
        if not VAULT_DB_PATH.exists():
            return {'error': 'Vault database not found', 'indexed': 0}

        vault_db = sqlite3.connect(f'file:{VAULT_DB_PATH}?mode=ro', uri=True)
        vault_db.row_factory = sqlite3.Row

        # Get documents not yet indexed
        index_db = sqlite3.connect(str(self.index_db))
        existing = set(r[0] for r in index_db.execute(
            'SELECT content_hash FROM embeddings'
        ).fetchall())

        # Fetch search_index entries (they have pre-extracted content)
        rows = vault_db.execute(
            'SELECT doc_id, title, content, rel_path, type FROM search_index LIMIT ?',
            (limit,)
        ).fetchall()
        vault_db.close()

        indexed = 0
        skipped = 0
        for row in rows:
            text = (row['title'] or '') + '\n' + (row['content'] or '')
            if not text.strip():
                continue
            # Truncate for embedding — use title + first 2000 chars
            embed_text = text[:2000]
            h = self.content_hash(embed_text)
            if h in existing:
                skipped += 1
                continue

            embedding = self._embed_text(embed_text)
            if not embedding:
                continue

            index_db.execute(
                '''INSERT OR REPLACE INTO embeddings
                   (content_hash, title, source, doc_type, embedding, chunk_text, indexed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (h, row['title'], row['rel_path'], row['type'],
                 self._embedding_to_blob(embedding), embed_text[:500], time.time())
            )
            indexed += 1
            existing.add(h)

            # Batch commit every 50
            if indexed % 50 == 0:
                index_db.commit()
                log.info(f'Archivist: indexed {indexed} chunks...')

        index_db.execute(
            "INSERT OR REPLACE INTO index_meta (key, value) VALUES ('last_ingest', ?)",
            (datetime.now(timezone.utc).isoformat(),)
        )
        index_db.commit()
        index_db.close()

        return {'indexed': indexed, 'skipped': skipped, 'total_in_vault': len(rows)}

    def semantic_search(self, query, top_k=TOP_K):
        """Embed query and find top-K matching vault chunks by cosine similarity."""
        query_embedding = self._embed_text(query)
        if not query_embedding:
            return []

        db = sqlite3.connect(str(self.index_db))
        rows = db.execute(
            'SELECT content_hash, title, source, doc_type, embedding, chunk_text FROM embeddings'
        ).fetchall()
        db.close()

        if not rows:
            return []

        # Cosine similarity search
        results = []
        for row in rows:
            stored_emb = self._blob_to_embedding(row[4])
            if len(stored_emb) != len(query_embedding):
                continue
            sim = self._cosine_similarity(query_embedding, stored_emb)
            results.append({
                'content_hash': row[0],
                'title': row[1],
                'source': row[2],
                'doc_type': row[3],
                'chunk_text': row[5],
                'similarity': sim,
            })

        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, a, b):
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def stats(self):
        """Return archivist index statistics."""
        db = sqlite3.connect(str(self.index_db))
        count = db.execute('SELECT COUNT(*) FROM embeddings').fetchone()[0]
        meta = dict(db.execute('SELECT key, value FROM index_meta').fetchall())
        db.close()
        return {
            'indexed_chunks': count,
            'last_ingest': meta.get('last_ingest', 'never'),
            'cas_dir': str(self.cas_dir),
            'embed_model': EMBED_MODEL,
        }


# ══════════════════════════════════════════════════════════════
# LAYER 2: CONTEXT COMPILER (Provenance Engine)
# ══════════════════════════════════════════════════════════════
# Transforms raw retrieval into deterministic context with
# proof-carrying metadata (RUN_ID, source hashes, timestamps).

class ContextCompiler:
    """Deterministic context generation with proof-carrying retrieval."""

    def __init__(self, archivist: ArchivistNode):
        self.archivist = archivist

    def compile_context(self, query, top_k=TOP_K):
        """
        Given a user query, produce a structured context object with:
        - run_id: unique identifier for this retrieval run
        - fragments: list of proof-carrying context fragments
        - provenance_chain: hash chain linking all fragments
        """
        run_id = hashlib.sha256(
            f'{query}:{time.time()}'.encode()
        ).hexdigest()[:16]

        # Semantic retrieval from archivist
        results = self.archivist.semantic_search(query, top_k)

        fragments = []
        chain_hash = hashlib.sha256(run_id.encode()).hexdigest()

        for i, r in enumerate(results):
            # Proof-carrying: each fragment includes its content hash
            # and the running chain hash for tamper detection
            fragment = {
                'index': i,
                'content_hash': r['content_hash'],
                'title': r['title'],
                'source': r['source'],
                'doc_type': r['doc_type'],
                'text': r['chunk_text'],
                'similarity': round(r['similarity'], 4),
                'chain_parent': chain_hash,
            }

            # Extend the hash chain
            chain_hash = hashlib.sha256(
                f'{chain_hash}:{r["content_hash"]}'.encode()
            ).hexdigest()
            fragment['chain_hash'] = chain_hash

            fragments.append(fragment)

        # Skeptical verification pass
        verified_fragments = []
        for f in fragments:
            status = self.verify_fragment(f)
            f['verification'] = status
            if status != 'STALE':
                verified_fragments.append(f)
            else:
                log.info(f'Provenance: demoting STALE fragment {f.get("content_hash", "")[:8]} from {f.get("source", "unknown")}')

        return {
            'run_id': run_id,
            'query': query,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'fragment_count': len(verified_fragments),
            'fragments': verified_fragments,
            'chain_head': chain_hash,
        }

    def verify_fragment(self, fragment, current_file_state=None):
        """Check if a retrieved fragment's source still matches disk state.
        Returns: 'VERIFIED', 'STALE', or 'UNVERIFIABLE'"""
        source = fragment.get('source', '')
        text = fragment.get('text', '')
        if not source or not os.path.exists(source):
            return 'UNVERIFIABLE'
        try:
            with open(source, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            # Check if the fragment text still appears in the source file
            if text.strip()[:200] in content:
                return 'VERIFIED'
            return 'STALE'
        except Exception:
            return 'UNVERIFIABLE'

    def to_system_prompt(self, compiled_context):
        """
        Convert compiled context into a system prompt for the LLM.
        Emits SYMBOL/SIGNATURE format per provenance spec.
        """
        if not compiled_context['fragments']:
            return None

        lines = [
            f"[PROVENANCE RUN {compiled_context['run_id']}]",
            f"Retrieved {compiled_context['fragment_count']} context fragments from Veritas Vault.",
            f"Chain head: {compiled_context['chain_head'][:12]}…",
            "",
            "RELEVANT CONTEXT:",
            "=" * 40,
        ]

        for f in compiled_context['fragments']:
            lines.append(f"\n[FRAGMENT {f['index']}] sim={f['similarity']} type={f['doc_type']}")
            lines.append(f"SOURCE: {f['source']}")
            lines.append(f"HASH: {f['content_hash'][:12]}…")
            lines.append(f"{f['text']}")
            lines.append("-" * 40)

        lines.append("")
        lines.append("Use the above context to inform your response. "
                     "Cite sources by their FRAGMENT index when relevant.")

        return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════
# LAYER 3: FORENSIC TRACE SEALING (S.E.A.L.)
# ══════════════════════════════════════════════════════════════
# Security Evidence Audit Lock — cryptographic chain covering
# the entire run trace from query to response.

class TraceSealer:
    """S.E.A.L. — generates tamper-evident audit trails."""

    def __init__(self, seal_dir=None):
        self.seal_dir = seal_dir or (CAS_DIR / 'seals')
        self.seal_dir.mkdir(parents=True, exist_ok=True)

    def seal_run(self, compiled_context, llm_response):
        """
        Create a S.E.A.L. for a complete query→context→response run.
        Returns the seal object with full hash chain.
        """
        run_id = compiled_context['run_id']

        # Build the trace
        trace = {
            'run_id': run_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'query_hash': hashlib.sha256(
                compiled_context['query'].encode()
            ).hexdigest(),
            'context_chain_head': compiled_context['chain_head'],
            'fragment_hashes': [
                f['content_hash'] for f in compiled_context['fragments']
            ],
            'response_hash': hashlib.sha256(
                (llm_response or '').encode()
            ).hexdigest(),
        }

        # Final seal = hash of entire trace
        seal_hash = hashlib.sha256(
            json.dumps(trace, sort_keys=True).encode()
        ).hexdigest()
        trace['seal_hash'] = seal_hash

        # Persist seal to disk
        seal_path = self.seal_dir / f'{run_id}.seal.json'
        seal_path.write_text(json.dumps(trace, indent=2))

        return trace

    def verify_seal(self, run_id):
        """Verify a seal's integrity by recomputing the hash and recursive chain."""
        seal_path = self.seal_dir / f'{run_id}.seal.json'
        if not seal_path.exists():
            return {'valid': False, 'error': 'Seal not found'}

        trace = json.loads(seal_path.read_text())
        stored_hash = trace.pop('seal_hash', '')
        
        # 1. Verify recursive chain of custody
        computed_chain_head = hashlib.sha256(run_id.encode()).hexdigest()
        for f_hash in trace.get('fragment_hashes', []):
            computed_chain_head = hashlib.sha256(
                f'{computed_chain_head}:{f_hash}'.encode()
            ).hexdigest()
            
        if computed_chain_head != trace.get('context_chain_head'):
            return {'valid': False, 'error': 'S.E.A.L. chain truncation detected'}

        # 2. Verify overall seal hash
        recomputed = hashlib.sha256(
            json.dumps(trace, sort_keys=True).encode()
        ).hexdigest()

        return {
            'valid': recomputed == stored_hash,
            'run_id': run_id,
            'stored_hash': stored_hash[:16] + '…',
            'recomputed_hash': recomputed[:16] + '…',
        }

    def list_seals(self, limit=20):
        """List recent seals."""
        seals = sorted(self.seal_dir.glob('*.seal.json'), reverse=True)[:limit]
        results = []
        for s in seals:
            try:
                data = json.loads(s.read_text())
                results.append({
                    'run_id': data.get('run_id'),
                    'timestamp': data.get('timestamp'),
                    'seal_hash': data.get('seal_hash', '')[:16] + '…',
                    'fragments': len(data.get('fragment_hashes', [])),
                })
            except Exception:
                pass
        return results


# ══════════════════════════════════════════════════════════════
# UNIFIED PROVENANCE STACK
# ══════════════════════════════════════════════════════════════

class ProvenanceStack:
    """
    Full Provenance Layer — orchestrates all 3 layers:
    Archivist → Context Compiler → Trace Sealer

    Background daemon thread keeps archivist index fresh.
    """

    REFRESH_INTERVAL = 1800  # 30 minutes between incremental ingests

    def __init__(self):
        self.archivist = ArchivistNode()
        self.compiler = ContextCompiler(self.archivist)
        self.sealer = TraceSealer()
        self._bg_thread = None
        log.info('Provenance Stack initialized (3 layers active)')

    def start_background_archivist(self):
        """Start the background archivist daemon thread."""
        if self._bg_thread and self._bg_thread.is_alive():
            return  # Already running
        self._bg_thread = threading.Thread(
            target=self._archivist_loop, daemon=True, name='archivist-daemon'
        )
        self._bg_thread.start()
        log.info('Archivist daemon started')

    def _archivist_loop(self):
        """Background loop: seed on first run, then incremental refreshes."""
        # Wait for Ollama to be ready
        time.sleep(5)

        try:
            stats = self.archivist.stats()
            existing = stats['indexed_chunks']
            log.info(f'Archivist: {existing} chunks already indexed')

            if existing < 100:
                # First-time or sparse index: seed with initial batch
                log.info('Archivist: seeding initial index (up to 200 docs)...')
                result = self.archivist.ingest_from_vault(limit=200)
                log.info(f'Archivist: seed complete — indexed={result.get("indexed", 0)}, '
                         f'skipped={result.get("skipped", 0)}')
            else:
                # Already seeded: only ingest truly new documents
                log.info(f'Archivist: index loaded ({existing} chunks), checking for new docs...')
                result = self.archivist.ingest_from_vault(limit=50)
                new = result.get('indexed', 0)
                if new > 0:
                    log.info(f'Archivist: {new} new docs indexed')
                else:
                    log.info('Archivist: index is current, no new docs')
        except Exception as e:
            log.warning(f'Archivist seed failed (non-fatal): {e}')

        # Periodic refresh loop
        while True:
            time.sleep(self.REFRESH_INTERVAL)
            try:
                result = self.archivist.ingest_from_vault(limit=50)
                new = result.get('indexed', 0)
                if new > 0:
                    log.info(f'Archivist refresh: {new} new docs indexed')
            except Exception as e:
                log.warning(f'Archivist refresh failed: {e}')

    def rag_query(self, query, top_k=TOP_K):
        """
        Full RAG pipeline:
        1. Compile context from vault via archivist embeddings
        2. Generate system prompt with proof-carrying fragments
        3. Return context + system prompt for LLM injection
        """
        compiled = self.compiler.compile_context(query, top_k)
        system_prompt = self.compiler.to_system_prompt(compiled)
        return {
            'compiled_context': compiled,
            'system_prompt': system_prompt,
        }

    def build_task_scoped_prompt(self, task_description, intent="TASK", tool_set=None, available_tokens=8192):
        """Build a system prompt dynamically based on task context to save tokens."""
        from pathlib import Path
        context_dir = Path(r'C:\Users\rlope\.veritas')
        
        def read_ctx(name):
            try: return (context_dir / name).read_text(encoding='utf-8')
            except Exception: return ''

        prompt_parts = []
        base_core = read_ctx('omega_core.md')
        if not base_core:
            base_core = read_ctx('omega_context.md')
        prompt_parts.append(base_core)

        if intent in ('TASK', 'FOLLOWUP'):
            prompt_parts.append(read_ctx('omega_rules.md'))
            
        if intent == 'TASK':
            prompt_parts.append(read_ctx('omega_traps.md'))
            
            # Use RAG to fetch only the rules/style guidelines relevant to the specific sub-tasks
            if task_description:
                # Query for specific context so we don't load the entire omega_projects.md
                rag_res = self.rag_query(task_description + " project guidelines rules styles", top_k=3)
                if rag_res and rag_res.get('compiled_context', {}).get('fragment_count', 0) > 0:
                    prompt_parts.append("## Task-Scoped Project Guidelines (RAG)\n" + rag_res['system_prompt'])
                else:
                    # Fallback
                    prompt_parts.append(read_ctx('omega_projects.md'))

        full_prompt = '\n\n'.join(p for p in prompt_parts if p.strip())
        
        # Heuristic 4 chars per token roughly
        max_chars = available_tokens * 4
        if len(full_prompt) > max_chars:
            full_prompt = full_prompt[:max_chars] + "\n\n...[TRUNCATED FOR VRAM CONTEXT LIMIT]..."
            
        return full_prompt

    def seal_response(self, compiled_context, llm_response):
        """Seal a complete run with S.E.A.L."""
        return self.sealer.seal_run(compiled_context, llm_response)

    def status(self):
        """Full provenance stack health status."""
        arch_stats = self.archivist.stats()
        seal_count = len(list(self.sealer.seal_dir.glob('*.seal.json')))
        bg_alive = self._bg_thread.is_alive() if self._bg_thread else False
        return {
            'status': 'active',
            'layers': ['archivist', 'context_compiler', 'trace_sealer'],
            'archivist': arch_stats,
            'seals_count': seal_count,
            'embed_model': EMBED_MODEL,
            'vault_connected': VAULT_DB_PATH.exists(),
            'background_daemon': 'running' if bg_alive else 'stopped',
        }

    def ingest(self, limit=500):
        """Manual vault ingestion into archivist CAS."""
        return self.archivist.ingest_from_vault(limit)


# Singleton instance with auto-start background archivist
_stack = None
_lock = threading.Lock()

def get_stack():
    global _stack
    if _stack is None:
        with _lock:
            if _stack is None:
                _stack = ProvenanceStack()
                _stack.start_background_archivist()
    return _stack
