"""Google developer ecosystem scraper for The Coder's Bible.

VERITAS seal: 0a4d0642e7b5a30a317c8f9e2feeec57dc9fc160b5543de18f182263e6076698
Commit:       69e50f77716ba2332e1c48265be296851c913471
Domains:      gemini, vertexai, gcloud, firebase, android, tensorflow, jax

All sources are public GitHub raw endpoints — zero authentication required.
INSERT OR IGNORE guarantees idempotency across multiple runs.
"""
import requests, sqlite3, hashlib, time, re, os, sys
from datetime import datetime, timezone

DB      = os.path.join(os.path.dirname(__file__), "coders_bible.db")
HEADERS = {"User-Agent": "CodersBible/1.0 (documentation indexer; public repos only)"}
DELAY   = 0.35  # polite crawl delay

# ── Shared helpers ────────────────────────────────────────────────────────────

def fetch(url: str) -> str | None:
    """Fetch content from a URL via HTTP GET.
    
    Args:
        url: The URL to fetch.
        
    Returns:
        The response text or None if the request fails.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        time.sleep(DELAY)
        return r.text
    except Exception as e:
        print(f"  SKIP {url}: {e}")
        return None

def chunk_text(text: str, max_len: int = 1500) -> list[str]:
    """Split text into chunks of maximum length while preserving paragraphs.
    
    Args:
        text: The text to split.
        max_len: The maximum length of each chunk.
        
    Returns:
        A list of string chunks.
    """
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
    return [c for c in chunks if len(c) > 60]

def walk_tree(repo: str, branch: str, prefixes: list[str], ext: tuple[str, ...] = (".md", ".rst", ".ipynb"), limit: int = 2000) -> list[str]:
    """Walk GitHub git tree; return list of matching path strings.
    
    Args:
        repo: GitHub repository name.
        branch: Git branch to walk.
        prefixes: List of directory prefixes to filter.
        ext: Tuple of allowed file extensions.
        limit: Maximum number of paths to return.
        
    Returns:
        List of file paths matching criteria.
    """
    url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
    r = requests.get(url, headers=HEADERS, timeout=20)
    time.sleep(DELAY)
    if r.status_code != 200:
        print(f"  tree fail {repo}@{branch}: {r.status_code}")
        return []
    tree = r.json().get("tree", [])
    paths = [
        t["path"] for t in tree
        if t["type"] == "blob"
        and t["path"].endswith(ext)
        and (not prefixes or any(t["path"].startswith(p) for p in prefixes))
    ]
    return paths[:limit]

def insert_fragments(conn: sqlite3.Connection, fragments: list[dict[str, str]]) -> None:
    """Insert scraped document fragments into the SQLite database.
    
    Args:
        conn: SQLite database connection.
        fragments: List of fragment dictionaries.
    """
    ts = datetime.now(timezone.utc).isoformat()
    for f in fragments:
        fid = hashlib.sha256(f["content"].encode()).hexdigest()[:16]
        try:
            conn.execute(
                """INSERT OR IGNORE INTO fragments
                   (id, content, source, tier, ingested_at, ftype, lang_version, tags)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (fid, f["content"], f["source"], f.get("tier", "A"),
                 ts, f.get("ftype", "doc"), f.get("lang_version"), f.get("tags", ""))
            )
        except Exception:
            pass
    conn.commit()

# ── 1. Gemini API / Google AI Python SDK ─────────────────────────────────────

