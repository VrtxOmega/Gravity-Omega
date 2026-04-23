"""
GOLIATH HUNTER — OMEGA_PATTERN_ENGINE v1.0
==========================================
Self-directing intelligence layer.

Takes IntelNode objects from OmegaArray, finds patterns, builds an
entity co-occurrence graph, detects contradictions between sources,
and emits NEW SEEDS for the next search cycle.

This is what makes Gravity Omega self-directing:
  discovered entities → new seeds → new searches → more entities → repeat
"""

import re
import json
import hashlib
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Tuple, Set, Optional

from .omega_array import IntelNode


# ── Entity Extractor ─────────────────────────────────────────────────────────

class EntityExtractor:
    """
    Extracts named entities and signals from text using regex patterns.
    No external NLP dependency — works out of the box.
    """

    PATTERNS = {
        "PERSON": [
            r"\b([A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b",
        ],
        "ORG": [
            r"\b([A-Z][A-Za-z&\.\s]{2,40}(?:Inc|LLC|Corp|Ltd|Co\.|Authority|Agency|Department|Bureau|Commission|Group|Holdings|Industries|Services|Solutions|Associates|Partners|Foundation|Institute|University|College)\.?)\b",
        ],
        "LOCATION": [
            r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?,\s*[A-Z]{2})\b",  # City, ST
            r"\b([A-Z][a-z]+ County)\b",
            r"\b([A-Z][a-z]+ (?:River|Lake|Creek|Bay|Harbor|Port|Valley))\b",
        ],
        "CHEMICAL": [
            r"\b(PFAS|PFOA|PFOS|PFHxS|AFFF|TCE|PCB|benzene|manganese|trichloroethylene|chromium|arsenic|lead|mercury|nitrate|chloroform)\b",
            r"\b(\d+[\.,]\d+\s*(?:µg/L|ug/L|mg/L|ppb|ppm|ng/L))\b",
        ],
        "MONEY": [
            r"\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand|M|B|K))?",
            r"\b\d+[\.,]\d+\s*(?:million|billion)\s*dollars?\b",
        ],
        "DATE": [
            r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})\b",
            r"\b(\d{4}-\d{2}-\d{2})\b",
            r"\b(\d{1,2}/\d{1,2}/\d{4})\b",
        ],
        "REGULATION": [
            r"\b((?:EPA|IEPA|CERCLA|RCRA|CWA|CAA|TSCA|MCL|MCLG|SDWA|FOIA|10-K|8-K|SEC|DOJ|FBI|PFAS|H\.R\.\s*\d+)\b)",
        ],
        "EMAIL": [
            r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b",
        ],
        "DOMAIN": [
            r"\b((?:[a-zA-Z0-9-]+\.)+(?:com|gov|org|net|edu|mil))\b",
        ],
    }

    @classmethod
    def extract(cls, text: str) -> Dict[str, List[str]]:
        """Extract all entity types from text."""
        results: Dict[str, List[str]] = defaultdict(list)
        for etype, patterns in cls.PATTERNS.items():
            for pat in patterns:
                flags = re.IGNORECASE if etype == "CHEMICAL" else 0
                for m in re.finditer(pat, text, flags):
                    val = m.group(0).strip()
                    if val and val not in results[etype]:
                        results[etype].append(val)
        return dict(results)

    @classmethod
    def extract_flat(cls, text: str) -> List[str]:
        """Return a flat list of all extracted entity strings."""
        flat = []
        for vals in cls.extract(text).values():
            flat.extend(vals)
        return flat


# ── Contradiction Vector ──────────────────────────────────────────────────────

@dataclass
class ContradictionVector:
    """
    A proven contradiction between two sources.
    source_a claims X in public. source_b contains evidence of ¬X.
    """
    vector_id: str = ""
    entity: str = ""              # the entity at the center of the contradiction
    claim_a: str = ""             # what source_a says publicly
    claim_b: str = ""             # what source_b reveals
    node_a_id: str = ""           # IntelNode sha256 of source A
    node_b_id: str = ""           # IntelNode sha256 of source B
    node_a_url: str = ""
    node_b_url: str = ""
    tier: str = "TIER_B"          # TIER_A (quantitative), TIER_B (qualitative)
    timestamp: str = ""
    confidence: float = 0.0

    def seal(self):
        payload = f"{self.node_a_id}|{self.node_b_id}|{self.entity}"
        self.vector_id = hashlib.sha256(payload.encode()).hexdigest()[:16].upper()
        self.timestamp = datetime.utcnow().isoformat()
        return self

    def to_dict(self):
        return asdict(self)


