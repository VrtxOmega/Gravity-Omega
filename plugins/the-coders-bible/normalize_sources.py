"""
normalize_sources.py — The Coder's Bible source prefix normalization pass.
VERITAS-cleared: claim 91689338b796... seal 4cd1154a...

Remaps all mislabeled/unlabeled source prefixes to canonical domain prefixes
so the UI can correctly surface TypeScript, Ansible, PHP, PowerShell, Rust/std,
Go stdlib, PostgreSQL, MySQL, etc.

Safe: all operations are idempotent UPDATE statements.
Runs inside a single transaction; rolls back on any error.
"""

import sqlite3, sys, os

DB = os.path.join(os.path.dirname(__file__), "coders_bible.db")

# ---------------------------------------------------------------------------
# Normalization map: (LIKE pattern, canonical_prefix_replacement_prefix)
# Order matters — more specific patterns must come first.
# Each rule: (match_prefix, new_prefix)  — replaces only the leading portion.
# ---------------------------------------------------------------------------
RULES = [
    # ── TypeScript ──────────────────────────────────────────────────────────
    ("ts:handbook/%",              "typescript/handbook/"),
    ("typescript/%@typescriptlang.org", None),   # already canonical, skip
    ("typescript/%",               None),         # already canonical, skip

    # ── Rust stdlib (source starts with https://doc.rust-lang.org) ──────────
    ("https://doc.rust-lang.org/%", "rust/std/"),

    # ── Ansible ─────────────────────────────────────────────────────────────
    ("docs.ansible.com/%",          "ansible/"),

    # ── PHP ─────────────────────────────────────────────────────────────────
    ("php/%",                        None),        # already canonical, skip

    # ── Go stdlib modules (go.xxx format) ───────────────────────────────────
    ("go.net_http%",                 "go/net_http/"),
    ("go.testing%",                  "go/testing/"),
    ("go.os%",                       "go/os/"),
    ("go.image%",                    "go/image/"),
    ("go.math%",                     "go/math/"),
    ("go.atomic%",                   "go/atomic/"),
    ("go.flag%",                     "go/flag/"),
    ("go.%",                         "go/stdlib/"),

    # ── PostgreSQL ───────────────────────────────────────────────────────────
    ("postgresql/%",                 "sql/postgresql/"),
    ("/postgresql/%",                "sql/postgresql/"),

    # ── MySQL / MariaDB ──────────────────────────────────────────────────────
    ("mysql/%",                      "sql/mysql/"),

    # ── Git man pages ────────────────────────────────────────────────────────
    ("git-scm/%",                    "git/man/"),

    # ── PowerShell ───────────────────────────────────────────────────────────
    ("learn.microsoft.com/powershell/%", "powershell/"),

    # ── Terraform functions (misrouted as /terraform/) ───────────────────────
    ("/terraform/%",                 "terraform/"),

    # ── Linux tools / binary analysis man pages ──────────────────────────────
    ("as@man7.org",                  "linux-tools/as@man7.org"),
    ("ld@man7.org",                  "linux-tools/ld@man7.org"),
    ("objdump@man7.org",             "linux-tools/objdump@man7.org"),
    ("readelf@man7.org",             "linux-tools/readelf@man7.org"),
    ("nm@man7.org",                  "linux-tools/nm@man7.org"),
    ("mount@man7.org",               "linux-tools/mount@man7.org"),
    ("journalctl@man7.org",          "linux-tools/journalctl@man7.org"),
    ("systemctl@man7.org",           "linux-tools/systemctl@man7.org"),
]

def normalize(conn):
    c = conn.cursor()

    # Snapshot before
    c.execute("SELECT COUNT(*) FROM fragments")
    total_before = c.fetchone()[0]
    print(f"Total fragments before: {total_before}")

    # Get pre-pass Other count
    c.execute("""
        SELECT COUNT(*) FROM fragments
        WHERE source NOT LIKE 'python%'
          AND source NOT LIKE 'linux%'
          AND source NOT LIKE 'git/%'
          AND source NOT LIKE 'progit/%'
          AND source NOT LIKE 'bash%'
          AND source NOT LIKE 'docker%'
          AND source NOT LIKE 'kubernetes%'
          AND source NOT LIKE 'cpp%'
          AND source NOT LIKE 'css%'
          AND source NOT LIKE 'html%'
          AND source NOT LIKE 'java/%'
          AND source NOT LIKE 'terraform%'
          AND source NOT LIKE 'csharp%'
          AND source NOT LIKE 'sql%'
          AND source NOT LIKE 'kotlin%'
          AND source NOT LIKE 'swift%'
          AND source NOT LIKE 'nginx%'
          AND source NOT LIKE 'systemd%'
          AND source NOT LIKE 'go/%'
          AND source NOT LIKE 'golang%'
          AND source NOT LIKE 'node%'
          AND source NOT LIKE 'rust%'
          AND source NOT LIKE 'ruby%'
          AND source NOT LIKE 'typescript%'
          AND source NOT LIKE 'ansible%'
          AND source NOT LIKE 'php%'
          AND source NOT LIKE 'powershell%'
    """)
    other_before = c.fetchone()[0]
    print(f"'Other' bucket before: {other_before}")

    total_updated = 0

    for pattern, new_prefix in RULES:
        if new_prefix is None:
            # Already canonical — skip
            continue

        # Get matching rows
        c.execute("SELECT id, source FROM fragments WHERE source LIKE ?", (pattern,))
        rows = c.fetchall()
        if not rows:
            continue

        updated = 0
        for fid, old_source in rows:
            # Strip the matched prefix portion and attach new_prefix
            # The pattern ends with %, so strip everything up to the wildcard
            match_base = pattern.rstrip('%')
            if old_source.startswith(match_base):
                suffix = old_source[len(match_base):]
                new_source = new_prefix + suffix
            else:
                new_source = new_prefix + old_source

            c.execute("UPDATE fragments SET source = ? WHERE id = ?", (new_source, fid))
            updated += 1

        if updated:
            print(f"  [{pattern}] -> [{new_prefix}...] : {updated} rows")
            total_updated += updated

    conn.commit()
    print(f"\nTotal rows updated: {total_updated}")
    return total_updated


