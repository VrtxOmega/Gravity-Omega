"""Phase 2 scrapers — NO GitHub API. Direct raw URLs + official doc sites only."""
import requests, sqlite3, hashlib, time, re, os
from bs4 import BeautifulSoup
from datetime import datetime

DB = os.path.join(os.path.dirname(__file__), "coders_bible.db")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DocsIndexer/2.0)"}
DELAY = 0.4

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        time.sleep(DELAY)
        return r.text
    except Exception as e:
        print(f"  SKIP {url[:80]}: {e}")
        return None

def chunk(text, mx=1400):
    paras = re.split(r'\n{2,}', text.strip())
    chunks, cur = [], ""
    for p in paras:
        if len(cur)+len(p) > mx and cur:
            chunks.append(cur.strip())
            cur = p
        else:
            cur += ("\n\n"+p if cur else p)
    if cur.strip(): chunks.append(cur.strip())
    return [c for c in chunks if len(c) > 60]

def text_from(html, sel="article,main,.content,body"):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(["script","style","nav","footer"]): t.decompose()
    el = soup.select_one(sel) or soup.body
    return el.get_text("\n", strip=True) if el else ""

def save(conn, frags):
    for f in frags:
        fid = hashlib.sha256(f["content"].encode()).hexdigest()[:16]
        try:
            conn.execute("INSERT OR IGNORE INTO fragments (id,content,source,tier,ingested_at) VALUES(?,?,?,?,?)",
                (fid, f["content"], f["source"], f["tier"], datetime.utcnow().isoformat()))
        except: pass
    conn.commit()
    return len(frags)

# ── Kubernetes ── official docs pages (no API)
def scrape_k8s():
    print("\n=== Kubernetes ===")
    pages = [
        "concepts/overview/what-is-kubernetes","concepts/overview/components",
        "concepts/workloads/pods","concepts/workloads/deployments",
        "concepts/workloads/statefulsets","concepts/workloads/daemonset",
        "concepts/workloads/jobs","concepts/workloads/cronjobs",
        "concepts/services-networking/service","concepts/services-networking/ingress",
        "concepts/services-networking/network-policies","concepts/storage/volumes",
        "concepts/storage/persistent-volumes","concepts/storage/storage-classes",
        "concepts/configuration/configmap","concepts/configuration/secret",
        "concepts/configuration/resource-management-for-pods-and-containers",
        "concepts/security/overview","concepts/scheduling-eviction/assign-pod-node",
        "concepts/cluster-administration/logging","concepts/extend-kubernetes/api-extension/custom-resources",
        "tasks/run-application/run-stateless-application-deployment",
        "tasks/configure-pod-container/configure-liveness-readiness-startup-probes",
        "tasks/manage-kubernetes-objects/declarative-config",
        "tasks/access-application-cluster/access-cluster",
        "tasks/access-application-cluster/ingress-minikube",
        "reference/kubectl/cheatsheet","reference/glossary",
        "setup/production-environment/tools/kubeadm/install-kubeadm",
        "setup/production-environment/container-runtimes",
    ]
    frags = []
    for p in pages:
        html = fetch(f"https://kubernetes.io/docs/{p}/")
        if not html: continue
        t = text_from(html, "article,.td-content")
        for c in chunk(t): frags.append({"content":c,"source":f"kubernetes/{p}@kubernetes.io","tier":"A"})
        print(f"  k8s/{p.split('/')[-1]}: {len(chunk(t))}")
    return frags

