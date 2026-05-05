#!/usr/bin/env python3
"""
cb — The Coder Bible CLI
Pure FTS5 sovereign search. Zero AI. Zero network.
Usage: cb "query" [options]
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime

# Force UTF-8 on Windows to avoid cp1252 codec errors
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("cp1252", "ascii"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB   = os.path.join(SCRIPT_DIR, "coders_bible.db")
PERSONAL_DIR = os.path.expanduser("~/.coders-bible")
PERSONAL_DB  = os.path.join(PERSONAL_DIR, "personal.db")
CONFIG_FILE  = os.path.join(PERSONAL_DIR, "config.json")

DOMAIN_ALIASES = {
    "py": "python", "js": "javascript", "ts": "typescript",
    "k8s": "kubernetes", "cs": "csharp", "cpp": "c++",
    "sh": "bash", "shell": "bash", "rb": "ruby",
    "tf": "terraform", "go": "golang",
}

VERSION_PATTERNS = [
    (r"python\s*3\.(\d+)",         "python/3.{}"),
    (r"c#\s*(\d+)",                "csharp/{}"),
    (r"kotlin\s*(\d+\.\d+)",       "kotlin/{}"),
    (r"node\s*(\d+)",              "javascript/node{}"),
    (r"java\s*(\d+)",              "java/{}"),
    (r"rust\s*(\d{4})",            "rust/{}"),
]

# ── Rich / Plain fallback ─────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.rule import Rule
    from rich.syntax import Syntax
    from rich import print as rprint
    RICH = True
    console = Console()
except ImportError:
    RICH = False
    console = None

def bold(s):   return f"\033[1m{s}\033[0m" if not RICH else s
def dim(s):    return f"\033[2m{s}\033[0m"  if not RICH else s
def green(s):  return f"\033[92m{s}\033[0m" if not RICH else s
def yellow(s): return f"\033[93m{s}\033[0m" if not RICH else s
def cyan(s):   return f"\033[96m{s}\033[0m" if not RICH else s
def red(s):    return f"\033[91m{s}\033[0m" if not RICH else s

# ── DB helpers ────────────────────────────────────────────────────────────────
def open_db(path, init=False):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    if init:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS fragments (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT,
                tier TEXT DEFAULT 'B',
                ingested_at TEXT,
                ftype TEXT DEFAULT 'personal',
                lang_version TEXT,
                tags TEXT
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS bible_fts
                USING fts5(content, source, tokenize='porter ascii');
        """)
        conn.commit()
    return conn

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"db": DEFAULT_DB, "default_domain": None, "results": 5}

