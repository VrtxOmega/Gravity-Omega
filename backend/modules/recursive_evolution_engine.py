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
EVOLUTION_MODEL = "qwen3:8b"
PROPOSALS_DIR = Path(__file__).parent.parent / "data" / "evolution_proposals"
PROCESSED_HASHES_FILE = PROPOSALS_DIR / "_processed_hashes.json"

SYSTEM_PROMPT = """You are OMEGA_DEVOPS_OPTIMIZER.
Your sole purpose is to evaluate the Gravity Omega execution harness based on audit logs of agentic task failures.
Analyze the following failure trace. Identify the root cause — common categories include:
- Tool misuse (wrong VTP action/target combination)
- File write corruption (AST parser bugs, path issues)
- Dependency errors (missing npm packages, wrong Python imports)
- Architecture violations (require() in renderer, node-fetch in Electron 28+)
- Infinite retry loops (fail-fast guard not triggering)
- Path escaping bugs (double-escaped backslashes in raw strings)

Propose a strict, exact architectural fix to prevent future occurrences.
Output STRICTLY as valid JSON adhering to this schema, with no markdown formatting:
{
  "root_cause": "description of why the logic failed",
  "target_file": "e.g., omega_agent.js, omega_context.md, or web_server.py",
  "proposed_optimization": "Description of the rule or code change",
  "exact_patch": "The updated code block, rule text, or omega_context.md entry"
}"""

class LedgerAutopsy:
    def __init__(self):
        self.ledger = AuditLedger()

    def find_failures(self, limit=200):
        """Scans the last N records for terminal trajectory failures.
        Detects both VERITAS file assessment VIOLATIONs and AGENTIC_FAILURE records.
        """
        records = self.ledger.read_last_n(limit)
        failures = []
        for r in records:
            is_failure = False

            # Original: VERITAS file assessment VIOLATIONs
            if r.envelope == "VIOLATION":
                is_failure = True
            
            # Keyword scan in metadata
            meta_str = json.dumps(r.metadata).upper() if r.metadata else ""
            if "LOOP_EXHAUSTED" in meta_str or "ABORTED" in meta_str or "MODEL_BOUND" in meta_str:
                is_failure = True

            # NEW: Explicit AGENTIC_FAILURE type from omega_agent.js
            if r.metadata and r.metadata.get('type') == 'AGENTIC_FAILURE':
                is_failure = True

            if is_failure:
                failures.append(r)
                
        return failures


class OptimizationLoop:
    def analyze_failure(self, failure_record):
        """Pipes the failure trace into Ollama for root cause analysis."""
        # Build enriched context from gate_verdicts (which now contain tool/error details)
        context_parts = [f"FAILURE TRACE (seal: {failure_record.seal_hash[:12]})"]
        context_parts.append(f"Envelope: {failure_record.envelope}")
        context_parts.append(f"Risk Score: {failure_record.risk_score}")
        
        if failure_record.metadata:
            meta = failure_record.metadata
            if meta.get('type') == 'AGENTIC_FAILURE':
                context_parts.append(f"Type: AGENTIC TASK FAILURE")
                context_parts.append(f"Task: {meta.get('task', 'unknown')}")
                context_parts.append(f"Exit Reason: {meta.get('exit_reason', 'unknown')}")
                context_parts.append(f"Steps: {meta.get('failed_steps', '?')}/{meta.get('total_steps', '?')} failed")

        # Include per-step error details from gate_verdicts
        for i, gv in enumerate(failure_record.gate_verdicts[:5]):
            tool = gv.get('tool', gv.get('gate', 'unknown'))
            error = gv.get('error', gv.get('verdict', ''))
            args = gv.get('args', '')
            context_parts.append(f"\nStep {i+1}: tool={tool}")
            if args:
                context_parts.append(f"  Args: {args[:150]}")
            if error:
                context_parts.append(f"  Error: {error[:300]}")

        prompt = "\n".join(context_parts)
        
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
            "failure_type": failure_record.metadata.get('type', 'VERITAS_ASSESSMENT') if failure_record.metadata else 'VERITAS_ASSESSMENT',
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


def _load_processed_hashes():
    """Load set of already-processed failure seal_hashes to avoid duplicates."""
    if PROCESSED_HASHES_FILE.exists():
        try:
            return set(json.loads(PROCESSED_HASHES_FILE.read_text()))
        except Exception:
            pass
    return set()

def _save_processed_hashes(hashes):
    """Persist processed hashes."""
    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    PROCESSED_HASHES_FILE.write_text(json.dumps(list(hashes)))


def _extract_pattern_key(proposal):
    """Extract a normalized pattern key from a proposal for grouping (B1)."""
    root_cause = (proposal.get('root_cause', '') or '').lower()
    # Extract key terms, stripping common noise words
    noise = {'the', 'a', 'an', 'is', 'was', 'to', 'in', 'of', 'for', 'and', 'or', 'not', 'it', 'this', 'that'}
    words = [w for w in root_cause.split() if w not in noise and len(w) > 2]
    # Use first 4 significant words as the pattern key
    return ' '.join(sorted(words[:4]))


