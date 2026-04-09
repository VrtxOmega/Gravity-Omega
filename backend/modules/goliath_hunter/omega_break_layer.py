"""
GOLIATH HUNTER — OMEGA_BREAK_LAYER v1.0
=========================================
The adversarial falsification gate. Runs AFTER Province seals proofs.

For every synthesis the engine produces, forces three questions:
  1. What data would DISPROVE this? (falsification check)
  2. What doesn't fit this theory?  (counter-evidence scan)
  3. Where are we ASSUMING vs CONFIRMING? (assumption audit)

Outputs a BreakReport alongside the dossier. If the synthesis
survives all three passes, it earns a CONFIRMED_HARD status.
If it fails any pass, it is flagged ASSUMED, WEAK, or CONTRADICTED.

Aligned with VERITAS Ω Gate 7 (ADVERSARY) and NAEF.
No external deps — stdlib only.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from .omega_array import IntelNode
from .omega_pattern_engine import PatternReport
from .omega_province import SealedProof


# ── Status codes ─────────────────────────────────────────────────────────────

CONFIRMED_HARD  = "CONFIRMED_HARD"   # passed all 3 break tests
ASSUMED         = "ASSUMED"          # at least one claim rests on assumption
WEAK            = "WEAK"             # insufficient counter-evidence searched
CONTRADICTED    = "CONTRADICTED"     # active counter-evidence found in nodes


# ── Break Finding ─────────────────────────────────────────────────────────────

@dataclass
class BreakFinding:
    """One adversarial finding against a claim or entity."""
    target: str              # entity or claim being stress-tested
    test: str                # which of the 3 tests flagged this
    flag: str                # ASSUMED / WEAK / CONTRADICTED
    reason: str              # why it was flagged
    counter_evidence: str    # quote or reference from nodes that cuts against it
    seal: str = ""

    def __post_init__(self):
        payload = f"{self.target}|{self.test}|{self.flag}|{self.reason}"
        self.seal = hashlib.sha256(payload.encode()).hexdigest()[:16].upper()


@dataclass
class BreakReport:
    """Full adversarial falsification report for one hunt cycle."""
    run_id: str
    timestamp: str
    findings: List[BreakFinding] = field(default_factory=list)
    confirmed_claims: List[str]  = field(default_factory=list)
    assumed_claims: List[str]    = field(default_factory=list)
    weak_claims: List[str]       = field(default_factory=list)
    contradicted_claims: List[str] = field(default_factory=list)
    overall_status: str = ASSUMED

    def to_markdown(self) -> str:
        lines = [
            "# 🔴 BREAK LAYER — Adversarial Falsification Report",
            f"**Run:** `{self.run_id}` | **Generated:** {self.timestamp}",
            f"**Overall Status:** `{self.overall_status}`",
            "",
            "> *For every synthesis: What would disprove this? What doesn't fit? Where am I assuming?*",
            "",
            "---",
            "",
        ]

        if self.confirmed_claims:
            lines += [
                "## ✅ CONFIRMED_HARD — Survived All 3 Break Tests",
                "",
            ]
            for c in self.confirmed_claims:
                lines.append(f"- `{c}`")
            lines.append("")

        if self.contradicted_claims:
            lines += [
                "## 🔴 CONTRADICTED — Active Counter-Evidence Found",
                "",
            ]
            for c in self.contradicted_claims:
                lines.append(f"- `{c}`")
            lines.append("")

        if self.assumed_claims:
            lines += [
                "## 🟡 ASSUMED — Rests on Unconfirmed Assumption",
                "",
            ]
            for c in self.assumed_claims:
                lines.append(f"- `{c}`")
            lines.append("")

        if self.weak_claims:
            lines += [
                "## 🟠 WEAK — Insufficient Counter-Evidence Searched",
                "",
            ]
            for c in self.weak_claims:
                lines.append(f"- `{c}`")
            lines.append("")

        lines += ["---", "", "## Break Finding Detail", ""]
        for i, f in enumerate(self.findings, 1):
            lines += [
                f"### {i}. [{f.flag}] `{f.target}`",
                f"**Test:** {f.test}",
                f"**Reason:** {f.reason}",
                f"**Counter-evidence:** {f.counter_evidence or 'None found — absence is itself a flag.'}",
                f"**Seal:** `{f.seal}`",
                "",
            ]

        return "\n".join(lines)


# ── The Three Tests ───────────────────────────────────────────────────────────

class FalsificationTest:
    """
    Test 1: What data would DISPROVE this claim?
    Looks for nodes that directly contradict the claimed fact.
    E.g., if claim is "Olin released lead into groundwater",
    looks for nodes saying "Olin site groundwater CLEAN" or "no violations found".
    """
    NAME = "FALSIFICATION"

    NEGATION_PATTERNS = [
        r"\bno\s+(violation|contamination|release|spill|plume|evidence)\b",
        r"\bwithin\s+(legal|regulatory|safe)\s+limits?\b",
        r"\bbelow\s+(mcl|action level|detection limit)\b",
        r"\bclean[ed]?\s+(up|site|water)\b",
        r"\bremediat(ed|ion complete)\b",
        r"\bcomplian[ct]\b",
        r"\bno\s+significant\s+(risk|hazard|impact)\b",
        r"\bnot\s+(detected|found|confirmed)\b",
    ]

    @classmethod
    def test(cls, entity: str, nodes: List[IntelNode]) -> Optional[BreakFinding]:
        """Check if any nodes contain negating language for this entity."""
        relevant = [n for n in nodes
                    if entity.lower() in (n.full_text + n.snippet + n.title).lower()]

        counter_hits = []
        for n in relevant:
            text = (n.full_text + " " + n.snippet).lower()
            for pat in cls.NEGATION_PATTERNS:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    # Find context around the match
                    start = max(0, m.start() - 80)
                    end   = min(len(text), m.end() + 80)
                    counter_hits.append(f"[{n.source}] ...{text[start:end].strip()}...")
                    break

        if counter_hits:
            return BreakFinding(
                target=entity,
                test=cls.NAME,
                flag=CONTRADICTED,
                reason=f"Found {len(counter_hits)} node(s) with language that negates the claimed hazard.",
                counter_evidence=counter_hits[0][:300],
            )
        return None


class CounterFitTest:
    """
    Test 2: What doesn't fit this theory?
    Looks for anomalous nodes — high-confidence nodes about the target
    entity that don't mention the expected contamination keywords.
    If a company has 20 EPA hits and none mention the pollutant — suspicious.
    """
    NAME = "COUNTER_FIT"

    EXPECTED_KEYWORDS = {
        "contamination": ["contamina", "pollut", "spill", "release", "plume",
                          "hazard", "toxic", "violation"],
        "pfas":          ["pfas", "pfoa", "pfos", "pfba", "afff", "forever chemical"],
        "benzene":       ["benzene", "voc", "toluene", "xylene", "hydrocarbon"],
        "lead":          ["lead", "pb ", "heavy metal", "ammunition", "explosive"],
        "groundwater":   ["groundwater", "aquifer", "well", "drinking water", "plume"],
    }

    @classmethod
    def test(cls, entity: str, nodes: List[IntelNode],
             expected_topic: str = "contamination") -> Optional[BreakFinding]:
        """Check if nodes about this entity fail to mention expected topic keywords."""
        relevant = [n for n in nodes
                    if entity.lower() in (n.full_text + n.snippet + n.title).lower()]

        if not relevant:
            return BreakFinding(
                target=entity,
                test=cls.NAME,
                flag=WEAK,
                reason="No nodes found about this entity at all. "
                       "Cannot confirm — absence of evidence is not evidence of absence, "
                       "but warrants deeper search.",
                counter_evidence="Zero relevant nodes retrieved.",
            )

        kws = cls.EXPECTED_KEYWORDS.get(expected_topic, cls.EXPECTED_KEYWORDS["contamination"])
        nodes_without_topic = []
        for n in relevant:
            text = (n.full_text + n.snippet + n.title).lower()
            if not any(kw in text for kw in kws):
                nodes_without_topic.append(n)

        if len(nodes_without_topic) > len(relevant) * 0.7:
            # More than 70% of entity-relevant nodes don't mention the topic
            titles = [n.title[:60] for n in nodes_without_topic[:3]]
            return BreakFinding(
                target=entity,
                test=cls.NAME,
                flag=ASSUMED,
                reason=f"{len(nodes_without_topic)}/{len(relevant)} nodes about this entity "
                       f"don't mention '{expected_topic}'. "
                       f"The association may be assumed rather than confirmed.",
                counter_evidence="Sample non-matching nodes: " + "; ".join(titles),
            )
        return None


class AssumptionAuditTest:
    """
    Test 3: Where are we ASSUMING vs CONFIRMING?
    Scores each entity based on evidence quality.
    Flags entities that appear only in DORK_ENGINE or dry-run nodes
    (i.e., inferred from search results rather than primary sources).
    """
    NAME = "ASSUMPTION_AUDIT"

    # Sources ordered by epistemic authority
    PRIMARY_SOURCES = {"EPA_ECHO", "SEC_EDGAR", "COURT_LISTENER", "ICIJ_OFFSHORE"}
    SECONDARY_SOURCES = {"WAYBACK", "GITHUB_CODE", "SUBDOMAIN_CRT"}
    TERTIARY_SOURCES  = {"DORK_ENGINE"}   # search results only — assumptions possible

    @classmethod
    def test(cls, entity: str, nodes: List[IntelNode]) -> Optional[BreakFinding]:
        relevant = [n for n in nodes
                    if entity.lower() in (n.full_text + n.snippet + n.title).lower()]

        if not relevant:
            return BreakFinding(
                target=entity,
                test=cls.NAME,
                flag=ASSUMED,
                reason="Entity appears in synthesis but has zero supporting nodes. "
                       "Pure assumption — no evidence found.",
                counter_evidence="",
            )

        source_types = {n.source for n in relevant}
        primary_count   = sum(1 for n in relevant if n.source in cls.PRIMARY_SOURCES)
        tertiary_only   = source_types.issubset(cls.TERTIARY_SOURCES | {"DRY_RUN"})
        avg_conf        = sum(n.confidence for n in relevant) / len(relevant)

        if tertiary_only:
            return BreakFinding(
                target=entity,
                test=cls.NAME,
                flag=ASSUMED,
                reason="Entity supported only by DORK_ENGINE (web search) nodes. "
                       "No primary source (EPA, SEC, court record) has confirmed this. "
                       "Treat as a lead, not a fact.",
                counter_evidence=f"All {len(relevant)} nodes from DORK_ENGINE. "
                                 f"Avg confidence: {avg_conf:.2f}.",
            )

        if primary_count == 0 and avg_conf < 0.65:
            return BreakFinding(
                target=entity,
                test=cls.NAME,
                flag=WEAK,
                reason=f"No primary-source nodes (EPA/SEC/Court). "
                       f"Average confidence {avg_conf:.2f} is below threshold. "
                       f"Increase --max-fetch and target primary sources.",
                counter_evidence=f"Sources available: {source_types}",
            )

        return None  # passes assumption audit


# ── Break Layer Orchestrator ───────────────────────────────────────────────────

class OmegaBreakLayer:
    """
    Runs all three break tests against every significant entity and proof
    in the hunt results, producing a BreakReport.

    Usage in conductor pipeline:
        break_layer = OmegaBreakLayer()
        break_report = break_layer.run(report, sealed_proofs, all_nodes)
    """

    def __init__(self, top_n_entities: int = 20):
        self.top_n = top_n_entities

    def run(self,
            report: PatternReport,
            sealed_proofs: List[SealedProof],
            nodes: List[IntelNode]) -> BreakReport:

        br = BreakReport(
            run_id=report.run_id,
            timestamp=datetime.utcnow().isoformat(),
        )

        # Entities to stress-test: top entities + entities from sealed proofs
        entities_to_test = [e for e, _ in report.top_entities[:self.top_n]]
        if sealed_proofs:
            proof_entities = [p.vector.entity for p in sealed_proofs]
            entities_to_test = list(dict.fromkeys(proof_entities + entities_to_test))

        for entity in entities_to_test:
            passed = 0
            entity_findings = []

            # Determine expected topic from entity name
            topic = "contamination"
            e_lower = entity.lower()
            if any(w in e_lower for w in ["pfas", "afff", "pfoa"]):
                topic = "pfas"
            elif any(w in e_lower for w in ["benzene", "voc"]):
                topic = "benzene"
            elif any(w in e_lower for w in ["lead", "olin", "ammunition"]):
                topic = "lead"

            # Test 1: Falsification
            f1 = FalsificationTest.test(entity, nodes)
            if f1:
                entity_findings.append(f1)
                br.findings.append(f1)
            else:
                passed += 1

            # Test 2: Counter-fit
            f2 = CounterFitTest.test(entity, nodes, topic)
            if f2:
                entity_findings.append(f2)
                br.findings.append(f2)
            else:
                passed += 1

            # Test 3: Assumption audit
            f3 = AssumptionAuditTest.test(entity, nodes)
            if f3:
                entity_findings.append(f3)
                br.findings.append(f3)
            else:
                passed += 1

            # Classify entity
            flags = {f.flag for f in entity_findings}
            if CONTRADICTED in flags:
                br.contradicted_claims.append(entity)
            elif ASSUMED in flags:
                br.assumed_claims.append(entity)
            elif WEAK in flags:
                br.weak_claims.append(entity)
            elif passed == 3:
                br.confirmed_claims.append(entity)

        # Overall status
        if br.contradicted_claims:
            br.overall_status = CONTRADICTED
        elif br.assumed_claims:
            br.overall_status = ASSUMED
        elif br.weak_claims:
            br.overall_status = WEAK
        else:
            br.overall_status = CONFIRMED_HARD

        n_total   = len(entities_to_test)
        n_pass    = len(br.confirmed_claims)
        n_contra  = len(br.contradicted_claims)
        n_assumed = len(br.assumed_claims)
        n_weak    = len(br.weak_claims)

        print(f"[BREAK_LAYER] Results: "
              f"{n_pass} CONFIRMED | {n_assumed} ASSUMED | "
              f"{n_weak} WEAK | {n_contra} CONTRADICTED / {n_total} total")

        return br