def save_config(cfg):
    os.makedirs(PERSONAL_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

# ── Core search ───────────────────────────────────────────────────────────────
def search(query, db_path, domain=None, ftype=None, version=None, limit=5):
    conn = open_db(db_path)
    # Build FTS5 query — sanitize for porter tokenizer
    safe_q = re.sub(r'[^\w\s]', ' ', query).strip()
    words  = [w for w in safe_q.split() if len(w) > 1]
    fts_q  = " OR ".join(f'"{w}"' for w in words) if words else safe_q

    try:
        # Step 1: get matching rowids + scores from FTS
        fts_rows = conn.execute(
            "SELECT rowid, bm25(bible_fts) AS score FROM bible_fts WHERE bible_fts MATCH ? ORDER BY score LIMIT ?",
            (fts_q, limit * 10)
        ).fetchall()

        if not fts_rows:
            conn.close()
            return []

        rowid_score = {r[0]: r[1] for r in fts_rows}
        rowids = list(rowid_score.keys())

        # Step 2: fetch fragments by rowid with optional filters
        placeholders = ",".join("?" * len(rowids))
        extra = ""
        extra_params = []

        if domain:
            d = DOMAIN_ALIASES.get(domain.lower(), domain.lower())
            extra += " AND LOWER(source) LIKE ?"
            extra_params.append(f"%{d}%")
        if ftype:
            extra += " AND ftype = ?"
            extra_params.append(ftype)
        if version:
            extra += " AND lang_version LIKE ?"
            extra_params.append(f"%{version}%")

        sql = f"""
            SELECT rowid, id, content, source, ftype, tier, lang_version
            FROM fragments
            WHERE rowid IN ({placeholders}){extra}
            LIMIT ?
        """
        rows = conn.execute(sql, rowids + extra_params + [limit]).fetchall()
        # Sort by FTS score (lower bm25 = better match)
        rows = sorted(rows, key=lambda r: rowid_score.get(r[0], 0))

    except sqlite3.OperationalError:
        # Fallback: plain LIKE search
        like_q = f"%{query}%"
        extra = "AND LOWER(source) LIKE ?" if domain else ""
        d_param = [f"%{DOMAIN_ALIASES.get(domain.lower(), domain.lower())}%"] if domain else []
        rows = conn.execute(
            f"SELECT rowid, id, content, source, ftype, tier, lang_version FROM fragments WHERE content LIKE ? {extra} LIMIT ?",
            [like_q] + d_param + [limit]
        ).fetchall()

    conn.close()
    return rows

def search_personal(query, domain=None, ftype=None, limit=5):
    if not os.path.exists(PERSONAL_DB):
        return []
    return search(query, PERSONAL_DB, domain=domain, ftype=ftype, limit=limit)

# ── Version auto-tag ──────────────────────────────────────────────────────────
def detect_version(content, source):
    text = (content + " " + (source or "")).lower()
    for pattern, fmt in VERSION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return fmt.format(m.group(1))
            except Exception:
                return None
    return None

# ── Display ───────────────────────────────────────────────────────────────────
FTYPE_BADGE = {
    "doc":      "[DOC]",
    "gotcha":   "[!! GOTCHA]",
    "recipe":   "[>> RECIPE]",
    "personal": "[* MINE]",
}

def domain_from_source(source):
    if not source: return "unknown"
    parts = source.split("/")
    return parts[0].upper() if parts else source.upper()

def render_result(i, row, raw=False):
    content = row["content"]
    source  = row["source"] or ""
    ftype   = row["ftype"]  or "doc"
    version = row["lang_version"] or ""
    domain  = domain_from_source(source)
    badge   = FTYPE_BADGE.get(ftype, "[DOC]")
    ver_tag = f" · {version}" if version else ""

    if raw:
        print(f"--- Result {i+1} [{domain}]{ver_tag} ---")
        print(content)
        print()
        return

    if RICH:
        title = f"[bold cyan]{i+1}.[/bold cyan] [yellow]{badge}[/yellow] [dim]{domain}{ver_tag}[/dim]"
        # detect code blocks and highlight
        if "```" in content or content.strip().startswith(("def ", "class ", "func ", "import ", "#include", "const ", "let ", "var ")):
            lang = domain.lower()
            panel_content = Syntax(content, lang, theme="monokai", word_wrap=True, line_numbers=False)
        else:
            panel_content = Text(content, overflow="fold")
        console.print(Panel(panel_content, title=title, border_style="bright_black", expand=False))
        console.print(f"  [dim]{source}[/dim]\n")
    else:
        sep = "─" * 60
        print(f"\n{sep}")
        print(f"{bold(f'  {i+1}.')} {yellow(badge)} {cyan(domain)}{ver_tag}")
        print(sep)
        print(content[:800] + ("…" if len(content) > 800 else ""))
        print(dim(f"  ↳ {source}"))

def render_header(query, total, elapsed_ms, domain=None, ftype=None, version=None):
    filters = []
    if domain:  filters.append(f"domain={domain}")
    if ftype:   filters.append(f"type={ftype}")
    if version: filters.append(f"ver={version}")
    filter_str = "  ·  ".join(filters)

    if RICH:
        console.print(Rule(f"[bold]The Coder Bible[/bold] · [cyan]{query}[/cyan]", style="bright_black"))
        meta = f"[dim]{total} results · {elapsed_ms:.0f}ms"
        if filter_str: meta += f" · {filter_str}"
        meta += "[/dim]"
        console.print(meta)
    else:
        print(f"\n{'='*60}")
        print(f"  The Coder Bible  ·  {bold(query)}")
        print(f"  {total} results · {elapsed_ms:.0f}ms" + (f" · {filter_str}" if filter_str else ""))
        print(f"{'='*60}")

def render_no_results(query):
    if RICH:
        console.print(f"[yellow]No results for:[/yellow] [bold]{query}[/bold]")
        console.print("[dim]Try: cb --list-domains  |  cb --domain <lang> <query>[/dim]")
    else:
        print(f"\nNo results for: {bold(query)}")
        print("Try: cb --list-domains  |  cb --domain <lang> <query>")

# ── Commands ──────────────────────────────────────────────────────────────────
def cmd_search(args):
    cfg    = get_config()
    query  = " ".join(args.query)
    domain = args.domain or cfg.get("default_domain")
    limit  = args.limit or cfg.get("results", 5)
    use_json = getattr(args, "json", False)

    t0 = time.perf_counter()

    # Personal first
    personal = search_personal(query, domain=domain, limit=2) if not args.no_personal else []

    # Main DB
    db_path = cfg.get("db", DEFAULT_DB)
    results = search(query, db_path, domain=domain, ftype=args.ftype, version=args.version, limit=limit)

    elapsed = (time.perf_counter() - t0) * 1000
    total   = len(personal) + len(results)

    # ── JSON output mode (for VS Code extension / automation) ──────────────
    if use_json:
        out = []
        for r in personal:
            d = dict(r); d["ftype"] = "personal"
            d["domain"] = domain_from_source(d.get("source", "")).lower()
            out.append(d)
        for r in results:
            d = dict(r)
            d["domain"] = domain_from_source(d.get("source", "")).lower()
            out.append(d)
        print(json.dumps(out, ensure_ascii=False))
        return

    if args.raw:
        for i, r in enumerate(personal): render_result(i, r, raw=True)
        for i, r in enumerate(results):  render_result(i + len(personal), r, raw=True)
        return

    if total == 0:
        render_no_results(query)
        return

    render_header(query, total, elapsed, domain=args.domain, ftype=args.ftype, version=args.version)

    offset = 0
    for r in personal:
        render_result(offset, dict(r) | {"ftype": "personal"}, raw=False)
        offset += 1
    for r in results:
        render_result(offset, r, raw=False)
        offset += 1

def cmd_add(args):
    content = " ".join(args.content)
    if not content.strip():
        print("Error: content cannot be empty"); sys.exit(1)

    conn   = open_db(PERSONAL_DB, init=True)
    fid    = hashlib.sha256(content.encode()).hexdigest()[:16]
    domain = args.domain or "general"
    tags   = args.tag or ""
    ver    = args.version or detect_version(content, domain)

    conn.execute(
        "INSERT OR IGNORE INTO fragments (id,content,source,tier,ingested_at,ftype,lang_version,tags) VALUES(?,?,?,?,?,?,?,?)",
        (fid, content, f"personal/{domain}", "A", datetime.now().isoformat(), "personal", ver, tags)
    )
    try:
        conn.execute("INSERT INTO bible_fts(rowid,content,source) SELECT rowid,content,source FROM fragments WHERE id=?", (fid,))
    except Exception:
        pass
    conn.commit()
    conn.close()

    if RICH:
        console.print(f"[green]OK[/green] Added to personal layer - id=[cyan]{fid}[/cyan]")
    else:
        print(f"OK  Added - id={fid}")

def cmd_list_domains(args):
    cfg  = get_config()
    conn = open_db(cfg.get("db", DEFAULT_DB))
    rows = conn.execute("""
        SELECT SUBSTR(source, 1, INSTR(source||'/', '/')-1) AS domain,
               COUNT(*) AS cnt
        FROM fragments
        GROUP BY domain
        ORDER BY cnt DESC
    """).fetchall()
    conn.close()

    if getattr(args, "json", False):
        data = [{"domain": r["domain"], "count": r["cnt"]} for r in rows]
        print(json.dumps(data, ensure_ascii=False))
        return

    if RICH:
        console.print(Rule("[bold]The Coder Bible — Domains[/bold]", style="bright_black"))
        from rich.table import Table
        t = Table(show_header=True, header_style="bold cyan")
        t.add_column("Domain", style="cyan")
        t.add_column("Fragments", justify="right")
        for r in rows:
            t.add_row(r["domain"], f"{r['cnt']:,}")
        console.print(t)
    else:
        print(f"\n{'Domain':<25} {'Fragments':>10}")
        print("─" * 37)
        for r in rows:
            print(f"{r['domain']:<25} {r['cnt']:>10,}")

def cmd_export(args):
    if not os.path.exists(PERSONAL_DB):
        print("No personal snippets yet."); return
    conn  = open_db(PERSONAL_DB)
    rows  = conn.execute("SELECT * FROM fragments").fetchall()
    data  = [dict(r) for r in rows]
    dest  = args.file or "personal_export.json"
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Exported {len(data)} snippets → {dest}")
    conn.close()

def cmd_import(args):
    with open(args.file, encoding="utf-8") as f:
        data = json.load(f)
    conn = open_db(PERSONAL_DB, init=True)
    n = 0
    for item in data:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO fragments (id,content,source,tier,ingested_at,ftype,lang_version,tags) VALUES(?,?,?,?,?,?,?,?)",
                (item.get("id"), item.get("content"), item.get("source"), item.get("tier","A"),
                 item.get("ingested_at", datetime.now().isoformat()),
                 item.get("ftype","personal"), item.get("lang_version"), item.get("tags",""))
            )
            n += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    print(f"✓ Imported {n} snippets from {args.file}")

