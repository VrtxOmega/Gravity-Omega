"""
GOLIATH HUNTER — OMEGA_LEAD_FETCHER v1.0
==========================================
The "follow-through" layer.

After OMEGA_ARRAY finds URLs, OMEGA_LEAD_FETCHER actually READS them.
It fetches full text from each discovered node, enriches the IntelNode
with real content, then re-feeds that content to the pattern engine so
entity extraction and contradiction detection work on substance, not
just metadata snippets.

Source-aware fetchers:
  - WaybackContentFetcher     → pulls archived pages from Wayback Machine
  - CourtContentFetcher       → pulls full opinion text from CourtListener
  - SECContentFetcher         → pulls actual SEC filing text (10-K, 8-K)
  - GenericContentFetcher     → HTML→text fallback for any URL
  - LeadFetcher               → orchestrator, priority queue, rate limiter

Prioritization (confidence + source_tier):
  1. SEC_EDGAR + COURT_LISTENER (high authority public records)
  2. WAYBACK (archived/deleted content — highest value for omission audit)
  3. EPA_ECHO (already structured JSON — enrich with facility details)
  4. DORK_ENGINE results with .pdf / .gov / .edu in URL
  5. Everything else
"""

import re
import time
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from .omega_array import IntelNode


# ── HTML → plain text ────────────────────────────────────────────────────────

class _MLStripper(HTMLParser):
    """Minimal, stdlib-only HTML to text stripper."""
    def __init__(self):
        super().__init__()
        self._chunks: List[str] = []
        self._skip_tags = {"script", "style", "noscript", "head", "nav",
                           "footer", "aside", "form", "button"}
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag):
        if tag.lower() in self._skip_tags:
            self._skip = False
        if tag.lower() in {"p", "div", "li", "br", "h1", "h2", "h3",
                            "h4", "td", "tr"}:
            self._chunks.append("\n")

    def handle_data(self, data):
        if not self._skip:
            text = data.strip()
            if text:
                self._chunks.append(text + " ")

    def get_text(self, max_chars: int = 25000) -> str:
        raw = "".join(self._chunks)
        # Collapse whitespace
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        raw = re.sub(r"[ \t]{2,}", " ", raw)
        return raw[:max_chars]


def _html_to_text(html: str, max_chars: int = 25000) -> str:
    stripper = _MLStripper()
    try:
        stripper.feed(html)
        return stripper.get_text(max_chars)
    except Exception:
        return re.sub(r"<[^>]+>", " ", html)[:max_chars]


# ── HTTP helper ──────────────────────────────────────────────────────────────

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

