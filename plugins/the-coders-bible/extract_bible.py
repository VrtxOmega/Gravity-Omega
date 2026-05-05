"""
Extract Bible fragments from omega_brain.db into a standalone coders_bible.db.
This separates the The Coder's Bible data from the Omega Brain operational database.
"""

import sqlite3
import os
import time

SRC_PATH = os.path.expanduser("~/.omega-brain/omega_brain.db")
DST_PATH = os.path.join(os.path.dirname(__file__), "coders_bible.db")

def main():
    print("=" * 60)
    print("CODER'S BIBLE -- Database Extraction")
    print("=" * 60)
    print(f"Source: {SRC_PATH}")
    print(f"Target: {DST_PATH}")
    print()

    # --- Verify source ---
    if not os.path.exists(SRC_PATH):
        print("ERROR: Source database not found!")
        return

    src = sqlite3.connect(SRC_PATH)
    src.row_factory = sqlite3.Row

    # Show what's in omega_brain
    tables = [r[0] for r in src.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    print(f"Omega Brain tables: {tables}")

    frag_count = src.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
    print(f"Fragment count: {frag_count}")

    if frag_count == 0:
        print("ERROR: No fragments found in source!")
        src.close()
        return

    # Sample a few sources to verify
    sources = src.execute(
        "SELECT DISTINCT source FROM fragments LIMIT 10"
    ).fetchall()
    print(f"Sample sources: {[r[0][:60] for r in sources]}")
    print()

    # --- Create standalone database ---
    if os.path.exists(DST_PATH):
        backup = DST_PATH + ".bak"
        print(f"Backing up existing: {backup}")
        os.rename(DST_PATH, backup)

    dst = sqlite3.connect(DST_PATH)

    # Create fragments table (Bible-only schema, no embeddings)
    dst.execute("""
        CREATE TABLE IF NOT EXISTS fragments (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            source TEXT DEFAULT '',
            tier TEXT DEFAULT 'B',
            ingested_at TEXT DEFAULT ''
        )
    """)

    # Bulk copy all fragments
    print(f"Extracting {frag_count} fragments...")
    t0 = time.time()

    batch_size = 5000
    offset = 0
    total_copied = 0

    while True:
        rows = src.execute(
            "SELECT id, content, source, tier, ingested_at FROM fragments LIMIT ? OFFSET ?",
            (batch_size, offset)
        ).fetchall()

        if not rows:
            break

        dst.executemany(
            "INSERT OR IGNORE INTO fragments (id, content, source, tier, ingested_at) VALUES (?, ?, ?, ?, ?)",
            [(r[0], r[1], r[2], r[3], r[4]) for r in rows]
        )
        total_copied += len(rows)
        offset += batch_size
        print(f"  ... {total_copied}/{frag_count}")

    dst.commit()
    elapsed = time.time() - t0
    print(f"Copied {total_copied} fragments in {elapsed:.1f}s")
    print()

    # --- Build FTS5 index ---
    print("Building FTS5 index...")
    t1 = time.time()

    dst.execute("DROP TABLE IF EXISTS bible_fts")
    dst.execute("""
        CREATE VIRTUAL TABLE bible_fts USING fts5(
            content,
            source,
            content='fragments',
            content_rowid='rowid'
        )
    """)

    # Populate FTS
    dst.execute("""
        INSERT INTO bible_fts(rowid, content, source)
        SELECT rowid, content, source FROM fragments
    """)
    dst.commit()

    fts_count = dst.execute("SELECT COUNT(*) FROM bible_fts").fetchone()[0]
    elapsed2 = time.time() - t1
    print(f"FTS5 indexed {fts_count} fragments in {elapsed2:.1f}s")
    print()

    # --- Create INSERT trigger for future additions ---
    dst.execute("""
        CREATE TRIGGER IF NOT EXISTS fragments_ai AFTER INSERT ON fragments BEGIN
            INSERT INTO bible_fts(rowid, content, source)
            VALUES (new.rowid, new.content, new.source);
        END
    """)
    dst.commit()
    print("INSERT trigger installed for auto-indexing.")

    # --- Integrity check ---
    result = dst.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"Integrity check: {result}")

    # --- Final stats ---
    db_size = os.path.getsize(DST_PATH)
    final_count = dst.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
    fts_final = dst.execute("SELECT COUNT(*) FROM bible_fts").fetchone()[0]

    print()
    print("=" * 60)
    print("EXTRACTION COMPLETE")
    print(f"  Fragments: {final_count}")
    print(f"  FTS5 indexed: {fts_final}")
    print(f"  Database size: {db_size / (1024*1024):.1f} MB")
    print(f"  Location: {DST_PATH}")
    print(f"  Omega Brain: UNTOUCHED")
    print("=" * 60)

    src.close()
    dst.close()


if __name__ == "__main__":
    main()
