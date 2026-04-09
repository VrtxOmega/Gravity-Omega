"""
PROJECT THERMAL-SHIELD
Morphological Idea Generator with CLAEG/NAEF Verification

Architecture:
1. Primitive Library (design components, mechanisms, regimes, losses)
2. Morphological Chart Generator (systematic combinations)
3. Candidate Generator (permutation engine)
4. CLAEG/NAEF Gate (verification compiler)

Domain: Passive Cooling / Heat Transfer
Goal: Generate constraint-complete thermal designs
"""

import json
import hashlib
from datetime import datetime
from itertools import product
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


# =============================================================================
# MODULE 1: PRIMITIVE LIBRARY
# =============================================================================

@dataclass
class Primitive:
    """Base class for design primitives"""
    name: str
    category: str
    properties: Dict[str, Any]
    
    def to_dict(self):
        return asdict(self)


class PrimitiveLibrary:
    """
    Sovereign Library of Design Primitives.
    Stores atomic components for morphological combination.
    """
    
    def __init__(self):
        self.primitives = {
            'heat_source': [],
            'transfer_mechanism': [],
            'geometry': [],
            'material': [],
            'control': [],
            'regime': [],
            'loss_model': [],
            'failure_mode': []
        }
        self._populate_thermal_primitives()
    
    def _populate_thermal_primitives(self):
        """Populate library with passive cooling primitives"""
        
        # Heat Sources
        self.add_primitive('heat_source', Primitive(
            name="Electronic Component",
            category="heat_source",
            properties={
                "power_range": "1-100W",
                "temperature_limit": "85C",
                "footprint": "variable"
            }
        ))
        
        self.add_primitive('heat_source', Primitive(
            name="CPU/GPU",
            category="heat_source",
            properties={
                "power_range": "50-300W",
                "temperature_limit": "100C",
                "pulse_behavior": "transient"
            }
        ))
        
        # Transfer Mechanisms
        self.add_primitive('transfer_mechanism', Primitive(
            name="Natural Convection",
            category="transfer_mechanism",
            properties={
                "regime": "Rayleigh_dependent",
                "loss_model": "Nu_correlation",
                "boundary_requirement": "free_surface",
                "efficiency": "theoretical_range: 5-15%"
            }
        ))
        
        self.add_primitive('transfer_mechanism', Primitive(
            name="Heat Pipe",
            category="transfer_mechanism",
            properties={
                "regime": "two_phase",
                "loss_model": "wick_resistance + vapor_flow",
                "boundary_requirement": "sealed_enclosure",
                "efficiency": "theoretical_range: 40-90%"
            }
        ))
        
        self.add_primitive('transfer_mechanism', Primitive(
            name="Phase Change Material",
            category="transfer_mechanism",
            properties={
                "regime": "latent_heat",
                "loss_model": "Stefan_problem",
                "boundary_requirement": "container",
                "efficiency": "storage_capacity_dependent"
            }
        ))
        
        self.add_primitive('transfer_mechanism', Primitive(
            name="Capillary Action",
            category="transfer_mechanism",
            properties={
                "regime": "surface_tension",
                "loss_model": "Hagen-Poiseuille",
                "boundary_requirement": "wicking_structure",
                "efficiency": "pore_size_dependent"
            }
        ))
        
        # Geometries
        self.add_primitive('geometry', Primitive(
            name="Finned Array",
            category="geometry",
            properties={
                "surface_area_multiplier": "5-20x",
                "flow_regime": "laminar_or_turbulent",
                "pressure_drop": "K_factor_required"
            }
        ))
        
        self.add_primitive('geometry', Primitive(
            name="Pin Fin",
            category="geometry",
            properties={
                "surface_area_multiplier": "10-30x",
                "flow_regime": "turbulent",
                "pressure_drop": "high"
            }
        ))
        
        self.add_primitive('geometry', Primitive(
            name="Microchannel",
            category="geometry",
            properties={
                "surface_area_multiplier": "50-100x",
                "flow_regime": "laminar_forced",
                "pressure_drop": "very_high"
            }
        ))
        
        # Materials
        self.add_primitive('material', Primitive(
            name="Copper",
            category="material",
            properties={
                "thermal_conductivity": "385 W/mK",
                "density": "8960 kg/m3",
                "cost": "moderate"
            }
        ))
        
        self.add_primitive('material', Primitive(
            name="Aluminum",
            category="material",
            properties={
                "thermal_conductivity": "205 W/mK",
                "density": "2700 kg/m3",
                "cost": "low"
            }
        ))
        
        self.add_primitive('material', Primitive(
            name="Graphene Composite",
            category="material",
            properties={
                "thermal_conductivity": "1000-5000 W/mK",
                "density": "variable",
                "cost": "very_high"
            }
        ))
        
        # Control Methods (Passive)
        self.add_primitive('control', Primitive(
            name="None (Passive)",
            category="control",
            properties={
                "type": "passive",
                "reliability": "high",
                "power": "0W"
            }
        ))
        
        self.add_primitive('control', Primitive(
            name="Bimetallic Valve",
            category="control",
            properties={
                "type": "passive_mechanical",
                "reliability": "moderate",
                "power": "0W",
                "failure_mode": "fatigue"
            }
        ))
        
        # Regimes
        self.add_primitive('regime', Primitive(
            name="Steady State",
            category="regime",
            properties={
                "assumption": "d/dt = 0",
                "justification_required": "timescale_separation"
            }
        ))
        
        self.add_primitive('regime', Primitive(
            name="Transient",
            category="regime",
            properties={
                "assumption": "time_dependent",
                "justification_required": "thermal_mass_model"
            }
        ))
        
        # Loss Models
        self.add_primitive('loss_model', Primitive(
            name="Nusselt Correlation",
            category="loss_model",
            properties={
                "applies_to": "convection",
                "regime": "natural_or_forced",
                "form": "Nu = f(Ra, Pr) or f(Re, Pr)"
            }
        ))
        
        self.add_primitive('loss_model', Primitive(
            name="Fourier Conduction",
            category="loss_model",
            properties={
                "applies_to": "solid_conduction",
                "regime": "steady_or_transient",
                "form": "q = -k∇T"
            }
        ))
        
        self.add_primitive('loss_model', Primitive(
            name="Contact Resistance",
            category="loss_model",
            properties={
                "applies_to": "interface",
                "regime": "pressure_dependent",
                "form": "R_contact = f(pressure, roughness)"
            }
        ))
        
        # Failure Modes
        self.add_primitive('failure_mode', Primitive(
            name="Thermal Runaway",
            category="failure_mode",
            properties={
                "cause": "insufficient_dissipation",
                "indicator": "T > T_limit"
            }
        ))
        
        self.add_primitive('failure_mode', Primitive(
            name="Fatigue (Thermal Cycling)",
            category="failure_mode",
            properties={
                "cause": "cyclic_stress",
                "indicator": "N > N_fatigue"
            }
        ))
    
    def add_primitive(self, category: str, primitive: Primitive):
        """Add primitive to library"""
        if category in self.primitives:
            self.primitives[category].append(primitive)
    
    def get_category(self, category: str) -> List[Primitive]:
        """Get all primitives in a category"""
        return self.primitives.get(category, [])
    
    def export_library(self) -> dict:
        """Export entire library as JSON-serializable dict"""
        return {
            cat: [p.to_dict() for p in prims]
            for cat, prims in self.primitives.items()
        }


