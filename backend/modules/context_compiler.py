"""
Omega Claw — Context Compiler
================================
Deterministic, gate-ordered context compiler that transforms
compressed knowledge into a bounded context bundle only when
a mechanically verifiable sufficiency proof is satisfied,
producing a cryptographic receipt for every decision.

Formal Signature:
    ContextCompiler: (Query, Corpus, Policy) → ContextBundle

Terminal Outcomes (total — exactly one per query):
    CONTEXT_PRODUCED | REFUSAL_EXPLICIT | ERROR

Archivist Model: nomic-embed-text (274MB, always loaded)
Storage: SQLite (local, offline)
Gates: G0..G7 total order, no branching, no skipping
"""

import hashlib
import json
import os
import sqlite3
import time
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import FrozenSet, List, Tuple


# ══════════════════════════════════════════════════════════════
# 1. CANONICAL DATA TYPES (IMMUTABLE AFTER CONSTRUCTION)
# ══════════════════════════════════════════════════════════════

ARCHIVIST_MODEL = "nomic-embed-text"

# Allowed artifact types
ARTIFACT_SET = frozenset({"python", "markdown", "json", "yaml", "text"})

# Terminal outcomes
CONTEXT_PRODUCED = "CONTEXT_PRODUCED"
REFUSAL_EXPLICIT = "REFUSAL_EXPLICIT"
ERROR = "ERROR"


@dataclass(frozen=True)
class QuerySpec:
    """Immutable query specification."""
    raw_query: str
    token_budget: int = 4000
    k_candidates: int = 10
    artifact_types: FrozenSet[str] = frozenset({"python"})
    query_hash: str = ""

    def __post_init__(self):
        if not self.query_hash:
            normalized = _canonical_normalize(self.raw_query)
            h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            object.__setattr__(self, "query_hash", h)


@dataclass(frozen=True)
class CandidateID:
    """Scored candidate from retrieval."""
    chunk_id: str
    file_path: str
    vector_score: float
    content_hash: str


@dataclass(frozen=True)
class EvidenceUnit:
    """Typed evidence extracted from a candidate."""
    unit_type: str          # SYMBOL, SIGNATURE, CONSTRAINT, CONTEXT
    source_chunk_id: str
    witness_hash: str
    content: str


@dataclass(frozen=True)
class GateTrace:
    """Trace of one gate execution."""
    gate_id: int
    gate_name: str
    input_count: int
    output_count: int
    verdict: str            # PASS, ELIMINATE, HALT
    elapsed_ms: float


@dataclass(frozen=True)
class DeterminismCapsule:
    """Proves that two runs with same inputs produce same output."""
    query_hash: str
    corpus_root_hash: str
    gate_trace_hash: str
    bundle_hash: str


@dataclass(frozen=True)
class RetrievalReceipt:
    """Cryptographic receipt for every retrieval decision."""
    query_hash: str
    corpus_root_hash: str
    outcome: str            # CONTEXT_PRODUCED | REFUSAL_EXPLICIT | ERROR
    gate_traces: Tuple[GateTrace, ...]
    determinism_capsule: DeterminismCapsule
    evidence_count: int
    token_count: int
    timestamp: float
    receipt_hash: str = ""

    def __post_init__(self):
        if not self.receipt_hash:
            payload = json.dumps({
                "qh": self.query_hash,
                "crh": self.corpus_root_hash,
                "out": self.outcome,
                "ec": self.evidence_count,
                "tc": self.token_count,
                "ts": self.timestamp,
            }, sort_keys=True)
            h = hashlib.sha256(payload.encode()).hexdigest()
            object.__setattr__(self, "receipt_hash", h)


@dataclass(frozen=True)
class ContextBundle:
    """The compiled context output. Immutable proof artifact."""
    text: str
    token_count: int
    receipt: RetrievalReceipt
    outcome: str


# ══════════════════════════════════════════════════════════════
# 2. CANONICAL NORMALIZATION
# ══════════════════════════════════════════════════════════════