def scrape_gemini() -> list[dict[str, str]]:
    """Scrape Gemini API documentation and return chunks."""
    print("\n=== Scraping Gemini API docs ===")
    frags = []
    repos = [
        # Official Gemini API cookbook (notebooks + guides)
        ("google-gemini/cookbook",           "main",   ["quickstarts/", "examples/", "gemini-2/"],
         "gemini"),
        # Python SDK
        ("google-gemini/generative-ai-python","main",  ["docs/", "samples/"],
         "gemini"),
        # Gemma open-weights model docs
        ("google-deepmind/gemma",            "main",   [""],
         "gemini"),
    ]
    for repo, branch, prefixes, domain in repos:
        paths = walk_tree(repo, branch, prefixes)
        print(f"  {repo}: {len(paths)} files")
        for p in paths:
            raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{p}"
            text = fetch(raw)
            if not text:
                continue
            # Strip notebook JSON down to markdown/code cells only
            if p.endswith(".ipynb"):
                try:
                    import json as _json
                    nb = _json.loads(text)
                    cell_texts = []
                    for cell in nb.get("cells", []):
                        src = "".join(cell.get("source", []))
                        if src.strip():
                            cell_texts.append(src)
                    text = "\n\n".join(cell_texts)
                except Exception:
                    pass
            for c in chunk_text(text):
                frags.append({"content": c, "source": f"{domain}/{p}@github.com",
                              "tier": "A", "ftype": "doc", "tags": "gemini,google-ai"})
    print(f"  Gemini total: {len(frags)} chunks")
    return frags

# ── 2. Vertex AI ──────────────────────────────────────────────────────────────

def scrape_vertexai() -> list[dict[str, str]]:
    """Scrape Vertex AI documentation and return chunks."""
    print("\n=== Scraping Vertex AI docs ===")
    frags = []
    repos = [
        # Vertex AI samples (official Google Cloud)
        ("GoogleCloudPlatform/vertex-ai-samples", "main",
         ["notebooks/official/", "notebooks/community/", "community-content/"],
         "vertexai"),
        # Model Garden notebooks
        ("GoogleCloudPlatform/model-garden-notebooks", "main", [""],
         "vertexai"),
        # Generative AI on Google Cloud
        ("GoogleCloudPlatform/generative-ai", "main",
         ["gemini/", "language/", "search/", "vision/", "audio/"],
         "vertexai"),
    ]
    for repo, branch, prefixes, domain in repos:
        paths = walk_tree(repo, branch, prefixes, ext=(".md", ".ipynb", ".py"))
        print(f"  {repo}: {len(paths)} files")
        for p in paths:
            raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{p}"
            text = fetch(raw)
            if not text:
                continue
            if p.endswith(".ipynb"):
                try:
                    import json as _json
                    nb = _json.loads(text)
                    text = "\n\n".join(
                        "".join(c.get("source", [])) for c in nb.get("cells", [])
                    )
                except Exception:
                    pass
            for c in chunk_text(text):
                frags.append({"content": c, "source": f"{domain}/{p}@github.com",
                              "tier": "A", "ftype": "doc", "tags": "vertexai,gcp"})
    print(f"  Vertex AI total: {len(frags)} chunks")
    return frags

# ── 3. Google Cloud (gcloud CLI + general GCP) ───────────────────────────────

def scrape_gcloud() -> list[dict[str, str]]:
    """Scrape Google Cloud documentation and return chunks."""
    print("\n=== Scraping Google Cloud docs ===")
    frags = []
    repos = [
        # GCP docs (public mirror of cloud.google.com/docs source)
        ("GoogleCloudPlatform/cloud-foundation-fabric", "master",
         ["blueprints/", "modules/", "fast/"],
         "gcloud"),
        # gcloud CLI reference source
        ("twistedpair/google-cloud-sdk", "master",
         ["lib/googlecloudsdk/command_lib/"],
         "gcloud"),
        # GCP best practices + architecture guides
        ("GoogleCloudPlatform/professional-services", "main",
         ["examples/", "tools/"],
         "gcloud"),
        # GCP Python client library docs
        ("googleapis/google-cloud-python", "main",
         ["packages/google-cloud-storage/docs/",
          "packages/google-cloud-bigquery/docs/",
          "packages/google-cloud-pubsub/docs/"],
         "gcloud"),
    ]
    for repo, branch, prefixes, domain in repos:
        paths = walk_tree(repo, branch, prefixes, ext=(".md", ".rst"))
        print(f"  {repo}: {len(paths)} files")
        for p in paths:
            raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{p}"
            text = fetch(raw)
            if not text:
                continue
            for c in chunk_text(text):
                frags.append({"content": c, "source": f"{domain}/{p}@github.com",
                              "tier": "A", "ftype": "doc", "tags": "gcloud,gcp"})
    # google-auth and googleapis-common-protos README pages
    quickrefs = [
        ("googleapis/google-auth-library-python", "main", "README.rst", "gcloud"),
        ("googleapis/google-api-python-client",   "main", "docs/start.md", "gcloud"),
        ("googleapis/google-api-python-client",   "main", "docs/auth.md", "gcloud"),
        ("googleapis/google-api-python-client",   "main", "docs/batch.md", "gcloud"),
        ("googleapis/google-api-python-client",   "main", "docs/pagination.md", "gcloud"),
        ("googleapis/google-api-python-client",   "main", "docs/errors.md", "gcloud"),
        ("googleapis/google-api-python-client",   "main", "docs/media.md", "gcloud"),
    ]
    for repo, branch, path, domain in quickrefs:
        raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
        text = fetch(raw)
        if text:
            for c in chunk_text(text):
                frags.append({"content": c, "source": f"{domain}/{path}@github.com",
                              "tier": "A", "ftype": "doc", "tags": "gcloud,googleapis"})
    print(f"  GCloud total: {len(frags)} chunks")
    return frags

