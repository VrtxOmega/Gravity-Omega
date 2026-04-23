"""Sync CSS to WSL + update sentinel backup and state.json hash."""
import hashlib, json, shutil
from pathlib import Path

src = Path('/mnt/c/Veritas_Lab/gravity-omega-v2/renderer/styles/omega.css')
wsl_live = Path('/home/veritas/gravity-omega-v2/renderer/styles/omega.css')
bkp = Path('/home/veritas/.omega_sentinel/baseline/renderer__styles__omega.css')
state_file = Path('/home/veritas/.omega_sentinel/state.json')

shutil.copy2(src, wsl_live)
shutil.copy2(src, bkp)

new_hash = hashlib.sha256(src.read_bytes()).hexdigest()
state = json.loads(state_file.read_text())
state['file_hashes']['renderer/styles/omega.css'] = new_hash
state_file.write_text(json.dumps(state, indent=2))

print(f'CSS synced. New hash: {new_hash[:12]}')
