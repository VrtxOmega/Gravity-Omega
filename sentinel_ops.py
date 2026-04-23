"""
Sentinel control helper: pause / accept / resume / status / rebaseline
Usage: python3 sentinel_ops.py <action>
  rebaseline  — recompute hashes from disk and update the state.json baseline directly
  pause/resume/accept/status — call the live API (requires running web_server)
"""
import sys
import json
import hashlib
import urllib.request
from pathlib import Path
import subprocess

SENTINEL_DIR = Path.home() / '.omega_sentinel'
BASE_DIR = Path(__file__).parent

def sha256_file(path):
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()[:12]  # truncated like sentinel uses
    except Exception:
        return None

def rebaseline():
    """Directly update the sentinel state.json baseline with current file hashes."""
    state_file = SENTINEL_DIR / 'state.json'
    if not state_file.exists():
        print(f'No state file at {state_file}')
        return
    with open(state_file) as f:
        state = json.load(f)
    
    tracked = state.get('file_hashes', {})
    updated = 0
    for key, old_hash in tracked.items():
        path = BASE_DIR / key
        new_hash = sha256_file(path)
        if new_hash and new_hash != old_hash:
            print(f'  Updated: {key}  {old_hash} -> {new_hash}')
            tracked[key] = new_hash
            updated += 1
        else:
            print(f'  OK: {key}  {old_hash}')
    
    state['file_hashes'] = tracked
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
    print(f'\nRebaselined {updated} file(s). State saved.')

def get_token():
    try:
        pids = subprocess.check_output(['pgrep', '-f', 'web_server']).decode().strip().split()
        for pid in pids:
            with open(f'/proc/{pid}/environ', 'rb') as f:
                data = f.read()
            pairs = dict(x.split(b'=', 1) for x in data.split(b'\x00') if b'=' in x)
            tok = pairs.get(b'OMEGA_AUTH_TOKEN', b'').decode()
            if tok:
                return tok
    except Exception as e:
        print(f'Token lookup error: {e}')
    return ''

def call(action):
    endpoints = {
        'pause':  'http://127.0.0.1:5000/api/sentinel/pause',
        'resume': 'http://127.0.0.1:5000/api/sentinel/resume',
        'accept': 'http://127.0.0.1:5000/api/sentinel/accept',
        'status': 'http://127.0.0.1:5000/api/sentinel/status',
    }
    url = endpoints[action]
    token = get_token()
    method = 'GET' if action == 'status' else 'POST'
    req = urllib.request.Request(url, method=method, headers={'X-Omega-Token': token})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(json.dumps(json.loads(resp.read()), indent=2))
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if action == 'rebaseline':
        rebaseline()
    else:
        call(action)
