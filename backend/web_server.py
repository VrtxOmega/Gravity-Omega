
# ── Advanced Modules ──
def register_advanced_modules():
    register_module('cerberus', 'Cerberus Engine', 'Email/Tuning Engine with high assurance execution bounds.', 'ACTIVE', 'advanced', handler=__import__('modules.cerberus', fromlist=['run_handler']).run_handler)
    register_module('chain_sniper', 'Chain Sniper', 'DeFi Chain Analysis and State-Desynchronization discovery.', 'ACTIVE', 'advanced', handler=__import__('modules.chain_sniper', fromlist=['run_handler']).run_handler)
    register_module('exploit_monitor', 'Exploit Monitor', 'Vulnerability Exploit Tracker with live mempool integration.', 'ACTIVE', 'advanced', handler=__import__('modules.exploit_monitor', fromlist=['run_handler']).run_handler)
    register_module('hydra', 'Hydra Scanner v3.0', 'AST-based multi-language security scanner (Omniscient Evolution).', 'ACTIVE', 'advanced', handler=__import__('modules.hydra', fromlist=['run_handler']).run_handler)
    register_module('omega_claw', 'Omega Claw', 'Autonomous Extraction Loop Engine for Cloud Run execution.', 'ACTIVE', 'advanced', handler=__import__('modules.omega_claw', fromlist=['run_handler']).run_handler)
    register_module('titan_engine', 'Titan Compute Engine', 'Distributed orchestration and computational bounds enforcement.', 'ACTIVE', 'advanced', handler=__import__('modules.titan_engine', fromlist=['run_handler']).run_handler)


"""
GRAVITY OMEGA v2.0 — Python Backend (web_server.py)

Flask-based backend running on port 5000. Provides:
  - 27 module registry with execute/describe endpoints
  - AI routing (Vertex AI → OpenAI → Ollama fallback)
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
import time
import hashlib
import threading
import subprocess
import platform
import sqlite3
import logging
from pathlib import Path
from omega_sentinel import get_sentinel

# Provenance Stack (Module 20)
from provenance_stack import get_stack as get_provenance_stack
from datetime import datetime, timezone
from functools import wraps

# ── HIGH ASSURANCE SHIELD MODULES ──
from omega_ssrf_shield import SSRFShield
from omega_process_identity import BinaryIdentityCache
from omega_ancestor_verify import AncestorVerification
from omega_bypass_trap import BypassTrap

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

# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════

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

# ══════════════════════════════════════════════════════════════
# FLASK APP
# ══════════════════════════════════════════════════════════════

app = Flask(__name__)


def require_auth(f):
    """Verify X-Omega-Token header matches the handshake token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if AUTH_TOKEN and request.headers.get('X-Omega-Token') != AUTH_TOKEN:
            abort(401, 'Invalid auth token')
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════
# MODULE REGISTRY — 27 Modules
# ══════════════════════════════════════════════════════════════

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