# =============================================================================
# MODULE 2: MORPHOLOGICAL CHART GENERATOR
# =============================================================================

class MorphologicalChart:
    """
    Generates systematic combinations of primitives.
    Each dimension can have multiple options.
    """
    
    def __init__(self, library: PrimitiveLibrary):
        self.library = library
        self.dimensions = {}
    
    def define_chart(self, required_dimensions: List[str]):
        """
        Define which primitive categories are required for a design.
        
        Example: ['heat_source', 'transfer_mechanism', 'geometry', 'material']
        """
        for dim in required_dimensions:
            options = self.library.get_category(dim)
            if options:
                self.dimensions[dim] = options
    
    def generate_candidates(self, max_combinations: int = 1000) -> List[Dict]:
        """
        Generate all possible combinations up to max_combinations.
        
        Returns list of candidate designs (each is a dict of primitives)
        """
        if not self.dimensions:
            return []
        
        # Get all dimension names and their options
        dim_names = list(self.dimensions.keys())
        dim_options = [self.dimensions[dim] for dim in dim_names]
        
        # Generate cartesian product
        candidates = []
        for combo in product(*dim_options):
            if len(candidates) >= max_combinations:
                break
            
            # Create candidate as dict
            candidate = {
                dim_names[i]: combo[i]
                for i in range(len(dim_names))
            }
            candidate['id'] = hashlib.sha256(
                json.dumps({k: v.name for k, v in candidate.items()}, sort_keys=True).encode()
            ).hexdigest()[:12]
            
            candidates.append(candidate)
        
        return candidates


