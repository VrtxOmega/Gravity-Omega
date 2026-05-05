"""Multi-source documentation scraper for The Coder's Bible."""
import requests, sqlite3, hashlib, time, re, os, sys, json
from bs4 import BeautifulSoup
from datetime import datetime

DB = os.path.join(os.path.dirname(__file__), "coders_bible.db")
HEADERS = {"User-Agent": "CodersBible/1.0 (documentation indexer)"}
DELAY = 0.3  # seconds between requests

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        time.sleep(DELAY)
        return r.text
    except Exception as e:
        print(f"  SKIP {url}: {e}")
        return None

def chunk_text(text, max_len=1500):
    paragraphs = re.split(r'\n{2,}', text.strip())
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) > max_len and current:
            chunks.append(current.strip())
            current = p
        else:
            current += "\n\n" + p if current else p
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 50]

def insert_fragments(conn, fragments):
    for f in fragments:
        fid = hashlib.sha256(f["content"].encode()).hexdigest()[:16]
        try:
            conn.execute(
                "INSERT OR IGNORE INTO fragments (id, content, source, tier, ingested_at) VALUES (?,?,?,?,?)",
                (fid, f["content"], f["source"], f["tier"], datetime.utcnow().isoformat())
            )
        except Exception:
            pass
    conn.commit()

def extract_text(html, selector="article, .content, main, .man-page, #content, body"):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    el = soup.select_one(selector) or soup.body
    return el.get_text(separator="\n", strip=True) if el else ""

# ── Git ──
def scrape_git():
    print("\n=== Scraping Git docs ===")
    frags = []
    
    # Git core docs
    try:
        r = requests.get("https://api.github.com/repos/git/git/contents/Documentation", headers=HEADERS)
        if r.status_code == 200:
            files = [item["name"] for item in r.json() if item["name"].endswith(".txt") or item["name"].endswith(".adoc")]
        else:
            files = ["git-add.txt","git-branch.txt","git-commit.txt","git-checkout.txt","git-merge.txt","git-rebase.txt","git-log.txt","git-status.txt","git-pull.txt","git-push.txt","git-clone.txt","git-config.txt","git-diff.txt","git-fetch.txt","git-reset.txt","git-stash.txt","git-tag.txt","git-remote.txt","git-submodule.txt"]
            
        for f in files:
            url = f"https://raw.githubusercontent.com/git/git/master/Documentation/{f}"
            text = fetch(url)
            if not text: continue
            for c in chunk_text(text):
                frags.append({"content": c, "source": f"git/{f}@github.com", "tier": "A"})
            print(f"  git/{f}: {len(chunk_text(text))} chunks")
    except Exception as e:
        print(f"  Git core error: {e}")

    # Pro Git Book
    try:
        chapters = ["01-introduction","02-git-basics","03-git-branching","04-git-server","05-distributed-git","06-github","07-git-tools","08-customizing-git","09-git-and-other-systems","10-git-internals"]
        for ch in chapters:
            url = f"https://api.github.com/repos/progit/progit2/contents/book/{ch}"
            r = requests.get(url, headers=HEADERS)
            if r.status_code == 200:
                for item in r.json():
                    if item["name"].endswith(".asc"):
                        text = fetch(item["download_url"])
                        if not text: continue
                        for c in chunk_text(text):
                            frags.append({"content": c, "source": f"progit/{ch}/{item['name']}@github.com", "tier": "A"})
                        print(f"  progit/{item['name']}: {len(chunk_text(text))} chunks")
    except Exception as e:
        print(f"  ProGit error: {e}")

    return frags

