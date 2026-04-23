"""
Omega Claw — Risk Calibrator
==============================
Maps gate pipeline results → operational envelope.

Three envelopes:
  SOVEREIGN  — All gates PASS. Unrestricted execution.
  SHIELDED   — WARNs present but no FAILs. Read-only.
  CONTAINED  — Any FAIL. Sandboxed, network-blocked.

Escalation is monotonic: any CONTAINED gate → CONTAINED final.
NAEF compliant: no optimism, no deferred closure.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from gate_pipeline import GateResult, PASS, WARN, FAIL


# ══════════════════════════════════════════════════════════════
# ENVELOPE CONSTANTS
# ══════════════════════════════════════════════════════════════

SOVEREIGN = "SOVEREIGN"
SHIELDED = "SHIELDED"
CONTAINED = "CONTAINED"


# ══════════════════════════════════════════════════════════════
# RISK REPORT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RiskReport:
    """Immutable assessment report."""
    envelope: str                 # SOVEREIGN | SHIELDED | CONTAINED
    risk_score: float             # 0.0 (clean) → 1.0 (maximum risk)
    gate_summary: Dict[str, str]  # gate_name → verdict
    fail_count: int
    warn_count: int
    pass_count: int
    escalation_reason: str        # Human-readable reason for envelope choice

    def to_dict(self) -> dict:
        return asdict(self)


# ══════════════════════════════════════════════════════════════
# CALIBRATION LOGIC
# ══════════════════════════════════════════════════════════════

# Weight each gate for risk scoring
_GATE_WEIGHTS = {
    "G1_SYNTAX":   0.30,    # Can't reason about broken code
    "G2_SECURITY": 0.30,    # Injection/exfil is critical
    "G3_DEPS":     0.10,    # Missing deps is recoverable
    "G4_AUTH":     0.20,    # Policy violations are serious
    "G5_BOUNDARY": 0.10,    # Size limits are soft
}

# Verdict to numeric severity
_VERDICT_SCORE = {
    PASS: 0.0,
    WARN: 0.5,
    FAIL: 1.0,
}


def calibrate(gate_results: List[GateResult]) -> RiskReport:
    """Map gate results to an operational envelope.

    Rules (monotonic escalation, NAEF-compliant):
      1. Any FAIL → CONTAINED (no exceptions)
      2. Any WARN → SHIELDED (degraded trust)
      3. All PASS → SOVEREIGN (full trust)
    """
    summary = {}
    fail_count = 0
    warn_count = 0
    pass_count = 0
    weighted_score = 0.0

    for gr in gate_results:
        summary[gr.gate] = gr.verdict
        if gr.verdict == FAIL:
            fail_count += 1
        elif gr.verdict == WARN:
            warn_count += 1
        else:
            pass_count += 1

        weight = _GATE_WEIGHTS.get(gr.gate, 0.1)
        weighted_score += weight * _VERDICT_SCORE.get(gr.verdict, 0.0)

    # Clamp
    risk_score = min(1.0, max(0.0, weighted_score))

    # Envelope decision — monotonic escalation
    if fail_count > 0:
        envelope = CONTAINED
        reasons = [gr.detail for gr in gate_results if gr.verdict == FAIL]
        reason = f"CONTAINED: {fail_count} gate(s) FAILED — " + "; ".join(reasons[:3])
    elif warn_count > 0:
        envelope = SHIELDED
        reasons = [gr.detail for gr in gate_results if gr.verdict == WARN]
        reason = f"SHIELDED: {warn_count} warning(s) — " + "; ".join(reasons[:3])
    else:
        envelope = SOVEREIGN
        reason = "SOVEREIGN: All 5 gates PASS — unrestricted execution authorized"

    return RiskReport(
        envelope=envelope,
        risk_score=round(risk_score, 4),
        gate_summary=summary,
        fail_count=fail_count,
        warn_count=warn_count,
        pass_count=pass_count,
        escalation_reason=reason,
    )
