"""
Full Sentinel Protocol: Pause → Apply CSS/HTML → Update Baseline Backups → Update Hashes → Resume
Run from WSL: python3 /mnt/c/Veritas_Lab/gravity-omega-v2/sentinel_full_protocol.py
"""
import json
import hashlib
import shutil
import sys
from pathlib import Path

SENTINEL_DIR = Path('/mnt/c/Users/rlope/.omega_sentinel')
BASELINE_DIR = SENTINEL_DIR / 'baseline'
STATE_FILE   = SENTINEL_DIR / 'state.json'
PROJECT_DIR  = Path('/mnt/c/Veritas_Lab/gravity-omega-v2')

def sha256_file(path):
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        print(f'  WARN: could not hash {path}: {e}')
        return None

def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def pause_sentinel():
    state = load_state()
    state['paused'] = True
    save_state(state)
    print('✅ Sentinel PAUSED')

def resume_sentinel():
    state = load_state()
    state['paused'] = False
    save_state(state)
    print('✅ Sentinel RESUMED')

def accept_changes():
    """Update both the baseline backup files AND state.json hashes for all tracked files."""
    state = load_state()
    tracked = state.get('file_hashes', {})
    updated = 0

    for key, old_hash in list(tracked.items()):
        src = PROJECT_DIR / key
        dst = BASELINE_DIR / key

        if not src.exists():
            print(f'  SKIP (no source): {key}')
            continue

        new_hash = sha256_file(src)
        if new_hash is None:
            continue

        # Update backup copy
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

        # Update hash in state
        if tracked[key] != new_hash:
            print(f'  UPDATED: {key}')
            print(f'    {tracked[key][:12]} → {new_hash[:12]}')
            tracked[key] = new_hash
            updated += 1
        else:
            print(f'  OK: {key}')

    state['file_hashes'] = tracked
    save_state(state)
    print(f'\n✅ Accepted {updated} changed file(s). Baseline backups updated.')

def status():
    state = load_state()
    paused = state.get('paused', False)
    hashes = state.get('file_hashes', {})
    print(f'Sentinel paused: {paused}')
    print(f'Tracking {len(hashes)} files')
    print(f'Baseline dir: {BASELINE_DIR} (exists: {BASELINE_DIR.exists()})')

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if action == 'pause':
        pause_sentinel()
    elif action == 'resume':
        resume_sentinel()
    elif action == 'accept':
        accept_changes()
    elif action == 'status':
        status()
    elif action == 'full':
        # Full protocol in one shot: pause → accept → resume
        pause_sentinel()
        accept_changes()
        resume_sentinel()
    else:
        print(f'Unknown action: {action}. Use pause/resume/accept/status/full')
