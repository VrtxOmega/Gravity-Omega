"""
Fix sentinel healing loop: update state.json hashes to match what's LIVE in the WSL project.
The sentinel heals when live_hash != baseline_hash. We fix state.json so baseline_hash = live_hash,
then also update the backup files to match.
"""
import hashlib, json, shutil
from pathlib import Path

root = Path('/home/veritas/gravity-omega-v2')
baseline_dir = Path('/home/veritas/.omega_sentinel/baseline')
state_file = Path('/home/veritas/.omega_sentinel/state.json')

def sha256(path):
    return hashlib.sha256(open(path,'rb').read()).hexdigest()

state = json.load(open(state_file))

# Fix ALL entries: set hash TO the current live file hash, and update backup copy
for key, old_hash in list(state['file_hashes'].items()):
    live = root / key
    if not live.exists():
        print(f'  SKIP (no live): {key}')
        continue

    live_hash = sha256(live)
    safe_name = key.replace('/', '__').replace('\\\\', '__')
    backup = baseline_dir / safe_name

    if live_hash != old_hash:
        print(f'  FIX: {key}')
        print(f'       state:{old_hash[:12]} live:{live_hash[:12]}')
        state['file_hashes'][key] = live_hash
        # Update backup to match live
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, backup)
    else:
        print(f'  OK:  {key}  {old_hash[:12]}')

json.dump(state, open(state_file, 'w'), indent=2)
print('\nAll hashes and backups synced to live state. Sentinel should stop healing.')
