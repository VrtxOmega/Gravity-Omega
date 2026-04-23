"""
GOLIATH HUNTER — OMEGA_CONDUCTOR v1.0
=======================================
Main orchestrator for the self-directing OSINT engine.

  Entry points:
    run_hunt(seed, depth, ...) — full pipeline
    mirror_module(name)        — clone any existing GOLIATH module for fine-tuning

  Omega integration:
    When web_server.py imports this, it gets routes:
      POST /api/hunter/run       — start a hunt
      GET  /api/hunter/status/<job_id>  — poll job status
      GET  /api/hunter/jobs      — list all jobs

  Does NOT modify any existing Omega file beyond one import line.
"""

import sys
import os
# Ensure the parent modules/ directory is on the path so
# relative package imports work whether we're imported OR run directly.
_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

import hashlib
import json
import os
import shutil
import sys
import threading
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ── Paths ────────────────────────────────────────────────────────────────────

MODULE_DIR   = Path(__file__).parent
MODULES_DIR  = MODULE_DIR.parent   # backend/modules
WORKSPACE    = Path("C:/GOLIATH_WORKSPACE")
INTEL_DIR    = WORKSPACE / "INTEL"
INTEL_DIR.mkdir(parents=True, exist_ok=True)

# In-memory job registry
_jobs: Dict[str, dict] = {}
_jobs_lock = threading.Lock()


# ── Local imports ─────────────────────────────────────────────────────────────

from .omega_array        import OmegaArray, IntelNode
from .omega_pattern_engine import OmegaPatternEngine, PatternReport
from .omega_province     import OmegaProvince
from .omega_dossier      import OmegaDossier
from .omega_lead_fetcher import LeadFetcher
from .omega_break_layer  import OmegaBreakLayer


# ── Hunt Run ──────────────────────────────────────────────────────────────────