# =============================================================================
# MODULE 3: CLAEG/NAEF VERIFICATION GATE
# =============================================================================

class VerificationGate:
    """
    CLAEG/NAEF compiler for candidate designs.
    Rejects anything with missing declarations or narrative rescue.
    """
    
    def __init__(self):
        # NAEF patterns (narrative rescue detection)
        self.narrative_patterns = [
            "assume negligible",
            "should work",
            "likely",
            "probably",
            "industry standard",
            "experts say",
            "we'll solve later",
            "good enough",
            "approximately",
            "roughly"
        ]
    
    def verify_candidate(self, candidate: Dict) -> Dict:
        """
        Run CLAEG + NAEF checks on a candidate design.
        
        Returns audit result with:
        - status: PASS / INCONCLUSIVE / VIOLATION
        - reason: why it failed (if applicable)
        - declarations: what was declared
        - missing: what's missing
        """
        result = {
            'candidate_id': candidate.get('id', 'unknown'),
            'timestamp': datetime.now().isoformat(),
            'status': 'UNKNOWN',
            'reason': '',
            'declarations': {},
            'missing': [],
            'score': 0
        }
        
        # CLAEG Gate 1: Boundary declaration
        if 'transfer_mechanism' in candidate:
            mech = candidate['transfer_mechanism']
            if 'boundary_requirement' in mech.properties:
                result['declarations']['boundary'] = mech.properties['boundary_requirement']
            else:
                result['missing'].append('boundary_requirement')
        
        # CLAEG Gate 2: Regime declaration
        regime_declared = False
        if 'transfer_mechanism' in candidate:
            mech = candidate['transfer_mechanism']
            if 'regime' in mech.properties:
                result['declarations']['regime'] = mech.properties['regime']
                regime_declared = True
        
        if not regime_declared:
            result['missing'].append('regime')
        
        # CLAEG Gate 3: Loss/Closure model
        loss_declared = False
        if 'transfer_mechanism' in candidate:
            mech = candidate['transfer_mechanism']
            if 'loss_model' in mech.properties:
                result['declarations']['loss_model'] = mech.properties['loss_model']
                loss_declared = True
        
        if not loss_declared:
            result['missing'].append('loss_model')
        
        # CLAEG Gate 4: Efficiency bounds
        if 'transfer_mechanism' in candidate:
            mech = candidate['transfer_mechanism']
            eff = mech.properties.get('efficiency', '')
            
            # NAEF check: detect narrative rescue
            eff_lower = eff.lower()
            for pattern in self.narrative_patterns:
                if pattern in eff_lower:
                    result['status'] = 'VIOLATION'
                    result['reason'] = f"NAEF: Narrative rescue detected in efficiency: '{pattern}'"
                    return result
            
            if 'theoretical_range' in eff or 'dependent' in eff:
                result['declarations']['efficiency_bound'] = eff
            else:
                result['missing'].append('efficiency_bound')
        
        # Determine final status
        if result['missing']:
            result['status'] = 'INCONCLUSIVE'
            result['reason'] = f"Missing declarations: {', '.join(result['missing'])}"
            result['score'] = 0
        else:
            # Check if THEORETICAL vs MODEL_BOUND
            eff = candidate.get('transfer_mechanism', Primitive('', '', {})).properties.get('efficiency', '')
            if 'theoretical' in eff.lower():
                result['status'] = 'THEORETICAL_MAX'
                result['reason'] = "All declarations present, but theoretical efficiency (ideal case)"
                result['score'] = 1
            else:
                result['status'] = 'MODEL_BOUND'
                result['reason'] = "All required declarations present"
                result['score'] = 2
        
        return result


# =============================================================================
# MODULE 4: IDEA FORGE (MAIN PIPELINE)
# =============================================================================

