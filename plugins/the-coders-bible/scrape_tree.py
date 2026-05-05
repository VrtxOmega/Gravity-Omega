"""
scrape_tree.py — The Coder Bible deep tree-walk scraper
Zero AI. Zero GitHub Auth API.
Uses the public unauthenticated git-trees endpoint:
  https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1
This endpoint is rate-limited at 60 req/hr without auth (we use it sparingly
— one call per repo to get the tree, then raw.githubusercontent.com for files).
The tree endpoint does NOT require a GitHub token.
"""
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime

import requests

DB      = os.path.join(os.path.dirname(__file__), "coders_bible.db")
RAW     = "https://raw.githubusercontent.com"
TREE_EP = "https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CodersBibleIndexer/3.0)",
           "Accept": "application/vnd.github.v3+json"}
DELAY   = 0.30
MIN_LEN = 80
MAX_LEN = 1800

# ── HTTP ─────────────────────────────────────────────────────────────────────
def fetch(url, retries=2):
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            if r.status_code in (403, 429):
                print(f"  RATE-LIMITED {url[:60]} — waiting 30s")
                time.sleep(30)
                continue
            if r.status_code == 404:
                return None
            r.raise_for_status()
            time.sleep(DELAY)
            return r.text
        except Exception as e:
            if attempt == retries:
                print(f"  SKIP {url[:70]}: {e}")
                return None
            time.sleep(1.5)
    return None

def fetch_tree(owner, repo):
    """Fetch full recursive file list for a repo. Returns list of path strings."""
    url  = TREE_EP.format(owner=owner, repo=repo)
    text = fetch(url)
    if not text:
        return []
    try:
        data = json.loads(text)
        return [item["path"] for item in data.get("tree", []) if item["type"] == "blob"]
    except Exception as e:
        print(f"  TREE parse error {owner}/{repo}: {e}")
        return []

def fetch_raw(owner, repo, branch, path):
    return fetch(f"{RAW}/{owner}/{repo}/{branch}/{path}")

# ── Text processing ───────────────────────────────────────────────────────────
def clean_python(code):
    """Extract docstrings + comments from Python source as readable text."""
    lines = code.splitlines()
    out   = []
    in_doc = False
    doc_delim = None
    for ln in lines:
        s = ln.strip()
        # Module/function/class docstrings
        if not in_doc:
            if s.startswith('"""') or s.startswith("'''"):
                delim = s[:3]
                if s.count(delim) >= 2 and len(s) > 6:
                    out.append(s.strip(delim).strip())
                else:
                    in_doc = True
                    doc_delim = delim
                    out.append(s[3:])
            elif s.startswith('#'):
                out.append(s.lstrip('#').strip())
            elif s.startswith('def ') or s.startswith('class ') or s.startswith('async def '):
                out.append(s)
        else:
            if doc_delim and doc_delim in s:
                out.append(s[:s.index(doc_delim)].strip())
                in_doc = False
            else:
                out.append(s)
    return "\n".join(ln for ln in out if ln.strip())

def chunk_text(text, ftype="recipe", max_len=MAX_LEN, min_len=MIN_LEN):
    text = text.strip()
    if not text:
        return []
    # For recipe/gotcha prefer heading splits
    if ftype in ("recipe", "gotcha"):
        parts = re.split(r'\n(?=#{1,4} )', text)
        chunks = [p.strip()[:max_len] for p in parts if len(p.strip()) >= min_len]
        if chunks:
            return chunks
    # Paragraph split fallback
    paras  = re.split(r'\n{2,}', text)
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) > max_len and cur:
            if len(cur) >= min_len:
                chunks.append(cur.strip())
            cur = p
        else:
            cur += ("\n\n" + p if cur else p)
    if cur.strip() and len(cur.strip()) >= min_len:
        chunks.append(cur.strip())
    return chunks

# ── DB ────────────────────────────────────────────────────────────────────────
def save(conn, frags):
    inserted = 0
    for f in frags:
        fid = hashlib.sha256(f["content"].encode()).hexdigest()[:16]
        cur = conn.execute(
            """INSERT OR IGNORE INTO fragments
               (id,content,source,tier,ingested_at,ftype,lang_version,tags)
               VALUES(?,?,?,?,?,?,?,?)""",
            (fid, f["content"], f["source"], f.get("tier","B"),
             datetime.now(datetime.timezone.utc if hasattr(datetime,'timezone') else None).isoformat()
             datetime.utcnow().isoformat(),
             f.get("ftype","recipe"), f.get("lang_version"), f.get("tags",""))
        )
        inserted += cur.rowcount
    conn.commit()
    return inserted

# ══════════════════════════════════════════════════════════════════════════════
# REPO WALK CONFIGS
# Each entry specifies what paths to collect inside the repo tree.
# ══════════════════════════════════════════════════════════════════════════════

