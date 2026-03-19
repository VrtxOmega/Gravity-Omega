#!/usr/bin/env python3
"""
Omega Sentinel — Self-Awareness & Auto-Heal Daemon
═══════════════════════════════════════════════════
Baselines Omega's core files, watches for changes,
and auto-reverts if things break. Runs as background
thread inside the Flask backend.

Features:
  1. BASELINE: Hash + copy all critical files on first run
  2. WATCH: Every 30s, detect file changes
  3. AWARENESS: Log changes so Omega knows what shifted
  4. AUTO-HEAL: If health check fails, revert broken files from baseline
"""

import hashlib
import json
import logging
import os
import shutil
import threading
import time
from pathlib import Path

log = logging.getLogger('omega.sentinel')

# ── Config ──────────────────────────────────────────────────
SENTINEL_DIR = Path.home() / '.omega_sentinel'
BASELINE_DIR = SENTINEL_DIR / 'baseline'
STATE_FILE = SENTINEL_DIR / 'state.json'
CHANGELOG = SENTINEL_DIR / 'changelog.jsonl'
CHECK_INTERVAL = 30  # seconds

# Critical files to watch (relative to project root)
WATCHED_FILES = [
    'backend/web_server.py',
    'backend/provenance_stack.py',
    'backend/omega_sentinel.py',
    # v3.0: Updated to surviving module files
    'backend/modules/hybrid_coordinator.py',
    'backend/modules/veritas_neural_core.py',
    'backend/modules/benchmark_harness.py',
    'backend/modules/risk_calibrator.py',
    'backend/modules/titan_monitor.py',
    'backend/modules/omega_test_harness.py',
]

# These are on the Windows side -- watch via /mnt/c paths
WATCHED_ELECTRON_FILES = [
    '/mnt/c/Veritas_Lab/gravity-omega-v2/main.js',
    '/mnt/c/Veritas_Lab/gravity-omega-v2/preload.js',
    '/mnt/c/Veritas_Lab/gravity-omega-v2/renderer/app.js',
    '/mnt/c/Veritas_Lab/gravity-omega-v2/renderer/index.html',
    '/mnt/c/Veritas_Lab/gravity-omega-v2/renderer/styles/omega.css',
    '/mnt/c/Veritas_Lab/gravity-omega-v2/omega/omega_bridge.js',
]

# Health check URL
HEALTH_URL = 'http://127.0.0.1:5000/api/status'


