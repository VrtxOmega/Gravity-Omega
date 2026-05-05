"""Audit coders_bible.db to identify internal/operational Omega Brain fragments."""
import sqlite3

db = sqlite3.connect("coders_bible.db")

# Top 50 sources by frequency
rows = db.execute(
    "SELECT source, COUNT(*) as cnt FROM fragments GROUP BY source ORDER BY cnt DESC LIMIT 50"
).fetchall()

print("=" * 70)
print("TOP 50 SOURCES BY FRAGMENT COUNT")
print("=" * 70)
for src, cnt in rows:
    flag = ""
    if any(x in src for x in ["veritas", "aegis", "omega", "test_", "qa", "debug", "watermark", "struct_src", "only_source", "source_x", "source_y", "tier_a_src", "code-review"]):
        flag = "  <-- INTERNAL"
    print(f"  {cnt:>6}  {src[:70]}{flag}")

# Count clearly internal fragments
internal_patterns = [
    "veritas%", "aegis%", "omega%", "test_%", "qa", "debug%",
    "struct_src", "only_source", "source_x", "source_y", "tier_a_src",
    "code-review", "user-session"
]

where_clauses = " OR ".join([f"source LIKE '{p}'" for p in internal_patterns])
internal_count = db.execute(f"SELECT COUNT(*) FROM fragments WHERE {where_clauses}").fetchone()[0]

total = db.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]

print()
print("=" * 70)
print(f"TOTAL FRAGMENTS:    {total}")
print(f"INTERNAL/JUNK:      {internal_count}")
print(f"CLEAN DOC FRAGS:    {total - internal_count}")
print("=" * 70)

# Sample internal ones
print()
print("SAMPLE INTERNAL FRAGMENTS:")
print("-" * 70)
samples = db.execute(f"SELECT source, substr(content, 1, 120) FROM fragments WHERE {where_clauses} LIMIT 20").fetchall()
for src, txt in samples:
    print(f"  [{src}]")
    print(f"  {txt}")
    print()

db.close()