class ThermalShieldForge:
    """
    PROJECT THERMAL-SHIELD
    Main pipeline: Proposer → Verifier → Survivors
    """
    
    def __init__(self):
        self.library = PrimitiveLibrary()
        self.chart = MorphologicalChart(self.library)
        self.gate = VerificationGate()
        
        self.candidates = []
        self.results = []
    
    def generate_candidates(self, max_count: int = 1000):
        """Generate candidate designs"""
        print(f"\n[PROPOSER] Generating up to {max_count} candidates...")
        
        # Define morphological dimensions
        self.chart.define_chart([
            'heat_source',
            'transfer_mechanism',
            'geometry',
            'material'
        ])
        
        self.candidates = self.chart.generate_candidates(max_count)
        print(f"[PROPOSER] Generated {len(self.candidates)} candidates")
    
    def verify_all(self):
        """Run CLAEG/NAEF gate on all candidates"""
        print(f"\n[VERIFIER] Running CLAEG/NAEF gate on {len(self.candidates)} candidates...")
        
        self.results = []
        for candidate in self.candidates:
            result = self.gate.verify_candidate(candidate)
            self.results.append(result)
        
        # Summary
        summary = {
            'total': len(self.results),
            'VIOLATION': sum(1 for r in self.results if r['status'] == 'VIOLATION'),
            'INCONCLUSIVE': sum(1 for r in self.results if r['status'] == 'INCONCLUSIVE'),
            'THEORETICAL_MAX': sum(1 for r in self.results if r['status'] == 'THEORETICAL_MAX'),
            'MODEL_BOUND': sum(1 for r in self.results if r['status'] == 'MODEL_BOUND')
        }
        
        print(f"\n[VERIFIER] Results:")
        for status, count in summary.items():
            if status != 'total':
                pct = (count / summary['total'] * 100) if summary['total'] > 0 else 0
                print(f"  {status}: {count} ({pct:.1f}%)")
        
        return summary
    
    def get_survivors(self, min_score: int = 1) -> List[Dict]:
        """Get candidates that passed verification"""
        survivors = []
        for i, result in enumerate(self.results):
            if result['score'] >= min_score:
                survivors.append({
                    'candidate': self.candidates[i],
                    'verification': result
                })
        return survivors
    
    def export_report(self, filepath: str):
        """Export full report with survivors and rejects"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'project': 'THERMAL-SHIELD',
            'total_candidates': len(self.candidates),
            'summary': {
                'VIOLATION': sum(1 for r in self.results if r['status'] == 'VIOLATION'),
                'INCONCLUSIVE': sum(1 for r in self.results if r['status'] == 'INCONCLUSIVE'),
                'THEORETICAL_MAX': sum(1 for r in self.results if r['status'] == 'THEORETICAL_MAX'),
                'MODEL_BOUND': sum(1 for r in self.results if r['status'] == 'MODEL_BOUND')
            },
            'survivors': self.get_survivors(min_score=1),
            'all_results': self.results
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n[EXPORT] Report saved to {filepath}")


# =============================================================================
# EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("="*80)
    print("PROJECT THERMAL-SHIELD")
    print("Morphological Idea Generator with CLAEG/NAEF Verification")
    print("="*80)
    
    forge = ThermalShieldForge()
    
    # Step 1: Generate candidates
    forge.generate_candidates(max_count=1000)
    
    # Step 2: Verify all
    summary = forge.verify_all()
    
    # Step 3: Get survivors
    survivors = forge.get_survivors(min_score=1)
    print(f"\n[SURVIVORS] {len(survivors)} designs passed verification")
    
    # Show top 10 survivors
    print("\n[TOP SURVIVORS]")
    for i, survivor in enumerate(survivors[:10], 1):
        cand = survivor['candidate']
        ver = survivor['verification']
        
        print(f"\n{i}. Design {ver['candidate_id'][:8]} [{ver['status']}]")
        print(f"   Heat Source: {cand['heat_source'].name}")
        print(f"   Transfer: {cand['transfer_mechanism'].name}")
        print(f"   Geometry: {cand['geometry'].name}")
        print(f"   Material: {cand['material'].name}")
        print(f"   Declarations: {list(ver['declarations'].keys())}")
        if ver['missing']:
            print(f"   Missing: {ver['missing']}")
    
    # Step 4: Export report
    report_path = r"c:\Veritas_Lab\THERMAL_SHIELD_REPORT.json"
    forge.export_report(report_path)
    
    print("\n" + "="*80)
    print("FORGE COMPLETE")
    print("="*80)
