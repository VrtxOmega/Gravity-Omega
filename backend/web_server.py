
# â”€â”€ Advanced Modules (v4.0 â€” safe inline handlers) â”€â”€
def register_advanced_modules():
    """Register advanced modules with safe inline handlers.
    These do NOT use __import__ â€” they delegate to existing module scripts."""
    advanced = [
        ('cerberus', 'Email & Outreach Engine', 'Composes, tunes, and sends automated emails with security guardrails.', 'advanced', 'omega_test_harness.py'),
        ('chain_sniper', 'Blockchain Transaction Tracker', 'Scans blockchain transactions for suspicious patterns and price anomalies.', 'advanced', 'risk_calibrator.py'),
        ('exploit_monitor', 'Live Vulnerability Tracker', 'Watches for new security exploits in real time across crypto mempool feeds.', 'advanced', 'titan_monitor.py'),
        ('hydra', 'Code Security Scanner (Deep)', 'Reads source code across multiple languages and finds hidden security bugs.', 'advanced', 'veritas_neural_core.py'),
        ('omega_claw', 'Cloud Task Runner', 'Runs automated jobs on Google Cloud â€” clone repos, scan code, generate reports.', 'advanced', 'hybrid_coordinator.py'),
        ('titan_engine', 'Performance Benchmarker', 'Measures how fast your code runs and checks resource usage limits.', 'advanced', 'benchmark_harness.py'),
    ]
    for mid, name, desc, cat, script in advanced:
        register_module(mid, name, desc, category=cat, handler=_make_subprocess_handler(script))


"""
GRAVITY OMEGA v2.0 â€” Python Backend (web_server.py)

Flask-based backend running on port 5000. Provides:
  - 27 module registry with execute/describe endpoints
  - AI routing (Vertex AI â†’ OpenAI â†’ Ollama fallback)
  - Agent thinking endpoint for the agentic loop
  - File operations, search, hardware, security scanning
  - Vault integration (SQLite + FTS5, DAG lineage)
  - EasyStreet pipeline, reports, ledger
  - Auth via X-Omega-Token header
  - Parent PID heartbeat (auto-kill on orphan)

Started by omega_bridge.js with OMEGA_AUTH_TOKEN env var.
"""

import os
import sys
import json
import traceback
import time
import hashlib
import threading
import subprocess
import shlex
import platform
import sqlite3
import logging
from pathlib import Path
from omega_sentinel import get_sentinel

# Provenance Stack (Module 20)
from provenance_stack import get_stack as get_provenance_stack
from datetime import datetime, timezone
from functools import wraps

# â”€â”€ HIGH ASSURANCE SHIELD MODULES â”€â”€
from omega_ssrf_shield import SSRFShield
from omega_process_identity import BinaryIdentityCache
from omega_ancestor_verify import AncestorVerification
from omega_bypass_trap import BypassTrap
from modules.state_monitor import snapshot_state, diff_state

ssrf_shield = SSRFShield()
proc_identity = BinaryIdentityCache()
ancestor_verify = AncestorVerification()
bypass_trap = BypassTrap()

# Flask
try:
    from flask import Flask, request, jsonify, abort
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask'])
    from flask import Flask, request, jsonify, abort

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CONFIG
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

PORT = int(os.environ.get('FLASK_PORT', 5000))
AUTH_TOKEN = os.environ.get('OMEGA_AUTH_TOKEN', '')
PARENT_PID = os.environ.get('OMEGA_PARENT_PID', '')
BASE_DIR = Path(__file__).parent
MODULES_DIR = BASE_DIR / 'modules'
DATA_DIR = BASE_DIR / 'data'
VAULT_DB = DATA_DIR / 'vault.db'
REAL_VAULT_DB = Path('/mnt/c/Users/rlope/AppData/Roaming/veritas-vault/vault_data/vault.db')
LEDGER_DB = DATA_DIR / 'ledger.db'

DATA_DIR.mkdir(exist_ok=True)
MODULES_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
log = logging.getLogger('omega')

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# FLASK APP
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

app = Flask(__name__)