# ── 4. Firebase ───────────────────────────────────────────────────────────────

def scrape_firebase() -> list[dict[str, str]]:
    """Scrape Firebase documentation and return chunks."""
    print("\n=== Scraping Firebase docs ===")
    frags = []
    repos = [
        ("firebase/firebase-admin-python",     "master", [""],    "firebase"),
        ("firebase/firebase-admin-node",       "master", [""],    "firebase"),
        ("firebase/quickstart-python",         "master", [""],    "firebase"),
        ("firebase/quickstart-js",             "master", [""],    "firebase"),
        ("firebase/quickstart-android",        "master", [""],    "firebase"),
        ("firebase/firebase-ios-sdk",          "main",   ["docs/"], "firebase"),
        ("invertase/react-native-firebase",    "main",   ["docs/"], "firebase"),
    ]
    for repo, branch, prefixes, domain in repos:
        paths = walk_tree(repo, branch, prefixes, ext=(".md", ".rst"))
        print(f"  {repo}: {len(paths)} files")
        for p in paths:
            raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{p}"
            text = fetch(raw)
            if not text:
                continue
            for c in chunk_text(text):
                frags.append({"content": c, "source": f"{domain}/{p}@github.com",
                              "tier": "A", "ftype": "doc", "tags": "firebase,google"})
    print(f"  Firebase total: {len(frags)} chunks")
    return frags

# ── 5. Android ───────────────────────────────────────────────────────────────

def scrape_android() -> list[dict[str, str]]:
    """Scrape Android documentation and return chunks."""
    print("\n=== Scraping Android docs ===")
    frags = []
    repos = [
        # Official Android developer samples
        ("android/architecture-samples",  "main",   [""],       "android"),
        ("android/compose-samples",       "main",   [""],       "android"),
        ("android/nowinandroid",          "main",   ["docs/"],  "android"),
        # Jetpack docs source
        ("androidx/androidx",             "androidx-main",
         ["compose/docs/", "navigation/navigation-compose/guide/"],
         "android"),
        # Android Kotlin guides
        ("Kotlin/kotlinx.coroutines",     "master", ["docs/"],  "android"),
        # Google I/O sample (architecture patterns)
        ("google/iosched",                "main",   [""],       "android"),
    ]
    for repo, branch, prefixes, domain in repos:
        paths = walk_tree(repo, branch, prefixes, ext=(".md", ".kt"))
        print(f"  {repo}: {len(paths)} files")
        for p in paths:
            if p.endswith(".kt") and len(p) > 200:
                continue   # skip auto-generated mega-files
            raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{p}"
            text = fetch(raw)
            if not text:
                continue
            for c in chunk_text(text, 1200):
                frags.append({"content": c, "source": f"{domain}/{p}@github.com",
                              "tier": "A", "ftype": "doc", "tags": "android,kotlin"})
    print(f"  Android total: {len(frags)} chunks")
    return frags

# ── 6. TensorFlow ────────────────────────────────────────────────────────────

