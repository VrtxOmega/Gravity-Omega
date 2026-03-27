#!/usr/bin/env python3
"""
Omega Sentinel v2 — Smart Self-Awareness & Auto-Heal Daemon
═══════════════════════════════════════════════════════════════
Git-aware, intelligently classified change detection.

v2 Upgrades:
  1. GIT-AWARE: Auto-accept changes committed to git HEAD
  2. 3-TIER CLASSIFICATION: COMMITTED / HEALTHY_UNCOMMITTED / CORRUPTION
  3. STARTUP GRACE: 60s cooldown before first check
  4. ATOMIC STATE: temp-file + rename for crash-safe state writes
  5. SEVERITY ALERTS: critical (heal), info (accept), silent (committed)
"""

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

log = logging.getLogger('omega.sentinel')

# ── Config ──────────────────────────────────────────────────
SENTINEL_DIR = Path.home() / '.omega_sentinel'
BASELINE_DIR = SENTINEL_DIR / 'baseline'
STATE_FILE = SENTINEL_DIR / 'state.json'
CHANGELOG = SENTINEL_DIR / 'changelog.jsonl'
CHECK_INTERVAL = 30       # seconds between checks
STARTUP_GRACE_S = 60      # seconds to wait after start before first check
HEALTH_RETRIES = 2        # retry health check before declaring unhealthy
HEALTH_RETRY_DELAY = 3    # seconds between health check retries

# ── KILL SWITCH — set to False to re-enable Sentinel ──
SENTINEL_DISABLED = True