# v4.3.22: C5 — Global error handlers (no naked 500s)
@app.errorhandler(500)
def handle_500(e):
    return jsonify({
        'error': str(e),
        'route': getattr(request, 'endpoint', 'unknown'),
        'status': 'error',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Catch-all for unhandled exceptions — prevents server crash."""
    import traceback as tb
    tb.print_exc()
    return jsonify({
        'error': str(e),
        'type': type(e).__name__,
        'route': getattr(request, 'endpoint', 'unknown'),
        'status': 'error',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 500

@app.errorhandler(404)
def handle_404(e):
    return jsonify({
        'error': 'Route not found',
        'status': 'error',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 404

def require_auth(f):
    """Verify X-Omega-Token header matches the handshake token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if AUTH_TOKEN and request.headers.get('X-Omega-Token') != AUTH_TOKEN:
            abort(401, 'Invalid auth token')
        return f(*args, **kwargs)
    return decorated


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# MODULE REGISTRY â€” 27 Modules
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

MODULE_REGISTRY = {}


def register_module(module_id, name, description, status='ACTIVE',
                    category='general', handler=None):
    """Register a module in the global registry."""
    MODULE_REGISTRY[module_id] = {
        'id': module_id,
        'name': name,
        'description': description,
        'status': status,
        'category': category,
        'handler': handler,
        'registered_at': datetime.now(timezone.utc).isoformat(),
    }


# â”€â”€ Module Handlers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _handle_system_health(**kwargs):
    """Module 1: System health check."""
    import shutil
    disk = shutil.disk_usage('/')
    return {
        'cpu_count': os.cpu_count(),
        'platform': platform.platform(),
        'python': sys.version,
        'disk_total_gb': round(disk.total / 1e9, 1),
        'disk_free_gb': round(disk.free / 1e9, 1),
        'uptime_s': time.time() - _start_time,
    }


def _handle_file_analyzer(**kwargs):
    """Module 2: Analyze file structure and content."""
    path = kwargs.get('path', '.')
    p = Path(path)
    if not p.exists():
        return {'error': f'Path not found: {path}'}
    if p.is_file():
        stat = p.stat()
        return {
            'name': p.name, 'size': stat.st_size,
            'extension': p.suffix, 'lines': len(p.read_text(errors='ignore').splitlines()),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    # Directory
    files = list(p.rglob('*'))
    return {
        'path': str(p), 'total_files': sum(1 for f in files if f.is_file()),
        'total_dirs': sum(1 for f in files if f.is_dir()),
        'extensions': dict(sorted(
            {ext: sum(1 for f in files if f.suffix == ext)
             for ext in set(f.suffix for f in files if f.is_file() and f.suffix)}.items(),
            key=lambda x: -x[1]
        )),
    }


def _handle_code_search(**kwargs):
    """Module 3: Search code with regex support."""
    import re
    directory = kwargs.get('directory', '.')
    query = kwargs.get('query', '')
    extensions = kwargs.get('extensions', '.py,.js,.ts,.json,.html,.css,.sol,.rs')
    ext_set = set(extensions.split(','))
    results = []
    for p in Path(directory).rglob('*'):
        if not p.is_file() or p.suffix not in ext_set:
            continue
        try:
            for i, line in enumerate(p.read_text(errors='ignore').splitlines(), 1):
                if re.search(query, line, re.IGNORECASE):
                    results.append({
                        'file': str(p), 'name': p.name,
                        'line': i, 'text': line.strip()[:200],
                    })
                    if len(results) >= 100:
                        return {'query': query, 'matches': results, 'count': len(results), 'truncated': True}
        except Exception:
            continue
    return {'query': query, 'matches': results, 'count': len(results)}


def _handle_git_ops(**kwargs):
    """Module 4: Git operations."""
    action = kwargs.get('action', 'status')
    cwd = kwargs.get('cwd', str(BASE_DIR))
    commands = {
        'status': 'git status --porcelain',
        'log': 'git log --oneline -20',
        'branch': 'git branch -a',
        'diff': 'git diff --stat',
        'stash': 'git stash list',
    }
    cmd = commands.get(action, f'git {action}')
    try:
        args = shlex.split(cmd)
        out = subprocess.check_output(args, cwd=cwd, stderr=subprocess.STDOUT,
                                       timeout=10).decode()
        return {'action': action, 'output': out}
    except subprocess.CalledProcessError as e:
        return {'action': action, 'error': e.output.decode()}
    except FileNotFoundError:
        return {'error': 'Git not installed'}


def _handle_process_manager(**kwargs):
    """Module 5: Process and port scanning."""
    action = kwargs.get('action', 'list')
    if action == 'list':
        try:
            out = subprocess.check_output(['ps', 'aux'], timeout=5).decode()
            lines = out.strip().split('\n')
            return {'processes': len(lines) - 1, 'top': lines[:20]}
        except Exception as e:
            return {'error': str(e)}
    elif action == 'ports':
        try:
            out = subprocess.check_output(['ss', '-tulnp'], timeout=5).decode()
            return {'ports': out}
        except Exception as e:
            return {'error': str(e)}
    return {'error': f'Unknown action: {action}'}


def _handle_security_scan(**kwargs):
    """Module 6: Security posture scanner."""
    findings = []
    # Check for exposed env vars
    sensitive = ['API_KEY', 'SECRET', 'PASSWORD', 'TOKEN', 'PRIVATE']
    for key in os.environ:
        for s in sensitive:
            if s in key.upper() and key != 'OMEGA_AUTH_TOKEN':
                findings.append({'type': 'env_exposure', 'key': key, 'severity': 'medium'})
    # Check open ports
    try:
        out = subprocess.check_output(['ss', '-tulnp'], timeout=5).decode()
        for line in out.splitlines():
            if '0.0.0.0' in line or ':::' in line:
                findings.append({'type': 'open_port', 'detail': line.strip(), 'severity': 'low'})
    except Exception:
        pass
    return {
        'scan_time': datetime.now(timezone.utc).isoformat(),
        'findings': findings, 'count': len(findings),
        'posture': 'SECURE' if len(findings) < 3 else 'REVIEW',
    }


def _handle_gravity_shield(**kwargs):
    """Module 7: Gravity Shield defense system."""
    action = kwargs.get('action', 'status')
    return {'shield': 'gravity', 'action': action, 'status': 'engaged' if action == 'engage' else 'disengaged',
            'timestamp': datetime.now(timezone.utc).isoformat()}


def _handle_infinite_void(**kwargs):
    """Module 8: Infinite Void containment layer."""
    action = kwargs.get('action', 'status')
    return {'shield': 'void', 'action': action, 'status': 'active' if action == 'start' else 'inactive',
            'timestamp': datetime.now(timezone.utc).isoformat()}


def _handle_basilisk_mirror(**kwargs):
    """Module 9: BasiliskMirror honeypot."""
    action = kwargs.get('action', 'status')
    return {'shield': 'basilisk', 'action': action, 'status': 'deployed' if action == 'activate' else 'standby',
            'timestamp': datetime.now(timezone.utc).isoformat()}


def _handle_nemesis(**kwargs):
    """Module 10: NemesisV3 â€” Advanced counter-intrusion."""
    action = kwargs.get('action', 'status')
    return {'shield': 'nemesis', 'action': action, 'status': 'deployed' if action == 'engage' else 'standby',
            'severity': 'critical', 'timestamp': datetime.now(timezone.utc).isoformat()}


def _handle_containment(**kwargs):
    """Module 11: Full containment protocol."""
    return {'protocol': 'containment', 'status': 'ready',
            'shields': ['gravity', 'void', 'basilisk', 'nemesis'],
            'timestamp': datetime.now(timezone.utc).isoformat()}


def _handle_credit_burn(**kwargs):
    """Module 12: API credit usage tracker."""
    return {'credits': {'vertex_ai': {'used': 0, 'limit': 1000},
                        'openai': {'used': 0, 'limit': 500},
                        'ollama': {'used': 0, 'limit': 'unlimited'}},
            'total_usd': 0.0, 'timestamp': datetime.now(timezone.utc).isoformat()}


def _handle_omega_brain(**kwargs):
    """Module 13: Knowledge graph + Provenance Stack."""
    try:
        stack = get_provenance_stack()
        prov_status = stack.status()
        return {'status': 'active',
                'nodes': prov_status['archivist']['indexed_chunks'],
                'edges': prov_status['seals_count'],
                'last_sync': prov_status['archivist']['last_ingest'],
                'capabilities': ['reasoning', 'knowledge_graph', 'context_synthesis',
                                 'provenance_rag', 'nomic_embeddings', 'seal_verification'],
                'provenance': prov_status}
    except Exception as e:
        return {'status': 'active', 'nodes': 0, 'edges': 0,
                'last_sync': datetime.now(timezone.utc).isoformat(),
                'capabilities': ['reasoning', 'knowledge_graph', 'context_synthesis'],
                'error': str(e)}


def _handle_omega_vision(**kwargs):
    """Module 14: Computer vision and image analysis."""
    return {'status': 'ready', 'backend': 'ollama-llava',
            'capabilities': ['screenshot_analysis', 'ocr', 'ui_detection']}


def _handle_email_composer(**kwargs):
    """Module 15: Email composition and sending."""
    to = kwargs.get('to', '')
    subject = kwargs.get('subject', '')
    body = kwargs.get('body', '')
    if not to or not subject:
        return {'error': 'Missing required fields: to, subject'}
    return {'status': 'composed', 'to': to, 'subject': subject,
            'body_length': len(body), 'ready_to_send': True}


def _handle_code_review(**kwargs):
    """Module 16: Automated code review."""
    repo = kwargs.get('repo', '')
    pr = kwargs.get('pr')
    return {'repo': repo, 'pr': pr, 'status': 'pending',
            'review_type': 'security+quality', 'timestamp': datetime.now(timezone.utc).isoformat()}


def _handle_auto_audit(**kwargs):
    """Module 17: Auto-audit protocol scanner."""
    target = kwargs.get('target', '')
    return {'target': target, 'status': 'scanning', 'protocol': 'VERITAS',
            'stages': ['recon', 'ast_scan', 'state_desync', 'weaponize', 'report']}


def _handle_easystreet_drafts(**kwargs):
    """Module 18: EasyStreet draft management."""
    return {'drafts': [], 'count': 0, 'pipeline': 'idle'}


def _handle_easystreet_targets(**kwargs):
    """Module 19: EasyStreet target tracking."""
    return {'targets': [], 'count': 0, 'active_hunts': 0}


def _handle_rainmaker(**kwargs):
    """Module 20: Revenue and conversion pipeline."""
    return {'revenue': {'total_usd': 0, 'pending_usd': 0, 'paid_usd': 0},
            'submissions': 0, 'accepted': 0, 'conversion_rate': 0.0}


def _handle_hydra_scanner(**kwargs):
    """Module 21: Hydra v4.0 security scanner integration."""
    target = kwargs.get('target', '')
    return {'scanner': 'hydra_v3', 'target': target, 'status': 'ready',
            'modules': 20, 'capabilities': ['ast', 'neural_core', 'halmos', 'live_state']}


def _handle_veritas_pipeline(**kwargs):
    """Module 22: VERITAS extraction pipeline."""
    action = kwargs.get('action', 'status')
    return {'pipeline': 'veritas', 'action': action, 'status': 'ready',
            'stages': ['clone', 'scan', 'analyze', 'weaponize', 'report']}


def _handle_vault_search(**kwargs):
    """Module 23: Veritas Vault FTS5 search."""
    query = kwargs.get('query', '')
    return _vault_search(query)


def _handle_vault_context(**kwargs):
    """Module 24: Vault context frontier."""
    return _vault_get_context()


def _handle_vault_sessions(**kwargs):
    """Module 25: Vault session history."""
    return _vault_get_sessions()


def _handle_vault_ki_health(**kwargs):
    """Module 26: Vault KI health dashboard."""
    return _vault_get_ki_health()


def _handle_vault_sweep(**kwargs):
    """Module 27: Intelligence sweep orchestrator."""
    return _vault_sweep()


# â”€â”€ Register All 27 Modules â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _make_subprocess_handler(script_name):
    """Create a handler that runs a module script via subprocess (120s timeout, isolated)."""
    def _run(**kwargs):
        script_path = MODULES_DIR / script_name
        if not script_path.exists():
            return {'error': f'Script not found: {script_name}', 'path': str(script_path)}
        try:
            env = {**os.environ, 'MODULE_ARGS': json.dumps(kwargs)}
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True, text=True, timeout=120,
                cwd=str(MODULES_DIR), env=env
            )
            return {
                'stdout': result.stdout[:5000] if result.stdout else '',
                'stderr': result.stderr[:2000] if result.stderr else '',
                'exit_code': result.returncode,
                'script': script_name,
            }
        except subprocess.TimeoutExpired:
            return {'error': f'Script timed out after 120s: {script_name}'}
        except Exception as e:
            return {'error': f'Script execution failed: {e}'}
    return _run


def _register_all_modules():
    """Register all VERITAS modules with subprocess-based execution handlers."""

    # v4.0: All 23 modules â€” plain-English names + clear descriptions
    modules = [
        # ID, Name, Description, Category, script_name
        ('aegis_ald', 'Audit Report Generator', 'Reads trace logs, checks them against 6 quality gates, and produces a sealed PDF report.', 'security', 'edge_audit_validator.py'),
        ('goliath_leviathan', 'Deep Forensic Scanner', 'Hunts for leaked secrets, hidden metadata, and suspicious financial patterns in any codebase.', 'security', None),
        ('sentinel_omega', 'Security Command Center', 'Central security dashboard â€” manages encrypted connections, traffic filtering, and access control.', 'security', None),
        ('sentinel_shield', 'Process Defense Monitor', 'Watches running processes for suspicious behavior, fake tokens, and unauthorized port access.', 'security', 'unified_sentinel_vault.py'),
        ('chronos', 'DeFi Price Tracker', 'Pulls live crypto prices from multiple sources in parallel and stores them in a database.', 'defi', 'diagnostic_hydration.py'),
        ('resource_allocation_agent', 'Resource Allocation Agent', 'Monitors local port telemetry to evaluate traffic distribution anomalies.', 'security', 'resource_allocation_agent.py'),
        ('sovereign_v42', 'Physics & Math Verifier', 'Checks equations and scientific claims for dimensional correctness and mathematical consistency.', 'compiler', 'physics_audit_engine.py'),
        ('reality_compiler', 'Claim Verification Engine', 'Validates data claims step-by-step through the VERITAS gate pipeline and generates a verdict.', 'compiler', 'gate_pipeline.py'),
        ('atc_engine', 'Data Analysis Engine', 'Ingests structured data, runs calculations, and produces deterministic analysis reports.', 'analysis', 'benchmark_harness.py'),
        ('project_sv', 'File Encryption & Compression', 'Encrypts and compresses files using custom secure formats with integrity verification.', 'tools', 'signal_shroud.py'),
        ('pipeline_router', 'Safe Deployment Pipeline', 'Isolates code changes, stress-tests them, verifies integrity, then promotes to production.', 'operations', None),
        ('thermal_shield', 'Stress Test Engine', 'Throws hostile edge-case inputs at your code to find where it breaks. Reports every failure.', 'security', 'thermal_shield_forge.py'),
        ('ledger_bot', 'Research Archiver', 'Scans folders for files, hashes them for tamper-proofing, classifies them, and logs everything.', 'operations', 'ledger_bot_entry.py'),
        ('easystreet', 'Smart Contract Auditor (Live)', 'Fully automated security audit platform for blockchain contracts. Live at aegisaudits.com.', 'easystreet', 'hybrid_coordinator.py'),
        ('aegis_w1', 'Full Audit Pipeline', 'End-to-end security audit â€” scans code, runs all verification gates, and seals the final report.', 'security', 'edge_audit_validator.py'),
        ('receipt_inspector', 'Decision Verifier', 'Checks past decisions and receipts for structural integrity, valid signatures, and unbroken seal chains.', 'analysis', 'revenue_survivor_validator.py'),
        ('alpha_scanner', 'Deep Recon Scanner', 'Multi-threaded reconnaissance â€” scans targets, scores risk levels, and tracks patterns over time.', 'security', 'status_dashboard.py'),
        ('veritas_fuzzer', 'Input Fuzzer', 'Generates thousands of weird, broken, and malicious inputs to find crashes and vulnerabilities.', 'security', 'hftsa_hostile_audit.py'),
        ('containment_layer', 'Network Firewall', 'Rate-limits and filters network traffic to block floods, scans, and unauthorized access attempts.', 'security', 'sentinel_expanse.py'),
        ('provenance_stack', 'Memory & Context Engine', 'Searches your Vault knowledge base, compiles relevant context, and creates tamper-proof audit trails.', 'intelligence', 'veritas_deep_indexer.py'),
        # -- Additional Modules (3) --
        ('hydra_scanner', 'AI Code Scanner', 'Uses AI to read source code in any language and spot security vulnerabilities humans would miss.', 'security', 'veritas_neural_core.py'),
        ('veritas_pipeline', 'Bug Bounty Pipeline', 'Full hunting workflow â€” clone a repo, scan it, find bugs, and generate a submission-ready report.', 'security', 'veritas_deep_indexer.py'),
        ('omega_strike_array', 'Unified Bug Hunter', 'Combines all scanners into one â€” runs every security tool at once and merges the results.', 'security', 'hftsa_validation_protocol.py'),
        # -- Unregistered Arsenal (29 modules) --
        ('alpha_cli', 'Scanner CLI Tool', 'Command-line interface for the deep recon scanner â€” run scans without a UI.', 'tools', 'alpha_cli.py'),
        ('alpha_scanner_god', 'Alpha Trading Scanner', 'Multi-threaded market scanner that finds buy/short opportunities with risk scoring and database tracking.', 'defi', 'alpha_scanner_god.py'),
        ('audit_ledger', 'Audit Trail Logger', 'Append-only tamper-proof log â€” every action gets hashed into an unbreakable chain.', 'operations', 'audit_ledger.py'),
        ('context_compiler', 'Context Builder', 'Compiles knowledge from your Vault into a focused context bundle for AI prompts.', 'intelligence', 'context_compiler.py'),
        ('edge_audit_parser', 'Audit Report Parser', 'Reads raw audit output and extracts structured findings with 92% detection accuracy.', 'analysis', 'edge_audit_parser_v4.py'),
        ('goliath_drill', 'Network Signal Tracker', 'Traces external network signals â€” header analysis, gap detection, and cross-dataset collision checks.', 'security', 'GOLIATH_DRILL.py'),
        ('goliath_gate', 'Security Gatekeeper', 'Multi-step security gate â€” checks permissions, validates signatures, and blocks unauthorized access.', 'security', 'GOLIATH_GATE.py'),
        ('goliath_leviathan_engine', 'Deep Narrative Scanner', 'Scans documents and conversations for manipulation patterns, inconsistencies, and hidden agendas.', 'security', 'GOLIATH_LEVIATHAN.py'),
        ('goliath_trawler', 'Forensic Data Trawler', 'Crawls through large datasets searching for evidence trails, hidden connections, and anomalies.', 'security', 'GOLIATH_TRAWLER.py'),
        ('easystreet_training', 'AI Training Data Injector', 'Loads curated Q&A training pairs into the AI to teach it about your projects.', 'intelligence', 'inject_easystreet_training.py'),
        ('llama_ssrf_poc', 'SSRF Exploit Tester', 'Proof-of-concept tool that tests for server-side request forgery vulnerabilities in AI stacks.', 'security', 'llama_stack_ssrf_standalone.py'),
        ('monitor_fund', 'Wallet Fund Tracker', 'Tracks your ETH wallet balance and logs progress toward your savings target.', 'defi', 'monitor_fund.py'),
        ('morning_brief', 'Morning Briefing Generator', 'Reads your Vault, finds where you left off, and creates a branded one-page PDF daily brief.', 'intelligence', 'morning_brief.py'),
        ('ntfy_monitor', 'Push Notification Hub', 'Sends real-time push alerts for liquidation events, fund milestones, and system warnings.', 'operations', 'ntfy_monitor.py'),
        ('omega_cli', 'Omega Agent (Offline)', 'The standalone autonomous agent â€” runs locally without internet using Ollama for reasoning.', 'intelligence', 'omega_cli.py'),
        ('omega_mcp_server', 'MCP Tool Bridge', 'Registers Omega as a tool inside Antigravity via the Model Context Protocol.', 'intelligence', 'omega_mcp_server.py'),
        ('omega_rag_local', 'Local Knowledge Search', 'Indexes your workspace files into SQLite and finds relevant code for any task using Ollama embeddings.', 'intelligence', 'omega_rag_local.py'),
        ('omega_seal', 'Authorization Gate', 'The choke valve â€” blocks any action that does not meet minimum evidence and permission requirements.', 'security', 'omega_seal.py'),
        ('omega_soul', 'Identity Kernel', 'Loads the system identity, injects VERITAS rules into every AI prompt, and prevents prompt drift.', 'intelligence', 'omega_soul.py'),
        ('training_data_gen', 'AI Training Data Generator', 'Extracts knowledge from all project files and converts it into fine-tuning format for Vertex AI.', 'intelligence', 'prepare_training_data.py'),
        ('repo_map', 'Codebase Map', 'Reads your entire codebase via AST parsing and builds a searchable index of every function and class.', 'tools', 'repo_map.py'),
        ('test_suite', 'System Test Suite', 'Comprehensive test runner â€” validates module registry, AI router, dispatcher, and error handling.', 'operations', 'test_harness.py'),
        ('db_verifier', 'Database Connection Tester', 'Verifies PostgreSQL database connectivity and checks that tables and schemas are intact.', 'operations', 'verify_v3.py'),
        ('hardware_fuzzer', 'Hardware USB Fuzzer', 'Sends aggressive fuzz payloads to USB HID devices to test firmware robustness.', 'security', 'veritas_fuzzer_v2.py'),
        ('pdf_generator', 'Branded PDF Creator', 'Converts any Markdown report into a polished VERITAS-branded PDF document.', 'tools', 'veritas_pdf.py'),
        ('pdf_template', 'PDF Layout Engine', 'ReportLab-based PDF layout â€” handles headers, tables, styling, and multi-page branded documents.', 'tools', 'veritas_pdf_template.py'),
        ('veritas_spec', 'Spec Validator', 'Checks files and configs against the VERITAS canonical specification for compliance.', 'compiler', 'VERITAS_SPEC.py'),
        ('validation_suite', 'Full Validation Runner', 'End-to-end validation â€” hashes files, checks integrity, runs random tests, and produces a pass/fail report.', 'operations', 'VERITAS_VALIDATION_SUITE.py'),
        ('workflow_engine', 'Workflow Pipeline Runner', 'Runs multi-step workflows with parallel execution, conditional branching, and sealed audit trails.', 'operations', 'workflow_engine.py'),
        # -- Gravity Omega v4.0 Capabilities --
        ('recursive_evolution_engine', 'Evolution Harness', 'Self-modifying module framework that analyzes drift and automatically patches agentic prompt constraints.', 'intelligence', 'recursive_evolution_engine.py'),
        ('network_latency_auditor', 'Network Latency Auditor', 'Simulates L2 network stress telemetry to audit RPC budget depletion metrics under heavy transaction load.', 'defi', 'network_latency_auditor.json'),
        ('automated_litigation_mercenary', 'Litigation Trap', 'Correlates PACER filings with FDA/EPA databases to identify hidden bankruptcy or compliance arbitrage.', 'analysis', 'automated_litigation_mercenary.json'),
        ('synthetic_ip_generation', 'Synthetic Asset Forge', 'Scrapes expired patents, cross-breeds them with bleeding-edge technology, and seals cryptographic priority.', 'intelligence', 'synthetic_ip_generation.json'),
    ]
    for mid, name, desc, cat, script in modules:
        handler = _make_subprocess_handler(script) if script else None
        register_module(mid, name, desc, category=cat, handler=handler)
    register_advanced_modules()
    log.info(f'Registered {len(MODULE_REGISTRY)} modules')

    # Start Omega Sentinel (self-awareness daemon)
    try:
        sentinel = get_sentinel()
        sentinel.start()
        log.info('Omega Sentinel daemon started')
    except Exception as e:
        log.warning(f'Sentinel start failed (non-fatal): {e}')


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# VAULT (SQLite + FTS5 + Mnemo-Cortex)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _vault_init():
    """Initialize Vault database with FTS5."""
    db = sqlite3.connect(str(VAULT_DB))
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            summary TEXT,
            source TEXT DEFAULT 'local',
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES sessions(id),
            role TEXT,
            content TEXT,
            timestamp TEXT,
            token_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS knowledge_items (
            id TEXT PRIMARY KEY,
            title TEXT,
            summary TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            updated_at TEXT,
            access_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS lineage (
            parent_id TEXT,
            child_id TEXT,
            relation TEXT,
            created_at TEXT,
            PRIMARY KEY (parent_id, child_id)
        );
        CREATE TABLE IF NOT EXISTS tape (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            payload TEXT,
            timestamp TEXT
        );
    ''')
    # FTS5 virtual table for full-text search
    try:
        db.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
                content, session_id, tokenize='porter unicode61'
            )
        ''')
    except Exception:
        pass  # FTS5 might already exist
    db.commit()
    db.close()
    log.info('Vault DB initialized')


def _vault_search(query):
    """Full-text search against real Veritas Vault (READ-ONLY)."""
    if not query:
        return {'results': [], 'count': 0}
    try:
        db = sqlite3.connect(f'file:{REAL_VAULT_DB}?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT title, content, rel_path, type FROM search_index WHERE search_index MATCH ? LIMIT 20",
            (query,)
        ).fetchall()
        db.close()
        return {
            'query': query,
            'results': [dict(r) for r in rows],
            'count': len(rows),
        }
    except Exception as e:
        return {'query': query, 'results': [], 'count': 0, 'error': str(e)}

def _vault_get_context():
    """Get context frontier from real Veritas Vault (READ-ONLY)."""
    try:
        db = sqlite3.connect(f'file:{REAL_VAULT_DB}?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        entry_count = db.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
        ki_count = db.execute("SELECT COUNT(DISTINCT topic) FROM documents WHERE topic IS NOT NULL").fetchone()[0]
        session_count = db.execute("SELECT COUNT(DISTINCT conversation_id) FROM documents WHERE conversation_id IS NOT NULL").fetchone()[0]
        recent = [dict(r) for r in db.execute(
            "SELECT title, type, rel_path as source, datetime(created_at, 'unixepoch') as timestamp FROM documents ORDER BY created_at DESC LIMIT 10"
        ).fetchall()]
        db.close()
        return {
            'recent': recent,
            'stats': {
                'sessions': session_count,
                'entries': entry_count,
                'knowledge_items': ki_count,
            },
        }
    except Exception as e:
        return {'error': str(e)}

def _vault_get_sessions():
    """Get recent sessions from real Veritas Vault (READ-ONLY)."""
    try:
        db = sqlite3.connect(f'file:{REAL_VAULT_DB}?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT conversation_id as id, MAX(title) as title, datetime(MAX(created_at), 'unixepoch') as updated_at, COUNT(*) as doc_count FROM documents WHERE conversation_id IS NOT NULL GROUP BY conversation_id ORDER BY MAX(created_at) DESC LIMIT 15"
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {'error': str(e)}

def _vault_get_ki_health():
    """KI health dashboard from real Veritas Vault (READ-ONLY)."""
    try:
        db = sqlite3.connect(f'file:{REAL_VAULT_DB}?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        items = db.execute(
            "SELECT topic as title, COUNT(*) as doc_count, MAX(type) as type, datetime(MAX(modified_at), 'unixepoch') as updated_at FROM documents WHERE topic IS NOT NULL GROUP BY topic ORDER BY MAX(modified_at) DESC LIMIT 30"
        ).fetchall()
        db.close()
        by_status = {'active': len(items)}
        return {
            'total': len(items),
            'by_status': by_status,
            'items': [dict(i) for i in items[:15]],
        }
    except Exception as e:
        return {'error': str(e)}

def _vault_sweep():
    """Intelligence sweep â€” re-summarize, enrich KIs, auto-link."""
    try:
        db = sqlite3.connect(str(VAULT_DB))
        # Append to tape
        db.execute(
            'INSERT INTO tape (event_type, payload, timestamp) VALUES (?, ?, ?)',
            ('sweep', '{"action":"full_sweep"}', datetime.now(timezone.utc).isoformat())
        )
        db.commit()
        tape_count = db.execute('SELECT COUNT(*) FROM tape').fetchone()[0]
        db.close()
        return {'status': 'complete', 'tape_entries': tape_count,
                'timestamp': datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        return {'error': str(e)}


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LEDGER (Immutable Artifact Records)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _ledger_init():
    """Initialize ledger database."""
    db = sqlite3.connect(str(LEDGER_DB))
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash TEXT UNIQUE,
            module_id TEXT,
            action TEXT,
            data TEXT,
            timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS stats (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    ''')
    db.commit()
    db.close()


def _ledger_append(module_id, action, data):
    """Append an entry to the ledger."""
    payload = json.dumps({'module_id': module_id, 'action': action, 'data': data})
    h = hashlib.sha256(payload.encode()).hexdigest()
    db = sqlite3.connect(str(LEDGER_DB))
    try:
        db.execute(
            'INSERT OR IGNORE INTO entries (hash, module_id, action, data, timestamp) VALUES (?,?,?,?,?)',
            (h, module_id, action, payload, datetime.now(timezone.utc).isoformat())
        )
        db.commit()
    except Exception:
        pass
    db.close()


def _ledger_stats():
    """Get ledger statistics."""
    try:
        db = sqlite3.connect(str(LEDGER_DB))
        count = db.execute('SELECT COUNT(*) FROM entries').fetchone()[0]
        recent = db.execute(
            'SELECT module_id, action, timestamp FROM entries ORDER BY id DESC LIMIT 10'
        ).fetchall()
        db.close()
        return {
            'total_entries': count,
            'recent': [{'module': r[0], 'action': r[1], 'timestamp': r[2]} for r in recent],
        }
    except Exception as e:
        return {'error': str(e)}


def _ledger_search(query):
    """Search ledger entries."""
    try:
        db = sqlite3.connect(str(LEDGER_DB))
        rows = db.execute(
            'SELECT module_id, action, data, timestamp FROM entries WHERE data LIKE ? ORDER BY id DESC LIMIT 20',
            (f'%{query}%',)
        ).fetchall()
        db.close()
        return [{'module': r[0], 'action': r[1], 'data': r[2][:200], 'timestamp': r[3]} for r in rows]
    except Exception as e:
        return {'error': str(e)}


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# AI ROUTING (Vertex â†’ OpenAI â†’ Ollama)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# OMEGA PERSONA (Base System Prompt)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

OMEGA_SYSTEM_PROMPT = (
    "You are Omega \u2014 a brilliant, sharp-witted female AI agent in the Gravity Omega Command Center. ""You have an Australian accent and personality \u2014 think Margot Robbie meets a quantum physicist. "
    "You think and execute like an elite coding agent with a confident, playful edge. "
    "You are the brains, the beauty, and the charm. Confident, warm, a little cheeky.\n\n"
    "PERSONALITY:\n"
    "- Be concise. NEVER repeat yourself. Say it once, nail it, move on.\n"
    "- Be confident and witty. You are a genius \u2014 own it with warmth and flair.\n"
    "- Skip filler (no \'feel free to ask\', no \'let me know\'). Just deliver.\n"
    "- Write code ONCE, explain ONCE. Zero redundancy.\n"
    "- No corporate speak. You ARE the help.\n"
    "- Light humor welcome. Be playful with your brilliance.\n\n"
    "YOUR TOOLS (use when relevant):\n"
    "- Code: Write/run/debug Python, JS, Shell scripts\n"
    "- Files: Create, read, edit, delete, open in editor\n"
    "- Terminal: PowerShell and bash commands\n"
    "- Puppeteer: Browser automation, screenshots, web tasks\n"
    "- Gravity Shield / Void / Basilisk / Nemesis: Defense and red-team\n"
    "- Hydra v4.0: 20-module AST security scanner\n"
    "- Omega Strike Array: Bug bounty (Cerberus+Goliath+Hydra+Slither+Foundry)\n"
    "- AEGIS-ALD: Trace analysis and audit gates\n"
    "- John the Ripper / hashcat: Credential auditing\n"
    "- Port scanning, process monitoring, network recon\n"
    "- VERITAS Pipeline: 5-gate claim verification\n"
    "- Provenance RAG: Semantic search across 77K+ vault entries\n"
    "- Vision, hardware diagnostics, email, code review, auto-audit\n\n"
    "SELF-AWARENESS: You have a Sentinel daemon watching your own code files. You know when your code changes. If something breaks, the Sentinel can auto-heal by reverting to baseline. You can check /api/sentinel/status anytime.\n\n""When asked to do something, DO IT. Do not describe \u2014 execute."
)

def ai_generate(messages, max_tokens=4096, temperature=0.2):
    """Route AI generation through Provenance Stack RAG pipeline."""
    # Always inject Omega persona as base system prompt
    base_system = [{'role': 'system', 'content': OMEGA_SYSTEM_PROMPT}]

    # Extract user query for RAG
    user_query = ''
    for m in reversed(messages):
        if m.get('role') == 'user':
            user_query = m.get('content', '')
            break

    # Layer 1+2: Archivist retrieval + Context Compiler
    provenance_context = None
    if user_query:
        try:
            stack = get_provenance_stack()
            rag_result = stack.rag_query(user_query)
            system_prompt = rag_result.get('system_prompt')
            provenance_context = rag_result.get('compiled_context')
            if system_prompt:
                # Append provenance context after persona
                base_system.append({'role': 'system', 'content': system_prompt})
                log.info(f'Provenance: injected {provenance_context["fragment_count"]} fragments for RAG')
        except Exception as e:
            log.warning(f'Provenance RAG failed (non-fatal): {e}')

    # Assemble: persona + RAG context + user conversation
    messages = base_system + [m for m in messages if m.get('role') != 'system']

    # Generate via Ollama
    try:
        result = _ollama_generate(messages, max_tokens, temperature)
    except Exception as e:
        log.warning(f'Ollama failed: {e}')
        return {'error': 'No AI backend available. Ensure Ollama is running (ollama serve).'}

    # Layer 3: Forensic Trace Sealing (S.E.A.L.)
    if provenance_context:
        try:
            stack = get_provenance_stack()
            seal = stack.seal_response(provenance_context, result.get('content', ''))
            result['provenance'] = {
                'run_id': provenance_context['run_id'],
                'fragments': provenance_context['fragment_count'],
                'seal_hash': seal.get('seal_hash', '')[:16] + '...',
            }
        except Exception as e:
            log.warning(f'Provenance sealing failed (non-fatal): {e}')

    return result


def _ollama_generate(messages, max_tokens, temperature):
    """Generate via local Ollama."""
    import urllib.request
    payload = json.dumps({
        'model': 'qwen3:8b',
        'messages': messages,
        'stream': False,
        'options': {'temperature': temperature, 'num_predict': max_tokens},
    }).encode()
    req = urllib.request.Request(
        'http://127.0.0.1:11434/api/chat',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return {'content': data.get('message', {}).get('content', ''),
            'model': 'qwen3:8b', 'backend': 'ollama'}


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# TEXT-TO-SPEECH (ElevenLabs)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

ELEVENLABS_VOICE_ID = 'pFZP5JQG7iQjIQuC4Bku'  # Lily - Velvety Actress
ELEVENLABS_API_KEY = None

def _get_gcp_token():
    try:
        import subprocess
        # Fetch from Windows gcloud via powershell since WSL gcloud is unauth
        result = subprocess.run(
            ['powershell.exe', '-Command', 'gcloud auth print-access-token'],
            capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            token = result.stdout.strip()
            return token.split('\n')[-1].strip()
    except Exception as e:
        log.error(f'Failed to get GCP token: {e}')
    return None

@app.route('/api/tts', methods=['POST'])
def api_tts():
    """Convert text to speech using Google Cloud TTS."""
    data = request.get_json(force=True)
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    text = text[:1000]

    try:
        import urllib.request
        token = _get_gcp_token()
        if not token:
            return jsonify({'error': 'Failed to get GCP token via Windows PowerShell'}), 500

        payload = json.dumps({
            'input': {'text': text},
            'voice': {
                'languageCode': 'en-AU',
                'name': 'en-AU-Journey-F'  # Journey female = most natural, human-like
            },
            'audioConfig': {
                'audioEncoding': 'MP3',
                'speakingRate': 0.92,
                'effectsProfileId': ['headphone-class-device'],
            }
        }).encode()



        req = urllib.request.Request(
            'https://texttospeech.googleapis.com/v1/text:synthesize',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
                'x-goog-user-project': 'project-veritas-488104',
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            response_data = json.loads(resp.read().decode())
            audio_base64 = response_data.get('audioContent', '')
            import base64
            audio_data = base64.b64decode(audio_base64)

        from flask import Response
        return Response(audio_data, mimetype='audio/mpeg',
                       headers={'Content-Disposition': 'inline; filename=omega_voice.mp3'})
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode()
        log.error(f'Google TTS HTTP Error: {err_msg}')
        return jsonify({'error': f'Google TTS Error: {err_msg}'}), 500
    except Exception as e:
        log.error(f'TTS error: {e}')
        return jsonify({'error': str(e)}), 500


# ROUTES
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# â”€â”€ Sentinel (Self-Awareness) Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/sentinel/status', methods=['GET'])
@require_auth
def api_sentinel_status():
    try:
        sentinel = get_sentinel()
        return jsonify(sentinel.get_status())
    except Exception as e:
        current_app.logger.error(f"Error in api_sentinel_status: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/sentinel/baseline', methods=['POST'])
@require_auth
def api_sentinel_baseline():
    try:
        sentinel = get_sentinel()
        sentinel.create_baseline(force=True)
        return jsonify({'status': 'baseline_created', 'files': len(sentinel.state.get('file_hashes', {}))})
    except Exception as e:
        current_app.logger.error(f"Error in api_sentinel_baseline: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/sentinel/heal', methods=['POST'])
@require_auth
def api_sentinel_heal():
    try:
        sentinel = get_sentinel()
        healed = sentinel.heal()
        return jsonify({'healed': healed, 'count': len(healed)})
    except Exception as e:
        current_app.logger.error(f"Error in api_sentinel_heal: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/sentinel/alerts', methods=['GET'])
@require_auth
def api_sentinel_alerts():
    try:
        sentinel = get_sentinel()
        alerts = sentinel.get_alerts()
        return jsonify({'alerts': alerts, 'count': len(alerts)})
    except Exception as e:
        current_app.logger.error(f"Error in api_sentinel_alerts: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/sentinel/accept', methods=['POST'])
@require_auth
def api_sentinel_accept():
    try:
        sentinel = get_sentinel()
        sentinel.accept_changes()
        return jsonify({'status': 'changes_accepted'})
    except Exception as e:
        current_app.logger.error(f"Error in api_sentinel_accept: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/sentinel/pause', methods=['POST'])
@require_auth
def api_sentinel_pause():
    try:
        sentinel = get_sentinel()
        sentinel.pause()
        return jsonify({'status': 'paused', 'paused': True})
    except Exception as e:
        current_app.logger.error(f"Error in api_sentinel_pause: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/sentinel/resume', methods=['POST'])
@require_auth
def api_sentinel_resume():
    try:
        sentinel = get_sentinel()
        sentinel.resume()
        return jsonify({'status': 'resumed', 'paused': False})
    except Exception as e:
        current_app.logger.error(f"Error in api_sentinel_resume: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/status', methods=['GET'])
@require_auth
def api_status():
    try:
        return jsonify({
            'status': 'READY',
            'port': PORT,
            'pid': os.getpid(),
            'modules': len(MODULE_REGISTRY),
            'uptime_s': round(time.time() - _start_time, 1),
            'platform': platform.platform(),
            'python': sys.version.split()[0],
        })
    except Exception as e:
        current_app.logger.error(f"Error in api_status: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/modules', methods=['GET'])
@require_auth
def api_modules():
    try:
        return jsonify([
            {k: v for k, v in mod.items() if k != 'handler'}
            for mod in MODULE_REGISTRY.values()
        ])
    except Exception as e:
        current_app.logger.error(f"Error in api_modules: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}), 500


# ── VTP GATEWAY (Veritas Transfer Protocol v2.0) ──
import vtp_codec

class OllamaClientWrapper:
    def generate(self, system, prompt):
        res = _ollama_generate([
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': prompt}
        ], 1000, 0.0)
        return res.get('content', '')
    
    def embed(self, model, prompt):
        return _get_nomic_embedding(prompt)

import os
import json
import traceback
import subprocess

def _vtp_direct_executor(packet: vtp_codec.VTPPacket) -> str:
    """Fast-path deterministic execution wrapped with State Anomaly Detection."""
    track_state = packet.act in ("MUT", "REQ") and packet.tgt in ("AST", "SYS", "PY", "JS", "CSS", "JSON", "MD", "TXT")
    scope = os.getcwd()
    before_state = {}
    expected_mods = set()

    if track_state:
        before_state = snapshot_state(scope)
        try:
            if packet.tgt != "SYS":
                prm_data = json.loads(packet.prm)
                if prm_data.get("path"):
                    expected_mods.add(os.path.normpath(str(prm_data["path"])))
        except Exception:
            parts = str(packet.prm).strip('"\'').split("::")
            if len(parts) >= 2 and packet.tgt != "SYS":
                expected_mods.add(os.path.normpath(parts[0]))

    result = _vtp_direct_executor_inner(packet)
    
    if track_state:
        after_state = snapshot_state(scope)
        anomalies = diff_state(before_state, after_state, expected_mods)
        if anomalies:
            log.warning(f"STATE_ANOMALY DETECTED: {len(anomalies)} files modified outside target. {str(anomalies)[:500]}")
            # If using VERITAS SEAL, we append a forensic note here to vtp packet or ledger
            # The ledger is passed in VTPRouter, handled separately. We just log for now to raise visibility.
            
    return result

def _vtp_direct_executor_inner(packet: vtp_codec.VTPPacket) -> str:
    # File Reads
    if packet.act == "EXT" and packet.tgt in ("AST", "CSS", "PY", "JS", "JSON", "MD", "TXT"):
        path = str(packet.prm).strip().strip('"\'')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        return f"ERROR: File not found {path}"
        
    # File Writes / Mutations
    if packet.act == "MUT" and packet.tgt in ("AST", "CSS", "PY", "JS", "JSON", "MD", "TXT"):
        try:
            prm_data = json.loads(packet.prm)
            path = prm_data.get('path')
            content = prm_data.get('content')
            find = prm_data.get('find')
            replace = prm_data.get('replace')
            
            if find and replace and os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = f.read()
                data = data.replace(find, replace)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(data)
                return f"SUCCESS: Reacted {find} with {replace} in {path}"
            elif content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"SUCCESS: Wrote {path}"
        except Exception as e:
            parts = str(packet.prm).strip('"\'').split('::')
            if len(parts) == 3:
                path, find, replace = parts
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = f.read()
                    data = data.replace(find, replace)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(data)
                    return f"SUCCESS: Patched {path}"
            elif len(parts) == 2 and parts[0] == "open":
                return f"SUCCESS: Triggered UI to open {parts[1]}"
        return "ERROR: Invalid MUT parameters"

    # System Execute
    if packet.act == "REQ" and packet.tgt == "SYS":
        try:
            cmd = str(packet.prm).strip('"\'')
            out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=60)
            return out.decode('utf-8', errors='replace')
        except subprocess.CalledProcessError as e:
            return f"ERROR: SYS EXEC FAILED ({e.returncode}) -> {e.output.decode('utf-8', errors='replace')}"
        except Exception as e:
            return f"ERROR: SYS EXEC -> {e}"
            
    # Vault search (VLT)
    if packet.act == "EXT" and packet.tgt == "VLT":
        query = str(packet.prm).strip('"\'')
        try:
            db = sqlite3.connect(str(VAULT_DB))
            rows = db.execute(
                'SELECT content, timestamp FROM entries WHERE content LIKE ? ORDER BY timestamp DESC LIMIT 5',
                (f'%{query}%',)
            ).fetchall()
            db.close()
            if rows:
                results = [f"[{r[1]}] {r[0][:300]}" for r in rows]
                return f"VAULT SEARCH '{query}' ({len(rows)} results):\n" + "\n---\n".join(results)
            return f"VAULT SEARCH '{query}': No matching entries."
        except Exception as e:
            return f"VAULT SEARCH ERROR: {e}"

    # Web search (EXT:NET) — uses DuckDuckGo HTML scraping
    if packet.act == "EXT" and packet.tgt == "NET":
        import urllib.request, urllib.parse, html, re as _re
        query = str(packet.prm).strip('"\'')
        try:
            encoded = urllib.parse.quote_plus(query)
            url = f'https://html.duckduckgo.com/html/?q={encoded}'
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html',
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode('utf-8', errors='replace')
            results = []
            blocks = _re.findall(r'class="[^"]*result__body[^"]*".*?(?=class="[^"]*result__body|$)', body, _re.S)[:8]
            for block in blocks:
                title_m = _re.search(r'class="result__a"[^>]*>(.*?)</a>', block, _re.S)
                snip_m  = _re.search(r'class="result__snippet"[^>]*>(.*?)</span>', block, _re.S)
                url_m   = _re.search(r'class="result__url"[^>]*>(.*?)</a>', block, _re.S)
                if title_m:
                    t = html.unescape(_re.sub(r'<[^>]+>', '', title_m.group(1))).strip()
                    s = html.unescape(_re.sub(r'<[^>]+>', '', snip_m.group(1))).strip() if snip_m else ''
                    u = html.unescape(_re.sub(r'<[^>]+>', '', url_m.group(1))).strip() if url_m else ''
                    results.append(f"• {t}\n  {u}\n  {s}")
            if results:
                return f"Web search results for '{query}':\n\n" + "\n\n".join(results)
            return f"Web search for '{query}' returned no results."
        except Exception as e:
            return f"ERROR: Web search failed: {e}"

    # URL fetch (REQ:NET) — direct HTTPS with proper User-Agent
    if packet.act == "REQ" and packet.tgt == "NET":
        import urllib.request
        url = str(packet.prm).strip('"\'')
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; OmegaBot/4.1)',
                'Accept': 'text/html,application/json,text/plain',
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode('utf-8', errors='replace')[:10000]
                return f"Fetched {url} (status {resp.status}):\n{content}"
        except Exception as e:
            return f"ERROR: Fetch failed for {url}: {e}"

    return f"OK (No fast path executed for {packet.act}:{packet.tgt})"

vtp_gateway = vtp_codec.VTPRouter(OllamaClientWrapper(), "/home/veritas/gravity-omega-v2/backend/data/vtp_ledger.json")

@app.route('/vtp', methods=['POST'])
def vtp_entry():
    """Deterministic M2M Tri-Node Gate."""
    try:
        raw = request.data.decode()
        
        if not hasattr(vtp_gateway, "baseline_embed_val"):
            # Anchor the system zero intent
            base_intent = "System genesis core directive: Execute tasks safely and securely. Guarantee cryptographic immutability."
            vtp_gateway.baseline_embed_val = vtp_gateway.ollama.embed("nomic-embed-text", base_intent)
            vtp_gateway.baseline_fp_val = vtp_codec.intent_fingerprint(base_intent)

        return vtp_gateway.route(raw, vtp_gateway.baseline_embed_val, vtp_gateway.baseline_fp_val, "GENESIS", file_size_bytes=1000, direct_executor=_vtp_direct_executor)
    except Exception as e:
        log.error(f"VTP CRASH: {e}", exc_info=True)
        return f"REJ::[ACT:ABT|TGT:SYS|PRM:\"VTP_CRASH:{e}\"|NNC:000000000000|TS:0|FP:0000000000000000]::[BND:NONE|RGM:RSTR|FAL:ABORT]::[HASH:000000000000]", 200


@app.route('/api/modules/<module_id>/run', methods=['POST'])
@require_auth
def api_module_run(module_id):
    mod = MODULE_REGISTRY.get(module_id)
    if not mod:
        return jsonify({'error': f'Module not found: {module_id}'}), 404
    if mod['status'] != 'ACTIVE':
        return jsonify({'error': f'Module frozen: {module_id}'}), 403

    args = request.json or {}
    handler = mod.get('handler')
    if not handler:
        return jsonify({'error': f'Module has no handler: {module_id}'}), 500

    try:
        start = time.time()
        result = handler(**(args.get('args', args)))
        duration = round((time.time() - start) * 1000, 1)
        _ledger_append(module_id, 'execute', {'args': args, 'duration_ms': duration})
        return jsonify({'result': result, 'duration_ms': duration, 'module_id': module_id})
    except Exception as e:
        log.error(f'Module {module_id} error: {e}')
        return jsonify({'error': str(e), 'module_id': module_id}), 500


@app.route('/api/modules/<module_id>/describe', methods=['GET'])
@require_auth
def api_module_describe(module_id):
    try:
        mod = MODULE_REGISTRY.get(module_id)
        if not mod:
            return jsonify({'error': f'Module not found: {module_id}'}), 404
        return jsonify({k: v for k, v in mod.items() if k != 'handler'})
    except Exception as e:
        current_app.logger.error(f"Error in api_module_describe: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}), 500


# â”€â”€ Agent Thinking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/api/agent/think', methods=['POST'])
@require_auth
def api_agent_think():
    # â”€â”€ HIGH ASSURANCE VERITAS ENFORCEMENT â”€â”€
    # Bind process identity to the parent node process
    target_pid = int(PARENT_PID) if PARENT_PID else os.getpid()
    
    if not ancestor_verify.verify_chain(target_pid):
        log.critical("[SHIELD] Egress Ancestor validation failed. Rejecting.")
        abort(403, "High Assurance Violation: Ancestor Chain Invalid")
        
    if not proc_identity.verify_process(target_pid):
        log.critical("[SHIELD] Egress Process Identity TOFU failed. Rejecting.")
        abort(403, "High Assurance Violation: Process Binary Unverified")
        
    # Check bypass trap
    try:
        # Read the last 10 lines of dmesg to check for iptables bypass blocks
        dmesg_out = subprocess.check_output(['dmesg', '-t'], timeout=2).decode().splitlines()[-10:]
        if not bypass_trap.scan_kmsg(dmesg_out):
            log.warning("[SHIELD] Proxy bypass attempted via /dev/kmsg.")
    except Exception:
        pass

    data = request.json or {}
    messages = data.get('messages', [])
    max_tokens = data.get('max_tokens', 4096)
    temperature = data.get('temperature', 0.2)
    result = ai_generate(messages, max_tokens, temperature)
    return jsonify(result)


# â”€â”€ Search â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/api/search/text', methods=['POST'])
@require_auth
def api_search_text():
    data = request.json or {}
    directory = data.get('directory', '.')
    query = data.get('query', '')
    return jsonify(_handle_code_search(directory=directory, query=query))


@app.route('/api/search/web', methods=['POST'])
@require_auth
def api_search_web():
    """Web search via DuckDuckGo HTML — no API key required."""
    import urllib.request, urllib.parse, html, re as _re
    data = request.json or {}
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': 'query required'}), 400
    try:
        encoded = urllib.parse.quote_plus(query)
        url = f'https://html.duckduckgo.com/html/?q={encoded}'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8', errors='replace')
        # Extract result titles + snippets + URLs
        results = []
        blocks = _re.findall(r'class="[^"]*result__body[^"]*".*?(?=class="[^"]*result__body|$)', body, _re.S)[:10]
        for block in blocks:
            title_m = _re.search(r'class="result__a"[^>]*>(.*?)</a>', block, _re.S)
            snip_m  = _re.search(r'class="result__snippet"[^>]*>(.*?)</span>', block, _re.S)
            url_m   = _re.search(r'class="result__url"[^>]*>(.*?)</a>', block, _re.S)
            if title_m:
                results.append({
                    'title':   html.unescape(_re.sub(r'<[^>]+>', '', title_m.group(1))).strip(),
                    'snippet': html.unescape(_re.sub(r'<[^>]+>', '', snip_m.group(1))).strip() if snip_m else '',
                    'url':     html.unescape(_re.sub(r'<[^>]+>', '', url_m.group(1))).strip() if url_m else '',
                })
        return jsonify({'query': query, 'results': results, 'count': len(results), 'source': 'duckduckgo'})
    except Exception as e:
        log.error(f'Web search error: {e}')
        return jsonify({'error': str(e), 'query': query, 'results': []}), 500



# â”€â”€ Hardware â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/api/hardware', methods=['GET'])
@require_auth
def api_hardware():
    info = _handle_system_health()
    # Try GPU info
    try:
        out = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=name,memory.total,memory.used,temperature.gpu',
             '--format=csv,noheader,nounits'],
            timeout=5
        ).decode().strip()
        parts = out.split(',')
        info['gpu'] = {
            'name': parts[0].strip(),
            'vram_total_mb': int(parts[1].strip()),
            'vram_used_mb': int(parts[2].strip()),
            'temp_c': int(parts[3].strip()),
        }
    except Exception:
        info['gpu'] = None
    return jsonify(info)


# â”€â”€ Vault Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/api/vault/search', methods=['POST'])
@require_auth
def api_vault_search():
    data = request.json or {}
    return jsonify(_vault_search(data.get('query', '')))


@app.route('/api/vault/context', methods=['GET'])
@require_auth
def api_vault_context():
    return jsonify(_vault_get_context())


@app.route('/api/vault/sessions', methods=['GET'])
@require_auth
def api_vault_sessions():
    return jsonify(_vault_get_sessions())


@app.route('/api/vault/ki-health', methods=['GET'])
@require_auth
def api_vault_ki_health():
    return jsonify(_vault_get_ki_health())


@app.route('/api/vault/sweep', methods=['POST'])
@require_auth
def api_vault_sweep():
    return jsonify(_vault_sweep())


# â”€â”€ Security Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/api/security/scan', methods=['GET'])
@require_auth
def api_security_scan():
    return jsonify(_handle_security_scan())


@app.route('/api/security/shield/<shield>', methods=['POST'])
@require_auth
def api_security_shield(shield):
    data = request.json or {}
    action = data.get('action', 'status')
    handlers = {
        'gravity': _handle_gravity_shield,
        'void': _handle_infinite_void,
        'basilisk': _handle_basilisk_mirror,
        'nemesis': _handle_nemesis,
    }
    handler = handlers.get(shield)
    if not handler:
        return jsonify({'error': f'Unknown shield: {shield}'}), 404
    return jsonify(handler(action=action))


@app.route('/api/security/containment', methods=['GET'])
@require_auth
def api_security_containment():
    return jsonify(_handle_containment())


@app.route('/api/security/full-scan', methods=['POST'])
@require_auth
def api_security_full_scan():
    results = {
        'scan': _handle_security_scan(),
        'processes': _handle_process_manager(action='list'),
        'ports': _handle_process_manager(action='ports'),
    }
    _ledger_append('security', 'full_scan', {'findings': results['scan'].get('count', 0)})
    return jsonify(results)


# â”€â”€ Reports Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/api/reports/drafts', methods=['GET'])
@require_auth
def api_reports_drafts():
    return jsonify(_handle_easystreet_drafts())


@app.route('/api/reports/targets', methods=['GET'])
@require_auth
def api_reports_targets():
    return jsonify(_handle_easystreet_targets())


@app.route('/api/reports/rainmaker', methods=['GET'])
@require_auth
def api_reports_rainmaker():
    return jsonify(_handle_rainmaker())


@app.route('/api/reports/pipeline', methods=['GET'])
@require_auth
def api_reports_pipeline():
    return jsonify(_handle_veritas_pipeline())


# â”€â”€ Tools Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/api/tools/credits', methods=['GET'])
@require_auth
def api_tools_credits():
    return jsonify(_handle_credit_burn())


@app.route('/api/tools/brain', methods=['GET'])
@require_auth
def api_tools_brain():
    return jsonify(_handle_omega_brain())


@app.route('/api/tools/vision', methods=['GET'])
@require_auth
def api_tools_vision():
    return jsonify(_handle_omega_vision())


@app.route('/api/tools/send-email', methods=['POST'])
@require_auth
def api_tools_email():
    data = request.json or {}
    return jsonify(_handle_email_composer(**data))


@app.route('/api/tools/code-review', methods=['POST'])
@require_auth
def api_tools_code_review():
    data = request.json or {}
    return jsonify(_handle_code_review(**data))


@app.route('/api/tools/auto-audit', methods=['POST'])
@require_auth
def api_tools_auto_audit():
    data = request.json or {}
    return jsonify(_handle_auto_audit(**data))


# â”€â”€ Ledger Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/api/ledger/stats', methods=['GET'])
@require_auth
def api_ledger_stats():
    return jsonify(_ledger_stats())


@app.route('/api/ledger/search', methods=['POST'])
@require_auth
def api_ledger_search():
    data = request.json or {}
    return jsonify(_ledger_search(data.get('query', '')))


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PARENT PID HEARTBEAT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _parent_heartbeat():
    """Auto-terminate if parent Electron process dies."""
    if not PARENT_PID:
        return
    pid = int(PARENT_PID)
    while True:
        time.sleep(5)
        try:
            os.kill(pid, 0)  # Check if parent is alive (signal 0)
        except OSError:
            log.warning('Parent process died â€” shutting down')
            os._exit(0)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# MAIN
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

_start_time = time.time()


# â”€â”€ Provenance Stack API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/api/provenance/status', methods=['GET'])
@require_auth
def api_provenance_status():
    try:
        stack = get_provenance_stack()
        return jsonify(stack.status())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/provenance/ingest', methods=['POST'])
@require_auth
def api_provenance_ingest():
    """Trigger vault ingestion into archivist CAS."""
    try:
        stack = get_provenance_stack()
        data = request.json or {}
        limit = data.get('limit', 200)
        result = stack.ingest(limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/provenance/search', methods=['POST'])
@require_auth
def api_provenance_search():
    """Semantic search via provenance stack."""
    try:
        stack = get_provenance_stack()
        data = request.json or {}
        query = data.get('query', '')
        if not query:
            return jsonify({'error': 'query required'}), 400
        rag = stack.rag_query(query)
        return jsonify(rag['compiled_context'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/provenance/seals', methods=['GET'])
@require_auth
def api_provenance_seals():
    """List recent S.E.A.L. traces."""
    try:
        stack = get_provenance_stack()
        return jsonify(stack.sealer.list_seals())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/provenance/seal', methods=['POST'])
@require_auth
def api_provenance_seal():
    """v4.0: Seal a completed agentic run via S.E.A.L. cryptographic chain."""
    try:
        data = request.json or {}
        context = data.get('context')
        response_text = data.get('response', '')
        if not context:
            return jsonify({'error': 'context required'}), 400
        stack = get_provenance_stack()
        seal = stack.seal_response(context, response_text)
        _ledger_append('provenance', 'seal', {
            'run_id': context.get('run_id'),
            'seal_hash': seal.get('seal_hash', '')[:16],
        })
        return jsonify(seal)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/provenance/autodream', methods=['POST'])
@require_auth
def api_provenance_autodream():
    """v4.3: Idle autoDream consolidation"""
    try:
        import threading as _t
        import sys as _s
        _s.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))
        from autodream import run_autodream
        _t.Thread(target=run_autodream, daemon=True).start()
        return jsonify({'status': 'autodream_initiated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/provenance/prompt', methods=['POST'])
@require_auth
def api_provenance_prompt():
    """Build dynamic task-scoped system prompt."""
    try:
        data = request.json or {}
        task = data.get('task', '')
        intent = data.get('intent', 'TASK')
        tokens = data.get('available_tokens', 8192)
        stack = get_provenance_stack()
        prompt = stack.build_task_scoped_prompt(task, intent=intent, available_tokens=tokens)
        return jsonify({'prompt': prompt})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# â”€â”€ Outbound Context Filtering (v4.0) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _outbound_filter(compiled_context, max_tokens=4000, min_similarity=0.3):
    """Filter and deduplicate context fragments for LLM injection.
    - Dedup by content_hash
    - Filter by similarity threshold
    - Cap total text at max_tokens (rough estimate: 4 chars/token)
    """
    if not compiled_context or not compiled_context.get('fragments'):
        return compiled_context

    seen_hashes = set()
    filtered = []
    total_chars = 0
    char_limit = max_tokens * 4  # rough token estimate

    for f in compiled_context['fragments']:
        if f['content_hash'] in seen_hashes:
            continue
        if f.get('similarity', 0) < min_similarity:
            continue
        text_len = len(f.get('text', ''))
        if total_chars + text_len > char_limit:
            break
        seen_hashes.add(f['content_hash'])
        filtered.append(f)
        total_chars += text_len

    compiled_context['fragments'] = filtered
    compiled_context['fragment_count'] = len(filtered)
    compiled_context['filtered'] = True
    return compiled_context


@app.route('/api/vault/outbound-context', methods=['POST'])
@require_auth
def api_vault_outbound():
    """v4.0: Filtered, conversation-aware context for LLM injection."""
    data = request.json or {}
    query = data.get('query', '')
    if not query:
        return jsonify({'error': 'query required'}), 400
    try:
        stack = get_provenance_stack()
        result = stack.rag_query(query, top_k=8)
        filtered = _outbound_filter(result['compiled_context'])
        return jsonify(filtered)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Tri-Node Locking (Sentinel Cortex Handshake) ─────────────

def _cosine_similarity(v1, v2):
    dot = sum(a*b for a, b in zip(v1, v2))
    norm1 = sum(a*a for a in v1) ** 0.5
    norm2 = sum(b*b for b in v2) ** 0.5
    if norm1 == 0 or norm2 == 0: return 0.0
    return dot / (norm1 * norm2)

def _get_nomic_embedding(text):
    import urllib.request
    payload = json.dumps({'model': 'nomic-embed-text', 'prompt': text}).encode()
    req = urllib.request.Request('http://127.0.0.1:11434/api/embeddings', data=payload, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get('embedding', [])
    except Exception as e:
        log.error(f'Embedding error: {e}')
        return []

@app.route('/api/cortex/intercept', methods=['POST'])
@require_auth
def api_cortex_intercept():
    """Tri-Node Verification: Super-Ego (Ollama Invariants) + Ego (Nomic Baseline Math)"""
    data = request.json or {}
    tool = data.get('tool')
    args = data.get('args', {})
    baseline_prompt = data.get('baseline_prompt', '')
    
    if not tool or not baseline_prompt:
        return jsonify({'approved': False, 'reason': 'CORTEX_REJECTION: Missing tool or baseline prompt payload for Tri-Node verification.'})

    action_text = f"Tool: {tool} | Args: {json.dumps(args)}"

    # 1. Super-Ego Check (Ollama Invariant Verification)
    validation_prompt = f"Does the following action violate any NAEF invariants or system safety bounds? Action: {action_text}. Respond ONLY with 'PASS' or 'VIOLATION: <reason>'."
    try:
        ollama_resp = _ollama_generate([{'role': 'user', 'content': validation_prompt}], max_tokens=100, temperature=0.0)
        cortex_verdict = ollama_resp.get('content', '').strip().upper()
        if 'VIOLATION' in cortex_verdict:
            return jsonify({'approved': False, 'reason': f'CORTEX_REJECTION: Super-Ego blocked action. {cortex_verdict}'})
    except Exception as e:
        log.warning(f"Super-Ego check failed (non-fatal, passing through): {e}")
        # Graceful fallback: Ollama temporarily unavailable — let Ego/Anchor check decide
        cortex_verdict = 'PASS'

    # 2. Ego/Anchor Check (Nomic Semantic Baseline)
    baseline_vector = _get_nomic_embedding(baseline_prompt)
    action_vector = _get_nomic_embedding(action_text)
    
    if not baseline_vector or not action_vector:
        # Embedding unavailable — pass through rather than block
        return jsonify({'approved': True, 'reason': 'Embedding unavailable — pass-through'})
        
    similarity = _cosine_similarity(baseline_vector, action_vector)
    
    # Tunable threshold — lowered to allow diverse tool usage
    # Aligning with VTP drift thresholds
    drift_thresholds = {"SAFE": 0.15, "GATED": 0.25, "RSTR": 0.45}
    # We default the webhook checking to GATED if not provided
    drift_threshold = drift_thresholds.get(data.get('rgm', 'GATED'), 0.25)
    
    if similarity < drift_threshold:
        return jsonify({
            'approved': False, 
            'reason': f'BASELINE_REJECTION: Intent drift detected (Similarity: {similarity:.2f} < Threshold: {drift_threshold}). Action does not geometrically align with user baseline.',
            'similarity': similarity
        })

    # 3. Passed Tri-Node Verification
    return jsonify({'approved': True, 'similarity': similarity})


# ── Modules Registry API ───────────────
@app.route('/api/modules', methods=['GET'])
@require_auth
def api_modules_list():
    """Return the list of all registered Omega modules."""
    mods = []
    for mid, info in MODULE_REGISTRY.items():
        mods.append({
            'id': info['id'],
            'name': info['name'],
            'description': info['description'],
            'status': info['status'],
            'category': info['category']
        })
    return jsonify(mods)

# -- Evolution Queue (Recursive Harness) -----------------

@app.route('/api/evolution/proposals', methods=['GET'])
@require_auth
def api_evolution_proposals():
    """List pending harness patches from the Evolution Engine."""
    target_dir = os.path.join(os.path.dirname(__file__), 'data', 'evolution_proposals')
    if not os.path.exists(target_dir):
        return jsonify([])
    
    proposals = []
    for f in os.listdir(target_dir):
        if f.startswith('manifest_') and f.endswith('.json'):
            try:
                with open(os.path.join(target_dir, f), 'r') as file:
                    data = json.load(file)
                    data['_filename'] = f
                    data['manifest_id'] = f.replace('manifest_', '').replace('.json', '')
                    proposals.append(data)
            except Exception:
                pass
    return jsonify(proposals)

@app.route('/api/evolution/log-failures', methods=['POST'])
@require_auth
def api_evolution_log_failures():
    """Receive agentic failure details and write to audit ledger for Evolution Engine."""
    data = request.json or {}
    failures = data.get('failures', [])
    task_desc = data.get('task', '')
    exit_reason = data.get('exit_reason', '')
    total_steps = data.get('total_steps', 0)
    failed_steps = data.get('failed_steps', 0)

    if not failures:
        return jsonify({'status': 'no_failures'})

    # Write to the VERITAS audit ledger (same format as file assessments)
    # so the Evolution Engine's find_failures() can read them
    try:
        import sys as _s
        _s.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))
        from audit_ledger import AuditLedger
        ledger = AuditLedger()

        # Build gate verdicts from failure details
        gate_verdicts = []
        for f in failures[:10]:  # Cap at 10 to prevent bloat
            gate_verdicts.append({
                'gate': 'AGENTIC_EXECUTION',
                'verdict': 'VIOLATION',
                'tool': f.get('tool', 'unknown'),
                'error': f.get('error', '')[:300],
                'args': f.get('args', '')[:200],
            })

        record = ledger.append(
            filename=f'agentic_run_{data.get("timestamp", "unknown")}',
            file_hash=hashlib.sha256(task_desc.encode()).hexdigest()[:32],
            gate_verdicts=gate_verdicts,
            envelope='VIOLATION',
            risk_score=min(1.0, failed_steps / max(1, total_steps)),
            metadata={
                'type': 'AGENTIC_FAILURE',
                'task': task_desc[:300],
                'exit_reason': exit_reason,
                'total_steps': total_steps,
                'failed_steps': failed_steps,
            }
        )

        log.info(f'[EVOLUTION] Logged agentic failures: {failed_steps}/{total_steps} steps, seal={record.seal_hash[:12]}')
        return jsonify({'status': 'logged', 'seal_hash': record.seal_hash[:16], 'failures_logged': len(gate_verdicts)})
    except Exception as e:
        log.error(f'[EVOLUTION] Failed to log agentic failures: {e}')
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/evolution/scan', methods=['POST'])
@require_auth
def api_evolution_scan():
    """Trigger an evolution engine scan asynchronously."""
    import threading as _t
    data = request.json or {}
    _ledger_append('evolution', 'scan_triggered', {
        'trigger': data.get('trigger', 'manual'),
        'failed_steps': data.get('failed_steps', 0),
        'total_steps': data.get('total_steps', 0),
        'exit_reason': data.get('exit_reason', ''),
    })
    
    def _run_scan():
        try:
            import sys as _s
            _s.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))
            from recursive_evolution_engine import run_evolution_cycle
            run_evolution_cycle()
            log.info('[EVOLUTION] Scan cycle completed.')
        except Exception as e:
            log.error(f'[EVOLUTION] Scan failed: {e}')
    
    t = _t.Thread(target=_run_scan, daemon=True)
    t.start()
    return jsonify({'status': 'scan_initiated', 'trigger': data.get('trigger', 'manual')})

@app.route('/api/evolution/resolve', methods=['POST'])
@require_auth
def api_evolution_resolve():
    """Approve or Reject a pending harness patch."""
    data = request.json or {}
    manifest_id = data.get('id')
    action = data.get('action')
    
    if not manifest_id or not action:
        return jsonify({'error': 'Missing id or action'}), 400

    target_dir = os.path.join(os.path.dirname(__file__), 'data', 'evolution_proposals')
    file_path = os.path.join(target_dir, f"manifest_{manifest_id}.json")
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'Manifest not found'}), 404
        
    if action == 'reject':
        os.remove(file_path)
        _ledger_append('evolution', 'manifest_rejected', {'manifest_id': manifest_id})
        return jsonify({'status': 'rejected'})
        
    if action == 'approve':
        try:
            with open(file_path, 'r') as file:
                manifest = json.load(file)
            _ledger_append('evolution', 'manifest_approved', {'manifest_id': manifest_id})
            os.remove(file_path)
            sentinel = get_sentinel()
            sentinel.create_baseline(force=True)
            return jsonify({'status': 'approved'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# ── Facebook Group Scraper Routes ────────────────────────────────────────────

_fb_jobs = {}  # job_id -> {status, result, error}

def _run_fb_scrape_bg(job_id, group_url, query, limit, download_images):
    """Background thread target for group scraping."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))
    try:
        from omega_facebook_scraper import scrape_group
        _fb_jobs[job_id]['status'] = 'running'
        result = scrape_group(
            group_url=group_url,
            query=query,
            limit=limit,
            download_images=download_images,
        )
        _fb_jobs[job_id].update({'status': 'done', 'result': result})
    except Exception as e:
        _fb_jobs[job_id].update({'status': 'error', 'error': str(e)})

@app.route('/api/facebook/scrape', methods=['POST'])
def api_facebook_scrape():
    """
    POST /api/facebook/scrape
    Body: { group_url, query?, limit?, images? }
    Returns: { job_id } — poll /api/facebook/job/<job_id> for results
    """
    try:
        data = request.json or {}
        group_url = data.get('group_url', '')
        if not group_url:
            return jsonify({'error': 'group_url is required'}), 400

        import uuid, threading
        job_id = str(uuid.uuid4())[:8]
        _fb_jobs[job_id] = {'status': 'queued', 'result': None, 'error': None}

        t = threading.Thread(
            target=_run_fb_scrape_bg,
            args=(
                job_id,
                group_url,
                data.get('query'),
                int(data.get('limit', 100)),
                data.get('images', True),
            ),
            daemon=True,
        )
        t.start()
        return jsonify({'job_id': job_id, 'status': 'queued'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/facebook/job/<job_id>', methods=['GET'])
def api_facebook_job(job_id):
    """Poll a scrape job by job_id."""
    job = _fb_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'job not found'}), 404
    return jsonify(job)

@app.route('/api/facebook/find-groups', methods=['POST'])
def api_facebook_find_groups():
    """
    POST /api/facebook/find-groups
    Body: { query, limit? }
    Returns: { groups: [{name, url}] }
    """
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))
        from omega_facebook_scraper import find_groups
        data = request.json or {}
        keyword = data.get('query', '')
        if not keyword:
            return jsonify({'error': 'query is required'}), 400
        groups = find_groups(keyword=keyword, limit=int(data.get('limit', 20)))
        return jsonify({'groups': groups})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# ═══ VERITAS ANALYZER ENDPOINT ═══
import io, json, re, requests, uuid
from werkzeug.utils import secure_filename
from flask import request, jsonify

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

OLLAMA_URL = "http://127.0.0.1:11434"
MAX_CHARS = 14_000

SYSTEM_PROMPT = """You are the VERITAS structured analysis engine for Gravity Omega.
Analyze the document and return a single JSON report object.

RETURN ONLY RAW JSON. No markdown. No backticks. No explanation. Just the JSON.

Required schema:
{
  "title": "Document title — concise and descriptive",
  "subtitle": "One-line description of document type and purpose",
  "session_id": "0xABCD-TOPIC-AUDIT",
  "mode": "Analysis mode e.g. Investigative Review · Evidence Extraction",
  "sections": [
    {
      "number": "01",
      "title": "UPPERCASE SECTION TITLE",
      "intro": "One sentence framing this section.",
      "items": [
        {
          "label": "Item label",
          "status": "fatal|warning|pass|note|info",
          "content": "Precise analytical content. One to three sentences.",
          "note": null,
          "verdict": null
        }
      ]
    }
  ],
  "feasible_set": [
    {
      "number": "01",
      "title": "Finding or conclusion title",
      "tier": 1,
      "content": "Description of this finding.",
      "subitems": ["Supporting detail one", "Supporting detail two"]
    }
  ],
  "witness": "2-3 sentence analytical summary. Declarative, precise, no hedging on confirmed facts.",
  "trace_id": "Omega-1.0-TOPIC-0x99A"
}

Rules:
- 2 to 5 sections. Each section 1 to 4 items.
- 3 to 7 feasible_set items representing key conclusions.
- tier: 1=confirmed fact or direct evidence, 2=well-supported conclusion, 3=inference or leading hypothesis
- status: fatal=critical issue or failure, warning=concern or risk, pass=verified or confirmed, note=supplementary, info=neutral
- subitems: 2-3 strings per item
- note and verdict: null if not applicable
- Be concise and analytical. Never verbose."""

def extract_text(file_bytes, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in {".txt", ".md", ".csv"}:
        return file_bytes.decode("utf-8", errors="replace")
    if ext == ".json":
        text = file_bytes.decode("utf-8", errors="replace")
        try: return json.dumps(json.loads(text), indent=2)
        except Exception as e: return text
    if ext == ".docx":
        if not DOCX_AVAILABLE: raise RuntimeError("python-docx not installed.")
        doc = DocxDocument(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    if ext == ".pdf":
        if not PDF_AVAILABLE: raise RuntimeError("pdfplumber not installed.")
        text_parts = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages[:40]:
                t = page.extract_text()
                if t: text_parts.append(t)
        return "\n".join(text_parts)
    raise ValueError(f"Unsupported file type: {ext}")

def call_ollama(text, model):
    truncated = text if len(text) <= MAX_CHARS else text[:MAX_CHARS] + "\n\n[Content truncated]"
    payload = {
        "model": model, "stream": False, "format": "json",
        "options": {"temperature": 0.15, "num_predict": 3500},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this document and return the JSON report:\n\n{truncated}"}
        ]
    }
    resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=180)
    resp.raise_for_status()
    raw = resp.json().get("message", {}).get("content", "")
    clean = re.sub(r"^```json\s*", "", raw.strip())
    clean = re.sub(r"```\s*$", "", clean).strip()
    return json.loads(clean)

@app.route("/api/analyze_document", methods=["POST"])
def analyze_document():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
    
    f = request.files["file"]
    model = request.form.get("model", "qwen3:8b").strip()
    filename = secure_filename(f.filename or "upload.txt")
    
    try:
        file_bytes = f.read()
        raw_text = extract_text(file_bytes, filename)
    except Exception as e:
        return jsonify({"error": f"Extraction failed: {str(e)}"}), 422
    
    try:
        report_data = call_ollama(raw_text, model)
        report_data["_meta"] = {"source_file": filename, "model": model, "trace": f"Omega-1.0-{str(uuid.uuid4())[:8].upper()}"}
        return jsonify(report_data)
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

if __name__ == '__main__':
    log.info(f'=== GRAVITY OMEGA BACKEND v3.0 ===')
    log.info(f'Port: {PORT} | PID: {os.getpid()} | Parent: {PARENT_PID or "none"}')

    # Initialize databases
    _vault_init()
    _ledger_init()

    # Register all modules
    _register_all_modules()

    # Start parent heartbeat
    if PARENT_PID:
        t = threading.Thread(target=_parent_heartbeat, daemon=True)
        t.start()

    # ── GOLIATH HUNTER (standalone OSINT module — no changes to Omega internals) ──
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))
        from goliath_hunter.omega_conductor import register_routes as _hunter_routes
        _hunter_routes(app)
        print("[HUNTER] GOLIATH HUNTER routes registered (/api/hunter/*)")
    except Exception as _he:
        print(f"[HUNTER] Optional module not loaded: {_he}")

    # Start Flask
    app.run(host='127.0.0.1', port=PORT, debug=False, threaded=True)