def scrape_tensorflow() -> list[dict[str, str]]:
    """Scrape TensorFlow documentation and return chunks."""
    print("\n=== Scraping TensorFlow docs ===")
    frags = []
    repos = [
        # Official TF docs (site source)
        ("tensorflow/docs",       "master",
         ["site/en/guide/", "site/en/tutorials/", "site/en/api_docs/"],
         "tensorflow"),
        # TF Keras docs
        ("keras-team/keras",      "master",  ["docs/", "guides/"],    "tensorflow"),
        # TFX (TensorFlow Extended)
        ("tensorflow/tfx",        "master",  ["docs/", "guides/"],    "tensorflow"),
        # TF Model Garden
        ("tensorflow/models",     "master",  ["official/", "research/nlp/"],
         "tensorflow"),
        # TF Lite
        ("tensorflow/tflite-micro", "main",  ["docs/"],               "tensorflow"),
    ]
    for repo, branch, prefixes, domain in repos:
        paths = walk_tree(repo, branch, prefixes, ext=(".md", ".ipynb"))
        print(f"  {repo}: {len(paths)} files")
        for p in paths:
            raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{p}"
            text = fetch(raw)
            if not text:
                continue
            if p.endswith(".ipynb"):
                try:
                    import json as _json
                    nb = _json.loads(text)
                    text = "\n\n".join(
                        "".join(c.get("source", [])) for c in nb.get("cells", [])
                    )
                except Exception:
                    pass
            for c in chunk_text(text):
                frags.append({"content": c, "source": f"{domain}/{p}@github.com",
                              "tier": "A", "ftype": "doc", "tags": "tensorflow,ml"})
    print(f"  TensorFlow total: {len(frags)} chunks")
    return frags

# ── 7. JAX ───────────────────────────────────────────────────────────────────

def scrape_jax() -> list[dict[str, str]]:
    """Scrape JAX documentation and return chunks."""
    print("\n=== Scraping JAX docs ===")
    frags = []
    repos = [
        ("google/jax",       "main", ["docs/"],      "jax"),
        ("google/flax",      "main", ["docs/"],      "jax"),
        ("google/orbax",     "main", ["docs/"],      "jax"),
        ("google-deepmind/optax", "main", ["docs/"], "jax"),
    ]
    for repo, branch, prefixes, domain in repos:
        paths = walk_tree(repo, branch, prefixes, ext=(".md", ".rst", ".ipynb"))
        print(f"  {repo}: {len(paths)} files")
        for p in paths:
            raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{p}"
            text = fetch(raw)
            if not text:
                continue
            if p.endswith(".ipynb"):
                try:
                    import json as _json
                    nb = _json.loads(text)
                    text = "\n\n".join(
                        "".join(c.get("source", [])) for c in nb.get("cells", [])
                    )
                except Exception:
                    pass
            for c in chunk_text(text):
                frags.append({"content": c, "source": f"{domain}/{p}@github.com",
                              "tier": "A", "ftype": "doc", "tags": "jax,ml,google"})
    print(f"  JAX total: {len(frags)} chunks")
    return frags

# ── 8. Google APIs Python Client (gotchas + recipes) ─────────────────────────