# ── C# ── docs.microsoft.com raw markdown mirror + HTML
def scrape_csharp():
    print("\n=== C# ===")
    # Direct raw markdown from dotnet/docs — known file paths, no API
    raw_files = [
        "docs/csharp/tour-of-csharp/overview.md",
        "docs/csharp/fundamentals/types/index.md",
        "docs/csharp/fundamentals/types/classes.md",
        "docs/csharp/fundamentals/types/interfaces.md",
        "docs/csharp/fundamentals/types/records.md",
        "docs/csharp/fundamentals/types/generics.md",
        "docs/csharp/fundamentals/object-oriented/index.md",
        "docs/csharp/fundamentals/object-oriented/polymorphism.md",
        "docs/csharp/fundamentals/object-oriented/inheritance.md",
        "docs/csharp/fundamentals/exceptions/index.md",
        "docs/csharp/fundamentals/functional/pattern-matching.md",
        "docs/csharp/fundamentals/functional/discards.md",
        "docs/csharp/fundamentals/coding-style/identifier-names.md",
        "docs/csharp/language-reference/keywords/index.md",
        "docs/csharp/language-reference/operators/index.md",
        "docs/csharp/language-reference/operators/lambda-expressions.md",
        "docs/csharp/language-reference/operators/async.md",
        "docs/csharp/language-reference/statements/index.md",
        "docs/csharp/language-reference/statements/iteration-statements.md",
        "docs/csharp/language-reference/statements/selection-statements.md",
        "docs/csharp/language-reference/statements/exception-handling-statements.md",
        "docs/csharp/linq/index.md","docs/csharp/linq/query-expression-basics.md",
        "docs/csharp/asynchronous-programming/index.md",
        "docs/csharp/asynchronous-programming/async-scenarios.md",
        "docs/csharp/programming-guide/delegates/index.md",
        "docs/csharp/programming-guide/events/index.md",
        "docs/csharp/programming-guide/generics/index.md",
        "docs/csharp/programming-guide/nullable-types/index.md",
        "docs/csharp/programming-guide/arrays/index.md",
        "docs/csharp/programming-guide/strings/index.md",
        "docs/csharp/programming-guide/collections/index.md",
        "docs/csharp/programming-guide/concepts/async/index.md",
        "docs/csharp/programming-guide/concepts/linq/index.md",
        "docs/csharp/programming-guide/file-system/index.md",
        "docs/csharp/iterators.md","docs/csharp/nullable-references.md",
        "docs/csharp/whats-new/csharp-12.md","docs/csharp/whats-new/csharp-11.md",
        "docs/csharp/whats-new/csharp-10.md",
        # language spec chapters
        "docs/csharp/language-reference/language-specification/introduction.md",
        "docs/csharp/language-reference/language-specification/types.md",
        "docs/csharp/language-reference/language-specification/expressions.md",
        "docs/csharp/language-reference/language-specification/statements.md",
        "docs/csharp/language-reference/language-specification/classes.md",
        "docs/csharp/language-reference/language-specification/interfaces.md",
        "docs/csharp/language-reference/language-specification/enums.md",
        "docs/csharp/language-reference/language-specification/delegates.md",
        "docs/csharp/language-reference/language-specification/exceptions.md",
        "docs/csharp/language-reference/language-specification/namespaces.md",
        # csharplang proposals
        "proposals/csharp-8.0/nullable-reference-types.md",
        "proposals/csharp-9.0/records.md","proposals/csharp-10.0/lambda-improvements.md",
        "proposals/csharp-11.0/required-members.md","proposals/csharp-12.0/primary-constructors.md",
    ]
    frags = []
    for f in raw_files:
        repo = "dotnet/docs" if f.startswith("docs/") else "dotnet/csharplang"
        branch = "main"
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/{f}"
        t = fetch(url)
        if t:
            for c in chunk(t): frags.append({"content":c,"source":f"csharp/{f}@github.com","tier":"A"})
    print(f"  C# total: {len(frags)} chunks")
    return frags

# ── C/C++ ── cppreference HTML + MS Docs raw + core guidelines
def scrape_cpp():
    print("\n=== C/C++ ===")
    frags = []
    # cppreference HTML pages
    cpp_pages = [
        "c/language","c/language/types","c/language/operator_arithmetic",
        "c/language/statements","c/language/functions","c/language/array",
        "c/language/pointer","c/language/struct","c/language/memory",
        "c/string/byte","c/io","c/numeric/math",
        "cpp/language","cpp/language/types","cpp/language/classes",
        "cpp/language/templates","cpp/language/lambda","cpp/language/coroutines",
        "cpp/language/move_constructor","cpp/language/raii",
        "cpp/language/operators","cpp/language/exceptions",
        "cpp/language/namespace","cpp/language/scope",
        "cpp/container","cpp/container/vector","cpp/container/map",
        "cpp/container/unordered_map","cpp/container/set","cpp/container/list",
        "cpp/algorithm","cpp/numeric","cpp/string","cpp/string/basic_string",
        "cpp/thread","cpp/atomic","cpp/chrono","cpp/filesystem",
        "cpp/memory","cpp/memory/unique_ptr","cpp/memory/shared_ptr",
        "cpp/utility/functional","cpp/utility/optional","cpp/utility/variant",
    ]
    for p in cpp_pages:
        html = fetch(f"https://en.cppreference.com/w/{p}")
        if not html: continue
        t = text_from(html, "#mw-content-text")
        for c in chunk(t): frags.append({"content":c,"source":f"c/{p}@cppreference.com","tier":"A"})
        print(f"  cpp/{p.split('/')[-1]}: {len(chunk(t))}")
    # C++ Core Guidelines raw
    for f in ["CppCoreGuidelines.md"]:
        t = fetch(f"https://raw.githubusercontent.com/isocpp/CppCoreGuidelines/master/{f}")
        if t:
            for c in chunk(t): frags.append({"content":c,"source":f"c/CppCoreGuidelines@github.com","tier":"A"})
    print(f"  C/C++ total: {len(frags)} chunks")
    return frags

