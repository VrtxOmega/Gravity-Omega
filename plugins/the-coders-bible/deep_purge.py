"""
Deep purge: Remove ALL operational/project/session fragments from the Bible DB.
These are Omega Brain artifacts that leaked into the knowledge base.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "coders_bible.db")

# Patterns that identify operational data, NOT documentation
PURGE_PATTERNS = [
    # Project names / internal tools
    "%gravity%", "%omega%", "%aegis%", "%sovereign%",
    "%moltbook%", "%breakaway%", "%shiftforge%", "%hermes%",
    "%antigravity%", "%veritas%", "%constellation%",
    # Session / conversation artifacts
    "%project_index%", "%skill:%", "%conv_%",
    # Test/debug sources
    "%test%fixture%", "%debug%session%",
    # Internal session logs
    "%-session-%", "%-audit%",
]

# Safeguard: patterns that MUST NOT be purged even if they match above
# (legitimate docs that happen to contain a trigger word)
SAFE_SOURCE_PATTERNS = [
    "docs.python.org%",
    "doc.rust-lang%",
    "ruby-doc.org%",
    "php.net%",
    "nginx.org%",
    "man7.org%",
    "go.dev%",
    "kubernetes.io%",
    "docker.com%",
    "ansible.com%",
    "terraform.io%",
    "registry.terraform%",
    "typescriptlang.org%",
    "nodejs.org%",
    "developer.mozilla%",
    "postgresql.org%",
    "mysql.com%",
    "mariadb.com%",
    "sqlite.org%",
    "git-scm.com%",
    "freedesktop.org%",
    "gnu.org%",
    "tldp.org%",
    "learn.microsoft%",
    "docs.microsoft%",
    "w3.org%",
    "cppreference%",
    "devdocs.io%",
    "npmjs.com%",
]

def main():
    conn = sqlite3.connect(DB)
    
    # First: identify all sources that match purge patterns
    all_sources = conn.execute("SELECT DISTINCT source FROM fragments").fetchall()
    all_sources = [r[0] for r in all_sources]
    
    to_purge = set()
    for source in all_sources:
        sl = source.lower()
        # Check if it matches any purge pattern
        matches_purge = False
        for p in PURGE_PATTERNS:
            pattern = p.strip("%").lower()
            if pattern in sl:
                matches_purge = True
                break
        
        # Check if it's a safe documentation source
        is_safe = False
        for sp in SAFE_SOURCE_PATTERNS:
            safe_p = sp.strip("%").lower()
            if safe_p in sl:
                is_safe = True
                break
        
        if matches_purge and not is_safe:
            to_purge.add(source)
    
    print(f"Sources to purge: {len(to_purge)}")
    for s in sorted(to_purge):
        count = conn.execute("SELECT COUNT(*) FROM fragments WHERE source=?", (s,)).fetchone()[0]
        print(f"  [{count:4d}] {s}")
    
    # Count total to remove
    total_purge = 0
    for s in to_purge:
        total_purge += conn.execute("SELECT COUNT(*) FROM fragments WHERE source=?", (s,)).fetchone()[0]
    
    before = conn.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
    print(f"\nBefore: {before} fragments")
    print(f"Purging: {total_purge} fragments from {len(to_purge)} sources")
    
    # Delete
    for s in to_purge:
        conn.execute("DELETE FROM fragments WHERE source=?", (s,))
    conn.commit()
    
    after = conn.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
    print(f"After: {after} fragments")
    print(f"Removed: {before - after}")
    
    # Rebuild FTS index
    print("\nRebuilding FTS5 index...")
    try:
        conn.execute("DELETE FROM bible_fts")
    except:
        pass
    conn.execute("INSERT INTO bible_fts(bible_fts) VALUES('rebuild')")
    conn.commit()
    print("FTS5 index rebuilt.")
    
    # Verify no contamination remains
    print("\n=== VERIFICATION ===")
    remaining = []
    for p in PURGE_PATTERNS:
        pattern = p
        rows = conn.execute("SELECT DISTINCT source FROM fragments WHERE source LIKE ?", (pattern,)).fetchall()
        for r in rows:
            sl = r[0].lower()
            is_safe = any(sp.strip("%").lower() in sl for sp in SAFE_SOURCE_PATTERNS)
            if not is_safe:
                remaining.append(r[0])
    
    if remaining:
        print(f"WARNING: {len(remaining)} contaminated sources still remain:")
        for r in remaining:
            print(f"  {r}")
    else:
        print("CLEAN: Zero operational artifacts remain.")
    
    conn.close()

if __name__ == "__main__":
    main()