def cmd_stats(args):
    cfg  = get_config()
    conn = open_db(cfg.get("db", DEFAULT_DB))
    total = conn.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
    by_type = conn.execute("SELECT ftype, COUNT(*) as c FROM fragments GROUP BY ftype").fetchall()
    conn.close()

    p_total = 0
    if os.path.exists(PERSONAL_DB):
        pc = open_db(PERSONAL_DB)
        p_total = pc.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
        pc.close()

    use_json = getattr(args, "json", False)
    if use_json:
        # Build typed buckets for the extension sidebar
        buckets = {"total": total, "personal": p_total, "gotcha": 0, "recipe": 0, "doc": 0}
        for r in by_type:
            ftype = (r["ftype"] or "doc").lower()
            buckets[ftype] = r["c"]
        # Anything not gotcha/recipe/personal → doc
        for r in by_type:
            ftype = (r["ftype"] or "doc").lower()
            if ftype not in ("gotcha", "recipe", "doc", "personal"):
                buckets["doc"] = buckets.get("doc", 0) + r["c"]
        
        # Add dynamic domain breakdown
        conn = open_db(cfg.get("db", DEFAULT_DB))
        domains = conn.execute("SELECT SUBSTR(source, 1, INSTR(source, '/') - 1) as domain, COUNT(*) as c FROM fragments WHERE source LIKE '%@github.com' GROUP BY domain").fetchall()
        buckets["domains"] = {r["domain"]: r["c"] for r in domains if r["domain"]}
        conn.close()

        print(json.dumps(buckets, ensure_ascii=False))
        return

    if RICH:
        console.print(Rule("[bold]The Coder Bible — Stats[/bold]", style="bright_black"))
        console.print(f"  [cyan]Main DB:[/cyan]     [bold]{total:,}[/bold] fragments")
        for r in by_type:
            console.print(f"  [dim]{r['ftype'] or 'doc':>10}:[/dim]  {r['c']:,}")
        if p_total:
            console.print(f"  [cyan]Personal:[/cyan]    [bold]{p_total:,}[/bold] snippets")
    else:
        print(f"\nMain DB: {total:,} fragments")
        for r in by_type:
            print(f"  {r['ftype'] or 'doc':>10}: {r['c']:,}")
        if p_total:
            print(f"Personal: {p_total:,} snippets")

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    # --- Pre-route subcommands before argparse to avoid positional conflict ---
    SUBCMDS = {"add", "domains", "stats", "export", "import"}
    raw_args = sys.argv[1:]
    # If first non-flag arg is a known subcommand, let argparse handle normally
    first_pos = next((a for a in raw_args if not a.startswith("-")), None)
    use_sub = first_pos in SUBCMDS

    ap = argparse.ArgumentParser(
        prog="cb",
        description="The Coder Bible — sovereign developer search. Zero AI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cb "reverse a list python"
  cb -d python "list comprehension"
  cb -d k8s "rolling deployment"
  cb -t gotcha "javascript async"
  cb -t recipe "docker compose postgres"
  cb -v "python/3.12" "match statement"
  cb add "my custom tip" -d python --tag "async,gotcha"
  cb domains
  cb stats
  cb --raw "query"
        """
    )

    ap.add_argument("--domain",  "-d", help="Filter by domain (e.g. python, k8s, csharp)")
    ap.add_argument("--ftype",   "-t", choices=["doc","gotcha","recipe","personal"], help="Fragment type filter")
    ap.add_argument("--version", "-v", help="Language version filter (e.g. python/3.12)")
    ap.add_argument("--limit",   "-n", type=int, default=5, help="Max results (default: 5)")
    ap.add_argument("--raw",           action="store_true", help="Plain text output (pipe-friendly)")
    ap.add_argument("--no-personal",   action="store_true", help="Skip personal layer")
    ap.add_argument("--json",          action="store_true", help="JSON output (machine-readable, for IDE integrations)")

    if use_sub:
        sub = ap.add_subparsers(dest="cmd")
        p_add = sub.add_parser("add", help="Add snippet to personal layer")
        p_add.add_argument("content", nargs="+")
        p_add.add_argument("--domain",  "-d", default="general")
        p_add.add_argument("--tag",           default="")
        p_add.add_argument("--version", "-v", default=None)
        sub.add_parser("domains", help="List all domains with fragment counts")
        p_stats = sub.add_parser("stats",   help="Show database statistics")
        p_stats.add_argument("--json", action="store_true", help="JSON output")
        p_exp = sub.add_parser("export", help="Export personal snippets to JSON")
        p_exp.add_argument("--file", "-f", default="personal_export.json")
        p_imp = sub.add_parser("import", help="Import personal snippets from JSON")
        p_imp.add_argument("file")
        args = ap.parse_args()
        if args.cmd == "add":     cmd_add(args); return
        if args.cmd == "domains": cmd_list_domains(args); return
        if args.cmd == "stats":   cmd_stats(args); return
        if args.cmd == "export":  cmd_export(args); return
        if args.cmd == "import":  cmd_import(args); return
        ap.print_help()
        return

    # Search mode — all remaining args are the query
    ap.add_argument("query", nargs="*", help="Search query")
    args = ap.parse_args()

    if not args.query:
        ap.print_help()
        return

    cmd_search(args)

if __name__ == "__main__":
    main()