class OmegaSentinel:
    """Self-awareness daemon for Omega."""

    def __init__(self, project_root='/home/veritas/gravity-omega-v2'):
        self.project_root = Path(project_root)
        self.running = False
        self.thread = None
        self.state = {
            'baseline_created': None,
            'last_check': None,
            'changes_detected': 0,
            'heals_performed': 0,
            'file_hashes': {},
            'change_log': [],
        }
        self.pending_alerts = []
        self._ensure_dirs()
        self._load_state()

    def _ensure_dirs(self):
        SENTINEL_DIR.mkdir(parents=True, exist_ok=True)
        BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    def _load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE) as f:
                    self.state = json.load(f)
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            log.warning(f'Sentinel state save failed: {e}')

    def _hash_file(self, path):
        """SHA-256 hash of file content."""
        try:
            with open(path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None

    def _all_watched_paths(self):
        """Return list of (key, absolute_path) tuples."""
        paths = []
        for rel in WATCHED_FILES:
            abs_path = self.project_root / rel
            paths.append((rel, str(abs_path)))
        for abs_path in WATCHED_ELECTRON_FILES:
            key = abs_path.split('gravity-omega-v2/')[-1] if 'gravity-omega-v2/' in abs_path else abs_path
            paths.append((key, abs_path))
        return paths

    # ── BASELINE ────────────────────────────────────────────
    def create_baseline(self, force=False):
        """Snapshot all critical files: hash + backup copy."""
        if self.state.get('baseline_created') and not force:
            log.info('Sentinel: baseline already exists, skipping (use force=True to re-baseline)')
            return

        log.info('Sentinel: creating baseline snapshot...')
        hashes = {}
        for key, path in self._all_watched_paths():
            h = self._hash_file(path)
            if h:
                hashes[key] = h
                # Copy to baseline dir
                safe_name = key.replace('/', '__').replace('\\', '__')
                try:
                    shutil.copy2(path, BASELINE_DIR / safe_name)
                except Exception as e:
                    log.warning(f'Sentinel: could not backup {key}: {e}')
            else:
                log.warning(f'Sentinel: file not found: {path}')

        self.state['file_hashes'] = hashes
        self.state['baseline_created'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        self.state['changes_detected'] = 0
        self.state['heals_performed'] = 0
        self.state['change_log'] = []
        self._save_state()
        log.info(f'Sentinel: baseline created — {len(hashes)} files tracked')

    # ── WATCH ───────────────────────────────────────────────
    def check_changes(self):
        """Compare current file hashes against baseline."""
        changes = []
        for key, path in self._all_watched_paths():
            baseline_hash = self.state.get('file_hashes', {}).get(key)
            current_hash = self._hash_file(path)

            if current_hash is None:
                if baseline_hash:
                    changes.append({
                        'file': key, 'type': 'DELETED',
                        'time': time.strftime('%Y-%m-%dT%H:%M:%S'),
                    })
            elif baseline_hash is None:
                changes.append({
                    'file': key, 'type': 'NEW',
                    'time': time.strftime('%Y-%m-%dT%H:%M:%S'),
                })
            elif current_hash != baseline_hash:
                changes.append({
                    'file': key, 'type': 'MODIFIED',
                    'time': time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'baseline_hash': baseline_hash[:12],
                    'current_hash': current_hash[:12],
                })

        if changes:
            self.state['changes_detected'] += len(changes)
            self.state['change_log'] = (self.state.get('change_log', []) + changes)[-50:]  # Keep last 50
            self._save_state()
            self._append_changelog(changes)
            log.info(f'Sentinel: {len(changes)} change(s) detected')

        self.state['last_check'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        return changes

    def _append_changelog(self, changes):
        """Append changes to the JSONL changelog."""
        try:
            with open(CHANGELOG, 'a') as f:
                for c in changes:
                    f.write(json.dumps(c) + '\n')
        except Exception:
            pass

    # ── AUTO-HEAL ───────────────────────────────────────────
    def health_check(self):
        """Check if backend is responding."""
        try:
            import urllib.request
            req = urllib.request.Request(HEALTH_URL, headers={'X-Omega-Auth': 'sentinel'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                return data.get('status') == 'online'
        except Exception:
            return False

    def heal(self, broken_files=None):
        """Revert broken files from baseline."""
        if broken_files is None:
            # Revert ALL changed files
            changes = self.check_changes()
            broken_files = [c['file'] for c in changes if c['type'] in ('MODIFIED', 'DELETED')]

        healed = []
        for key in broken_files:
            safe_name = key.replace('/', '__').replace('\\', '__')
            baseline_path = BASELINE_DIR / safe_name

            if not baseline_path.exists():
                log.warning(f'Sentinel: no baseline for {key}, cannot heal')
                continue

            # Find the actual path
            target = None
            for k, p in self._all_watched_paths():
                if k == key:
                    target = p
                    break

            if target:
                try:
                    shutil.copy2(str(baseline_path), target)
                    healed.append(key)
                    log.info(f'Sentinel: HEALED {key}')
                except Exception as e:
                    log.error(f'Sentinel: heal failed for {key}: {e}')

        if healed:
            self.state['heals_performed'] += len(healed)
            self.state['change_log'].append({
                'type': 'HEAL', 'files': healed,
                'time': time.strftime('%Y-%m-%dT%H:%M:%S'),
            })
            self._save_state()
            self.pending_alerts.append({
                'severity': 'critical',
                'message': f'Auto-healed {len(healed)} file(s): {", ".join(healed)}'
            })

        return healed

    # ── ACCEPT CHANGES (update baseline) ────────────────────
    def accept_changes(self):
        """Accept current state as new baseline (after upgrade)."""
        self.create_baseline(force=True)
        log.info('Sentinel: changes accepted — new baseline created')
        return True

    # ── STATUS ──────────────────────────────────────────────
    def get_status(self):
        """Return current sentinel status for Omega's awareness."""
        changes = self.check_changes()
        return {
            'baseline_created': self.state.get('baseline_created'),
            'last_check': self.state.get('last_check'),
            'files_tracked': len(self.state.get('file_hashes', {})),
            'changes_detected': self.state.get('changes_detected', 0),
            'heals_performed': self.state.get('heals_performed', 0),
            'current_changes': changes,
            'recent_log': self.state.get('change_log', [])[-10:],
            'running': self.running,
        }

    def get_alerts(self):
        """Consume and return pending alerts for the frontend."""
        alerts = list(self.pending_alerts)
        self.pending_alerts.clear()
        return alerts

    # ── DAEMON LOOP ─────────────────────────────────────────
    def _daemon_loop(self):
        """Background loop: check changes + auto-heal if broken."""
        log.info('Sentinel daemon started')
        while self.running:
            try:
                changes = self.check_changes()

                if changes:
                    # Check if backend is still healthy
                    healthy = self.health_check()
                    if not healthy:
                        log.warning('Sentinel: backend unhealthy after changes — auto-healing...')
                        healed = self.heal()
                        if healed:
                            log.info(f'Sentinel: auto-healed {len(healed)} files, backend should recover')
                    else:
                        # Changes detected but system healthy — log awareness
                        for c in changes:
                            log.info(f'Sentinel: [{c["type"]}] {c["file"]} — system healthy, accepting')

            except Exception as e:
                log.error(f'Sentinel daemon error: {e}')

            # Sleep in small chunks so we can stop quickly
            for _ in range(CHECK_INTERVAL):
                if not self.running:
                    break
                time.sleep(1)

        log.info('Sentinel daemon stopped')

    def start(self):
        """Start the sentinel daemon."""
        if self.running:
            return
        # Create baseline if first run
        if not self.state.get('baseline_created'):
            self.create_baseline()
        self.running = True
        self.thread = threading.Thread(target=self._daemon_loop, daemon=True, name='OmegaSentinel')
        self.thread.start()

    def stop(self):
        """Stop the sentinel daemon."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)


# Singleton
_sentinel = None

def get_sentinel(project_root='/home/veritas/gravity-omega-v2'):
    global _sentinel
    if _sentinel is None:
        _sentinel = OmegaSentinel(project_root)
    return _sentinel