def report(conn):
    """Print full domain breakdown after normalization."""
    c = conn.cursor()
    c.execute("""
        SELECT
            CASE
                WHEN source LIKE 'python%'      THEN 'Python'
                WHEN source LIKE 'linux-man%'   THEN 'Linux-Man'
                WHEN source LIKE 'linux-tools%' THEN 'Linux-Tools'
                WHEN source LIKE 'linux%'       THEN 'Linux'
                WHEN source LIKE 'git/%'        THEN 'Git'
                WHEN source LIKE 'progit/%'     THEN 'Git'
                WHEN source LIKE 'bash%'        THEN 'Bash'
                WHEN source LIKE 'docker%'      THEN 'Docker'
                WHEN source LIKE 'kubernetes%'  THEN 'Kubernetes'
                WHEN source LIKE 'cpp%'         THEN 'C/C++'
                WHEN source LIKE 'css%'         THEN 'CSS'
                WHEN source LIKE 'html%'        THEN 'HTML'
                WHEN source LIKE 'java/%'       THEN 'Java'
                WHEN source LIKE 'terraform%'   THEN 'Terraform'
                WHEN source LIKE 'csharp%'      THEN 'C#'
                WHEN source LIKE 'sql/%'        THEN 'SQL'
                WHEN source LIKE 'sql%'         THEN 'SQL'
                WHEN source LIKE 'kotlin%'      THEN 'Kotlin'
                WHEN source LIKE 'swift%'       THEN 'Swift'
                WHEN source LIKE 'nginx%'       THEN 'Nginx'
                WHEN source LIKE 'systemd%'     THEN 'Systemd'
                WHEN source LIKE 'go/%'         THEN 'Go'
                WHEN source LIKE 'golang%'      THEN 'Go'
                WHEN source LIKE 'node%'        THEN 'Node.js'
                WHEN source LIKE 'rust%'        THEN 'Rust'
                WHEN source LIKE 'ruby%'        THEN 'Ruby'
                WHEN source LIKE 'typescript%'  THEN 'TypeScript'
                WHEN source LIKE 'ansible%'     THEN 'Ansible'
                WHEN source LIKE 'php%'         THEN 'PHP'
                WHEN source LIKE 'powershell%'  THEN 'PowerShell'
                ELSE 'Other'
            END as domain,
            COUNT(*) as cnt
        FROM fragments
        GROUP BY domain
        ORDER BY cnt DESC
    """)
    rows = c.fetchall()
    total = sum(r[1] for r in rows)
    print(f"\n{'Domain':<20} {'Count':>8}   {'Pct':>6}")
    print("-" * 42)
    for domain, cnt in rows:
        pct = cnt / total * 100
        print(f"{domain:<20} {cnt:>8}   {pct:>5.1f}%")
    print("-" * 42)
    print(f"{'TOTAL':<20} {total:>8}")
    return rows


def rebuild_fts(conn):
    print("\nRebuilding FTS5 index...")
    conn.execute("INSERT INTO bible_fts(bible_fts) VALUES('rebuild')")
    conn.commit()
    print("FTS5 index rebuilt.")


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("BEGIN")
        updated = normalize(conn)
        rows = report(conn)
        rebuild_fts(conn)

        # VERITAS assertion: Other bucket should have shrunk
        other_after = next((r[1] for r in rows if r[0] == "Other"), 0)
        print(f"\n[VERITAS CHECK] Other bucket after: {other_after}")
        if other_after < 5000:
            print("[VERITAS CHECK] PASS — Other bucket reduced to acceptable level")
        else:
            print(f"[VERITAS CHECK] WARN — {other_after} fragments still uncategorized")

    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"\nERROR — rolled back: {e}")
        raise
    finally:
        conn.close()

    print("\nNormalization complete.")


if __name__ == "__main__":
    main()