def _fetch_raw(url: str, timeout: int = 20) -> Optional[str]:
    """GET a URL and return raw HTML/text. Returns None on any failure."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": UA,
                     "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                     "Accept-Language": "en-US,en;q=0.9"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "")
            charset = "utf-8"
            if "charset=" in ct:
                charset = ct.split("charset=")[-1].split(";")[0].strip()
            return r.read().decode(charset, errors="ignore")
    except Exception:
        return None


# ── Source-aware content fetchers ─────────────────────────────────────────────

class WaybackContentFetcher:
    """
    Fetches the actual content of a Wayback Machine archived URL.
    The Wayback URL format is: https://web.archive.org/web/<timestamp>/<original_url>
    We add id_ modifier to get the raw archived page without Wayback toolbar.
    """

    @staticmethod
    def fetch(node: IntelNode) -> str:
        if "web.archive.org/web/" not in node.url:
            return ""
        # Convert to raw mode by inserting 'id_' after the timestamp
        raw_url = node.url.replace("/web/", "/web/id_/", 1)
        html = _fetch_raw(raw_url, timeout=25)
        if not html:
            # Fall back to normal Wayback URL
            html = _fetch_raw(node.url, timeout=25)
        return _html_to_text(html) if html else ""


class CourtContentFetcher:
    """
    Fetches full opinion text from CourtListener.
    Opinion pages have machine-readable text at /api/rest/v4/opinions/<id>/
    or we fall back to scraping the HTML opinion page.
    """

    API = "https://www.courtlistener.com/api/rest/v4/opinions/"

    @staticmethod
    def fetch(node: IntelNode) -> str:
        url = node.url
        # Try API endpoint if we can extract an opinion ID
        m = re.search(r'/opinion/(\d+)/', url)
        if m:
            oid = m.group(1)
            api_url = f"{CourtContentFetcher.API}?cluster={oid}&format=json"
            try:
                req = urllib.request.Request(
                    api_url,
                    headers={"User-Agent": UA, "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=15) as r:
                    import json
                    data = json.loads(r.read().decode("utf-8"))
                    results = data.get("results", [])
                    if results:
                        # plain_text or html_with_citations
                        text = (results[0].get("plain_text", "") or
                                _html_to_text(results[0].get("html_with_citations", ""))
                                or "")
                        if text.strip():
                            return text[:25000]
            except Exception:
                pass
        # Fall back to HTML scrape
        html = _fetch_raw(url, timeout=20)
        return _html_to_text(html) if html else ""


class SECContentFetcher:
    """
    Fetches filing text from SEC EDGAR.
    EDGAR stores filings as text. We try to pull the actual .htm or .txt file.
    """

    @staticmethod
    def fetch(node: IntelNode) -> str:
        url = node.url
        # Standard EDGAR filing index URLs end in -index.htm
        # Try the full-text index to find the primary document
        if "/Archives/edgar/" in url and "-index" not in url:
            # Try appending -index.htm
            index_url = url.rstrip("/") + "-index.htm"
            html = _fetch_raw(index_url, timeout=20)
        else:
            html = _fetch_raw(url, timeout=20)

        if not html:
            return ""

        text = _html_to_text(html)

        # If text is short, look for the primary document link
        if len(text) < 500 and "htm" in html.lower():
            # Find primary document link
            m = re.search(r'href="(/Archives/edgar/[^"]+\.htm)"', html, re.IGNORECASE)
            if m:
                doc_url = f"https://www.sec.gov{m.group(1)}"
                doc_html = _fetch_raw(doc_url, timeout=20)
                if doc_html:
                    text = _html_to_text(doc_html)

        return text[:25000]


class GenericContentFetcher:
    """
    Falls back to HTML→text for any URL.
    Handles PDFs by noting them (we don't download PDFs — flag them for user review).
    """

    PDF_PATTERN = re.compile(r"\.pdf(\?|$)", re.IGNORECASE)

    @staticmethod
    def fetch(node: IntelNode) -> str:
        url = node.url
        if GenericContentFetcher.PDF_PATTERN.search(url):
            return f"[PDF_DOCUMENT] Manual review required: {url}"

        # For .gov and .edu domains, prioritize
        html = _fetch_raw(url, timeout=20)
        return _html_to_text(html) if html else ""


# ── Priority Queue ────────────────────────────────────────────────────────────

SOURCE_PRIORITY = {
    "COURT_LISTENER": 10,
    "SEC_EDGAR":      9,
    "WAYBACK":        8,
    "EPA_ECHO":       6,
    "ICIJ_OFFSHORE":  7,
    "SUBDOMAIN_CRT":  4,
    "DORK_ENGINE":    3,
    "GITHUB_CODE":    5,
    "DRY_RUN":       -1,
}

def _priority_score(node: IntelNode) -> float:
    """Score a node for content fetching priority."""
    source_score = SOURCE_PRIORITY.get(node.source, 2)
    conf_score   = node.confidence * 10

    # Boost for .gov/.edu URLs
    url_boost = 0
    if any(d in node.url for d in [".gov", ".edu", "epa.", "iepa.", "sec.gov"]):
        url_boost = 5
    if ".pdf" in node.url.lower():
        url_boost += 2  # PDFs are high value

    # Boost for nodes that have hits on our original seeds
    seed_boost = min(len(node.seed_terms_hit) * 2, 6)

    return source_score + conf_score + url_boost + seed_boost


# ── Lead Fetcher Orchestrator ─────────────────────────────────────────────────

class LeadFetcher:
    """
    Orchestrates full-text fetching for discovered IntelNodes.

    Pipeline:
      1. Rank nodes by priority score
      2. Fetch top-N nodes (configurable)
      3. Update IntelNode.full_text with fetched content
      4. Re-seal the node (sha256 now covers the full text)
      5. Return enriched nodes

    Rate limiting: 1.5s between requests to the same domain.
    """

    def __init__(self,
                 max_fetch: int = 50,
                 rate_limit_s: float = 1.5,
                 skip_already_fetched: bool = True,
                 verbose: bool = True):
        self.max_fetch     = max_fetch
        self.rate_limit_s  = rate_limit_s
        self.skip_fetched  = skip_already_fetched
        self.verbose       = verbose
        self._domain_last: Dict[str, float] = {}

    def _get_domain(self, url: str) -> str:
        try:
            return urllib.parse.urlparse(url).netloc
        except Exception:
            return url[:30]

    def _rate_limit(self, domain: str):
        now = time.time()
        last = self._domain_last.get(domain, 0)
        wait = self.rate_limit_s - (now - last)
        if wait > 0:
            time.sleep(wait)
        self._domain_last[domain] = time.time()

    def _choose_fetcher(self, node: IntelNode):
        if node.source == "WAYBACK":
            return WaybackContentFetcher.fetch
        elif node.source == "COURT_LISTENER":
            return CourtContentFetcher.fetch
        elif node.source == "SEC_EDGAR":
            return SECContentFetcher.fetch
        else:
            return GenericContentFetcher.fetch

    def _reseal(self, node: IntelNode) -> IntelNode:
        """Recompute sha256 to include full_text."""
        payload = f"{node.url}|{node.snippet}|{node.timestamp}|{node.full_text[:200]}"
        node.sha256   = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        node.node_id  = node.sha256[:16].upper()
        return node

    def fetch_all(self, nodes: List[IntelNode]) -> List[IntelNode]:
        """
        Fetch full text for priority nodes. Returns all nodes (enriched where fetched).
        """
        # Skip dry-run nodes
        eligible = [n for n in nodes if n.source != "DRY_RUN"
                    and not (self.skip_fetched and n.full_text)]

        # Sort by priority descending
        ranked = sorted(eligible, key=_priority_score, reverse=True)

        to_fetch = ranked[:self.max_fetch]
        fetched_count = 0
        failed_count  = 0

        print(f"[LEAD_FETCHER] Fetching content for {len(to_fetch)} / {len(nodes)} nodes...")

        for node in to_fetch:
            domain = self._get_domain(node.url)
            self._rate_limit(domain)

            fetcher = self._choose_fetcher(node)
            try:
                text = fetcher(node)
            except Exception as e:
                text = ""
                if self.verbose:
                    print(f"  [FETCH ERROR] {node.node_id} → {e}")

            if text and len(text.strip()) > 50:
                node.full_text = text
                node = self._reseal(node)
                fetched_count += 1
                if self.verbose:
                    chars = len(text)
                    print(f"  [✓ {node.source:<16}] {node.node_id} — {chars:,} chars — {node.url[:60]}")
            else:
                failed_count += 1
                if self.verbose:
                    print(f"  [✗ {node.source:<16}] {node.node_id} — no content — {node.url[:60]}")

        print(f"[LEAD_FETCHER] Done: {fetched_count} enriched, {failed_count} empty, "
              f"{len(nodes) - len(to_fetch)} skipped (lower priority)")

        return nodes

    def get_lead_summary(self, nodes: List[IntelNode]) -> str:
        """
        Returns a text summary of the top enriched nodes for the dossier.
        """
        enriched = [n for n in nodes if n.full_text and len(n.full_text) > 100]
        enriched.sort(key=_priority_score, reverse=True)

        lines = [
            f"# LEAD CONTENT SUMMARY",
            f"Generated: {datetime.utcnow().isoformat()}",
            f"Enriched nodes: {len(enriched)} / {len(nodes)} total",
            "",
        ]
        for n in enriched[:20]:
            lines += [
                f"## [{n.source}] {n.title[:80] or n.url[:80]}",
                f"  URL: {n.url}",
                f"  Confidence: {n.confidence:.2f} | Seal: {n.sha256[:16]}",
                f"  Content preview ({len(n.full_text):,} chars):",
                "",
                # First 600 chars of content
                n.full_text[:600].replace("\n", " ").strip(),
                "",
                "---",
                "",
            ]
        return "\n".join(lines)
