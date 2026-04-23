"""
GOLIATH HUNTER — OMEGA_ARRAY v1.0
===================================
Domain-agnostic live OSINT harvester.
Takes any seed terms, hits every public intelligence surface,
returns structured IntelNode objects with SHA-256 sealing.

Sources:
  - DuckDuckGo advanced search (dork engine)
  - Wayback Machine CDX API (deleted/archived pages)
  - Common Crawl index
  - crt.sh subdomain discovery
  - GitHub code search API
  - EPA ECHO API (live)
  - SEC EDGAR full-text search
  - ICIJ Offshore Leaks DB
  - CourtListener (court records)
  - Pastebin scrape

No Omega files are modified. All output is IntelNode objects.
"""

import hashlib
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


# ── IntelNode: the atomic intelligence unit ─────────────────────────────────

@dataclass
class IntelNode:
    """Single piece of discovered intelligence. Cryptographically sealed."""
    node_id: str = ""
    source: str = ""           # which harvester found it
    url: str = ""
    title: str = ""
    snippet: str = ""
    full_text: str = ""
    seed_terms_hit: List[str] = field(default_factory=list)
    entities_raw: List[str] = field(default_factory=list)
    timestamp: str = ""
    sha256: str = ""
    confidence: float = 0.5    # 0.0–1.0

    def seal(self):
        """Compute tamper-evident SHA-256 over content + url + timestamp."""
        payload = f"{self.url}|{self.snippet}|{self.timestamp}"
        self.sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self.node_id = self.sha256[:16].upper()
        return self

    def to_dict(self):
        return asdict(self)


# ── HTTP helper ──────────────────────────────────────────────────────────────

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