# ── Bash ── (bulk GitHub tree walker)
def scrape_bash():
    print("\n=== Scraping Bash docs (bulk) ===")
    frags = []
    # 1. GNU Bash manual HTML
    for url, src in [
        ("https://www.gnu.org/software/bash/manual/bash.html", "bash/manual@gnu.org"),
        ("https://tiswww.case.edu/php/chet/bash/bashref.html", "bash/bashref@tiswww"),
    ]:
        html = fetch(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup.find_all(["script","style","nav"]): tag.decompose()
            for sec in soup.find_all(["h2","h3"]):
                content, curr = [], sec.next_sibling
                while curr and getattr(curr, 'name', None) not in ["h2","h3"]:
                    if hasattr(curr, "get_text"): content.append(curr.get_text(separator="\n", strip=True))
                    curr = getattr(curr, 'next_sibling', None)
                text = sec.get_text(strip=True) + "\n" + "\n".join(content)
                for c in chunk_text(text, 1200):
                    frags.append({"content": c, "source": src, "tier": "A"})
    # 2. bash-guide + pure-bash-bible on GitHub
    for repo, branch, prefix in [
        ("dylanaraps/pure-bash-bible", "master", "pure-bash-bible"),
        ("anordal/shellharden", "master", "shellharden"),
    ]:
        r = requests.get(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1", headers=HEADERS)
        if r.status_code == 200:
            for item in r.json().get("tree", []):
                if item["path"].endswith((".md",".txt",".bash",".sh")) and item["type"]=="blob":
                    text = fetch(f"https://raw.githubusercontent.com/{repo}/{branch}/{item['path']}")
                    if text:
                        for c in chunk_text(text):
                            frags.append({"content": c, "source": f"bash/{prefix}/{item['path']}@github.com", "tier": "A"})
    # 3. TLDP Advanced Bash Guide
    for page in ["abs-guide.html"]:
        html = fetch(f"https://tldp.org/LDP/abs/{page}")
        if html:
            text = extract_text(html)
            for c in chunk_text(text, 1200):
                frags.append({"content": c, "source": f"bash/abs-guide@tldp.org", "tier": "B"})
    print(f"  Bash total: {len(frags)} chunks")
    return frags

# ── Docker (docs.docker.com) ──
def scrape_docker():
    print("\n=== Scraping Docker docs (Raw Markdown) ===")
    frags = []
    try:
        r = requests.get("https://api.github.com/repos/docker/docs/git/trees/main?recursive=1", headers=HEADERS)
        if r.status_code == 200:
            tree = r.json().get("tree", [])
            files = [t["path"] for t in tree if t["path"].startswith("content/") and t["path"].endswith(".md")]
        else:
            files = []
        
        for f in files:
            url = f"https://raw.githubusercontent.com/docker/docs/main/{f}"
            text = fetch(url)
            if not text: continue
            for c in chunk_text(text):
                frags.append({"content": c, "source": f"docker/{f}@github.com", "tier": "A"})
            print(f"  docker/{os.path.basename(f)}: {len(chunk_text(text))} chunks")
    except Exception as e:
        print(f"  Docker error: {e}")
    return frags

# ── Kubernetes ── (multi-repo bulk walker)
def scrape_kubernetes():
    print("\n=== Scraping Kubernetes docs (bulk) ===")
    frags = []
    repos = [
        ("kubernetes/website", "main",   "content/en/docs/"),
        ("kubernetes/community", "master", ""),
        ("kelseyhightower/kubernetes-the-hard-way", "master", ""),
        ("kubernetes/examples", "master", ""),
        ("kubernetes-sigs/kustomize", "master", "docs/"),
    ]
    for repo, branch, prefix in repos:
        try:
            r = requests.get(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1", headers=HEADERS)
            if r.status_code != 200:
                print(f"  tree fail {repo}: {r.status_code}")
                continue
            tree = r.json().get("tree", [])
            files = [t["path"] for t in tree
                     if t["path"].endswith(".md") and t["type"]=="blob"
                     and (not prefix or t["path"].startswith(prefix))]
            print(f"  {repo}: {len(files)} files")
            for f in files:
                text = fetch(f"https://raw.githubusercontent.com/{repo}/{branch}/{f}")
                if not text: continue
                for c in chunk_text(text):
                    frags.append({"content": c, "source": f"kubernetes/{f}@github.com", "tier": "A"})
        except Exception as e:
            print(f"  k8s error {repo}: {e}")
    print(f"  Kubernetes total: {len(frags)} chunks")
    return frags

# ── C/C++ ── (multi-repo bulk walker)
def scrape_cpp():
    print("\n=== Scraping C/C++ docs (bulk) ===")
    frags = []
    repos = [
        ("MicrosoftDocs/cpp-docs", "main",   ["docs/cpp/", "docs/standard-library/", "docs/c-runtime-library/"]),
        ("cppreference/cppreference-doc", "master", [""]),
        ("isocpp/CppCoreGuidelines", "master", [""]),
        ("fffaraz/awesome-cpp", "master",     [""]),
    ]
    for repo, branch, prefixes in repos:
        try:
            r = requests.get(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1", headers=HEADERS)
            if r.status_code != 200:
                print(f"  tree fail {repo}: {r.status_code}")
                continue
            tree = r.json().get("tree", [])
            files = [t["path"] for t in tree
                     if t["path"].endswith(".md") and t["type"]=="blob"
                     and any(t["path"].startswith(p) for p in prefixes)]
            print(f"  {repo}: {len(files)} files")
            for f in files:
                text = fetch(f"https://raw.githubusercontent.com/{repo}/{branch}/{f}")
                if not text: continue
                for c in chunk_text(text):
                    frags.append({"content": c, "source": f"c/{f}@github.com", "tier": "A"})
        except Exception as e:
            print(f"  C/C++ error {repo}: {e}")
    print(f"  C/C++ total: {len(frags)} chunks")
    return frags

# ── CSS / HTML ── (MDN + bulk GitHub walker)
def scrape_mdn_web():
    print("\n=== Scraping CSS/HTML docs (bulk) ===")
    frags = []
    # 1. MDN CSS — all properties from mdn/content
    repos_css_html = [
        ("mdn/content", "main", "files/en-us/web/css/",  "css"),
        ("mdn/content", "main", "files/en-us/web/html/", "html"),
    ]
    for repo, branch, prefix, domain in repos_css_html:
        try:
            r = requests.get(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1", headers=HEADERS)
            if r.status_code != 200:
                print(f"  tree fail {repo}/{prefix}: {r.status_code}")
                continue
            tree = r.json().get("tree", [])
            files = [t["path"] for t in tree
                     if t["path"].lower().startswith(prefix)
                     and t["path"].endswith(".md") and t["type"]=="blob"]
            print(f"  {repo}/{prefix}: {len(files)} files")
            for f in files:
                text = fetch(f"https://raw.githubusercontent.com/{repo}/{branch}/{f}")
                if not text: continue
                for c in chunk_text(text):
                    frags.append({"content": c, "source": f"{domain}/{f}@github.com", "tier": "A"})
        except Exception as e:
            print(f"  MDN {domain} error: {e}")
    # 2. CSS-Tricks almanac (GitHub mirror)
    try:
        r = requests.get("https://api.github.com/repos/nicktaylor/css-almanac/git/trees/master?recursive=1", headers=HEADERS)
        if r.status_code == 200:
            for t in r.json().get("tree",[]):
                if t["path"].endswith(".md"):
                    text = fetch(f"https://raw.githubusercontent.com/nicktaylor/css-almanac/master/{t['path']}")
                    if text:
                        for c in chunk_text(text):
                            frags.append({"content": c, "source": f"css/almanac/{t['path']}@github.com", "tier": "B"})
    except Exception: pass
    # 3. HTML spec living standard sections
    for section in ["semantics","forms","dom","scripting","browsers","microdata","interaction"]:
        html = fetch(f"https://html.spec.whatwg.org/multipage/{section}.html")
        if html:
            text = extract_text(html)
            for c in chunk_text(text, 1400):
                frags.append({"content": c, "source": f"html/spec/{section}@whatwg.org", "tier": "A"})
    print(f"  CSS/HTML total: {len(frags)} chunks")
    return frags

# ── Java (dev.java) ──
def scrape_java():
    print("\n=== Scraping Java docs (Raw Markdown) ===")
    frags = []
    try:
        r = requests.get("https://api.github.com/repos/java/devjava-content/git/trees/main?recursive=1", headers=HEADERS)
        if r.status_code == 200:
            tree = r.json().get("tree", [])
            files = [t["path"] for t in tree if t["path"].startswith("app/pages/") and t["path"].endswith(".md")]
        else:
            files = []
            
        for f in files:
            url = f"https://raw.githubusercontent.com/java/devjava-content/main/{f}"
            text = fetch(url)
            if not text: continue
            for c in chunk_text(text):
                frags.append({"content": c, "source": f"java/{os.path.basename(f)}@github.com", "tier": "A"})
            print(f"  java/{os.path.basename(f)}: {len(chunk_text(text))} chunks")
    except Exception as e:
        print(f"  Java error: {e}")
    return frags

# ── Terraform ──
def scrape_terraform():
    print("\n=== Scraping Terraform docs via Next.js API ===")
    build_id = "FXi0hUxaqLnv8ZF2NuF7g"
    pages = [
        "terraform/language", "terraform/language/resources/syntax", "terraform/language/data-sources",
        "terraform/language/values/variables", "terraform/language/values/outputs", "terraform/language/values/locals",
        "terraform/language/state", "terraform/language/settings", "terraform/language/functions",
        "terraform/language/expressions", "terraform/language/modules", "terraform/language/providers",
        "terraform/language/style", "terraform/language/syntax", "terraform/language/meta-arguments",
        "terraform/cli/commands/init", "terraform/cli/commands/plan", "terraform/cli/commands/apply",
        "terraform/cli/commands/destroy", "terraform/cli/commands/import", "terraform/cli/commands/validate",
        "terraform/cli/commands/workspace/list", "terraform/cli/commands/state", "terraform/intro"
    ]
    frags = []
    for p in pages:
        url = f"https://developer.hashicorp.com/_next/data/{build_id}/{p}.json"
        raw = fetch(url)
        if not raw: continue
        try:
            data = json.loads(raw)
            mdx = data["pageProps"]["mdxSource"]["compiledSource"]
            
            # Very basic extraction: regex to strip out jsx components/JS functions
            # In a real pipeline we'd evaluate the MDX or use a robust JSX stripper, 
            # but string manipulation gets the core textual content.
            text = re.sub(r'var \w+ = function[^{]+{[^}]+};', '', mdx)
            text = re.sub(r'return _jsx.*?\);', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', '', text)  # strip tags if any
            text = re.sub(r'\\n', '\n', text)
            
            for c in chunk_text(text):
                frags.append({"content": c, "source": f"{p}@developer.hashicorp.com", "tier": "A"})
            print(f"  {p}: {len(chunk_text(text))} chunks")
        except Exception as e:
            print(f"  Terraform JSON error on {p}: {e}")
    return frags

# ── C# / .NET ── (bulk GitHub tree walker)
def scrape_csharp():
    print("\n=== Scraping C# docs (bulk) ===")
    frags = []
    repos = [
        ("dotnet/docs",         "main",   ["docs/csharp/", "docs/standard/"]),
        ("dotnet/csharplang",   "main",   ["proposals/", "spec/"]),
        ("MicrosoftDocs/azure-docs", "main", ["articles/azure-functions/"]),
    ]
    for repo, branch, prefixes in repos:
        try:
            r = requests.get(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1", headers=HEADERS)
            if r.status_code != 200:
                print(f"  tree fail {repo}: {r.status_code}")
                continue
            tree = r.json().get("tree", [])
            files = [t["path"] for t in tree
                     if t["path"].endswith(".md") and t["type"]=="blob"
                     and any(t["path"].startswith(p) for p in prefixes)]
            print(f"  {repo}: {len(files)} files")
            for f in files:
                text = fetch(f"https://raw.githubusercontent.com/{repo}/{branch}/{f}")
                if not text: continue
                for c in chunk_text(text):
                    frags.append({"content": c, "source": f"csharp/{f}@github.com", "tier": "A"})
        except Exception as e:
            print(f"  C# error {repo}: {e}")
    print(f"  C# total: {len(frags)} chunks")
    return frags

# ── SQL (generic) ──
def scrape_sql():
    print("\n=== Scraping SQL reference ===")
    frags = []
    
    # PostgreSQL raw SGML
    try:
        r = requests.get("https://api.github.com/repos/postgres/postgres/contents/doc/src/sgml/ref", headers=HEADERS)
        if r.status_code == 200:
            pg_files = [item["name"] for item in r.json() if item["name"].endswith(".sgml")]
        else:
            pg_files = ["select.sgml", "insert.sgml", "create_table.sgml", "abort.sgml", "alter_aggregate.sgml", "alter_database.sgml", "alter_domain.sgml"]
            
        for p in pg_files:
            url = f"https://raw.githubusercontent.com/postgres/postgres/master/doc/src/sgml/ref/{p}"
            text = fetch(url)
            if not text: continue
            # Basic SGML strip
            text = re.sub(r'<[^>]+>', '', text)
            for c in chunk_text(text):
                frags.append({"content": c, "source": f"sql/postgres/{p}@github.com", "tier": "A"})
            print(f"  sql/postgres/{p}: {len(chunk_text(text))} chunks")
    except Exception as e:
        print(f"  Postgres error: {e}")

    # SQLite single pages
    sqlite_pages = ["lang.html", "vdbe.html", "fileformat2.html", "arch.html", "queryplanner.html", "fts3.html", "json1.html", "rtree.html"]
    for p in sqlite_pages:
        html = fetch(f"https://www.sqlite.org/{p}")
        if not html: continue
        text = extract_text(html, ".fancy")
        for c in chunk_text(text):
            frags.append({"content": c, "source": f"sql/sqlite/{p}@sqlite.org", "tier": "A"})
        print(f"  sql/sqlite/{p}: {len(chunk_text(text))} chunks")
        
    # W3Schools
    w3_pages = ["select","insert","update","delete","alter","create_table","drop_table","constraints","view","groupby","having","null_values","operators"]
    for p in w3_pages:
        html = fetch(f"https://www.w3schools.com/sql/sql_{p}.asp")
        if not html: continue
        text = extract_text(html, "#main")
        for c in chunk_text(text):
            frags.append({"content": c, "source": f"sql/w3schools/{p}@w3schools.com", "tier": "B"})
        print(f"  sql/w3schools/{p}: {len(chunk_text(text))} chunks")
        
    return frags

# ── Kotlin ── (bulk GitHub tree walker)
def scrape_kotlin():
    print("\n=== Scraping Kotlin docs (bulk) ===")
    frags = []
    repos = [
        ("JetBrains/kotlin",              "master", ["docs/", "libraries/stdlib/"]),
        ("Kotlin/kotlinx.coroutines",      "master", ["docs/"]),
        ("Kotlin/kotlinx.serialization",   "master", ["docs/"]),
        ("Kotlin/kotlin-in-action",        "master", [""]),
        ("MindorksOpenSource/From-Java-To-Kotlin", "master", [""]),
    ]
    for repo, branch, prefixes in repos:
        try:
            r = requests.get(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1", headers=HEADERS)
            if r.status_code != 200:
                print(f"  tree fail {repo}: {r.status_code}")
                continue
            tree = r.json().get("tree", [])
            files = [t["path"] for t in tree
                     if t["path"].endswith(".md") and t["type"]=="blob"
                     and any(t["path"].startswith(p) for p in prefixes)]
            print(f"  {repo}: {len(files)} files")
            for f in files:
                text = fetch(f"https://raw.githubusercontent.com/{repo}/{branch}/{f}")
                if not text: continue
                for c in chunk_text(text):
                    frags.append({"content": c, "source": f"kotlin/{f}@github.com", "tier": "A"})
        except Exception as e:
            print(f"  Kotlin error {repo}: {e}")
    # kotlinlang.org HTML (original 26 pages still valuable)
    pages = ["basic-syntax","basic-types","strings","control-flow","classes",
             "inheritance","properties","interfaces","data-classes","sealed-classes",
             "generics","enum-classes","functions","lambdas","collections-overview",
             "sequences","coroutines-overview","null-safety","exceptions",
             "annotations","scope-functions","operator-overloading",
             "delegation","object-declarations","inline-functions","extension-functions",
             "functional","type-aliases","destructuring-declarations","returns"]
    for p in pages:
        html = fetch(f"https://kotlinlang.org/docs/{p}.html")
        if not html: continue
        text = extract_text(html, "article")
        for c in chunk_text(text):
            frags.append({"content": c, "source": f"kotlin/{p}@kotlinlang.org", "tier": "A"})
    print(f"  Kotlin total: {len(frags)} chunks")
    return frags

# ── Swift ──
def scrape_swift():
    print("\n=== Scraping Swift docs (Raw Markdown) ===")
    frags = []
    
    directories = ["GuidedTour", "LanguageGuide", "LanguageReference"]
    for d in directories:
        try:
            r = requests.get(f"https://api.github.com/repos/swiftlang/swift-book/contents/TSPL.docc/{d}", headers=HEADERS)
            if r.status_code == 200:
                files = [item["name"] for item in r.json() if item["name"].endswith(".md")]
            else:
                files = []
                
            for f in files:
                url = f"https://raw.githubusercontent.com/swiftlang/swift-book/main/TSPL.docc/{d}/{f}"
                text = fetch(url)
                if not text: continue
                for c in chunk_text(text):
                    frags.append({"content": c, "source": f"swift/{d}/{f}@github.com", "tier": "A"})
                print(f"  swift/{f}: {len(chunk_text(text))} chunks")
        except Exception as e:
            print(f"  Swift error on {d}: {e}")
            
    return frags

# ═══════════════════════════════════════
# Google ecosystem (Gemini, Vertex AI, GCP, Firebase, Android, TF, JAX)
# ═══════════════════════════════════════
try:
    from scrape_google import GOOGLE_SCRAPERS
except ImportError:
    GOOGLE_SCRAPERS = []

# ═══════════════════════════════════════
# Main
# ═══════════════════════════════════════
ALL_SCRAPERS = [
    ("Git", scrape_git),
    ("Bash", scrape_bash),
    ("Docker", scrape_docker),
    ("Kubernetes", scrape_kubernetes),
    ("C/C++", scrape_cpp),
    ("CSS/HTML", scrape_mdn_web),
    ("Java", scrape_java),
    ("Terraform", scrape_terraform),
    ("C#", scrape_csharp),
    ("SQL", scrape_sql),
    ("Kotlin", scrape_kotlin),
    ("Swift", scrape_swift),
] + GOOGLE_SCRAPERS

def main():
    # Allow running specific scrapers via CLI args
    targets = sys.argv[1:] if len(sys.argv) > 1 else None

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    before = conn.execute("SELECT COUNT(*) as c FROM fragments").fetchone()["c"]
    print(f"Starting count: {before} fragments")

    total_new = 0
    for name, fn in ALL_SCRAPERS:
        if targets and name.lower() not in [t.lower() for t in targets]:
            continue
        try:
            frags = fn()
            if frags:
                insert_fragments(conn, frags)
                total_new += len(frags)
                print(f"  -> Inserted {len(frags)} fragments for {name}")
        except Exception as e:
            print(f"  ERROR in {name}: {e}")

    # Rebuild FTS
    print("\nRebuilding FTS5 index...")
    conn.execute("INSERT INTO bible_fts(bible_fts) VALUES('rebuild')")
    conn.commit()

    after = conn.execute("SELECT COUNT(*) as c FROM fragments").fetchone()["c"]
    print(f"\nDone! {before} -> {after} fragments (+{after - before} new)")
    conn.close()

if __name__ == "__main__":
    main()
