"""
Purge internal Omega Brain operational data from coders_bible.db.
These are test fixtures, vault session notes, and debug entries — NOT code documentation.
"""
import sqlite3

db = sqlite3.connect("coders_bible.db")

# Internal/operational source patterns to remove
PURGE_PATTERNS = [
    "test_a", "test_b", "only_source", "source_x", "source_y",
    "tier_a_src", "qa", "struct_src", "code-review", "user-session",
]

PURGE_LIKE = [
    "veritas_vault%",
    "aegis-%",
    "omega%",
    "debug%",
]

# Build DELETE query
conditions = []
for exact in PURGE_PATTERNS:
    conditions.append(f"source = '{exact}'")
for like in PURGE_LIKE:
    conditions.append(f"source LIKE '{like}'")

where = " OR ".join(conditions)

# Count before
before = db.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
purge_count = db.execute(f"SELECT COUNT(*) FROM fragments WHERE {where}").fetchone()[0]

print(f"Total fragments:  {before}")
print(f"To purge:         {purge_count}")
print()

# Show what's being purged
rows = db.execute(f"SELECT source, substr(content, 1, 80) FROM fragments WHERE {where}").fetchall()
for src, txt in rows:
    # Sanitize for cp1252 console
    safe_txt = txt.encode("ascii", errors="replace").decode("ascii")
    print(f"  DEL [{src}] {safe_txt}")

print()

# Delete
db.execute(f"DELETE FROM fragments WHERE {where}")
db.commit()

after = db.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
print(f"After purge:      {after}")
print(f"Removed:          {before - after}")

# Rebuild FTS5 index
print()
print("Rebuilding FTS5 index...")
db.execute("DROP TABLE IF EXISTS bible_fts")
db.execute("""
    CREATE VIRTUAL TABLE bible_fts USING fts5(
        content,
        source,
        content='fragments',
        content_rowid='rowid'
    )
""")
db.execute("""
    INSERT INTO bible_fts(rowid, content, source)
    SELECT rowid, content, source FROM fragments
""")

# Recreate trigger
db.execute("DROP TRIGGER IF EXISTS fragments_ai")
db.execute("""
    CREATE TRIGGER fragments_ai AFTER INSERT ON fragments BEGIN
        INSERT INTO bible_fts(rowid, content, source)
        VALUES (new.rowid, new.content, new.source);
    END
""")
db.commit()

fts_count = db.execute("SELECT COUNT(*) FROM bible_fts").fetchone()[0]
print(f"FTS5 re-indexed:  {fts_count}")

# Verify no internal sources remain
remaining = db.execute(f"SELECT COUNT(*) FROM fragments WHERE {where}").fetchone()[0]
print(f"Remaining junk:   {remaining}")

print()
print("PURGE COMPLETE.")
db.close()