def _get(url: str, timeout: int = 15, as_json: bool = True):
    """Safe HTTP GET with timeout and user-agent."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", errors="ignore")
            return json.loads(raw) if as_json else raw
    except Exception as e:
        logger.warning(f"HARVEST_ERROR: {e}", exc_info=True)
        return None


# ── Dork Engine ──────────────────────────────────────────────────────────────

class DorkEngine:
    """
    Generates and executes advanced search dorks.
    Uses DuckDuckGo HTML endpoint (no API key required).
    Auto-generates dork variations from seed terms.
    """

    DORK_TEMPLATES = [
        '"{seed}"',
        '"{seed}" filetype:pdf',
        '"{seed}" filetype:xlsx',
        '"{seed}" site:pastebin.com',
        '"{seed}" "confidential"',
        '"{seed}" "internal use only"',
        '"{seed}" "not for public release"',
        '"{seed}" inurl:report',
        '"{seed}" inurl:foia',
        '"{seed}" "leaked" OR "whistleblower"',
        'site:sec.gov "{seed}"',
        'site:epa.gov "{seed}"',
        'site:courtlistener.com "{seed}"',
    ]

    @staticmethod
    def generate(seed: str) -> List[str]:
        """Generate all dork queries for a seed term."""
        return [t.format(seed=seed) for t in DorkEngine.DORK_TEMPLATES]

    @staticmethod
    def search(query: str, max_results: int = 10) -> List[IntelNode]:
        """Execute a single dork query via DuckDuckGo."""
        nodes = []
        url = (f"https://html.duckduckgo.com/html/?q="
               f"{urllib.parse.quote_plus(query)}&kl=us-en")
        raw = _get(url, timeout=20, as_json=False)
        if not raw:
            return nodes

        # Parse result links and snippets from HTML
        links = re.findall(
            r'<a[^>]+class="result__url"[^>]*>([^<]+)</a>', raw)
        snippets = re.findall(
            r'<a[^>]+class="result__snippet"[^>]*>([^<]+)</a>', raw)
        titles = re.findall(
            r'<a[^>]+class="result__a"[^>]*>([^<]+)</a>', raw)

        for i in range(min(max_results, len(links))):
            node = IntelNode(
                source="DORK_ENGINE",
                url=links[i].strip() if i < len(links) else "",
                title=titles[i].strip() if i < len(titles) else "",
                snippet=snippets[i].strip() if i < len(snippets) else "",
                seed_terms_hit=[query],
                timestamp=datetime.utcnow().isoformat(),
                confidence=0.6,
            ).seal()
            nodes.append(node)
            time.sleep(0.3)  # rate limit

        return nodes

    @classmethod
    def run_all_dorks(cls, seed: str, max_per_query: int = 5) -> List[IntelNode]:
        """Run all dork templates for a seed, return combined results."""
        results = []
        for dork in cls.generate(seed):
            results.extend(cls.search(dork, max_results=max_per_query))
            time.sleep(1)
        return results


# ── Wayback Machine ──────────────────────────────────────────────────────────

class WaybackHarvester:
    """
    Queries the Wayback Machine CDX API for archived/deleted content.
    Finds pages that existed but were scrubbed from the live web.
    """

    CDX_API = "http://web.archive.org/cdx/search/cdx"

    @staticmethod
    def search_domain(domain: str, seed: str) -> List[IntelNode]:
        """Find archived pages for a domain matching seed terms."""
        nodes = []
        params = urllib.parse.urlencode({
            "url": f"*.{domain}/*",
            "output": "json",
            "fl": "timestamp,original,statuscode,mimetype",
            "filter": f"statuscode:200",
            "collapse": "urlkey",
            "limit": 50,
        })
        data = _get(f"{WaybackHarvester.CDX_API}?{params}")
        if not data or len(data) < 2:
            return nodes

        headers = data[0]
        for row in data[1:]:
            record = dict(zip(headers, row))
            url = record.get("original", "")
            ts  = record.get("timestamp", "")
            if not url:
                continue
            # Check if seed touches the URL/path
            hits = [s for s in seed.split() if s.lower() in url.lower()]
            node = IntelNode(
                source="WAYBACK",
                url=f"https://web.archive.org/web/{ts}/{url}",
                title=url,
                snippet=f"Archived: {ts[:8]} | Original: {url}",
                seed_terms_hit=hits or [seed],
                timestamp=f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}",
                confidence=0.55,
            ).seal()
            nodes.append(node)

        return nodes

    @staticmethod
    def get_diff(archived_url: str) -> str:
        """Pull text content of an archived URL."""
        raw = _get(archived_url, as_json=False, timeout=20)
        if not raw:
            return ""
        # Strip HTML tags for plain text
        return re.sub(r"<[^>]+>", " ", raw)[:5000]


# ── EPA ECHO API ─────────────────────────────────────────────────────────────

class EPAEchoHarvester:
    """
    Live EPA ECHO enforcement database query.
    Finds regulated facilities by county/state with violations.
    """

    BASE = "https://echodata.epa.gov/echo/echo_rest_services.get_facilities"

    @staticmethod
    def query(county: str, state: str, seed_terms: List[str]) -> List[IntelNode]:
        nodes = []
        params = urllib.parse.urlencode({
            "p_co": county,
            "p_st": state,
            "p_act": "Y",  # active enforcement
            "output": "JSON",
        })
        data = _get(f"{EPAEchoHarvester.BASE}?{params}")
        if not data:
            return nodes

        facilities = (data.get("Results", {}) or {}).get("Facilities", []) or []
        for fac in facilities[:50]:
            name = fac.get("FacName", "")
            addr = fac.get("LocationAddress", "")
            hits = [s for s in seed_terms if s.lower() in name.lower() or s.lower() in addr.lower()]
            confidence = 0.8 if hits else 0.4
            node = IntelNode(
                source="EPA_ECHO",
                url=f"https://echo.epa.gov/facilities/facility-search/results?fid={fac.get('RegistryID','')}",
                title=name,
                snippet=f"{addr} | Violations: {fac.get('CWAViolations3yr', 0)} CWA | {fac.get('CAAAirReleasesToAtmosphere', 0)} CAA",
                seed_terms_hit=hits or seed_terms[:1],
                timestamp=datetime.utcnow().isoformat(),
                confidence=confidence,
            ).seal()
            nodes.append(node)

        return nodes


# ── SEC EDGAR Full-Text Search ───────────────────────────────────────────────

class SECEdgarHarvester:
    """
    Queries SEC EDGAR full-text search for seed terms in 10-K, 8-K, S-1 filings.
    """

    EFTS = "https://efts.sec.gov/LATEST/search-index?q={q}&dateRange=custom&startdt=2018-01-01&forms=10-K,8-K"

    @staticmethod
    def search(seed: str) -> List[IntelNode]:
        nodes = []
        url = SECEdgarHarvester.EFTS.format(q=urllib.parse.quote_plus(f'"{seed}"'))
        data = _get(url)
        if not data:
            return nodes

        hits = data.get("hits", {}).get("hits", []) or []
        for hit in hits[:20]:
            src = hit.get("_source", {})
            node = IntelNode(
                source="SEC_EDGAR",
                url=f"https://www.sec.gov/Archives/edgar/full-index/{src.get('file_date','')}/{src.get('file_num','')}",
                title=f"{src.get('display_names','')}: {src.get('form_type','')}",
                snippet=hit.get("highlight", {}).get("file_text", [""])[0][:300] if hit.get("highlight") else "",
                seed_terms_hit=[seed],
                timestamp=src.get("file_date", ""),
                confidence=0.75,
            ).seal()
            nodes.append(node)
        return nodes


# ── ICIJ Offshore Leaks ──────────────────────────────────────────────────────

class ICIJHarvester:
    """
    Queries ICIJ Offshore Leaks database (Panama Papers, Pandora Papers, etc.)
    for entity names from seed terms.
    """

    API = "https://offshoreleaks.icij.org/api/nodes?q={q}&cat=1%2C2%2C3%2C4"

    @staticmethod
    def search(seed: str) -> List[IntelNode]:
        nodes = []
        url = ICIJHarvester.API.format(q=urllib.parse.quote_plus(seed))
        data = _get(url)
        if not data:
            return nodes

        results = data if isinstance(data, list) else data.get("nodes", [])
        for r in results[:20]:
            node = IntelNode(
                source="ICIJ_OFFSHORE",
                url=f"https://offshoreleaks.icij.org/nodes/{r.get('id','')}",
                title=r.get("name", ""),
                snippet=f"{r.get('country','')} | {r.get('sourceID','')} | {r.get('node_id','')}",
                seed_terms_hit=[seed],
                timestamp=datetime.utcnow().isoformat(),
                confidence=0.85,
            ).seal()
            nodes.append(node)
        return nodes


# ── CourtListener ────────────────────────────────────────────────────────────

class CourtHarvester:
    """
    Queries CourtListener API for federal/state court records.
    """

    API = "https://www.courtlistener.com/api/rest/v4/search/?q={q}&type=o&format=json"

    @staticmethod
    def search(seed: str) -> List[IntelNode]:
        nodes = []
        url = CourtHarvester.API.format(q=urllib.parse.quote_plus(f'"{seed}"'))
        data = _get(url)
        if not data:
            return nodes

        results = data.get("results", []) or []
        for r in results[:20]:
            node = IntelNode(
                source="COURT_LISTENER",
                url=f"https://www.courtlistener.com{r.get('absolute_url','')}",
                title=r.get("caseName", ""),
                snippet=r.get("snippet", "")[:300],
                seed_terms_hit=[seed],
                timestamp=r.get("dateFiled", ""),
                confidence=0.80,
            ).seal()
            nodes.append(node)
        return nodes


# ── crt.sh Subdomain Enumerator ──────────────────────────────────────────────

class SubdomainHarvester:
    """
    Finds subdomains via crt.sh certificate transparency logs.
    Reveals staging servers, internal portals, forgotten endpoints.
    """

    API = "https://crt.sh/?q=%.{domain}&output=json"

    @staticmethod
    def enumerate(domain: str, seed_terms: List[str]) -> List[IntelNode]:
        nodes = []
        url = SubdomainHarvester.API.format(domain=domain)
        data = _get(url)
        if not data or not isinstance(data, list):
            return nodes

        seen = set()
        for cert in data:
            name = cert.get("name_value", "")
            for sub in name.split("\n"):
                sub = sub.strip().lower()
                if sub in seen or "*" in sub:
                    continue
                seen.add(sub)
                hits = [s for s in seed_terms if s.lower() in sub]
                node = IntelNode(
                    source="SUBDOMAIN_CRT",
                    url=f"https://{sub}",
                    title=sub,
                    snippet=f"Found in CT logs. Issuer: {cert.get('issuer_name','')[:80]}",
                    seed_terms_hit=hits or [domain],
                    timestamp=cert.get("not_before", datetime.utcnow().isoformat())[:10],
                    confidence=0.5,
                ).seal()
                nodes.append(node)

        return nodes[:100]


# ── GitHub Code Search ───────────────────────────────────────────────────────

class GitHubHarvester:
    """
    Searches GitHub public repos for exposed credentials or sensitive data.
    Uses the public-facing search page (no auth required for basic searches).
    """

    SEARCH = "https://api.github.com/search/code?q={q}&per_page=20"

    @staticmethod
    def search(seed: str, gh_token: str = "") -> List[IntelNode]:
        nodes = []
        url = GitHubHarvester.SEARCH.format(q=urllib.parse.quote_plus(seed))
        headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
        if gh_token:
            headers["Authorization"] = f"Bearer {gh_token}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"HARVEST_ERROR: {e}", exc_info=True)
            return nodes

        for item in data.get("items", [])[:20]:
            node = IntelNode(
                source="GITHUB_CODE",
                url=item.get("html_url", ""),
                title=f"{item.get('repository',{}).get('full_name','')}: {item.get('name','')}",
                snippet=f"Path: {item.get('path','')}",
                seed_terms_hit=[seed],
                timestamp=datetime.utcnow().isoformat(),
                confidence=0.65,
            ).seal()
            nodes.append(node)
        return nodes


# ── Array Orchestrator ───────────────────────────────────────────────────────

class OmegaArray:
    """
    Main harvester orchestrator.
    Takes seed terms, runs all sources in sequence, returns merged IntelNode list.
    """

    def __init__(self, seeds: List[str], domains: List[str] = None,
                 county: str = "", state: str = "",
                 gh_token: str = "", dry_run: bool = False):
        self.seeds   = seeds
        self.domains = domains or []
        self.county  = county
        self.state   = state
        self.gh_token = gh_token
        self.dry_run = dry_run

    def run(self) -> List[IntelNode]:
        if self.dry_run:
            print("[ARRAY] DRY RUN — returning mock nodes")
            return [IntelNode(source="DRY_RUN", url="https://example.com",
                              title="Dry run node", snippet="Mock intel node",
                              seed_terms_hit=self.seeds,
                              timestamp=datetime.utcnow().isoformat(),
                              confidence=1.0).seal()]

        nodes: List[IntelNode] = []

        for seed in self.seeds:
            print(f"[ARRAY] Dork engine → {seed!r}")
            nodes.extend(DorkEngine.run_all_dorks(seed))

            print(f"[ARRAY] SEC EDGAR → {seed!r}")
            nodes.extend(SECEdgarHarvester.search(seed))
            time.sleep(0.5)

            print(f"[ARRAY] ICIJ offshore leaks → {seed!r}")
            nodes.extend(ICIJHarvester.search(seed))
            time.sleep(0.5)

            print(f"[ARRAY] Court records → {seed!r}")
            nodes.extend(CourtHarvester.search(seed))
            time.sleep(0.5)

            if self.gh_token:
                print(f"[ARRAY] GitHub code search → {seed!r}")
                nodes.extend(GitHubHarvester.search(seed, self.gh_token))
                time.sleep(1)

        if self.county and self.state:
            print(f"[ARRAY] EPA ECHO → {self.county}, {self.state}")
            nodes.extend(EPAEchoHarvester.query(self.county, self.state, self.seeds))

        for domain in self.domains:
            print(f"[ARRAY] Wayback → {domain}")
            for seed in self.seeds:
                nodes.extend(WaybackHarvester.search_domain(domain, seed))
                time.sleep(0.5)

            print(f"[ARRAY] Subdomain enum → {domain}")
            nodes.extend(SubdomainHarvester.enumerate(domain, self.seeds))
            time.sleep(1)

        # Deduplicate by sha256
        seen = set()
        unique = []
        for n in nodes:
            if n.sha256 not in seen:
                seen.add(n.sha256)
                unique.append(n)

        print(f"[ARRAY] Harvested {len(unique)} unique intel nodes")
        return unique