TREE_SOURCES = [
    # ── TheAlgorithms/Python — individual algorithm .py files ──────────────
    {
        "owner": "TheAlgorithms", "repo": "Python", "branch": "master",
        "ftype": "recipe", "domain": "python", "tier": "A",
        "tags": "python,recipe,algorithm",
        "include_exts": [".py"],
        "include_patterns": [],          # any .py file
        "exclude_patterns": ["test_", "__init__", "conftest", ".github"],
        "max_files": 300,
        "extractor": "python_docstring",  # extract docstrings + signatures
        "description": "TheAlgorithms Python — algorithm implementations",
    },
    # ── TheAlgorithms/JavaScript — individual algorithm .js files ──────────
    {
        "owner": "TheAlgorithms", "repo": "JavaScript", "branch": "master",
        "ftype": "recipe", "domain": "javascript", "tier": "A",
        "tags": "javascript,recipe,algorithm",
        "include_exts": [".js", ".ts"],
        "include_patterns": [],
        "exclude_patterns": ["test", "__tests__", "node_modules", ".github"],
        "max_files": 200,
        "extractor": "raw",
        "description": "TheAlgorithms JavaScript — algorithm implementations",
    },
    # ── 30-seconds/30-seconds-of-python — per-snippet .md files ────────────
    {
        "owner": "30-seconds", "repo": "30-seconds-of-python", "branch": "master",
        "ftype": "recipe", "domain": "python", "tier": "A",
        "tags": "python,recipe,snippet,30seconds",
        "include_exts": [".md"],
        "include_patterns": ["snippets/"],
        "exclude_patterns": [],
        "max_files": 300,
        "extractor": "raw",
        "description": "30-seconds-of-python per-snippet markdown files",
    },
    # ── rust-unofficial/patterns — individual pattern .md files ────────────
    {
        "owner": "rust-unofficial", "repo": "patterns", "branch": "main",
        "ftype": "recipe", "domain": "rust", "tier": "A",
        "tags": "rust,recipe,pattern,idiom",
        "include_exts": [".md"],
        "include_patterns": ["src/patterns/", "src/idioms/", "src/anti_patterns/"],
        "exclude_patterns": ["SUMMARY.md", "README.md"],
        "max_files": 100,
        "extractor": "raw",
        "description": "rust-unofficial/patterns — design patterns per file",
    },
    # ── basarat/typescript-book — all .md topic files ───────────────────────
    {
        "owner": "basarat", "repo": "typescript-book", "branch": "master",
        "ftype": "gotcha", "domain": "typescript", "tier": "A",
        "tags": "typescript,javascript,gotcha,deepdive",
        "include_exts": [".md"],
        "include_patterns": ["docs/"],
        "exclude_patterns": ["README.md", "CONTRIBUTING.md"],
        "max_files": 200,
        "extractor": "raw",
        "description": "basarat/typescript-book — all topic .md files",
    },
    # ── nicowillis is 404 — skip. Use goldbergyoni/nodebestpractices sections
    # ── goldbergyoni/nodebestpractices — per section .md files ─────────────
    {
        "owner": "goldbergyoni", "repo": "nodebestpractices", "branch": "master",
        "ftype": "gotcha", "domain": "javascript", "tier": "A",
        "tags": "nodejs,javascript,gotcha,bestpractice",
        "include_exts": [".md"],
        "include_patterns": ["sections/"],
        "exclude_patterns": ["README.md"],
        "max_files": 150,
        "extractor": "raw",
        "description": "nodebestpractices — per section .md files",
    },
    # ── Bash-Oneliner — already full from README; add wiki .md if any ───────
    # ── kvz/bash3boilerplate — boilerplate + gotcha docs ────────────────────
    {
        "owner": "kvz", "repo": "bash3boilerplate", "branch": "main",
        "ftype": "recipe", "domain": "bash", "tier": "A",
        "tags": "bash,recipe,boilerplate,template",
        "include_exts": [".md", ".bash", ".sh"],
        "include_patterns": [],
        "exclude_patterns": [".github", "test"],
        "max_files": 30,
        "extractor": "raw",
        "description": "bash3boilerplate — bash script templates and docs",
    },
    # ── anordal/shellharden — advice.md (was 404 on branch, try main) ───────
    {
        "owner": "anordal", "repo": "shellharden", "branch": "master",
        "ftype": "recipe", "domain": "bash", "tier": "A",
        "tags": "bash,recipe,shellharden,bestpractice",
        "include_exts": [".md"],
        "include_patterns": [],
        "exclude_patterns": [],
        "max_files": 20,
        "extractor": "raw",
        "description": "shellharden — safe bash advice docs",
    },
    # ── teivah/100-go-mistakes — chapter .md files (was 404 on README) ──────
    {
        "owner": "teivah", "repo": "100-go-mistakes", "branch": "master",
        "ftype": "gotcha", "domain": "golang", "tier": "A",
        "tags": "go,golang,gotcha,mistakes,100mistakes",
        "include_exts": [".md"],
        "include_patterns": [],
        "exclude_patterns": [],
        "max_files": 50,
        "extractor": "raw",
        "description": "100-go-mistakes — chapter gotcha files",
    },
    # ── faif/python-patterns — individual pattern .py files (docstrings) ────
    {
        "owner": "faif", "repo": "python-patterns", "branch": "master",
        "ftype": "recipe", "domain": "python", "tier": "A",
        "tags": "python,recipe,designpattern,gof",
        "include_exts": [".py"],
        "include_patterns": ["patterns/"],
        "exclude_patterns": ["test", "__init__"],
        "max_files": 60,
        "extractor": "python_docstring",
        "description": "python-patterns — GOF pattern implementations",
    },
    # ── tmrts/go-patterns — individual .go pattern files ────────────────────
    {
        "owner": "tmrts", "repo": "go-patterns", "branch": "master",
        "ftype": "recipe", "domain": "golang", "tier": "A",
        "tags": "go,golang,recipe,designpattern",
        "include_exts": [".go", ".md"],
        "include_patterns": [],
        "exclude_patterns": ["vendor", ".github"],
        "max_files": 60,
        "extractor": "raw",
        "description": "go-patterns — Go design pattern implementations",
    },
    # ── AllThingsSmitty/css-protips — individual tip sections ───────────────
    # (README already ingested; no per-file breakdown)

    # ── satwikkansal/wtfpython — chapter .md files ───────────────────────────
    {
        "owner": "satwikkansal", "repo": "wtfpython", "branch": "master",
        "ftype": "gotcha", "domain": "python", "tier": "A",
        "tags": "python,gotcha,wtf,quirk",
        "include_exts": [".md"],
        "include_patterns": [],
        "exclude_patterns": ["README.md", "CONTRIBUTING.md", "CHANGELOG.md"],
        "max_files": 50,
        "extractor": "raw",
        "description": "wtfpython — topic .md files",
    },
]