class HuntRun:
    """
    Single end-to-end intelligence hunt.
    seed      : initial search term(s), comma-separated
    depth     : how many self-directed re-search cycles (0=just the seed)
    domains   : optional domains for Wayback/subdomain enum
    county/state: optional EPA ECHO location
    gh_token  : optional GitHub token for code search
    dry_run   : if True, skip all real HTTP — use mock nodes
    """

    def __init__(self, seeds: List[str], depth: int = 1,
                 domains: List[str] = None,
                 county: str = "", state: str = "",
                 gh_token: str = "",
                 max_fetch: int = 50,
                 dry_run: bool = False):
        self.seeds     = seeds
        self.depth     = depth
        self.domains   = domains or []
        self.county    = county
        self.state     = state
        self.gh_token  = gh_token
        self.max_fetch = max_fetch
        self.dry_run   = dry_run

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        seed_slug = re.sub(r"[^a-zA-Z0-9]", "_", seeds[0])[:20]
        self.run_id  = f"{seed_slug}_{ts}"
        self.run_dir = INTEL_DIR / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, job_id: str = ""):
        """Run the full pipeline. Updates _jobs[job_id] with status."""
        # Add _prune_jobs inside the lock to prevent race
        _prune_jobs()
        
        def _update(status, msg="", progress=0):
            if job_id:
                _jobs_lock.acquire()
                try:
                    _jobs[job_id].update({
                        "status": status, "message": msg, "progress": progress,
                        "updated_at": datetime.utcnow().isoformat()
                    })
                finally:
                    _jobs_lock.release()
            print(f"[HUNTER] [{status}] {msg}")

        all_nodes: List[IntelNode] = []
        all_seeds = set(self.seeds)

        for cycle in range(self.depth + 1):
            cycle_seeds = list(self.seeds if cycle == 0
                               else new_seeds[:5])  # noqa: F821

            _update("RUNNING", f"Cycle {cycle+1}/{self.depth+1} — seeds: {cycle_seeds}", cycle * 30)

            # 1. ARRAY — harvest
            array = OmegaArray(
                seeds=cycle_seeds,
                domains=self.domains if cycle == 0 else [],
                county=self.county if cycle == 0 else "",
                state=self.state if cycle == 0 else "",
                gh_token=self.gh_token,
                dry_run=self.dry_run,
            )
            nodes = array.run()
            all_nodes.extend(nodes)
            if len(all_nodes) > 5000:
                all_nodes = all_nodes[-5000:]

            # Save raw nodes for this cycle
            raw_path = self.run_dir / f"raw_nodes_cycle{cycle}.json"
            raw_path.write_text(
                json.dumps([n.to_dict() for n in nodes], indent=2), encoding="utf-8")

            # 1b. LEAD FETCHER — deep-read discovered URLs
            if not self.dry_run:
                _update("RUNNING",
                        f"Lead Fetcher: reading content of top {self.max_fetch} nodes",
                        cycle * 25 + 12)
                fetcher = LeadFetcher(max_fetch=self.max_fetch)
                nodes   = fetcher.fetch_all(nodes)
                # Save enriched nodes
                enriched_path = self.run_dir / f"enriched_nodes_cycle{cycle}.json"
                enriched_path.write_text(
                    json.dumps([n.to_dict() for n in nodes], indent=2), encoding="utf-8")

            # 2. PATTERN ENGINE — analyze full content
            _update("RUNNING", f"Pattern analysis on {len(nodes)} nodes", cycle * 30 + 15)
            engine = OmegaPatternEngine(known_seeds=all_seeds)
            report = engine.analyze(nodes)

            # Save pattern report
            pr_path = self.run_dir / f"pattern_report_cycle{cycle}.json"
            pr_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

            new_seeds = report.new_seeds
            all_seeds.update(new_seeds)
            if len(all_seeds) > 5000:
                all_seeds = set(list(all_seeds)[-5000:])

            if cycle == self.depth or not new_seeds:
                break

        # 3. PROVINCE — seal contradiction proofs
        _update("RUNNING", "Running NAEF Province Gate", 70)
        province = OmegaProvince(self.run_dir / "proofs")
        province.index_nodes(all_nodes)
        all_vectors = [v for c in range(self.depth + 1)
                       for v in self._load_vectors(c)]
        # Use last cycle's report vectors
        all_vectors = report.contradiction_vectors
        sealed_proofs = province.process(all_vectors)

        audit = province.audit_of_omission(sealed_proofs)

        # 4a. BREAK LAYER — adversarial falsification (anti-bias gate)
        _update("RUNNING", "Running Break Layer — adversarial falsification gate", 78)
        break_layer  = OmegaBreakLayer(top_n_entities=20)
        break_report = break_layer.run(report, sealed_proofs, all_nodes)
        break_md     = break_report.to_markdown()
        break_path   = self.run_dir / "break_layer_report.md"
        break_path.write_text(break_md, encoding="utf-8")
        print(f"[BREAK_LAYER] Report saved → {break_path}")
        print(f"[BREAK_LAYER] Overall status: {break_report.overall_status}")

        lead_fetcher = LeadFetcher(max_fetch=0)  # no more fetching — just summarise
        lead_summary = lead_fetcher.get_lead_summary(all_nodes)
        lead_path = self.run_dir / "lead_content_summary.md"
        lead_path.write_text(lead_summary, encoding="utf-8")
        print(f"[LEAD_FETCHER] Lead summary saved → {lead_path}")

        # 4c. DOSSIER — generate report
        _update("RUNNING", "Generating dossier", 90)
        dossier = OmegaDossier(self.run_dir, self.run_id)
        md_path = dossier.generate(report, sealed_proofs, all_nodes, audit,
                                   lead_summary=lead_summary,
                                   break_layer_md=break_md)

        _update("COMPLETE", f"Dossier: {md_path}", 100)

        result = {
            "run_id":             self.run_id,
            "run_dir":            str(self.run_dir),
            "nodes_total":        len(all_nodes),
            "enriched_nodes":     sum(1 for n in all_nodes if n.full_text),
            "seeds_total":        len(all_seeds),
            "proofs":             len(sealed_proofs),
            "dossier":            str(md_path),
            "lead_summary":       str(lead_path),
            "break_layer_report": str(break_path),
            "break_status":       break_report.overall_status,
            "confirmed":          len(break_report.confirmed_claims),
            "assumed":            len(break_report.assumed_claims),
            "contradicted":       len(break_report.contradicted_claims),
        }
        if job_id:
            _jobs_lock.acquire()
            try:
                _jobs[job_id]["result"] = result
            finally:
                _jobs_lock.release()
        return result

    def _execute_wrapped(self, job_id: str = ""):
        """Wrapper that catches ALL exceptions in daemon thread so jobs don't zombie."""
        try:
            return self.execute(job_id)
        except Exception as exc:
            _jobs_lock.acquire()
            try:
                if job_id in _jobs:
                    _jobs[job_id].update({
                        "status": "FAILED",
                        "message": str(exc),
                        "updated_at": datetime.utcnow().isoformat()
                    })
            finally:
                _jobs_lock.release()
            log = logging.getLogger('goliath')
            log.error(f"Hunt job {job_id} crashed: {exc}", exc_info=True)
            raise

    def _load_vectors(self, cycle: int):
        """Load contradiction vectors saved by pattern engine."""
        try:
            p = self.run_dir / f"pattern_report_cycle{cycle}.json"
            data = json.loads(p.read_text())
            from .omega_pattern_engine import ContradictionVector
            return [ContradictionVector(**v) for v in data.get("contradiction_vectors", [])]
        except Exception:
            return []