# Critical files to watch (relative to project root)
WATCHED_FILES = [
    'backend/web_server.py',
    'backend/provenance_stack.py',
    'backend/omega_sentinel.py',
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

# ── Change Classification ────────────────────────────────────
COMMITTED = 'COMMITTED'                   # in git HEAD → silent auto-accept
HEALTHY_UNCOMMITTED = 'HEALTHY_UNCOMMITTED'  # not in git, system healthy → info alert, no heal
CORRUPTION = 'CORRUPTION'                 # not in git, system broken → auto-heal + critical alert


class OmegaSentinel:
    """Smart self-awareness daemon for Omega (v2)."""

    def __init__(self, project_root='/home/veritas/gravity-omega-v2'):
        self.project_root = Path(project_root)
        self.running = False
        self.thread = None
        self.state = {
            'baseline_created': None,
            'last_check': None,
            'changes_detected': 0,
            'heals_performed': 0,
            'auto_accepts': 0,
            'file_hashes': {},
            'change_log': [],
        }
        self.pending_alerts = []
        self.paused = False
        self._start_time = None
        self._git_available = self._check_git()
        self._ensure_dirs()
        self._load_state()

    def _check_git(self):
        """Check if git is available and we're in a repo."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--is-inside-work-tree'],
                cwd=str(self.project_root),
                capture_output=True, timeout=5, text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

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
        """Atomic state write — temp file + rename to prevent corruption."""
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(SENTINEL_DIR), suffix='.tmp', prefix='state_'
            )
            with os.fdopen(fd, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
            os.replace(tmp_path, str(STATE_FILE))
        except Exception as e:
            log.warning(f'Sentinel state save failed: {e}')
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

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

    # ── GIT AWARENESS ──────────────────────────────────────────
    def _is_git_committed(self, path):
        """Check if file's current content matches git HEAD.
        Returns True if file is clean (matches HEAD), False if dirty/uncommitted."""
        if not self._git_available:
            return False
        try:
            # For electron files on /mnt/c, use the Windows project root
            git_cwd = '/mnt/c/Veritas_Lab/gravity-omega-v2'
            if not path.startswith('/mnt/c'):
                git_cwd = str(self.project_root)

            result = subprocess.run(
                ['git', 'diff', '--quiet', 'HEAD', '--', path],
                cwd=git_cwd, capture_output=True, timeout=5,
            )
            # returncode 0 = no diff from HEAD = file is committed/clean
            return result.returncode == 0
        except Exception:
            return False

    def _classify_change(self, key, path, healthy):
        """Classify a detected change into one of three tiers."""
        if self._is_git_committed(path):
            return COMMITTED
        elif healthy:
            return HEALTHY_UNCOMMITTED
        else:
            return CORRUPTION

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
        self.state['auto_accepts'] = 0
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
                    'file': key, 'path': path, 'type': 'MODIFIED',
                    'time': time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'baseline_hash': baseline_hash[:12],
                    'current_hash': current_hash[:12],
                })

        if changes:
            self.state['changes_detected'] += len(changes)
            self.state['change_log'] = (self.state.get('change_log', []) + changes)[-50:]
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
                    # Don't persist 'path' to changelog (it's an internal field)
                    entry = {k: v for k, v in c.items() if k != 'path'}
                    f.write(json.dumps(entry) + '\n')
        except Exception:
            pass

    # ── HEALTH CHECK ───────────────────────────────────────
    def health_check(self):
        """Check if backend is responding with READY status.
        Retries to avoid false negatives from transient network issues."""
        import urllib.request
        for attempt in range(HEALTH_RETRIES):
            try:
                req = urllib.request.Request(HEALTH_URL, headers={'X-Omega-Auth': 'sentinel'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                    status = data.get('status', '')
                    # Accept both 'online' and 'READY'
                    if status in ('online', 'READY'):
                        return True
            except Exception:
                pass
            if attempt < HEALTH_RETRIES - 1:
                time.sleep(HEALTH_RETRY_DELAY)
        return False

    # ── AUTO-HEAL ───────────────────────────────────────────
    def heal(self, broken_files=None):
        """Revert broken files from baseline."""
        if broken_files is None:
            changes = self.check_changes()
            broken_files = [c['file'] for c in changes if c['type'] in ('MODIFIED', 'DELETED')]

        healed = []
        for key in broken_files:
            safe_name = key.replace('/', '__').replace('\\', '__')
            baseline_path = BASELINE_DIR / safe_name

            if not baseline_path.exists():
                log.warning(f'Sentinel: no baseline for {key}, cannot heal')
                continue

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
    def accept_changes(self, silent=False):
        """Accept current state as new baseline."""
        self.create_baseline(force=True)
        self.state['auto_accepts'] = self.state.get('auto_accepts', 0) + 1
        self._save_state()
        if not silent:
            log.info('Sentinel: changes accepted — new baseline created')
        return True

    # ── STATUS ──────────────────────────────────────────────
    def get_status(self):
        """Return current sentinel status for Omega's awareness."""
        changes = self.check_changes()
        return {
            'version': 2,
            'baseline_created': self.state.get('baseline_created'),
            'last_check': self.state.get('last_check'),
            'files_tracked': len(self.state.get('file_hashes', {})),
            'changes_detected': self.state.get('changes_detected', 0),
            'heals_performed': self.state.get('heals_performed', 0),
            'auto_accepts': self.state.get('auto_accepts', 0),
            'current_changes': changes,
            'recent_log': self.state.get('change_log', [])[-10:],
            'running': self.running,
            'git_available': self._git_available,
        }

    def get_alerts(self):
        """Consume and return pending alerts for the frontend."""
        alerts = list(self.pending_alerts)
        self.pending_alerts.clear()
        return alerts

    def pause(self):
        """Pause the sentinel — stops checking and healing."""
        self.paused = True
        log.info('Sentinel: PAUSED — auto-heal disabled')
        return True

    def resume(self):
        """Resume the sentinel — re-enables checking and healing."""
        self.paused = False
        log.info('Sentinel: RESUMED — auto-heal re-enabled')
        return True

    # ── DAEMON LOOP (v2 — Smart Classification) ──────────────
    def _daemon_loop(self):
        """Background loop with git-aware change classification."""
        log.info(f'Sentinel v2 daemon started (git={self._git_available})')
        self._start_time = time.time()

        # Startup grace period — let the backend fully initialize
        log.info(f'Sentinel: grace period ({STARTUP_GRACE_S}s)...')
        grace_remaining = STARTUP_GRACE_S
        while grace_remaining > 0 and self.running:
            time.sleep(min(5, grace_remaining))
            grace_remaining -= 5
        if not self.running:
            return
        log.info('Sentinel: grace period complete, monitoring active')

        while self.running:
            try:
                if self.paused:
                    pass  # skip all checks while paused
                else:
                    changes = self.check_changes()

                    if changes:
                        # Classify each change
                        healthy = self.health_check()
                        committed = []
                        uncommitted_healthy = []
                        corruption = []

                        for c in changes:
                            path = c.get('path', '')
                            if not path:
                                # Resolve path from key
                                for k, p in self._all_watched_paths():
                                    if k == c['file']:
                                        path = p
                                        break

                            tier = self._classify_change(c['file'], path, healthy)
                            c['classification'] = tier

                            if tier == COMMITTED:
                                committed.append(c)
                            elif tier == HEALTHY_UNCOMMITTED:
                                uncommitted_healthy.append(c)
                            else:
                                corruption.append(c)

                        # ── COMMITTED: Silent auto-accept ──
                        if committed and not uncommitted_healthy and not corruption:
                            for c in committed:
                                log.info(f'Sentinel: [{c["type"]}] {c["file"]} — git-committed, auto-accepting')
                            self.accept_changes(silent=True)

                        # ── HEALTHY_UNCOMMITTED: Info alert, accept new baseline ──
                        elif uncommitted_healthy and not corruption:
                            files = [c['file'] for c in uncommitted_healthy]
                            for c in uncommitted_healthy:
                                log.info(f'Sentinel: [{c["type"]}] {c["file"]} — uncommitted but healthy')
                            # Accept since system is healthy
                            self.accept_changes(silent=True)
                            self.pending_alerts.append({
                                'severity': 'info',
                                'message': f'Detected changes in {len(files)} file(s) — system healthy, accepted: {", ".join(files)}'
                            })

                        # ── CORRUPTION: Auto-heal + critical alert ──
                        elif corruption:
                            corrupt_files = [c['file'] for c in corruption]
                            log.warning(f'Sentinel: {len(corrupt_files)} file(s) corrupted — auto-healing')
                            healed = self.heal(broken_files=corrupt_files)
                            if healed:
                                log.info(f'Sentinel: healed {len(healed)} corrupted files')
                            # Also accept any committed changes that came with it
                            if committed:
                                self.accept_changes(silent=True)

            except Exception as e:
                log.error(f'Sentinel daemon error: {e}')

            # Sleep in small chunks so we can stop quickly
            for _ in range(CHECK_INTERVAL):
                if not self.running:
                    break
                time.sleep(1)

        log.info('Sentinel v2 daemon stopped')

    def start(self):
        """Start the sentinel daemon."""
        if SENTINEL_DISABLED:
            log.info('Sentinel v2 DISABLED by SENTINEL_DISABLED flag — not starting')
            return
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
