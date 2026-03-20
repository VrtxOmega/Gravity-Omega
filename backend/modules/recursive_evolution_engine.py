#!/usr/bin/env python3
"""
Omega Sentinel — Recursive Evolution Engine (Self-Critique Engine)
===================================================================
Implementation of the Recursive Harness Protocol.
Operates as an autonomous AI DevOps engineer profiling its own failure trajectories.

1. Ledger Autopsy: Scans `~/.omega_claw/audit_ledger.jsonl` for terminal failures.
2. Optimization Loop: Pipes failure context to local Ollama.
3. Harness Rewrite: Generates strict optimization patches (e.g. threshold tuning).
4. RESTRICTED Gate: Emits a cryptographic `manifest_<hash>.json` for human approval.
"""

import os
import json
import time
import hashlib
import urllib.request
import logging
from pathlib import Path
from audit_ledger import AuditLedger

logging.basicConfig(level=logging.INFO, format='%(asctime)s - RECURSIVE_ENGINE - %(levelname)s - %(message)s')

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
EVOLUTION_MODEL = "qwen2.5:7b" 
PROPOSALS_DIR = Path(__file__).parent.parent / "data" / "evolution_proposals"

SYSTEM_PROMPT = """You are OMEGA_DEVOPS_OPTIMIZER.
Your sole purpose is to evaluate the Gravity Omega execution harness based on cryogenic audit logs.
Analyze the following failure trace. Identify the root cause (e.g., AST recursion limit, context retrieval threshold, prompt hallucination, or tool misuse).
Propose a strict, exact architectural code-patch to optimize the operational harness logic and prevent future occurrences. 
Output STRICTLY as valid JSON adhering to this schema, with no markdown formatting around the output:
{
  "root_cause": "description of why the logic failed",
  "target_file": "e.g., omega_tools.js or provenance_stack.py",
  "proposed_optimization": "Description of the logical parameter or threshold change",
  "exact_patch": "The updated code block or logic to implement"
}"""

class LedgerAutopsy:
    def __init__(self):
        self.ledger = AuditLedger()

    def find_failures(self, limit=100):
        """Scans the last N records for terminal trajectory failures."""
        records = self.ledger.read_last_n(limit)
        failures = []
        for r in records:
            # We look for explicit VIOLATIONS, high risk bounds, or metadata containing ABORTED/LOOP_EXHAUSTED
            is_failure = False
            if r.envelope == "VIOLATION":
                is_failure = True
            
            meta_str = json.dumps(r.metadata).upper() if r.metadata else ""
            if "LOOP_EXHAUSTED" in meta_str or "ABORTED" in meta_str or "MODEL_BOUND" in meta_str:
                is_failure = True

            if is_failure:
                failures.append(r)
                
        return failures

class OptimizationLoop:
    def analyze_failure(self, failure_record):
        """Pipes the failure trace into Ollama for root cause architectural analysis."""
        prompt = f"FAILURE TRACE RECORD:\n{json.dumps(failure_record.to_dict(), indent=2)}"
        
        payload = {
            "model": EVOLUTION_MODEL,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        try:
            req = urllib.request.Request(
                OLLAMA_URL,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                response_text = data.get("response", "{}")
                return json.loads(response_text)
        except Exception as e:
            logging.error(f"Optimization Loop failed connecting to Ollama: {e}")
            return None

class HarnessRewrite:
    def __init__(self):
        os.makedirs(PROPOSALS_DIR, exist_ok=True)

    def compile_manifest(self, failure_record, proposal):
        """Compiles the proposed optimization into a RESTRICTED approval manifest."""
        manifest = {
            "protocol": "RECURSIVE_HARNESS_EVOLUTION",
            "timestamp": time.time(),
            "failure_reference_hash": failure_record.seal_hash,
            "target_file": proposal.get("target_file", "UNKNOWN"),
            "root_cause_analysis": proposal.get("root_cause", ""),
            "proposed_optimization": proposal.get("proposed_optimization", ""),
            "exact_patch": proposal.get("exact_patch", ""),
            "status": "PENDING_SOVEREIGN_APPROVAL"
        }
        
        manifest_str = json.dumps(manifest, sort_keys=True)
        manifest_hash = hashlib.sha256(manifest_str.encode('utf-8')).hexdigest()
        manifest["manifest_hash"] = manifest_hash
        
        out_path = PROPOSALS_DIR / f"manifest_{manifest_hash[:16]}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=4)
            
        logging.info(f"Generated Upgrade Manifest: {out_path}")
        return manifest

def run_evolution_cycle():
    logging.info("Initiating Recursive Harness Protocol...")
    autopsy = LedgerAutopsy()
    failures = autopsy.find_failures(limit=200)
    
    if not failures:
        logging.info("No terminal failures discovered in the examined ledger horizon. Harness optimal.")
        return

    logging.info(f"Discovered {len(failures)} terminal trajectories. Commencing Optimization Loop.")
    optimizer = OptimizationLoop()
    rewriter = HarnessRewrite()
    
    for f in failures:
        logging.info(f"Autopsying failure trace: {f.seal_hash[:12]}...")
        proposal = optimizer.analyze_failure(f)
        if proposal:
            rewriter.compile_manifest(f, proposal)
            logging.info("Manifest compiled and secured behind RESTRICTED gate.")
            
    logging.info("Evolution cycle absolute.")

if __name__ == "__main__":
    run_evolution_cycle()