# ── Module Mirror ─────────────────────────────────────────────────────────────

def mirror_module(module_name: str) -> Path:
    """
    Clone an existing GOLIATH module into goliath_hunter/mirror_<name>.py
    for independent fine-tuning. The original is never modified.

    Usage:
        from goliath_hunter import mirror_module
        path = mirror_module("GOLIATH_TRAWLER")
        # Edit path freely
    """
    candidates = [
        MODULES_DIR / f"{module_name}.py",
        MODULES_DIR / f"{module_name.upper()}.py",
        MODULES_DIR / f"{module_name.lower()}.py",
    ]
    src = next((c for c in candidates if c.exists()), None)
    if not src:
        raise FileNotFoundError(
            f"Module '{module_name}' not found in {MODULES_DIR}")

    dest = MODULE_DIR / f"mirror_{src.stem}.py"
    shutil.copy2(src, dest)
    header = (
        f"# MIRROR OF: {src.name}\n"
        f"# Cloned: {datetime.utcnow().isoformat()}\n"
        f"# Fine-tune this file freely. The original is untouched.\n\n"
    )
    content = dest.read_text(encoding="utf-8")
    dest.write_text(header + content, encoding="utf-8")
    print(f"[MIRROR] {src.name} → {dest}")
    return dest


# ── Public API ────────────────────────────────────────────────────────────────

def run_hunt(seed: str, depth: int = 1, domains: str = "",
             county: str = "", state: str = "",
             gh_token: str = "", max_fetch: int = 50,
             dry_run: bool = False) -> str:
    """
    Launch a hunt in a background thread.
    Returns job_id — poll /api/hunter/status/<job_id> for progress.
    """
    seeds = [s.strip() for s in seed.split(",") if s.strip()]
    domain_list = [d.strip() for d in domains.split(",") if d.strip()]

    job_id = hashlib.sha256(
        f"{seed}{time.time()}".encode()).hexdigest()[:16].upper()

    _jobs_lock.acquire()
    try:
        _jobs[job_id] = {
            "job_id":     job_id,
            "seeds":      seeds,
            "depth":      depth,
            "max_fetch":  max_fetch,
            "status":     "QUEUED",
            "message":    "Queued",
            "progress":   0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "result":     None,
        }
    finally:
        _jobs_lock.release()

    hunt = HuntRun(seeds=seeds, depth=depth, domains=domain_list,
                   county=county, state=state,
                   gh_token=gh_token, max_fetch=max_fetch, dry_run=dry_run)

    thread = threading.Thread(target=hunt._execute_wrapped, args=(job_id,), daemon=True)
    thread.start()
    return job_id