# ── Module Handlers ───────────────────────────────────────────

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
        out = subprocess.check_output(cmd.split(), cwd=cwd, stderr=subprocess.STDOUT,
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
    """Module 10: NemesisV3 — Advanced counter-intrusion."""
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
    """Module 21: Hydra v3.0 security scanner integration."""
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


# ── Register All 27 Modules ──────────────────────────────────

def _register_all_modules():
    """Register all 23 VERITAS modules (20 MCP + Hydra + Pipeline + Strike Array)."""
    modules = [
        # -- MCP Omega Command Center Modules (20) --
        ('aegis_ald', 'AEGIS-ALD Gate Pipeline', 'FastAPI server - ingests trace logs, runs 6 ALD observation gates, generates sealed PDF audit reports.', 'security'),
        ('goliath_leviathan', 'Goliath Leviathan - Forensic Scanner', 'Deep forensic disclosure scanner - secret detection, metadata harvesting, temporal probing, shadow mapping, financial kill-chain detection.', 'security'),
        ('sentinel_omega', 'Sentinel Omega - Cybersecurity Suite', 'Admin-elevated security command center: Tor-routed API gate, XOR obfuscation forge (VeritasForge), Gravity Shield egress filtering.', 'security'),
        ('sentinel_shield', 'Sentinel Shield - Defensive Monitor', 'Process-level defense suite: ESM scoring, Logic Flow Divergence detection, honeytoken tripwire, port sentry, CWE-338 scanner.', 'security'),
        ('chronos', 'Chronos - DeFi Hydration Engine', '10-worker parallel DeFi hydration engine - RPC rotation, WebSocket price streams, PostgreSQL persistence.', 'defi'),
        ('kinetic_siphon', 'Kinetic Siphon - Egress Monitor', 'Passive egress monitor - binds TCP port 445, detects unauthorized connections, generates HTML compliance triggers.', 'security'),
        ('sovereign_v42', 'Sovereign v4.2 - Physics Compiler', 'Constraint-locked epistemic compiler - dimensional analysis gates, Bernoulli/Hooke enforcement, equation parity.', 'compiler'),
        ('reality_compiler', 'Reality Compiler - VERITAS Gates', 'Schema validation, constraint compilation, gate-by-gate report generation following VERITAS Omega canonical gate order.', 'compiler'),
        ('atc_engine', 'ATC Falsification Engine', 'Flight data ingestion, separation probe with 2D CPA calculations, NIC isolation, deterministic vertical prediction.', 'analysis'),
        ('project_sv', 'Project SV - Compression Engine', 'Custom codec formats (.god/.sntl/.v6) with C implementations, Python benchmark harness, restoration pipeline.', 'tools'),
        ('pipeline_router', 'Detonation Pipeline', 'Isolation -> high-stress audit -> verification -> atomic promotion pipeline with RSS monitoring and SHA-256 integrity.', 'operations'),
        ('thermal_shield', 'Thermal Shield Forge', 'NAEF-compliant validation engine, hostile audit mode, thermal survivor testing with full reason-code registry.', 'security'),
        ('ledger_bot', 'VERITAS Ledger Bot', 'Deterministic research archiver - multi-root file ingest, SHA-256 hashing, classification, policy DNA enforcement.', 'operations'),
        ('easystreet', 'EasyStreet - AEGIS Audits (LIVE)', 'Fully autonomous smart contract security audit platform on Google Cloud Run. LIVE at aegisaudits.com.', 'easystreet'),
        ('aegis_w1', 'AEGIS ALD W1 - Gate Pipeline', 'Full VERITAS Omega gate pipeline - veritas_api + veritas_omega packages, golden verdict suite, sealed audit packets.', 'security'),
        ('receipt_inspector', 'Decision Receipt Inspector', 'Frozen stasis verifier - validates decision receipt bundles for structural integrity, hash verification, seal chain.', 'analysis'),
        ('alpha_scanner', 'Alpha Predator - God Scanner', '55KB deep reconnaissance scanner - multi-threaded target analysis, SQLite persistence, risk scoring, pattern detection.', 'security'),
        ('veritas_fuzzer', 'Veritas Fuzzer', 'Input fuzzing engine - generates adversarial payloads, boundary condition tests, malformed input sequences.', 'security'),
        ('containment_layer', 'Containment Layer - Packet Filter', 'VERITAS network containment - Kotlin PacketFilter with leaky bucket rate limiting, monotonic time decay.', 'security'),
        ('provenance_stack', 'Provenance Stack - Context Compiler', 'Module 20. Deterministic context compilation with proof-carrying retrieval, Archivist Node, Epistemic Engine, S.E.A.L.', 'intelligence'),
        # -- Additional VERITAS Modules (3) --
        ('hydra_scanner', 'Hydra Scanner v3.0', 'Hydra v3.0 Omniscient Evolution - 20-module AST-based security scanner with Neural Core, Halmos Handshake, Live-State Anchor.', 'security'),
        ('veritas_pipeline', 'VERITAS Extraction Pipeline', 'End-to-end extraction-to-conversion pipeline - Omni-Hunter loop, clone-scan-weaponize, State-Desync Kill Chain.', 'security'),
        ('omega_strike_array', 'Omega Strike Array - Bug Bounty Engine', 'Unified bug bounty hunting engine consolidating Cerberus, Goliath, Hydra v3, Slither, and Foundry into a single scanner.', 'security'),
    ]
    for mid, name, desc, cat in modules:
        register_module(mid, name, desc, category=cat)
    register_advanced_modules()
    log.info(f'Registered {len(MODULE_REGISTRY)} modules')

    # Start Omega Sentinel (self-awareness daemon)
    try:
        sentinel = get_sentinel()
        sentinel.start()
        log.info('Omega Sentinel daemon started')
    except Exception as e:
        log.warning(f'Sentinel start failed (non-fatal): {e}')


# ══════════════════════════════════════════════════════════════
# VAULT (SQLite + FTS5 + Mnemo-Cortex)
# ══════════════════════════════════════════════════════════════

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
    """Intelligence sweep — re-summarize, enrich KIs, auto-link."""
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


# ══════════════════════════════════════════════════════════════
# LEDGER (Immutable Artifact Records)
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# AI ROUTING (Vertex → OpenAI → Ollama)
# ══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════
# OMEGA PERSONA (Base System Prompt)
# ══════════════════════════════════════════════════════════════

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
    "- Hydra v3.0: 20-module AST security scanner\n"
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
        'model': 'qwen2.5:7b',
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
            'model': 'qwen2.5:7b', 'backend': 'ollama'}