# ── Entity Co-occurrence Graph ────────────────────────────────────────────────

class EntityGraph:
    """
    Builds an entity co-occurrence graph from IntelNode content.
    Nodes = entities. Edges = appeared together in the same source.
    High-degree nodes (many connections to other unsearched entities)
    become the next seeds.
    """

    def __init__(self):
        self.edges: Dict[Tuple[str, str], int] = defaultdict(int)
        self.node_sources: Dict[str, List[str]] = defaultdict(list)  # entity → [node_ids]
        self.entity_types: Dict[str, str] = {}

    def ingest(self, node: IntelNode, entities: Dict[str, List[str]]):
        """Add entity co-occurrences from a single IntelNode."""
        all_ents = []
        for etype, vals in entities.items():
            for v in vals:
                all_ents.append(v)
                self.entity_types[v] = etype
                self.node_sources[v].append(node.node_id)

        # Build edges between all pairs in this node
        for i, a in enumerate(all_ents):
            for b in all_ents[i+1:]:
                key = tuple(sorted([a, b]))
                self.edges[key] += 1

    def top_entities(self, n: int = 20, known_seeds: Set[str] = None) -> List[Tuple[str, int]]:
        """
        Return top-N entities by degree (total edge weight).
        Prioritize entities NOT in known_seeds (unexplored territory).
        """
        degree: Dict[str, int] = defaultdict(int)
        for (a, b), weight in self.edges.items():
            degree[a] += weight
            degree[b] += weight

        known = {s.lower() for s in (known_seeds or set())}
        ranked = sorted(
            [(ent, deg) for ent, deg in degree.items()
             if ent.lower() not in known and len(ent) > 3],
            key=lambda x: -x[1]
        )
        return ranked[:n]

    def suggest_new_seeds(self, known_seeds: Set[str], top_n: int = 5) -> List[str]:
        """Return the top new seeds the engine hasn't searched yet."""
        candidates = self.top_entities(top_n * 3, known_seeds)
        # Prefer ORGs and CHEMICALs over generic text
        priority = [(e, d) for e, d in candidates
                    if self.entity_types.get(e) in ("ORG", "CHEMICAL", "PERSON", "REGULATION")]
        fallback = [(e, d) for e, d in candidates if e not in dict(priority)]
        merged = priority + fallback
        return [e for e, _ in merged[:top_n]]


# ── Contradiction Detector ────────────────────────────────────────────────────

class ContradictionDetector:
    """
    Finds contradictions between public claims (high-confidence sources)
    and discovered evidence (lower-confidence sources).

    Contradiction logic:
      - A node from SEC_EDGAR or COURT_LISTENER with "safe" → public claim
      - A node from DORK_ENGINE or WAYBACK with a numeric measurement exceeding
        a known safety threshold → evidence
    """

    # Chemical safety thresholds (MCLs / EPA limits in µg/L)
    THRESHOLDS = {
        "pfas": 0.004,   # EPA MCL 2024
        "pfoa": 0.004,
        "pfos": 0.004,
        "pfhxs": 10.0,
        "manganese": 50.0,  # EPA secondary standard
        "arsenic": 10.0,
        "lead": 15.0,
        "nitrate": 10000.0,
        "tce": 5.0,
        "benzene": 5.0,
    }

    SAFE_CLAIM_PATTERNS = [
        r"(?i)water is safe",
        r"(?i)within (safe|acceptable|regulatory) limits",
        r"(?i)(no|not) (detected|found|present|identified)",
        r"(?i)compliant with (EPA|IEPA|federal|state) standards",
        r"(?i)poses no (risk|threat|health concern)",
        r"(?i)below (action|detection|reporting) level",
    ]

    MEASUREMENT_PATTERN = re.compile(
        r"([\d,]+\.?\d*)\s*(?:µg/L|ug/L|mg/L|ppb|ppm)",
        re.IGNORECASE
    )

    @classmethod
    def detect(cls, nodes: List[IntelNode]) -> List[ContradictionVector]:
        vectors = []

        # Separate "safe" claims from measurement evidence
        safe_nodes = [n for n in nodes if cls._has_safe_claim(n)]
        evidence_nodes = [n for n in nodes if cls._has_measurement(n)]

        for safe_node in safe_nodes:
            for ev_node in evidence_nodes:
                if safe_node.node_id == ev_node.node_id:
                    continue
                # Check if they share an entity
                shared = set(safe_node.seed_terms_hit) & set(ev_node.seed_terms_hit)
                if not shared:
                    # Check snippet overlap
                    safe_ents = set(EntityExtractor.extract_flat(
                        safe_node.title + " " + safe_node.snippet))
                    ev_ents = set(EntityExtractor.extract_flat(
                        ev_node.title + " " + ev_node.snippet))
                    shared = safe_ents & ev_ents
                if shared:
                    # Check if measurement exceeds threshold
                    measurements = cls.MEASUREMENT_PATTERN.findall(
                        ev_node.snippet + " " + ev_node.full_text)
                    for m_str in measurements:
                        try:
                            val = float(m_str.replace(",", ""))
                            # Find which chemical this might relate to
                            text_lower = (ev_node.snippet + ev_node.full_text).lower()
                            for chem, threshold in cls.THRESHOLDS.items():
                                if chem in text_lower and val > threshold:
                                    vec = ContradictionVector(
                                        entity=list(shared)[0],
                                        claim_a=f"Public statement: '{cls._safe_claim_match(safe_node)}'",
                                        claim_b=f"Evidence: {chem.upper()} measured at {val} µg/L (limit: {threshold})",
                                        node_a_id=safe_node.node_id,
                                        node_b_id=ev_node.node_id,
                                        node_a_url=safe_node.url,
                                        node_b_url=ev_node.url,
                                        tier="TIER_A",  # quantitative
                                        confidence=min(0.95, safe_node.confidence + ev_node.confidence),
                                    ).seal()
                                    vectors.append(vec)
                        except ValueError:
                            continue

        return vectors

    @classmethod
    def _has_safe_claim(cls, node: IntelNode) -> bool:
        text = f"{node.title} {node.snippet} {node.full_text}".lower()
        return any(re.search(p, text) for p in cls.SAFE_CLAIM_PATTERNS)

    @classmethod
    def _has_measurement(cls, node: IntelNode) -> bool:
        return bool(cls.MEASUREMENT_PATTERN.search(
            node.snippet + " " + node.full_text))

    @classmethod
    def _safe_claim_match(cls, node: IntelNode) -> str:
        text = f"{node.title} {node.snippet}"
        for p in cls.SAFE_CLAIM_PATTERNS:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(0)
        return node.snippet[:100]


