"""
scrape_tier2.py — The Coder Bible Tier 2: Gotchas + Recipes
Zero AI. Zero GitHub API. raw.githubusercontent.com only.
Recursive tree-walk via git trees API fallback to known file manifests.
Sets ftype='gotcha' or ftype='recipe' on every inserted fragment.
"""
import hashlib
import os
import re
import sqlite3
import sys
import time
from datetime import datetime

import requests

# ── Config ────────────────────────────────────────────────────────────────────
DB      = os.path.join(os.path.dirname(__file__), "coders_bible.db")
RAW     = "https://raw.githubusercontent.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CodersBibleIndexer/2.0)"}
DELAY   = 0.35
MIN_LEN = 80
MAX_LEN = 1600

# ── HTTP helpers ──────────────────────────────────────────────────────────────
def fetch(url, retries=2):
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            time.sleep(DELAY)
            return r.text
        except Exception as e:
            if attempt == retries:
                print(f"  SKIP {url[:80]}: {e}")
                return None
            time.sleep(1.0)
    return None

def fetch_raw(repo, branch, path):
    return fetch(f"{RAW}/{repo}/{branch}/{path}")

# ── Text processing ───────────────────────────────────────────────────────────
def strip_md_boilerplate(text):
    """Remove badges, license headers, nav links from markdown."""
    lines = text.splitlines()
    cleaned = []
    for ln in lines:
        l = ln.strip()
        # Skip badge lines, pure URLs, CI status lines
        if re.match(r'^\[!\[', l): continue
        if re.match(r'^https?://', l): continue
        if re.match(r'^!\[.*\]\(http', l): continue
        cleaned.append(ln)
    return "\n".join(cleaned)

def chunk_text(text, ftype="doc"):
    """
    Split text into indexable fragments.
    For gotchas/recipes: split on headings (## / ###) to preserve context.
    """
    text = strip_md_boilerplate(text).strip()
    if not text:
        return []

    if ftype in ("gotcha", "recipe"):
        # Split on markdown headings — each heading + body = one fragment
        parts = re.split(r'\n(?=#{1,3} )', text)
        chunks = []
        for p in parts:
            p = p.strip()
            if len(p) >= MIN_LEN:
                chunks.append(p[:MAX_LEN])
        return chunks if chunks else _para_chunk(text)

    return _para_chunk(text)

def _para_chunk(text):
    paras = re.split(r'\n{2,}', text)
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) > MAX_LEN and cur:
            if len(cur) >= MIN_LEN:
                chunks.append(cur.strip())
            cur = p
        else:
            cur += ("\n\n" + p if cur else p)
    if cur.strip() and len(cur.strip()) >= MIN_LEN:
        chunks.append(cur.strip())
    return chunks

# ── DB ────────────────────────────────────────────────────────────────────────
def save(conn, frags):
    inserted = 0
    for f in frags:
        fid = hashlib.sha256(f["content"].encode()).hexdigest()[:16]
        cur = conn.execute(
            """INSERT OR IGNORE INTO fragments
               (id, content, source, tier, ingested_at, ftype, lang_version, tags)
               VALUES (?,?,?,?,?,?,?,?)""",
            (fid, f["content"], f["source"], f.get("tier", "B"),
             datetime.utcnow().isoformat(),
             f.get("ftype", "doc"),
             f.get("lang_version"),
             f.get("tags", ""))
        )
        inserted += cur.rowcount
    conn.commit()
    return inserted

# ══════════════════════════════════════════════════════════════════════════════
# GOTCHA SOURCES
# Curated repos with real-world gotcha content — explicit file lists,
# no GitHub API. raw.githubusercontent.com only.
# ══════════════════════════════════════════════════════════════════════════════