def scrape_googleapis_gotchas() -> list[dict[str, str]]:
    """Targeted gotcha/recipe extraction from Google API client guides.
    
    Returns:
        List of fragment dictionaries containing gotchas and recipes.
    """
    print("\n=== Scraping Google APIs gotchas + recipes ===")
    frags = []

    GOTCHA_PATTERNS = re.compile(
        r'(note|warning|caution|important|gotcha|pitfall|common mistake'
        r'|be careful|watch out|don.t forget|remember to|avoid|deprecated'
        r'|breaking change|migration|troubleshoot)',
        re.IGNORECASE
    )
    RECIPE_PATTERNS = re.compile(
        r'(how to|step[- ]by[- ]step|example|sample|quickstart'
        r'|getting started|tutorial|recipe|snippet)',
        re.IGNORECASE
    )

    # curated high-signal gotcha sources within Google ecosystem
    targets = [
        # google-auth
        ("googleapis/google-auth-library-python", "main",
         "README.rst", "gcloud"),
        # service accounts + ADC
        ("GoogleCloudPlatform/python-docs-samples", "main",
         "auth/README.md", "gcloud"),
        # Gemini Python SDK changelog (breaking changes)
        ("google-gemini/generative-ai-python", "main",
         "CHANGELOG.md", "gemini"),
        # Firebase admin gotchas
        ("firebase/firebase-admin-python", "master",
         "CHANGELOG.md", "firebase"),
        # Vertex AI SDK changelog
        ("googleapis/python-aiplatform", "main",
         "CHANGELOG.md", "vertexai"),
        # TF migration guide
        ("tensorflow/docs", "master",
         "site/en/guide/migrate/migration_overview.md", "tensorflow"),
        # Keras migration guide
        ("keras-team/keras", "master",
         "guides/migrating_to_keras_3.md", "tensorflow"),
        # JAX sharp bits (famously dense gotcha doc)
        ("google/jax", "main",
         "docs/notebooks/Common_Gotchas_in_JAX.ipynb", "jax"),
        # Android Compose migration
        ("androidx/androidx", "androidx-main",
         "compose/docs/migrating-to-compose.md", "android"),
    ]

    for repo, branch, path, domain in targets:
        raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
        text = fetch(raw)
        if not text:
            continue
        # Parse notebooks
        if path.endswith(".ipynb"):
            try:
                import json as _json
                nb = _json.loads(text)
                text = "\n\n".join(
                    "".join(c.get("source", [])) for c in nb.get("cells", [])
                )
            except Exception:
                pass
        # Score each chunk for gotcha / recipe content
        for chunk in chunk_text(text, 1200):
            lines = chunk.splitlines()
            header = lines[0] if lines else ""
            is_gotcha = bool(GOTCHA_PATTERNS.search(header) or
                             GOTCHA_PATTERNS.search(chunk[:300]))
            is_recipe = bool(RECIPE_PATTERNS.search(header) or
                             RECIPE_PATTERNS.search(chunk[:300]))
            ftype = "gotcha" if is_gotcha else ("recipe" if is_recipe else "doc")
            frags.append({
                "content": chunk,
                "source":  f"{domain}/{path}@github.com",
                "tier":    "A",
                "ftype":   ftype,
                "tags":    f"google,{domain}",
            })

    print(f"  Google gotchas+recipes: {len(frags)} chunks  "
          f"({sum(1 for f in frags if f['ftype']=='gotcha')} gotchas, "
          f"{sum(1 for f in frags if f['ftype']=='recipe')} recipes)")
    return frags


# ═══════════════════════════════════════════════════════════════════════════════
# GOOGLE_SCRAPERS — plug into scrape_docs.py ALL_SCRAPERS list
# ═══════════════════════════════════════════════════════════════════════════════

GOOGLE_SCRAPERS = [
    ("Gemini API",          scrape_gemini),
    ("Vertex AI",           scrape_vertexai),
    ("Google Cloud",        scrape_gcloud),
    ("Firebase",            scrape_firebase),
    ("Android",             scrape_android),
    ("TensorFlow",          scrape_tensorflow),
    ("JAX",                 scrape_jax),
    ("Google Gotchas",      scrape_googleapis_gotchas),
]


def main() -> None:
    """Run all Google scrapers and insert into the The Coder Bible DB."""
    targets = [a.lower() for a in sys.argv[1:]] if len(sys.argv) > 1 else None

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    before = conn.execute("SELECT COUNT(*) as c FROM fragments").fetchone()["c"]
    print(f"Starting count: {before:,} fragments")

    total_new = 0
    for name, fn in GOOGLE_SCRAPERS:
        if targets and name.lower().split()[0] not in targets and name.lower() not in targets:
            continue
        try:
            frags = fn()
            if frags:
                insert_fragments(conn, frags)
                total_new += len(frags)
                print(f"  -> Inserted {len(frags):,} fragments for {name}")
        except Exception as e:
            print(f"  ERROR in {name}: {e}")

    # Rebuild FTS5 index
    print("\nRebuilding FTS5 index...")
    conn.execute("INSERT INTO bible_fts(bible_fts) VALUES('rebuild')")
    conn.commit()

    after = conn.execute("SELECT COUNT(*) as c FROM fragments").fetchone()["c"]
    print(f"\nDone! {before:,} -> {after:,} fragments (+{after - before:,} new)")
    conn.close()


if __name__ == "__main__":
    main()