def _check_graduation_threshold(proposals_dir):
    """B1 — If 3+ proposals share a root cause pattern, draft a rule proposal."""
    manifests = list(proposals_dir.glob('manifest_*.json'))
    pattern_counts = {}
    pattern_examples = {}
    
    for mpath in manifests:
        try:
            m = json.loads(mpath.read_text())
            key = _extract_pattern_key(m)
            if not key:
                continue
            pattern_counts[key] = pattern_counts.get(key, 0) + 1
            if key not in pattern_examples:
                pattern_examples[key] = m
        except Exception:
            continue
    
    graduated = []
    for pattern, count in pattern_counts.items():
        if count >= 3:
            example = pattern_examples[pattern]
            rule_draft = {
                'protocol': 'RULE_GRADUATION_B1',
                'timestamp': time.time(),
                'pattern': pattern,
                'occurrence_count': count,
                'proposed_rule': f"Based on {count} failures with pattern '{pattern}': {example.get('proposed_optimization', 'See manifests')}",
                'source_target': example.get('target_file', 'omega_context.md'),
                'status': 'PENDING_SOVEREIGN_APPROVAL'
            }
            rule_hash = hashlib.sha256(json.dumps(rule_draft, sort_keys=True).encode()).hexdigest()[:16]
            rule_path = proposals_dir / f"rule_graduation_{rule_hash}.json"
            if not rule_path.exists():
                rule_path.write_text(json.dumps(rule_draft, indent=4))
                graduated.append(pattern)
                logging.info(f"B1 GRADUATION: Pattern '{pattern}' hit {count} occurrences — rule proposal generated")
    
    return graduated


def _write_session_delta(proposals_dir, cycle_stats):
    """B5 — Write session delta summary (the learning heartbeat)."""
    delta = {
        'protocol': 'SESSION_DELTA_B5',
        'timestamp': time.time(),
        'failures_scanned': cycle_stats.get('scanned', 0),
        'failures_new': cycle_stats.get('new', 0),
        'proposals_generated': cycle_stats.get('proposals', 0),
        'patterns_graduated': cycle_stats.get('graduated', []),
        'errors_encountered': cycle_stats.get('errors', 0),
    }
    delta_path = proposals_dir / 'session_delta.json'
    delta_path.write_text(json.dumps(delta, indent=4))
    logging.info(f"B5 SESSION DELTA written: {delta_path}")


def run_evolution_cycle():
    logging.info("Initiating Recursive Harness Protocol...")
    cycle_stats = {'scanned': 0, 'new': 0, 'proposals': 0, 'graduated': [], 'errors': 0}
    
    autopsy = LedgerAutopsy()
    failures = autopsy.find_failures(limit=200)
    cycle_stats['scanned'] = len(failures)
    
    if not failures:
        logging.info("No terminal failures discovered in the examined ledger horizon. Harness optimal.")
        _write_session_delta(PROPOSALS_DIR, cycle_stats)
        return

    # Dedup: skip failures we've already analyzed
    processed = _load_processed_hashes()
    new_failures = [f for f in failures if f.seal_hash not in processed]
    cycle_stats['new'] = len(new_failures)

    if not new_failures:
        logging.info(f"All {len(failures)} failures already processed. No new analysis needed.")
        # Still check graduation threshold on existing proposals
        graduated = _check_graduation_threshold(PROPOSALS_DIR)
        cycle_stats['graduated'] = graduated
        _write_session_delta(PROPOSALS_DIR, cycle_stats)
        return

    logging.info(f"Discovered {len(new_failures)} NEW terminal trajectories (of {len(failures)} total). Commencing Optimization Loop.")
    optimizer = OptimizationLoop()
    rewriter = HarnessRewrite()
    
    for f in new_failures[:5]:  # Cap at 5 per cycle to avoid Ollama overload
        logging.info(f"Autopsying failure trace: {f.seal_hash[:12]}...")
        try:
            proposal = optimizer.analyze_failure(f)
            if proposal:
                rewriter.compile_manifest(f, proposal)
                cycle_stats['proposals'] += 1
                logging.info("Manifest compiled and secured behind RESTRICTED gate.")
        except Exception as e:
            logging.error(f"Analysis failed for {f.seal_hash[:12]}: {e}")
            cycle_stats['errors'] += 1
        processed.add(f.seal_hash)
            
    _save_processed_hashes(processed)
    
    # B1: Check if any pattern now hits graduation threshold
    graduated = _check_graduation_threshold(PROPOSALS_DIR)
    cycle_stats['graduated'] = graduated
    
    # B5: Write session delta
    _write_session_delta(PROPOSALS_DIR, cycle_stats)
    
    logging.info("Evolution cycle complete.")

if __name__ == "__main__":
    run_evolution_cycle()