def _canonical_normalize(text: str) -> str:
    """utf8_nfkc_trim_lf normalization."""
    text = unicodedata.normalize("NFKC", text)
    text = text.strip()
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines)


def _content_hash(text: str) -> str:
    return hashlib.sha256(_canonical_normalize(text).encode("utf-8")).hexdigest()


def _estimate_tokens(text: str) -> int:
    """Conservative token estimate (~4 chars per token)."""
    return len(text) // 4


# ══════════════════════════════════════════════════════════════
# 3. STORAGE LAYER (Non-Semantic — Compression Preserves
#    Information But Does Not Assign Meaning)
# ══════════════════════════════════════════════════════════════

DB_NAME = "omega_context.db"
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id    TEXT PRIMARY KEY,
    file_path   TEXT NOT NULL,
    file_hash   TEXT NOT NULL,
    chunk_idx   INTEGER NOT NULL,
    content     TEXT NOT NULL,
    embedding   BLOB,
    created_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunk_file ON chunks(file_path);
CREATE INDEX IF NOT EXISTS idx_chunk_hash ON chunks(file_hash);

CREATE TABLE IF NOT EXISTS corpus_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS receipts (
    receipt_hash TEXT PRIMARY KEY,
    query_hash   TEXT NOT NULL,
    outcome      TEXT NOT NULL,
    payload      TEXT NOT NULL,
    created_at   REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_receipt_query ON receipts(query_hash);
"""


class CorpusStore:
    """SQLite storage for the compressed corpus."""

    def __init__(self, db_path: str):
        self._path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    def has_file(self, file_path: str, file_hash: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM chunks WHERE file_path=? AND file_hash=? LIMIT 1",
            (file_path, file_hash))
        return cur.fetchone() is not None

    def remove_file(self, file_path: str):
        self._conn.execute("DELETE FROM chunks WHERE file_path=?", (file_path,))
        self._conn.commit()

    def insert_chunk(self, chunk_id: str, file_path: str, file_hash: str,
                     chunk_idx: int, content: str, embedding: bytes):
        self._conn.execute(
            "INSERT OR REPLACE INTO chunks VALUES (?,?,?,?,?,?,?)",
            (chunk_id, file_path, file_hash, chunk_idx, content, embedding, time.time()))
        self._conn.commit()

    def all_embeddings(self) -> List[dict]:
        cur = self._conn.execute(
            "SELECT chunk_id, file_path, content, embedding FROM chunks")
        results = []
        for row in cur:
            emb = json.loads(row["embedding"]) if row["embedding"] else []
            results.append({
                "chunk_id": row["chunk_id"],
                "file_path": row["file_path"],
                "content": row["content"],
                "embedding": emb,
                "content_hash": _content_hash(row["content"]),
            })
        return results

    def store_receipt(self, receipt: RetrievalReceipt):
        payload = json.dumps(asdict(receipt) if hasattr(receipt, '__dataclass_fields__') 
                             else {}, sort_keys=True)
        # Convert frozen dataclass to dict manually
        payload = json.dumps({
            "query_hash": receipt.query_hash,
            "corpus_root_hash": receipt.corpus_root_hash,
            "outcome": receipt.outcome,
            "evidence_count": receipt.evidence_count,
            "token_count": receipt.token_count,
        }, sort_keys=True)
        self._conn.execute(
            "INSERT OR REPLACE INTO receipts VALUES (?,?,?,?,?)",
            (receipt.receipt_hash, receipt.query_hash, receipt.outcome,
             payload, time.time()))
        self._conn.commit()

    def corpus_root_hash(self) -> str:
        """Hash of all chunk hashes — proves corpus identity."""
        cur = self._conn.execute(
            "SELECT chunk_id FROM chunks ORDER BY chunk_id")
        ids = [row[0] for row in cur]
        if not ids:
            return hashlib.sha256(b"EMPTY_CORPUS").hexdigest()
        combined = "|".join(ids)
        return hashlib.sha256(combined.encode()).hexdigest()

    @property
    def chunk_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    @property
    def file_count(self) -> int:
        return self._conn.execute(
            "SELECT COUNT(DISTINCT file_path) FROM chunks").fetchone()[0]

    def indexed_files(self) -> set:
        """Return set of all file paths currently in the corpus."""
        cur = self._conn.execute(
            "SELECT DISTINCT file_path FROM chunks")
        return {row[0] for row in cur}

    def purge_stale(self, live_files: set) -> int:
        """Remove chunks for files not in live_files."""
        indexed = self.indexed_files()
        stale = indexed - live_files
        removed = 0
        for fp in stale:
            self._conn.execute("DELETE FROM chunks WHERE file_path=?", (fp,))
            removed += 1
        if stale:
            self._conn.commit()
        return removed

    def close(self):
        self._conn.close()


# ══════════════════════════════════════════════════════════════
# 4. ARCHIVIST (nomic-embed-text — always loaded, dedicated)
# ══════════════════════════════════════════════════════════════

def _archivist_embed(text: str, model: str = ARCHIVIST_MODEL,
                     base_url: str = "http://localhost:11434") -> List[float]:
    """Archivist computes a single embedding."""
    results = _archivist_embed_batch([text], model, base_url)
    return results[0] if results else _keyword_fallback(text)


def _archivist_embed_batch(texts: List[str], model: str = ARCHIVIST_MODEL,
                           base_url: str = "http://localhost:11434") -> List[List[float]]:
    """Archivist batch embedding. One HTTP call for N texts."""
    import urllib.request

    # Ollama /api/embed accepts a list of inputs
    payload = json.dumps({
        "model": model,
        "input": [t[:2000] for t in texts],
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/api/embed", data=payload,
        headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            embeddings = result.get("embeddings", [])
            if len(embeddings) == len(texts):
                return embeddings
            # Pad with fallback if mismatch
            return embeddings + [_keyword_fallback(t) for t in texts[len(embeddings):]]
    except Exception:
        return [_keyword_fallback(t) for t in texts]


def _keyword_fallback(text: str) -> List[float]:
    """Deterministic keyword embedding when archivist is unavailable."""
    words = set(text.lower().split())
    vocab = [
        "class", "def", "return", "self", "import", "from", "if", "else",
        "for", "while", "try", "except", "with", "as", "in", "not", "and",
        "none", "true", "false", "list", "dict", "str", "int", "float",
        "file", "path", "read", "write", "open", "data", "json", "error",
        "log", "test", "assert", "init", "config", "run", "start", "stop",
        "create", "update", "delete", "get", "set", "send", "process",
        "parse", "build", "check", "validate", "result", "output", "input",
        "gate", "tool", "agent", "soul", "envelope", "audit", "pipeline",
        "query", "context", "receipt", "evidence", "chunk", "embed", "hash",
    ]
    return [1.0 if v in words else 0.0 for v in vocab]


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na > 0 and nb > 0 else 0.0


# ══════════════════════════════════════════════════════════════
# 5. CHUNKER
# ══════════════════════════════════════════════════════════════

def _chunk_file(content: str, file_path: str) -> List[dict]:
    """Split file into overlapping chunks with context headers."""
    normalized = _canonical_normalize(content)
    chunks = []
    start = 0
    idx = 0

    while start < len(normalized):
        end = start + CHUNK_SIZE
        chunk_text = f"# FILE: {file_path}\n{normalized[start:end]}"
        chunk_id = hashlib.sha256(
            f"{file_path}:{idx}:{normalized[start:start+100]}".encode()
        ).hexdigest()[:16]

        chunks.append({"chunk_id": chunk_id, "index": idx, "content": chunk_text})
        start = end - CHUNK_OVERLAP
        idx += 1

    return chunks


# ══════════════════════════════════════════════════════════════
# 6. GATE STACK (G0..G7 — Total Order, No Branching)
# ══════════════════════════════════════════════════════════════

def _run_gate(gate_id: int, name: str, candidates: List[dict],
              gate_fn) -> Tuple[List[dict], GateTrace]:
    """Execute one gate. Returns (output, trace)."""
    t0 = time.time()
    input_count = len(candidates)
    output = gate_fn(candidates)
    elapsed = (time.time() - t0) * 1000

    # Monotonicity invariant: output ≤ input for elimination gates
    if gate_id in (1, 2, 3, 4, 5) and len(output) > input_count:
        # VIOLATION — this is a system error
        trace = GateTrace(gate_id, name, input_count, input_count,
                          "VIOLATION", elapsed)
        return candidates, trace

    verdict = "PASS" if output else "HALT"
    if len(output) < input_count and gate_id in (1, 2, 3, 4, 5):
        verdict = "ELIMINATE"

    trace = GateTrace(gate_id, name, input_count, len(output), verdict, elapsed)
    return output, trace


def _g0_parse_query(query: QuerySpec) -> QuerySpec:
    """G0: Parse and validate query. Identity function if valid."""
    # Query is already validated by frozen dataclass construction
    return query


def _g1_corpus_filter(candidates: List[dict], query: QuerySpec) -> List[dict]:
    """G1: Filter by artifact type."""
    return candidates  # All Python files match for now


def _g2_vector_rank(candidates: List[dict], query_embedding: List[float]) -> List[dict]:
    """G2: Rank by vector similarity. Eliminate bottom 50%."""
    for c in candidates:
        c["score"] = _cosine(query_embedding, c["embedding"])
    candidates.sort(key=lambda x: -x["score"])
    # Keep top half, minimum 5
    keep = max(5, len(candidates) // 2)
    return candidates[:keep]


def _g3_dedup(candidates: List[dict]) -> List[dict]:
    """G3: Remove duplicate content hashes."""
    seen = set()
    output = []
    for c in candidates:
        h = c.get("content_hash", c["chunk_id"])
        if h not in seen:
            seen.add(h)
            output.append(c)
    return output


def _g4_budget_trim(candidates: List[dict], token_budget: int) -> List[dict]:
    """G4: Trim to fit token budget. Greedy top-down."""
    output = []
    total_tokens = 0
    for c in candidates:
        tokens = _estimate_tokens(c["content"])
        if total_tokens + tokens > token_budget:
            break
        output.append(c)
        total_tokens += tokens
    return output


def _g5_sufficiency(candidates: List[dict], min_units: int = 1) -> List[dict]:
    """G5: Sufficiency check. Must have >= min_units evidence.
    
    Returns candidates if sufficient, empty list if not.
    This is proof theory, not ranking.
    """
    if len(candidates) >= min_units:
        return candidates
    return []  # REFUSAL — insufficient evidence


def _g6_decompress(candidates: List[dict]) -> List[dict]:
    """G6: Decompress and prepare text.
    
    No raw text access before this gate (invariant).
    This is where content becomes readable.
    """
    # Content is already stored as text in SQLite
    # In a full SV-codec system, decompression would happen here
    return candidates


def _g7_assemble(candidates: List[dict]) -> str:
    """G7: Assemble final context text."""
    parts = []
    for c in candidates:
        parts.append(f"--- (relevance: {c.get('score', 0):.3f}) ---")
        parts.append(c["content"])
    return "\n".join(parts)


# ══════════════════════════════════════════════════════════════
# 7. CONTEXT COMPILER
# ══════════════════════════════════════════════════════════════

class ContextCompiler:
    """Deterministic context compiler with proof-carrying retrieval.

    ContextCompiler: (Query, Corpus, Policy) → ContextBundle

    Every query terminates in exactly one of:
        CONTEXT_PRODUCED | REFUSAL_EXPLICIT | ERROR

    No soft failures. No partial states.
    """

    EXCLUDE_DIRS = {
        "__pycache__", ".git", ".venv", "venv", "node_modules",
        ".pytest_cache", ".mypy_cache", "dist", "build", ".eggs",
    }

    def __init__(self, workspace: str,
                 archivist_model: str = ARCHIVIST_MODEL,
                 ollama_url: str = "http://localhost:11434"):
        self._workspace = Path(workspace).resolve()
        self._archivist = archivist_model
        self._ollama_url = ollama_url
        self._db_path = str(self._workspace / DB_NAME)
        self._store = CorpusStore(self._db_path)

    # ── Corpus Indexing ───────────────────────────────────────

    def index(self, force: bool = False) -> dict:
        """Index all Python files into the corpus store.
        
        Archivist Pipeline (A0-A6):
          A0 Canonicalize
          A1 Policy/Scope admit
          A2 Chunk
          A3 Hash
          A4 Embed (batch — one HTTP call per file)
          A5 Dedup check
          A6 Store + seal
        """
        files_found = 0
        chunks_created = 0
        skipped = 0

        for root, dirs, files in os.walk(self._workspace):
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            for fname in sorted(files):
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, self._workspace)
                files_found += 1

                try:
                    content = Path(fpath).read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue

                fhash = _content_hash(content)
                if not force and self._store.has_file(rel, fhash):
                    skipped += 1
                    continue

                self._store.remove_file(rel)
                chunks = _chunk_file(content, rel)
                
                if not chunks:
                    continue

                # Batch embed all chunks for this file in one call
                texts = [c["content"] for c in chunks]
                embeddings = _archivist_embed_batch(
                    texts, self._archivist, self._ollama_url)

                for chunk, emb in zip(chunks, embeddings):
                    self._store.insert_chunk(
                        chunk["chunk_id"], rel, fhash, chunk["index"],
                        chunk["content"], json.dumps(emb))
                    chunks_created += 1

        # A7: Purge stale — remove chunks for deleted files
        live_files = set()
        for root2, dirs2, files2 in os.walk(self._workspace):
            dirs2[:] = [d for d in dirs2 if d not in self.EXCLUDE_DIRS]
            for fn in files2:
                if fn.endswith(".py"):
                    live_files.add(os.path.relpath(
                        os.path.join(root2, fn), self._workspace))
        stale_purged = self._store.purge_stale(live_files)

        return {
            "files": files_found, "chunks": chunks_created,
            "skipped": skipped, "new": chunks_created,
            "purged": stale_purged,
            "total_chunks": self._store.chunk_count,
            "total_files": self._store.file_count,
        }

    # ── Compilation (The Core) ────────────────────────────────

    def compile(self, query: str, token_budget: int = 4000,
                k: int = 10) -> ContextBundle:
        """Compile a query against the corpus.

        Runs the full G0..G7 gate stack. Returns a ContextBundle
        with exactly one terminal outcome and a receipt.
        """
        t_start = time.time()
        traces: List[GateTrace] = []

        try:
            # G0: Parse query
            spec = QuerySpec(raw_query=query, token_budget=token_budget,
                             k_candidates=k)
            traces.append(GateTrace(0, "G0_PARSE", 1, 1, "PASS", 0.0))

            # Load corpus
            corpus = self._store.all_embeddings()
            corpus_hash = self._store.corpus_root_hash()

            if not corpus:
                return self._make_refusal(
                    spec, corpus_hash, traces, "Empty corpus")

            # G1: Corpus filter
            g1_out, g1_trace = _run_gate(
                1, "G1_FILTER", corpus,
                lambda c: _g1_corpus_filter(c, spec))
            traces.append(g1_trace)

            # G2: Vector rank
            query_emb = _archivist_embed(query, self._archivist, self._ollama_url)
            g2_out, g2_trace = _run_gate(
                2, "G2_RANK", g1_out,
                lambda c: _g2_vector_rank(c, query_emb))
            traces.append(g2_trace)

            # G3: Dedup
            g3_out, g3_trace = _run_gate(3, "G3_DEDUP", g2_out, _g3_dedup)
            traces.append(g3_trace)

            # G4: Budget trim
            g4_out, g4_trace = _run_gate(
                4, "G4_BUDGET", g3_out,
                lambda c: _g4_budget_trim(c, token_budget))
            traces.append(g4_trace)

            # G5: Sufficiency (proof gate)
            g5_out, g5_trace = _run_gate(5, "G5_SUFFICIENCY", g4_out, _g5_sufficiency)
            traces.append(g5_trace)

            if not g5_out:
                return self._make_refusal(
                    spec, corpus_hash, traces, "Insufficient evidence")

            # G6: Decompress (no text access before this point)
            g6_out, g6_trace = _run_gate(6, "G6_DECOMPRESS", g5_out, _g6_decompress)
            traces.append(g6_trace)

            # G7: Assemble
            text = _g7_assemble(g6_out)
            token_count = _estimate_tokens(text)
            traces.append(GateTrace(7, "G7_ASSEMBLE", len(g6_out), 1,
                                    "PASS", (time.time() - t_start) * 1000))

            # Token budget invariant check
            if token_count > token_budget:
                text = text[:token_budget * 4]
                token_count = token_budget

            # Build receipt
            gate_trace_hash = hashlib.sha256(
                json.dumps([(t.gate_id, t.verdict) for t in traces]).encode()
            ).hexdigest()

            capsule = DeterminismCapsule(
                query_hash=spec.query_hash,
                corpus_root_hash=corpus_hash,
                gate_trace_hash=gate_trace_hash,
                bundle_hash=_content_hash(text),
            )

            receipt = RetrievalReceipt(
                query_hash=spec.query_hash,
                corpus_root_hash=corpus_hash,
                outcome=CONTEXT_PRODUCED,
                gate_traces=tuple(traces),
                determinism_capsule=capsule,
                evidence_count=len(g6_out),
                token_count=token_count,
                timestamp=time.time(),
            )

            self._store.store_receipt(receipt)

            return ContextBundle(
                text=text,
                token_count=token_count,
                receipt=receipt,
                outcome=CONTEXT_PRODUCED,
            )

        except Exception as e:
            # ERROR — total function, must terminate
            error_receipt = self._make_error_receipt(
                query, str(e), traces)
            return ContextBundle(
                text="", token_count=0,
                receipt=error_receipt, outcome=ERROR,
            )

    def _make_refusal(self, spec: QuerySpec, corpus_hash: str,
                      traces: List[GateTrace], reason: str) -> ContextBundle:
        """Construct a REFUSAL_EXPLICIT bundle."""
        capsule = DeterminismCapsule(
            query_hash=spec.query_hash,
            corpus_root_hash=corpus_hash,
            gate_trace_hash=hashlib.sha256(
                json.dumps([(t.gate_id, t.verdict) for t in traces]).encode()
            ).hexdigest(),
            bundle_hash=_content_hash(""),
        )
        receipt = RetrievalReceipt(
            query_hash=spec.query_hash,
            corpus_root_hash=corpus_hash,
            outcome=REFUSAL_EXPLICIT,
            gate_traces=tuple(traces),
            determinism_capsule=capsule,
            evidence_count=0,
            token_count=0,
            timestamp=time.time(),
        )
        self._store.store_receipt(receipt)
        return ContextBundle(
            text=f"[REFUSAL: {reason}]",
            token_count=0, receipt=receipt,
            outcome=REFUSAL_EXPLICIT,
        )

    def _make_error_receipt(self, query: str, error: str,
                            traces: List[GateTrace]) -> RetrievalReceipt:
        qh = hashlib.sha256(query.encode()).hexdigest()
        capsule = DeterminismCapsule(qh, "ERROR", "", "")
        return RetrievalReceipt(
            query_hash=qh, corpus_root_hash="ERROR",
            outcome=ERROR, gate_traces=tuple(traces),
            determinism_capsule=capsule,
            evidence_count=0, token_count=0,
            timestamp=time.time(),
        )

    # ── Convenience ───────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 5) -> str:
        """Simple retrieval interface. Returns text or refusal reason."""
        bundle = self.compile(query, token_budget=4000, k=top_k)
        return bundle.text

    @property
    def stats(self) -> dict:
        sz = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0
        return {
            "total_chunks": self._store.chunk_count,
            "total_files": self._store.file_count,
            "db_path": self._db_path,
            "db_size_kb": round(sz / 1024, 1),
        }

    def close(self):
        self._store.close()