# ── CSS ── MDN bulk via known paths
def scrape_css():
    print("\n=== CSS ===")
    props = [
        "align-content","align-items","align-self","animation","animation-delay",
        "animation-direction","animation-duration","animation-fill-mode",
        "animation-iteration-count","animation-name","animation-play-state",
        "animation-timing-function","aspect-ratio","background","background-attachment",
        "background-clip","background-color","background-image","background-origin",
        "background-position","background-repeat","background-size","border",
        "border-collapse","border-radius","box-shadow","box-sizing",
        "calc","clip-path","color","column-gap","columns","content","cursor",
        "display","filter","flex","flex-direction","flex-flow","flex-wrap",
        "float","font","font-family","font-size","font-style","font-weight",
        "gap","grid","grid-area","grid-column","grid-row","grid-template",
        "grid-template-areas","grid-template-columns","grid-template-rows",
        "height","justify-content","justify-items","justify-self",
        "left","letter-spacing","line-height","list-style",
        "margin","max-height","max-width","min-height","min-width",
        "object-fit","opacity","order","outline","overflow","padding",
        "pointer-events","position","resize","right","row-gap",
        "text-align","text-decoration","text-overflow","text-shadow",
        "text-transform","top","transform","transform-origin","transition",
        "user-select","vertical-align","visibility","white-space",
        "width","word-break","word-wrap","z-index",
        "@media","@keyframes","@import","@supports",
        ":hover",":focus",":active",":nth-child",":first-child",":last-child",
        "::before","::after","::placeholder",
        "var","calc","clamp","min","max",
    ]
    frags = []
    for p in props:
        html = fetch(f"https://developer.mozilla.org/en-US/docs/Web/CSS/{p}")
        if not html: continue
        t = text_from(html, "article")
        for c in chunk(t): frags.append({"content":c,"source":f"css/{p}@mdn","tier":"A"})
    print(f"  CSS total: {len(frags)} chunks")
    return frags

# ── HTML ── MDN elements + WHATWG spec
def scrape_html():
    print("\n=== HTML ===")
    elements = [
        "a","abbr","address","area","article","aside","audio",
        "b","base","blockquote","body","br","button",
        "canvas","caption","cite","code","col","colgroup",
        "data","datalist","dd","del","details","dfn","dialog","div","dl","dt",
        "em","embed","fieldset","figcaption","figure","footer","form",
        "h1","h2","h3","head","header","hgroup","hr","html",
        "i","iframe","img","input","ins",
        "kbd","label","legend","li","link",
        "main","map","mark","menu","meta","meter",
        "nav","noscript","object","ol","optgroup","option","output",
        "p","picture","pre","progress","q","rp","rt","ruby",
        "s","samp","script","search","section","select","slot","small",
        "source","span","strong","style","sub","summary","sup",
        "table","tbody","td","template","textarea","tfoot","th","thead","time",
        "title","tr","track","u","ul","var","video","wbr",
    ]
    frags = []
    for el in elements:
        html = fetch(f"https://developer.mozilla.org/en-US/docs/Web/HTML/Element/{el}")
        if not html: continue
        t = text_from(html, "article")
        for c in chunk(t): frags.append({"content":c,"source":f"html/Element/{el}@mdn","tier":"A"})
    # HTML attributes
    for attr in ["accept","action","alt","async","autocomplete","autofocus","charset",
                 "class","contenteditable","crossorigin","data-*","defer","disabled",
                 "download","draggable","enctype","for","form","hidden","href","id",
                 "inputmode","lang","loading","method","multiple","name","novalidate",
                 "pattern","placeholder","readonly","rel","required","role","src",
                 "srcset","tabindex","target","title","type","value"]:
        html = fetch(f"https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/{attr}")
        if not html: continue
        t = text_from(html, "article")
        for c in chunk(t): frags.append({"content":c,"source":f"html/Attributes/{attr}@mdn","tier":"A"})
    print(f"  HTML total: {len(frags)} chunks")
    return frags