# ── Filter helpers ────────────────────────────────────────────────────────────
def matches_source(config, tree_paths):
    """Return filtered list of paths from tree matching config rules."""
    inc_exts     = set(config.get("include_exts", []))
    inc_pats     = config.get("include_patterns", [])
    exc_pats     = config.get("exclude_patterns", [])
    max_files    = config.get("max_files", 100)

    filtered = []
    for p in tree_paths:
        # Extension filter
        _, ext = os.path.splitext(p)
        if inc_exts and ext not in inc_exts:
            continue
        # Exclude patterns
        if any(pat in p for pat in exc_pats):
            continue
        # Include path patterns (if any specified, must match at least one)
        if inc_pats and not any(pat in p for pat in inc_pats):
            continue
        filtered.append(p)
        if len(filtered) >= max_files:
            break

    return filtered

# ── Extractors ────────────────────────────────────────────────────────────────
def extract_content(text, extractor, path):
    if extractor == "python_docstring":
        return clean_python(text)
    return text   # "raw" mode

# ── Main walker ───────────────────────────────────────────────────────────────
def walk_repo(config):
    owner  = config["owner"]
    repo   = config["repo"]
    branch = config["branch"]
    ftype  = config["ftype"]
    domain = config["domain"]
    tier   = config["tier"]
    tags   = config["tags"]
    extractor = config.get("extractor", "raw")

    print(f"\n  [{ftype.upper()}] {owner}/{repo}  ({domain})")

    # 1. Get file tree
    tree = fetch_tree(owner, repo)
    if not tree:
        print(f"    TREE empty or unavailable")
        return []

    # 2. Filter to relevant files
    paths = matches_source(config, tree)
    print(f"    {len(tree)} tree paths -> {len(paths)} selected")

    # 3. Fetch + chunk each file
    frags = []
    for path in paths:
        text = fetch_raw(owner, repo, branch, path)
        if not text or len(text.strip()) < MIN_LEN:
            continue
        content = extract_content(text, extractor, path)
        chunks  = chunk_text(content, ftype=ftype)
        for c in chunks:
            frags.append({
                "content":  c,
                "source":   f"{domain}/{repo}/{path}@raw.githubusercontent.com",
                "tier":     tier,
                "ftype":    ftype,
                "tags":     tags,
                "lang_version": None,
            })

    print(f"    => {len(frags)} chunks from {len(paths)} files")
    return frags

# ── Entry point ───────────────────────────────────────────────────────────────
def run(targets=None):
    conn   = sqlite3.connect(DB)
    before = conn.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
    print(f"\nPhase 3 Tree-Walk Scraper")
    print(f"Start: {before:,} fragments\n")

    sources = TREE_SOURCES
    if targets:
        sources = [s for s in sources if s["domain"] in targets or s["ftype"] in targets]

    total = 0
    for config in sources:
        try:
            frags = walk_repo(config)
            n = save(conn, frags)
            total += n
            print(f"    -> +{n} new inserted")
        except Exception as e:
            print(f"    ERROR: {e}")

    print("\nRebuilding FTS index...")
    try:
        conn.execute("INSERT INTO bible_fts(bible_fts) VALUES('rebuild')")
        conn.commit()
    except Exception as e:
        print(f"  FTS rebuild warning: {e}")

    after = conn.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
    conn.close()
    print(f"\nDone: {before:,} -> {after:,} (+{after-before:,} net)")
    return after - before

if __name__ == "__main__":
    targets = [a.lower() for a in sys.argv[1:]]
    run(targets or None)
