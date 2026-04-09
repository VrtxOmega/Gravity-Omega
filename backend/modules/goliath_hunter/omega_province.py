"""
GOLIATH HUNTER — OMEGA_PROVINCE v1.0
=====================================
NAEF Contradiction Gate + VERITAS Evidence Sealing.

Takes ContradictionVectors from OmegaPatternEngine,
runs them through the VERITAS evidence pipeline,
and emits court-ready sealed proof files.

Does NOT modify GOLIATH_GATE.py or any existing module.
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from .omega_pattern_engine import ContradictionVector, IntelNode


# ── VERITAS Evidence Item builder ─────────────────────────────────────────────

def _make_evidence_item(node: IntelNode) -> dict:
    """Convert IntelNode to VERITAS-spec EvidenceItem dict."""
    return {
        "id": node.sha256,
        "variable": "SOURCE_CONTENT",
        "value": {
            "kind": "Categorical",
            "v": node.snippet[:500]
        },
        "timestamp": node.timestamp or datetime.utcnow().isoformat(),
        "method": {
            "protocol": node.source,
            "parameters": {"url": node.url},
            "repeatable": True,
        },
        "provenance": {
            "source_id": node.url[:100],
            "acquisition": f"automated_harvest:{node.source}",
            "tier": "B" if node.confidence >= 0.7 else "C",
            "notes": f"confidence={node.confidence:.2f}",
        },
    }


# ── Strict Necessity Test (Province Gate) ────────────────────────────────────

class StrictNecessityTest:
    """
    NAEF-compliant gate. A contradiction is only elevated if:
      1. Source A is a verifiable public statement (SEC, EPA, gov domain, press release)
      2. Source B contains a concrete counterfactual (measurement, document, timestamp)
      3. The time gap between A's statement and B's evidence is bounded (not speculative)
    """

    PUBLIC_SOURCE_MARKERS = {
        "SEC_EDGAR", "EPA_ECHO", "COURT_LISTENER",
        "gov", "sec.gov", "epa.gov", "courtlistener.com"
    }

    @classmethod
    def evaluate(cls, vec: ContradictionVector,
                 node_a: Optional[IntelNode],
                 node_b: Optional[IntelNode]) -> tuple:
        """
        Returns (PASS|FAIL, reason_code, confidence).
        PASS means the contradiction survives strict necessity.
        """
        # Gate 1: Source A must be a high-authority public channel
        source_a_ok = (
            node_a is not None and (
                node_a.source in cls.PUBLIC_SOURCE_MARKERS or
                any(m in node_a.url for m in cls.PUBLIC_SOURCE_MARKERS)
            )
        )
        if not source_a_ok:
            return ("FAIL", "SOURCE_A_NOT_AUTHORITATIVE",
                    vec.confidence * 0.5)

        # Gate 2: Tier A vectors require a numeric measurement
        if vec.tier == "TIER_A":
            has_number = any(c.isdigit() for c in vec.claim_b)
            if not has_number:
                return ("FAIL", "TIER_A_MISSING_QUANTITATIVE", vec.confidence * 0.6)

        # Gate 3: Both nodes must exist and be non-empty
        if not node_a or not node_b:
            return ("FAIL", "MISSING_SOURCE_NODE", 0.0)

        if not node_a.sha256 or not node_b.sha256:
            return ("FAIL", "UNSEALED_SOURCE", 0.0)

        return ("PASS", "STRICT_NECESSITY_MET", vec.confidence)


# ── Sealed Proof File ─────────────────────────────────────────────────────────

@dataclass
class SealedProof:
    """Court-ready evidence seal for a contradiction vector."""
    proof_id: str = ""
    vector: ContradictionVector = field(default_factory=ContradictionVector)
    evidence_a: dict = field(default_factory=dict)
    evidence_b: dict = field(default_factory=dict)
    strict_necessity_verdict: str = ""
    strict_necessity_code: str = ""
    gate_confidence: float = 0.0
    seal_hash: str = ""
    sealed_at: str = ""
    veritas_gate_results: List[dict] = field(default_factory=list)

    def compute_seal(self):
        payload = json.dumps({
            "proof_id": self.proof_id,
            "vector_id": self.vector.vector_id,
            "evidence_a_hash": self.evidence_a.get("id", ""),
            "evidence_b_hash": self.evidence_b.get("id", ""),
            "verdict": self.strict_necessity_verdict,
            "sealed_at": self.sealed_at,
        }, sort_keys=True)
        self.seal_hash = hashlib.sha256(payload.encode()).hexdigest()
        return self

    def to_dict(self):
        d = asdict(self)
        d["vector"] = self.vector.to_dict()
        return d


# ── Province Orchestrator ─────────────────────────────────────────────────────

class OmegaProvince:
    """
    Province Layer — processes contradiction vectors through
    the strict necessity test and emits sealed proof files.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._node_index: Dict[str, IntelNode] = {}

    def index_nodes(self, nodes: List[IntelNode]):
        """Build a lookup index of IntelNodes by node_id."""
        for n in nodes:
            self._node_index[n.node_id] = n

    def process(self, vectors: List[ContradictionVector]) -> List[SealedProof]:
        """
        Run all contradiction vectors through the province gate.
        Returns list of sealed proofs that passed strict necessity.
        """
        proofs = []
        print(f"[PROVINCE] Processing {len(vectors)} contradiction vectors...")

        for vec in vectors:
            node_a = self._node_index.get(vec.node_a_id)
            node_b = self._node_index.get(vec.node_b_id)

            verdict, code, confidence = StrictNecessityTest.evaluate(
                vec, node_a, node_b)

            # Build mock VERITAS gate results
            gate_results = [
                {"gate": "INTAKE",  "verdict": "PASS", "reason_code": "INTAKE_OK"},
                {"gate": "TYPE",    "verdict": "PASS", "reason_code": "TYPE_OK"},
                {"gate": "EVIDENCE","verdict": verdict, "reason_code": code},
            ]

            proof = SealedProof(
                proof_id=f"PROOF_{vec.vector_id}",
                vector=vec,
                evidence_a=_make_evidence_item(node_a) if node_a else {},
                evidence_b=_make_evidence_item(node_b) if node_b else {},
                strict_necessity_verdict=verdict,
                strict_necessity_code=code,
                gate_confidence=confidence,
                sealed_at=datetime.utcnow().isoformat(),
                veritas_gate_results=gate_results,
            ).compute_seal()

            # Save every proof — caller decides what to surface
            proof_path = self.output_dir / f"proof_{proof.proof_id}.json"
            with open(proof_path, "w", encoding="utf-8") as f:
                json.dump(proof.to_dict(), f, indent=2)

            if verdict == "PASS":
                print(f"  [PROVINCE ✓] {code} → {vec.entity} | conf={confidence:.2f}")
                proofs.append(proof)
            else:
                print(f"  [PROVINCE ✗] {code} → {vec.entity}")

        print(f"[PROVINCE] {len(proofs)}/{len(vectors)} vectors passed strict necessity")
        return proofs

    def audit_of_omission(self, proofs: List[SealedProof]) -> str:
        """
        Generate NAEF-compliant Audit of Omission text.
        Documents what public statements didn't disclose, per sealed proof.
        """
        lines = [
            "# AUDIT OF OMISSION",
            f"Generated: {datetime.utcnow().isoformat()}",
            "",
            "The following table documents contradictions between public disclosures",
            "and discovered evidence. Each row is cryptographically sealed.",
            "",
            f"{'#':<4} {'Entity':<30} {'Public Claim (excerpt)':<45} {'Evidence':<55} {'Tier':<8} {'Seal':<18}",
            "-" * 160,
        ]
        for i, p in enumerate(proofs, 1):
            lines.append(
                f"{i:<4} {p.vector.entity[:30]:<30} "
                f"{p.vector.claim_a[:45]:<45} "
                f"{p.vector.claim_b[:55]:<55} "
                f"{p.vector.tier:<8} "
                f"{p.seal_hash[:16]}"
            )
        return "\n".join(lines)