# ── Kotlin ── kotlinlang.org official HTML
def scrape_kotlin():
    print("\n=== Kotlin ===")
    pages = [
        "basic-syntax","basic-types","strings","control-flow","returns",
        "exceptions","classes","inheritance","properties","interfaces",
        "functional-interfaces","data-classes","sealed-classes","enum-classes",
        "inline-classes","object-declarations","delegation","generics",
        "nested-classes","type-aliases","functions","lambdas",
        "inline-functions","operator-overloading","null-safety","equality",
        "this-expressions","extensions","destructuring-declarations",
        "type-checks-and-casts","collections-overview","constructing-collections",
        "iterators","ranges","sequences","list-operations","set-operations",
        "map-operations","collection-filtering","collection-transformations",
        "collection-aggregate-operations","collection-write-operations",
        "coroutines-overview","composing-suspending-functions",
        "coroutine-context-and-dispatchers","flow","channels","select-expression",
        "annotations","reflection","scope-functions","opt-in-requirements",
        "serialization","multiplatform","android-overview",
        "jvm-get-started","gradle","maven",
    ]
    frags = []
    for p in pages:
        html = fetch(f"https://kotlinlang.org/docs/{p}.html")
        if not html: continue
        t = text_from(html, "article,.article-content")
        for c in chunk(t): frags.append({"content":c,"source":f"kotlin/{p}@kotlinlang.org","tier":"A"})
        print(f"  kotlin/{p}: {len(chunk(t))}")
    return frags

# ── Bash ── GNU manual + TLDP ABS (no GitHub API)
def scrape_bash():
    print("\n=== Bash ===")
    frags = []
    html = fetch("https://www.gnu.org/software/bash/manual/bash.html")
    if html:
        soup = BeautifulSoup(html,"html.parser")
        for tag in soup.find_all(["script","style","nav"]): tag.decompose()
        for sec in soup.find_all(["h2","h3","h4"]):
            title = sec.get_text(strip=True)
            parts, cur = [], sec.next_sibling
            while cur and getattr(cur,"name",None) not in ["h2","h3","h4"]:
                if hasattr(cur,"get_text"): parts.append(cur.get_text("\n",strip=True))
                cur = getattr(cur,"next_sibling",None)
            t = title + "\n" + "\n".join(parts)
            for c in chunk(t,1200): frags.append({"content":c,"source":"bash/manual@gnu.org","tier":"A"})
    # TLDP ABS guide sections
    abs_pages = ["abs-guide.html"]
    for p in abs_pages:
        html = fetch(f"https://tldp.org/LDP/abs/{p}")
        if not html: continue
        t = text_from(html)
        for c in chunk(t,1200): frags.append({"content":c,"source":f"bash/abs/{p}@tldp.org","tier":"B"})
    # man pages (via man7.org)
    bash_cmds = ["bash.1","test.1","read.1","echo.1","printf.1","expr.1",
                 "grep.1","sed.1","awk.1","find.1","xargs.1","cut.1","sort.1",
                 "uniq.1","tr.1","wc.1","head.1","tail.1","cat.1","tee.1",
                 "chmod.1","chown.1","ln.1","cp.1","mv.1","rm.1","mkdir.1"]
    for m in bash_cmds:
        html = fetch(f"https://man7.org/linux/man-pages/man1/{m}.html")
        if not html: continue
        t = text_from(html, "#content,body")
        for c in chunk(t,1000): frags.append({"content":c,"source":f"bash/man/{m}@man7.org","tier":"A"})
    print(f"  Bash total: {len(frags)} chunks")
    return frags

SCRAPERS = [
    ("Kubernetes", scrape_k8s),
    ("C#",         scrape_csharp),
    ("C/C++",      scrape_cpp),
    ("CSS",        scrape_css),
    ("HTML",       scrape_html),
    ("Kotlin",     scrape_kotlin),
    ("Bash",       scrape_bash),
]

if __name__ == "__main__":
    import sys
    targets = [t.lower() for t in sys.argv[1:]]
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    before = conn.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
    print(f"Start: {before:,} fragments")
    total = 0
    for name, fn in SCRAPERS:
        if targets and name.lower() not in targets: continue
        try:
            frags = fn()
            n = save(conn, frags)
            total += n
            print(f"  -> +{n} for {name}")
        except Exception as e:
            print(f"  ERROR {name}: {e}")
    print("\nRebuilding FTS...")
    conn.execute("INSERT INTO bible_fts(bible_fts) VALUES('rebuild')")
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
    print(f"Done: {before:,} -> {after:,} (+{after-before:,})")
    conn.close()
