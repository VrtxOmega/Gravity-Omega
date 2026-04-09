"""Verify all sentinel-watched electron files match state.json hashes."""
import hashlib, json
from pathlib import Path

state_file = Path('/home/veritas/.omega_sentinel/state.json')
state = json.load(open(state_file))

# Electron files: watched via /mnt/c/ absolute paths, key = part after gravity-omega-v2/
electron_map = {
    'main.js':               '/mnt/c/Veritas_Lab/gravity-omega-v2/main.js',
    'preload.js':            '/mnt/c/Veritas_Lab/gravity-omega-v2/preload.js',
    'renderer/app.js':       '/mnt/c/Veritas_Lab/gravity-omega-v2/renderer/app.js',
    'renderer/index.html':   '/mnt/c/Veritas_Lab/gravity-omega-v2/renderer/index.html',
    'renderer/styles/omega.css': '/mnt/c/Veritas_Lab/gravity-omega-v2/renderer/styles/omega.css',
    'omega/omega_bridge.js': '/mnt/c/Veritas_Lab/gravity-omega-v2/omega/omega_bridge.js',
}

def sha256(p):
    return hashlib.sha256(open(p,'rb').read()).hexdigest()

all_ok = True
for key, abs_path in electron_map.items():
    state_hash = state['file_hashes'].get(key, 'MISSING')[:12]
    live_hash = sha256(abs_path)[:12]
    match = state_hash == live_hash
    status = 'OK' if match else 'MISMATCH'
    if not match:
        all_ok = False
    print(f'  {status}: {key}  state:{state_hash}  live:{live_hash}')

print()
print('ALL CLEAR' if all_ok else 'MISMATCHES DETECTED — sentinel will heal these files')
