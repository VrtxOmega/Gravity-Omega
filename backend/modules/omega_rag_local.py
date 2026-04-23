"""
Omega Claw — Local RAG Engine
================================
Indexes your workspace into SQLite. Embeds with Ollama.
Retrieves relevant code chunks for any task.

Zero cloud dependencies. Fully offline.
This is how a 7b model punches like a 32b.
"""

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log_fn = print  # can be replaced with logging


# ══════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════

DB_NAME = "omega_rag.db"

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id   TEXT PRIMARY KEY,
    file_path  TEXT,
    file_hash  TEXT,
    chunk_idx  INTEGER,
    content    TEXT,
    embedding  BLOB,
    created_at REAL
);
CREATE INDEX IF NOT EXISTS idx_file ON chunks(file_path);
CREATE INDEX IF NOT EXISTS idx_hash ON chunks(file_hash);
"""


class ChunkDB:
    """SQLite store for code chunks + embeddings."""

    def __init__(self, db_path: str):
        self._path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_CREATE_SQL)

    def has_file(self, file_path: str, file_hash: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM chunks WHERE file_path=? AND file_hash=? LIMIT 1",
            (file_path, file_hash),
        )
        return cur.fetchone() is not None

    def remove_file(self, file_path: str):
        self._conn.execute("DELETE FROM chunks WHERE file_path=?", (file_path,))
        self._conn.commit()

    def insert_chunk(self, chunk_id: str, file_path: str, file_hash: str,
                     chunk_idx: int, content: str, embedding: bytes):
        self._conn.execute(
            "INSERT OR REPLACE INTO chunks VALUES (?,?,?,?,?,?,?)",
            (chunk_id, file_path, file_hash, chunk_idx, content, embedding, time.time()),
        )
        self._conn.commit()

    def all_embeddings(self) -> List[dict]:
        cur = self._conn.execute("SELECT chunk_id, file_path, content, embedding FROM chunks")
        results = []
        for row in cur:
            emb = json.loads(row["embedding"]) if row["embedding"] else []
            results.append({
                "chunk_id": row["chunk_id"],
                "file_path": row["file_path"],
                "content": row["content"],
                "embedding": emb,
            })
        return results

    @property
    def chunk_count(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) FROM chunks")
        return cur.fetchone()[0]

    @property
    def file_count(self) -> int:
        cur = self._conn.execute("SELECT COUNT(DISTINCT file_path) FROM chunks")
        return cur.fetchone()[0]

    def close(self):
        self._conn.close()


# ══════════════════════════════════════════════════════════════
# CHUNKER
# ══════════════════════════════════════════════════════════════

CHUNK_SIZE = 600      # chars per chunk
CHUNK_OVERLAP = 100   # overlap between chunks


def chunk_file(content: str, file_path: str) -> List[dict]:
    """Split a file into overlapping chunks with context headers."""
    lines = content.split("\n")
    text = content
    chunks = []
    start = 0
    idx = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        chunk_text = text[start:end]

        # Add file path header for context
        header = f"# FILE: {file_path}\n"
        chunk_with_header = header + chunk_text

        chunk_id = hashlib.sha256(
            f"{file_path}:{idx}:{chunk_text[:100]}".encode()
        ).hexdigest()[:16]

        chunks.append({
            "chunk_id": chunk_id,
            "index": idx,
            "content": chunk_with_header,
        })

        start = end - CHUNK_OVERLAP
        idx += 1

    return chunks


def hash_file(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════
# OLLAMA EMBEDDINGS
# ══════════════════════════════════════════════════════════════

EMBED_MODEL = "nomic-embed-text"  # 274MB, purpose-built for embeddings


def ollama_embed(text: str, model: str = EMBED_MODEL,
                 base_url: str = "http://localhost:11434") -> List[float]:
    """Get embeddings from Ollama's /api/embed endpoint."""
    import urllib.request

    payload = json.dumps({
        "model": model,
        "input": text[:2000],
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            embeddings = result.get("embeddings", [[]])
            return embeddings[0] if embeddings else []
    except Exception:
        # Fallback: simple keyword vector
        return _keyword_embed(text)


def _keyword_embed(text: str) -> List[float]:
    """Fallback: keyword-based embedding when Ollama embed fails."""
    words = set(text.lower().split())
    vocab = [
        "class", "def", "return", "self", "import", "from", "if", "else",
        "for", "while", "try", "except", "with", "as", "in", "not", "and",
        "or", "none", "true", "false", "list", "dict", "str", "int", "float",
        "file", "path", "read", "write", "open", "close", "data", "json",
        "error", "log", "test", "assert", "init", "config", "run", "start",
        "stop", "create", "update", "delete", "get", "set", "send", "process",
        "parse", "build", "check", "validate", "result", "output", "input",
        "request", "response", "server", "client", "connect", "async", "await",
        "gate", "tool", "agent", "soul", "envelope", "audit", "pipeline",
    ]
    return [1.0 if v in words else 0.0 for v in vocab]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ══════════════════════════════════════════════════════════════
# RAG ENGINE
# ══════════════════════════════════════════════════════════════

class OmegaRAG:
    """Offline RAG engine for Omega Claw.

    Usage:
        rag = OmegaRAG("/path/to/workspace")
        rag.index()
        context = rag.retrieve("how does the gate pipeline work?")
    """

    EXCLUDE_DIRS = {
        "__pycache__", ".git", ".venv", "venv", "node_modules",
        ".pytest_cache", ".mypy_cache", "dist", "build", ".eggs",
    }

    def __init__(self, workspace: str, embed_model: str = EMBED_MODEL,
                 ollama_url: str = "http://localhost:11434"):
        self._workspace = Path(workspace).resolve()
        self._embed_model = embed_model
        self._ollama_url = ollama_url
        self._db_path = str(self._workspace / DB_NAME)
        self._db = ChunkDB(self._db_path)

    def index(self, force: bool = False) -> dict:
        """Index all Python files in the workspace.

        Returns: {"files": N, "chunks": N, "skipped": N, "new": N}
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
                rel_path = os.path.relpath(fpath, self._workspace)
                files_found += 1

                try:
                    content = Path(fpath).read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue

                fhash = hash_file(content)

                # Skip if already indexed with same hash
                if not force and self._db.has_file(rel_path, fhash):
                    skipped += 1
                    continue

                # Remove old chunks for this file
                self._db.remove_file(rel_path)

                # Chunk and embed
                chunks = chunk_file(content, rel_path)
                for chunk in chunks:
                    embedding = ollama_embed(
                        chunk["content"], self._embed_model, self._ollama_url
                    )
                    self._db.insert_chunk(
                        chunk_id=chunk["chunk_id"],
                        file_path=rel_path,
                        file_hash=fhash,
                        chunk_idx=chunk["index"],
                        content=chunk["content"],
                        embedding=json.dumps(embedding),
                    )
                    chunks_created += 1

        return {
            "files": files_found,
            "chunks": chunks_created,
            "skipped": skipped,
            "new": chunks_created,
            "total_chunks": self._db.chunk_count,
            "total_files": self._db.file_count,
        }

    def retrieve(self, query: str, top_k: int = 5) -> str:
        """Retrieve the most relevant code chunks for a query."""
        query_embedding = ollama_embed(query, self._embed_model, self._ollama_url)
        all_chunks = self._db.all_embeddings()

        if not all_chunks:
            return "[NO INDEXED CODE — run /index first]"

        # Score by cosine similarity
        scored = []
        for chunk in all_chunks:
            sim = cosine_similarity(query_embedding, chunk["embedding"])
            scored.append((sim, chunk))

        scored.sort(key=lambda x: -x[0])
        top = scored[:top_k]

        # Build context string
        parts = [f"[RETRIEVED CODE — {len(top)} chunks, query: \"{query[:60]}\"]"]
        for score, chunk in top:
            parts.append(f"\n--- (relevance: {score:.3f}) ---")
            parts.append(chunk["content"])

        return "\n".join(parts)

    @property
    def stats(self) -> dict:
        return {
            "total_chunks": self._db.chunk_count,
            "total_files": self._db.file_count,
            "db_path": self._db_path,
            "db_size_kb": round(os.path.getsize(self._db_path) / 1024, 1)
            if os.path.exists(self._db_path) else 0,
        }

    def close(self):
        self._db.close()