GOTCHA_SOURCES = [
    # Python gotchas / WATs
    {
        "repo": "satwikkansal/wtfpython", "branch": "master",
        "files": ["README.md"],
        "domain": "python", "ftype": "gotcha", "tier": "A",
        "tag": "python,gotcha,wtf",
    },
    # JavaScript WATs
    {
        "repo": "denysdovhan/wtfjs", "branch": "master",
        "files": ["README.md"],
        "domain": "javascript", "ftype": "gotcha", "tier": "A",
        "tag": "javascript,gotcha,wtf",
    },
    # Bash pitfalls (mywiki.wooledge.org mirror on GitHub)
    {
        "repo": "nicowillis/bash-pitfalls", "branch": "master",
        "files": ["README.md"],
        "domain": "bash", "ftype": "gotcha", "tier": "B",
        "tag": "bash,gotcha,pitfall",
    },
    # Bash strict mode
    {
        "repo": "alphabetum/bash-strict-mode", "branch": "master",
        "files": ["README.md"],
        "domain": "bash", "ftype": "gotcha", "tier": "A",
        "tag": "bash,gotcha,strictmode",
    },
    # CSS gotchas
    {
        "repo": "AllThingsSmitty/css-protips", "branch": "master",
        "files": ["README.md"],
        "domain": "css", "ftype": "gotcha", "tier": "A",
        "tag": "css,gotcha,protip",
    },
    # Git gotchas / tips
    {
        "repo": "git-tips/tips", "branch": "master",
        "files": ["README.md"],
        "domain": "git", "ftype": "gotcha", "tier": "A",
        "tag": "git,gotcha,tips",
    },
    # Docker gotchas / best practices
    {
        "repo": "hexops/dockerfile", "branch": "main",
        "files": ["README.md"],
        "domain": "docker", "ftype": "gotcha", "tier": "A",
        "tag": "docker,gotcha,dockerfile,bestpractice",
    },
    {
        "repo": "FuriKuri/docker-best-practices", "branch": "master",
        "files": ["README.md"],
        "domain": "docker", "ftype": "gotcha", "tier": "B",
        "tag": "docker,gotcha,bestpractice",
    },
    # Node.js best practices (gotcha-dense)
    {
        "repo": "goldbergyoni/nodebestpractices", "branch": "master",
        "files": ["README.md"],
        "domain": "javascript", "ftype": "gotcha", "tier": "A",
        "tag": "nodejs,javascript,gotcha,bestpractice",
    },
    # Python anti-patterns
    {
        "repo": "quantifiedcode/python-anti-patterns", "branch": "master",
        "files": ["README.rst"],
        "domain": "python", "ftype": "gotcha", "tier": "A",
        "tag": "python,gotcha,antipattern",
    },
    # Python security gotchas
    {
        "repo": "mpirnat/lets-be-bad-guys", "branch": "master",
        "files": ["README.md"],
        "domain": "python", "ftype": "gotcha", "tier": "A",
        "tag": "python,gotcha,security",
    },
    # SQL best practices / gotchas
    {
        "repo": "mattm/sql-style-guide", "branch": "master",
        "files": ["README.md"],
        "domain": "sql", "ftype": "gotcha", "tier": "A",
        "tag": "sql,gotcha,styleguide",
    },
    # Go pitfalls / common mistakes
    {
        "repo": "teivah/100-go-mistakes", "branch": "main",
        "files": ["README.md"],
        "domain": "golang", "ftype": "gotcha", "tier": "A",
        "tag": "go,golang,gotcha,mistakes",
    },
    {
        "repo": "ksimka/go-is-not-good", "branch": "master",
        "files": ["README.md"],
        "domain": "golang", "ftype": "gotcha", "tier": "B",
        "tag": "go,golang,gotcha,criticism",
    },
    # TypeScript deep dive gotchas
    {
        "repo": "basarat/typescript-book", "branch": "master",
        "files": [
            "docs/tips/nominalTyping.md",
            "docs/tips/statefulFunctions.md",
            "docs/tips/bind.md",
            "docs/tips/currying.md",
            "docs/tips/lazyObjectLiterals.md",
            "docs/javascript/closure.md",
            "docs/javascript/equality.md",
            "docs/javascript/this.md",
            "docs/javascript/null-undefined.md",
            "docs/javascript/truthy.md",
            "docs/javascript/number.md",
        ],
        "domain": "typescript", "ftype": "gotcha", "tier": "A",
        "tag": "typescript,javascript,gotcha",
    },
    # Rust common mistakes
    {
        "repo": "pretzelhammer/rust-blog", "branch": "master",
        "files": [
            "posts/common-rust-lifetime-misconceptions.md",
            "posts/sizedness-in-rust.md",
            "posts/tour-of-rusts-standard-library-traits.md",
        ],
        "domain": "rust", "ftype": "gotcha", "tier": "A",
        "tag": "rust,gotcha,lifetime",
    },
    # React gotchas
    {
        "repo": "vasanthk/react-bits", "branch": "master",
        "files": ["README.md"],
        "domain": "javascript", "ftype": "gotcha", "tier": "A",
        "tag": "react,javascript,gotcha,pattern",
    },
    # Kubernetes gotchas / production readiness
    {
        "repo": "diegolnasc/kubernetes-best-practices", "branch": "main",
        "files": ["README.md"],
        "domain": "kubernetes", "ftype": "gotcha", "tier": "A",
        "tag": "kubernetes,k8s,gotcha,bestpractice",
    },
    # Linux / sysadmin gotchas
    {
        "repo": "jlevy/the-art-of-command-line", "branch": "master",
        "files": ["README.md"],
        "domain": "bash", "ftype": "gotcha", "tier": "A",
        "tag": "linux,bash,gotcha,commandline",
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# RECIPE SOURCES
# Concrete, copy-paste patterns and cookbook content.
# ══════════════════════════════════════════════════════════════════════════════

RECIPE_SOURCES = [
    # Python cookbook patterns
    {
        "repo": "dabeaz/python-cookbook", "branch": "master",
        "files": ["README.rst"],
        "domain": "python", "ftype": "recipe", "tier": "A",
        "tag": "python,recipe,cookbook",
    },
    # 30 seconds of code — Python
    {
        "repo": "30-seconds/30-seconds-of-python", "branch": "master",
        "files": ["README.md"],
        "domain": "python", "ftype": "recipe", "tier": "A",
        "tag": "python,recipe,snippet",
    },
    # 30 seconds of code — JS
    {
        "repo": "30-seconds/30-seconds-of-code", "branch": "master",
        "files": ["README.md"],
        "domain": "javascript", "ftype": "recipe", "tier": "A",
        "tag": "javascript,recipe,snippet",
    },
    # Bash one-liners
    {
        "repo": "onceupon/Bash-Oneliner", "branch": "master",
        "files": ["README.md"],
        "domain": "bash", "ftype": "recipe", "tier": "A",
        "tag": "bash,recipe,oneliner",
    },
    # SQL recipes — mode analytics style guide has embedded examples
    {
        "repo": "learndb-py/learndb-py", "branch": "main",
        "files": ["README.md"],
        "domain": "sql", "ftype": "recipe", "tier": "B",
        "tag": "sql,recipe,learn",
    },
    # Docker compose recipes — awesome-compose
    {
        "repo": "docker/awesome-compose", "branch": "master",
        "files": ["README.md"],
        "domain": "docker", "ftype": "recipe", "tier": "A",
        "tag": "docker,recipe,compose",
    },
    # Makefile recipes — practical guide
    {
        "repo": "theicfire/makefiletutorial", "branch": "gh-pages",
        "files": ["README.md"],
        "domain": "makefile", "ftype": "recipe", "tier": "B",
        "tag": "makefile,recipe",
    },
    # Regex cheat-sheet / cookbook
    {
        "repo": "nicowillis/regex-cookbook", "branch": "master",
        "files": ["README.md"],
        "domain": "regex", "ftype": "recipe", "tier": "B",
        "tag": "regex,recipe,cookbook",
    },
    # Algorithm implementations — Python
    {
        "repo": "TheAlgorithms/Python", "branch": "master",
        "files": [
            "README.md",
            "sorts/README.md",
            "searches/README.md",
            "data_structures/README.md",
            "graphs/README.md",
            "dynamic_programming/README.md",
        ],
        "domain": "python", "ftype": "recipe", "tier": "A",
        "tag": "python,recipe,algorithm",
    },
    # Algorithm implementations — JavaScript
    {
        "repo": "TheAlgorithms/JavaScript", "branch": "master",
        "files": ["README.md"],
        "domain": "javascript", "ftype": "recipe", "tier": "A",
        "tag": "javascript,recipe,algorithm",
    },
    # Go patterns
    {
        "repo": "tmrts/go-patterns", "branch": "master",
        "files": ["README.md"],
        "domain": "golang", "ftype": "recipe", "tier": "A",
        "tag": "go,golang,recipe,pattern",
    },
    # Rust patterns
    {
        "repo": "rust-unofficial/patterns", "branch": "main",
        "files": [
            "src/SUMMARY.md",
            "src/patterns/behavioural/README.md",
            "src/patterns/creational/README.md",
            "src/patterns/structural/README.md",
            "src/idioms/README.md",
            "src/anti_patterns/README.md",
        ],
        "domain": "rust", "ftype": "recipe", "tier": "A",
        "tag": "rust,recipe,pattern",
    },
    # Kubernetes YAML recipes — real templates repo
    {
        "repo": "mhausenblas/rbac.dev", "branch": "master",
        "files": ["README.md"],
        "domain": "kubernetes", "ftype": "recipe", "tier": "A",
        "tag": "kubernetes,k8s,recipe,rbac",
    },
    {
        "repo": "BretFisher/kubernetes-mastery", "branch": "main",
        "files": ["README.md"],
        "domain": "kubernetes", "ftype": "recipe", "tier": "A",
        "tag": "kubernetes,k8s,recipe",
    },
    # CSS recipes — modern layout patterns
    {
        "repo": "una/CSSgram", "branch": "master",
        "files": ["README.md"],
        "domain": "css", "ftype": "recipe", "tier": "A",
        "tag": "css,recipe,filter",
    },
    # TypeScript utility patterns
    {
        "repo": "millsp/ts-toolbelt", "branch": "master",
        "files": ["README.md"],
        "domain": "typescript", "ftype": "recipe", "tier": "A",
        "tag": "typescript,recipe,utility",
    },
    # SQL — use-the-index-luke patterns
    {
        "repo": "winton/winton", "branch": "main",
        "files": ["README.md"],
        "domain": "sql", "ftype": "recipe", "tier": "B",
        "tag": "sql,recipe",
    },
    # Shell script best practices
    {
        "repo": "anordal/shellharden", "branch": "master",
        "files": ["advice.md"],
        "domain": "bash", "ftype": "recipe", "tier": "A",
        "tag": "bash,recipe,bestpractice,shellharden",
    },
    # Design patterns — Python implementations
    {
        "repo": "faif/python-patterns", "branch": "master",
        "files": ["README.md"],
        "domain": "python", "ftype": "recipe", "tier": "A",
        "tag": "python,recipe,designpattern",
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def scrape_source(entry):
    """Fetch all listed files from a source entry, return list of frag dicts."""
    repo    = entry["repo"]
    branch  = entry["branch"]
    domain  = entry["domain"]
    ftype   = entry["ftype"]
    tier    = entry.get("tier", "B")
    tag     = entry.get("tag", "")
    frags   = []

    for path in entry["files"]:
        text = fetch_raw(repo, branch, path)
        if not text:
            print(f"    MISS  {repo}/{path}")
            continue
        chunks = chunk_text(text, ftype=ftype)
        for c in chunks:
            frags.append({
                "content":      c,
                "source":       f"{domain}/{repo.split('/')[1]}/{path}@raw.githubusercontent.com",
                "tier":         tier,
                "ftype":        ftype,
                "lang_version": None,
                "tags":         tag,
            })
        print(f"    OK    {repo.split('/')[1]}/{path}  -> {len(chunks)} chunks")

    return frags


def run(targets=None):
    conn   = sqlite3.connect(DB)
    before = conn.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
    print(f"\nStart: {before:,} fragments in DB")

    all_sources = []
    if not targets or "gotcha" in targets:
        all_sources += [(s, "GOTCHA") for s in GOTCHA_SOURCES]
    if not targets or "recipe" in targets:
        all_sources += [(s, "RECIPE") for s in RECIPE_SOURCES]

    total_inserted = 0
    for entry, label in all_sources:
        repo = entry["repo"]
        print(f"\n  [{label}] {repo}  ({entry['domain']})")
        try:
            frags = scrape_source(entry)
            n = save(conn, frags)
            total_inserted += n
            print(f"    => +{n} new fragments")
        except Exception as exc:
            print(f"    ERROR: {exc}")

    print("\nRebuilding FTS index...")
    try:
        conn.execute("INSERT INTO bible_fts(bible_fts) VALUES('rebuild')")
        conn.commit()
    except Exception as e:
        print(f"  FTS rebuild warning: {e}")

    after = conn.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
    conn.close()
    print(f"\nDone: {before:,} -> {after:,} (+{after-before:,} net, +{total_inserted} inserted)")
    return after - before


if __name__ == "__main__":
    targets = [a.lower() for a in sys.argv[1:]]  # e.g. "gotcha" "recipe" or both
    run(targets or None)
