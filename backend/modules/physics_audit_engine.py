"""
VERITAS PHYSICS AUDIT ENGINE (Protocol-Compliant)
Enforces regime declarations and boundary conditions for physics calculations.
Prevents misuse of idealized formulas by requiring explicit assumption declarations.

PROTOCOL RULES:
- Sealed event types (no narrative leakage)
- No calculation without declared regime & boundary
- Outputs are strictly typed
- Missing declarations = INCONCLUSIVE
- Violations are clear and specific
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any


class PhysicsAuditEngine:
    """
    Core physics validation engine.
    Enforces the Veritas Protocol: No calculation without declared Regime & Boundary.
    """
    
    # SEALED EVENT TYPES - No other types allowed
    EVT_VIOLATION = "VIOLATION"
    EVT_INCONCLUSIVE = "INCONCLUSIVE"
    EVT_THEORETICAL_MAX = "THEORETICAL_MAX"
    EVT_MODEL_BOUND = "MODEL_BOUND"
    EVT_CONDITIONAL_PASS = "CONDITIONAL_PASS"
    
    def __init__(self, log_queue=None):
        """
        Initialize the audit engine.
        
        Args:
            log_queue: Optional queue for logging (for integration with larger systems)
        """
        self.log_queue = log_queue
        self.audit_history = []
    
    def log(self, event: str, msg: str, meta: Optional[Dict[str, Any]] = None) -> dict:
        """
        Log an audit result with strict event type enforcement.
        
        Args:
            event: Must be one of the sealed event types
            msg: Detailed explanation
            meta: Optional metadata dictionary
        
        Returns:
            Audit entry dictionary
        """
        # ENFORCE: Unknown event types are violations
        if event not in {
            self.EVT_VIOLATION,
            self.EVT_INCONCLUSIVE,
            self.EVT_THEORETICAL_MAX,
            self.EVT_MODEL_BOUND,
            self.EVT_CONDITIONAL_PASS,
        }:
            event = self.EVT_VIOLATION
            msg = f"ILLEGAL EVENT TYPE EMITTED. Original message: {msg}"
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "source": "PHYSICS_AUDIT",
            "event": event,
            "content": msg,
        }
        
        if meta:
            entry["meta"] = meta
        
        self.audit_history.append(entry)
        
        if self.log_queue:
            payload = json.dumps(entry)
            self.log_queue.put(payload)
        
        return entry
    
    # =============================================================================
    # KERNEL A: STEADY STATE SMUGGLING
    # =============================================================================
    
    def audit_steady_state(self, assert_steady_state: bool, timescale_justification: Optional[str]) -> dict:
        """
        Enforces: You cannot assert steady-state without declared justification.
        
        Args:
            assert_steady_state: Explicit assertion that d/dt = 0
            timescale_justification: Why time-dependent terms can be neglected
        
        Returns:
            Audit result dictionary
        """
        if not assert_steady_state:
            # Not claiming steady-state, no issue
            return self.log(
                self.EVT_MODEL_BOUND,
                "Time-dependent analysis. No steady-state assumption made."
            )
        
        # User IS claiming steady-state
        if not timescale_justification or timescale_justification in {"UNKNOWN", "NONE", ""}:
            return self.log(
                self.EVT_VIOLATION,
                "Steady-state asserted without declared timescale separation/evidence. "
                "You must justify why time-dependent terms can be neglected "
                "(e.g., 'Process reaches equilibrium in <1s, measurement at t>>100s')."
            )
        
        return self.log(
            self.EVT_CONDITIONAL_PASS,
            "Steady-state accepted under declared justification.",
            meta={"timescale_justification": timescale_justification}
        )
    
    # =============================================================================
    # KERNEL B: BERNOULLI EQUATION (Fluid Dynamics)
    # =============================================================================
    
    def audit_bernoulli(self, inputs: dict) -> dict:
        """
        Audits Bernoulli equation usage with complete regime gates.
        
        Bernoulli: P + (1/2)ρv² + ρgh = constant
        Valid ONLY for: inviscid, incompressible, steady flow along streamline
        
        Required inputs:
            - boundary: 'DECLARED' or 'UNKNOWN'
            - steady: True/False/None
            - compressibility: 'INCOMPRESSIBLE'/'COMPRESSIBLE'/'UNKNOWN'
            - viscosity: 'INVISCID'/'VISCOUS'/'UNKNOWN'
            - streamline: True/False/None
            - elevation_term: 'INCLUDED'/'NEGLECTED'/'UNKNOWN'
            - loss_model: None or 'DARCY'/'K_FACTOR' (required if VISCOUS)
        
        Returns:
            Audit result dictionary
        """
        boundary = inputs.get("boundary", "UNKNOWN")
        if boundary != "DECLARED":
            return self.log(
                self.EVT_INCONCLUSIVE,
                "Boundary/control volume undeclared. You must define the system boundary "
                "and endpoints where Bernoulli is being applied."
            )
        
        steady = inputs.get("steady", None)
        if steady is None:
            return self.log(
                self.EVT_INCONCLUSIVE,
                "Time regime undeclared. Declare whether flow is steady or transient."
            )
        if steady is False:
            return self.log(
                self.EVT_VIOLATION,
                "Bernoulli invoked under transient regime. Standard Bernoulli requires steady flow. "
                "Use unsteady Bernoulli equation with ∂φ/∂t term for transient analysis."
            )
        
        compressibility = inputs.get("compressibility", "UNKNOWN")
        viscosity = inputs.get("viscosity", "UNKNOWN")
        streamline = inputs.get("streamline", None)
        elevation_term = inputs.get("elevation_term", "UNKNOWN")
        
        # GATE: All regime parameters must be declared
        if compressibility == "UNKNOWN":
            return self.log(
                self.EVT_INCONCLUSIVE,
                "Compressibility undeclared. Is flow INCOMPRESSIBLE or COMPRESSIBLE?"
            )
        
        if viscosity == "UNKNOWN":
            return self.log(
                self.EVT_INCONCLUSIVE,
                "Viscosity regime undeclared. Is flow INVISCID (ideal) or VISCOUS (real)?"
            )
        
        if streamline is None:
            return self.log(
                self.EVT_INCONCLUSIVE,
                "Streamline applicability undeclared. Bernoulli applies along a streamline only."
            )
        
        if elevation_term == "UNKNOWN":
            return self.log(
                self.EVT_INCONCLUSIVE,
                "Elevation term (ρgh) handling undeclared. Is it INCLUDED or NEGLECTED?"
            )
        
        # GATE: Compressibility check
        if compressibility != "INCOMPRESSIBLE":
            return self.log(
                self.EVT_VIOLATION,
                "Bernoulli equation is INVALID for compressible flow. "
                "Use compressible flow equations (e.g., isentropic relations) instead."
            )
        
        # GATE: Streamline check
        if streamline is not True:
            return self.log(
                self.EVT_VIOLATION,
                "Bernoulli requested without streamline applicability. "
                "Equation is only valid along a streamline, not across streamlines."
            )
        
        # BRANCH: Inviscid (Ideal/Theoretical)
        if viscosity == "INVISCID":
            return self.log(
                self.EVT_THEORETICAL_MAX,
                "Bernoulli (inviscid) accepted as THEORETICAL UPPER BOUND only. "
                "No viscous dissipation modeled - this represents an ideal case with zero losses. "
                "Actual flow will have energy losses. Do NOT use for real-world predictions without adding loss terms.",
                meta={"elevation_term": elevation_term}
            )
        
        # BRANCH: Viscous (Real World)
        if viscosity == "VISCOUS":
            loss_model = inputs.get("loss_model", None)
            if not loss_model:
                return self.log(
                    self.EVT_VIOLATION,
                    "Viscous flow declared but loss/closure model missing. "
                    "You must specify how energy losses are calculated (e.g., DARCY-WEISBACH, K-FACTOR, HEAD_LOSS)."
                )
            
            return self.log(
                self.EVT_MODEL_BOUND,
                "Bernoulli with declared loss model accepted as model-bound estimate. "
                "Results are valid within the scope and assumptions of the loss model.",
                meta={
                    "loss_model": loss_model,
                    "elevation_term": elevation_term,
                    "compressibility": compressibility
                }
            )
        
        # Should never reach here
        return self.log(
            self.EVT_VIOLATION,
            f"Unknown viscosity regime: {viscosity}"
        )
    
    # =============================================================================
    # KERNEL C: HOOKE'S LAW (Structural Mechanics)
    # =============================================================================
    
    def audit_hooke(self, force: float, k: float, elastic_limit_x: Optional[float],
                    loading_regime: str, cycles_N: Optional[int] = None) -> dict:
        """
        Enforces: F = -kx is only valid in linear-elastic region.
        
        Hooke's Law applies ONLY below yield point and in appropriate loading regime.
        
        Args:
            force: Applied force (N)
            k: Spring constant or stiffness (N/m)
            elastic_limit_x: Maximum displacement before plastic deformation (m)
            loading_regime: 'STATIC', 'CYCLIC', 'IMPACT', or 'UNKNOWN'
            cycles_N: Number of load cycles (required for CYCLIC)
        
        Returns:
            Audit result dictionary
        """
        # GATE: Loading regime must be declared
        if loading_regime in {None, "UNKNOWN", ""}:
            return self.log(
                self.EVT_INCONCLUSIVE,
                "Loading regime undeclared. You must specify: STATIC, CYCLIC, or IMPACT loading."
            )
        
        # GATE: Stiffness validation
        if k is None or k == 0:
            return self.log(
                self.EVT_VIOLATION,
                "Invalid stiffness k (zero or undefined). Stiffness must be non-zero."
            )
        
        # Calculate displacement
        try:
            x = force / k
        except (ZeroDivisionError, TypeError) as e:
            return self.log(
                self.EVT_VIOLATION,
                f"Calculation error: {str(e)}"
            )
        
        # GATE: Elastic limit must be declared
        if elastic_limit_x is None:
            return self.log(
                self.EVT_INCONCLUSIVE,
                "Elastic limit undeclared. Provide maximum elastic displacement "
                "(or allowable stress/strain from material model).",
                meta={"computed_x": x}
            )
        
        # GATE: Check if within elastic region
        if abs(x) > elastic_limit_x:
            return self.log(
                self.EVT_VIOLATION,
                f"Elastic limit exceeded. Calculated displacement {x:.4f} m exceeds "
                f"elastic limit {elastic_limit_x:.4f} m. Hooke's Law is INVALID in the plastic regime. "
                f"Use plastic deformation models (e.g., von Mises, Tresca) instead.",
                meta={"computed_x": x, "elastic_limit_x": elastic_limit_x}
            )
        
        # BRANCH: Cyclic loading (fatigue)
        if loading_regime == "CYCLIC":
            if cycles_N is None:
                return self.log(
                    self.EVT_INCONCLUSIVE,
                    "Cyclic loading declared but number of cycles N not provided. "
                    "Fatigue model cannot be bounded without cycle count.",
                    meta={"computed_x": x}
                )
            
            return self.log(
                self.EVT_CONDITIONAL_PASS,
                f"Displacement {x:.4f} m is within elastic limit. "
                f"HOWEVER: For cyclic loading, result valid ONLY if fatigue life is sufficient. "
                f"Check S-N curve and verify N={cycles_N} < endurance limit for this stress amplitude.",
                meta={"computed_x": x, "cycles_N": cycles_N}
            )
        
        # BRANCH: Impact loading
        if loading_regime == "IMPACT":
            return self.log(
                self.EVT_CONDITIONAL_PASS,
                f"Displacement {x:.4f} m calculated for static load. "
                f"WARNING: Impact loading requires dynamic analysis with impact factor. "
                f"Static result may significantly underestimate peak displacement.",
                meta={"computed_x": x}
            )
        
        # BRANCH: Static loading (standard case)
        return self.log(
            self.EVT_MODEL_BOUND,
            f"Displacement {x:.4f} m is valid within declared linear-elastic limit.",
            meta={
                "computed_x": x,
                "elastic_limit_x": elastic_limit_x,
                "loading_regime": loading_regime
            }
        )
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def get_summary(self) -> dict:
        """Get summary of audit history."""
        summary = {
            "total_audits": len(self.audit_history),
            "by_type": {}
        }
        
        for event_type in [self.EVT_VIOLATION, self.EVT_INCONCLUSIVE, self.EVT_THEORETICAL_MAX,
                          self.EVT_MODEL_BOUND, self.EVT_CONDITIONAL_PASS]:
            count = sum(1 for entry in self.audit_history if entry["event"] == event_type)
            summary["by_type"][event_type] = count
        
        return summary
    
    def clear_history(self):
        """Clear audit history."""
        self.audit_history = []


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=== VERITAS PHYSICS AUDIT ENGINE (Protocol-Compliant) ===\n")
    
    engine = PhysicsAuditEngine()
    
    # Test 1: Steady State without justification (VIOLATION)
    print("TEST 1: Steady-state asserted without justification")
    result = engine.audit_steady_state(assert_steady_state=True, timescale_justification=None)
    print(f"  Event: {result['event']}")
    print(f"  Message: {result['content']}\n")
    
    # Test 2: Bernoulli - Missing boundary (INCONCLUSIVE)
    print("TEST 2: Bernoulli - Boundary undeclared")
    result = engine.audit_bernoulli({'boundary': 'UNKNOWN'})
    print(f"  Event: {result['event']}")
    print(f"  Message: {result['content']}\n")
    
    # Test 3: Bernoulli - Ideal case (THEORETICAL_MAX)
    print("TEST 3: Bernoulli - Complete ideal regime")
    result = engine.audit_bernoulli({
        'boundary': 'DECLARED',
        'steady': True,
        'compressibility': 'INCOMPRESSIBLE',
        'viscosity': 'INVISCID',
        'streamline': True,
        'elevation_term': 'INCLUDED'
    })
    print(f"  Event: {result['event']}")
    print(f"  Message: {result['content']}\n")
    
    # Test 4: Hooke - Beyond elastic limit (VIOLATION)
    print("TEST 4: Hooke's Law - Beyond elastic limit")
    result = engine.audit_hooke(force=1000, k=100, elastic_limit_x=5, loading_regime="STATIC")
    print(f"  Event: {result['event']}")
    print(f"  Message: {result['content']}\n")
    
    # Test 5: Hooke - Cyclic without cycles (INCONCLUSIVE)
    print("TEST 5: Hooke - Cyclic loading without cycle count")
    result = engine.audit_hooke(force=400, k=100, elastic_limit_x=5, loading_regime="CYCLIC", cycles_N=None)
    print(f"  Event: {result['event']}")
    print(f"  Message: {result['content']}\n")
    
    # Summary
    print("=== AUDIT SUMMARY ===")
    summary = engine.get_summary()
    print(f"Total Audits: {summary['total_audits']}")
    for event_type, count in summary['by_type'].items():
        if count > 0:
            print(f"  {event_type}: {count}")