# ── Pattern Report ────────────────────────────────────────────────────────────

@dataclass
class PatternReport:
    run_id: str = ""
    timestamp: str = ""
    seeds_searched: List[str] = field(default_factory=list)
    nodes_analyzed: int = 0
    top_entities: List[Tuple[str, int]] = field(default_factory=list)
    new_seeds: List[str] = field(default_factory=list)
    contradiction_vectors: List[ContradictionVector] = field(default_factory=list)
    entity_type_summary: Dict[str, int] = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        d["contradiction_vectors"] = [v.to_dict() for v in self.contradiction_vectors]
        return d


# ── Pattern Engine Orchestrator ───────────────────────────────────────────────

class OmegaPatternEngine:
    """
    Main pattern engine.
    Feed it IntelNodes from OmegaArray, get back a PatternReport with
    new seeds, contradiction vectors, and entity graph summary.
    """

    def __init__(self, known_seeds: List[str]):
        self.known_seeds = set(known_seeds)
        self.graph = EntityGraph()

    def analyze(self, nodes: List[IntelNode]) -> PatternReport:
        print(f"[PATTERN] Analyzing {len(nodes)} intel nodes...")

        entity_type_totals: Dict[str, int] = defaultdict(int)

        for node in nodes:
            text = f"{node.title} {node.snippet} {node.full_text}"
            entities = EntityExtractor.extract(text)
            # Enrich node's entity list
            node.entities_raw = EntityExtractor.extract_flat(text)
            self.graph.ingest(node, entities)
            for etype, vals in entities.items():
                entity_type_totals[etype] += len(vals)

        new_seeds = self.graph.suggest_new_seeds(self.known_seeds, top_n=8)
        top_ents  = self.graph.top_entities(n=25, known_seeds=self.known_seeds)
        contradictions = ContradictionDetector.detect(nodes)

        print(f"[PATTERN] New seeds discovered: {new_seeds}")
        print(f"[PATTERN] Contradiction vectors: {len(contradictions)}")

        return PatternReport(
            run_id=hashlib.sha256(str(self.known_seeds).encode()).hexdigest()[:12].upper(),
            timestamp=datetime.utcnow().isoformat(),
            seeds_searched=list(self.known_seeds),
            nodes_analyzed=len(nodes),
            top_entities=top_ents,
            new_seeds=new_seeds,
            contradiction_vectors=contradictions,
            entity_type_summary=dict(entity_type_totals),
        )