def _prune_jobs():
    """Remove completed/failed jobs older than 24h to prevent unbounded memory growth."""
    cutoff = datetime.utcnow().timestamp() - 86400
    _jobs_lock.acquire()
    try:
        stale = [
            jid for jid, j in _jobs.items()
            if j.get("status") in ("COMPLETED", "FAILED")
            and datetime.fromisoformat(j.get("updated_at", "2000-01-01")).timestamp() < cutoff
        ]
        for jid in stale:
            del _jobs[jid]
    finally:
        _jobs_lock.release()


def get_job_status(job_id: str) -> dict:
    _jobs_lock.acquire()
    try:
        return _jobs.get(job_id, {"error": "job not found"})
    finally:
        _jobs_lock.release()


def list_jobs() -> list:
    _prune_jobs()
    _jobs_lock.acquire()
    try:
        return list(_jobs.values())
    finally:
        _jobs_lock.release()


# ── Omega Route Registration ──────────────────────────────────────────────────
# This function is called by web_server.py with the Flask app.
# web_server.py adds ONE LINE:  from goliath_hunter.omega_conductor import register_routes

def register_routes(app, conductor_instance=None):
    """Register GOLIATH HUNTER API routes on the Flask app."""
    import re as _re  # local to avoid collision with module-level re

    @app.route("/api/hunter/run", methods=["POST"])
    def hunter_run():
        from flask import request, jsonify
        body = request.get_json(force=True, silent=True) or {}
        seed     = body.get("seed", "")
        dep    = int(body.get("depth", 1))
        dom    = body.get("domains", "")
        county = body.get("county", "")
        state  = body.get("state", "")
        tok    = body.get("gh_token", "")
        mf     = int(body.get("max_fetch", 50))
        dry    = bool(body.get("dry_run", False))

        if not seed:
            return jsonify({"error": "seed is required"}), 400

        job_id = run_hunt(seed, dep, dom, county, state, tok, mf, dry)
        return jsonify({"job_id": job_id, "status": "QUEUED"})

    @app.route("/api/hunter/status/<job_id>", methods=["GET"])
    def hunter_status(job_id):
        from flask import jsonify
        return jsonify(get_job_status(job_id))

    @app.route("/api/hunter/jobs", methods=["GET"])
    def hunter_jobs():
        from flask import jsonify
        return jsonify(list_jobs())

    @app.route("/api/hunter/mirror", methods=["POST"])
    def hunter_mirror():
        from flask import request, jsonify
        body = request.get_json(force=True, silent=True) or {}
        name = body.get("module_name", "")
        if not name:
            return jsonify({"error": "module_name required"}), 400
        try:
            dest = mirror_module(name)
            return jsonify({"mirrored_to": str(dest)})
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404


# ── Missing import fix ────────────────────────────────────────────────────────
import re  # needed by HuntRun for slug generation

# ── CLI Entry Point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="GOLIATH HUNTER — Self-directing OSINT engine")
    ap.add_argument("--seed",      required=True,  help="Comma-separated seed terms")
    ap.add_argument("--depth",     type=int, default=1, help="Re-search cycles")
    ap.add_argument("--domains",   default="",  help="Comma-separated domains for Wayback/subdomain enum")
    ap.add_argument("--county",    default="",  help="County for EPA ECHO")
    ap.add_argument("--state",     default="",  help="State (2-letter) for EPA ECHO")
    ap.add_argument("--max-fetch", type=int, default=50,
                    help="Max nodes to deep-read per cycle (default 50)")
    ap.add_argument("--dry-run",   action="store_true", help="Skip real HTTP, use mock nodes")
    ap.add_argument("--mirror",    default="",  help="Mirror a module for fine-tuning")
    args = ap.parse_args()

    if args.mirror:
        mirror_module(args.mirror)
        sys.exit(0)

    seeds = [s.strip() for s in args.seed.split(",") if s.strip()]
    domain_list = [d.strip() for d in args.domains.split(",") if d.strip()]

    hunt = HuntRun(
        seeds=seeds,
        depth=args.depth,
        domains=domain_list,
        county=args.county,
        state=args.state,
        max_fetch=args.max_fetch,
        dry_run=args.dry_run,
    )
    result = hunt.execute()
    print("\n" + "=" * 60)
    print("HUNT COMPLETE")
    print(json.dumps(result, indent=2))