# ══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════
# TEXT-TO-SPEECH (ElevenLabs)
# ══════════════════════════════════════════════════════════════

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
@require_auth
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
                'name': 'en-AU-Neural2-C'  # Female Australian
            },
            'audioConfig': {
                'audioEncoding': 'MP3',
                'speakingRate': 1.05,
                'pitch': -2.00
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
# ══════════════════════════════════════════════════════════════

# ── Sentinel (Self-Awareness) Routes ──────────────────────
@app.route('/api/sentinel/status', methods=['GET'])
@require_auth
def api_sentinel_status():
    sentinel = get_sentinel()
    return jsonify(sentinel.get_status())

@app.route('/api/sentinel/baseline', methods=['POST'])
@require_auth
def api_sentinel_baseline():
    sentinel = get_sentinel()
    sentinel.create_baseline(force=True)
    return jsonify({'status': 'baseline_created', 'files': len(sentinel.state.get('file_hashes', {}))})

@app.route('/api/sentinel/heal', methods=['POST'])
@require_auth
def api_sentinel_heal():
    sentinel = get_sentinel()
    healed = sentinel.heal()
    return jsonify({'healed': healed, 'count': len(healed)})

@app.route('/api/sentinel/alerts', methods=['GET'])
@require_auth
def api_sentinel_alerts():
    sentinel = get_sentinel()
    alerts = sentinel.get_alerts()
    return jsonify({'alerts': alerts, 'count': len(alerts)})

@app.route('/api/sentinel/accept', methods=['POST'])
@require_auth
def api_sentinel_accept():
    sentinel = get_sentinel()
    sentinel.accept_changes()
    return jsonify({'status': 'changes_accepted'})


@app.route('/api/status', methods=['GET'])
@require_auth
def api_status():
    return jsonify({
        'status': 'READY',
        'port': PORT,
        'pid': os.getpid(),
        'modules': len(MODULE_REGISTRY),
        'uptime_s': round(time.time() - _start_time, 1),
        'platform': platform.platform(),
        'python': sys.version.split()[0],
    })


@app.route('/api/modules', methods=['GET'])
@require_auth
def api_modules():
    return jsonify([
        {k: v for k, v in mod.items() if k != 'handler'}
        for mod in MODULE_REGISTRY.values()
    ])


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
    mod = MODULE_REGISTRY.get(module_id)
    if not mod:
        return jsonify({'error': f'Module not found: {module_id}'}), 404
    return jsonify({k: v for k, v in mod.items() if k != 'handler'})


# ── Agent Thinking ────────────────────────────────────────────

@app.route('/api/agent/think', methods=['POST'])
@require_auth
def api_agent_think():
    # ── HIGH ASSURANCE VERITAS ENFORCEMENT ──
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


# ── Search ────────────────────────────────────────────────────

@app.route('/api/search/text', methods=['POST'])
@require_auth
def api_search_text():
    data = request.json or {}
    directory = data.get('directory', '.')
    query = data.get('query', '')
    return jsonify(_handle_code_search(directory=directory, query=query))


# ── Hardware ──────────────────────────────────────────────────

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


# ── Vault Routes ──────────────────────────────────────────────

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


# ── Security Routes ───────────────────────────────────────────

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


# ── Reports Routes ────────────────────────────────────────────

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


# ── Tools Routes ──────────────────────────────────────────────

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


# ── Ledger Routes ─────────────────────────────────────────────

@app.route('/api/ledger/stats', methods=['GET'])
@require_auth
def api_ledger_stats():
    return jsonify(_ledger_stats())


@app.route('/api/ledger/search', methods=['POST'])
@require_auth
def api_ledger_search():
    data = request.json or {}
    return jsonify(_ledger_search(data.get('query', '')))


# ══════════════════════════════════════════════════════════════
# PARENT PID HEARTBEAT
# ══════════════════════════════════════════════════════════════

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
            log.warning('Parent process died — shutting down')
            os._exit(0)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

_start_time = time.time()


# ── Provenance Stack API ─────────────────────────────────────

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


if __name__ == '__main__':
    log.info(f'=== GRAVITY OMEGA BACKEND v2.0 ===')
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

    # Start Flask
    app.run(host='127.0.0.1', port=PORT, debug=False, threaded=True)
