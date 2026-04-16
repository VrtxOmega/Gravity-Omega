import os
import json
import hashlib
import hmac

# Setup environment mock before importing
os.environ['OMEGA_SENTINEL_STATE_SECRET'] = 'test-secret'

from omega_sentinel import OmegaSentinel, STATE_FILE, SENTINEL_DIR

# Disable actually running the daemon loop if needed
OmegaSentinel._ensure_dirs = lambda self: None

def run_test():
    sentinel = OmegaSentinel()
    
    # 1. Save valid state
    valid_state = {'test': 'data'}
    sentinel.state = valid_state.copy()
    sentinel._save_state()
    
    # 2. Verify it loads
    sentinel.state = {}
    sentinel._load_state()
    assert sentinel.state.get('test') == 'data', 'Valid state failed to load'
    print("[PASS] Valid state loads and verifies.")
    
    # 3. Poison the state
    with open(STATE_FILE, 'r') as f:
        raw = json.load(f)
    raw['test'] = 'poison'
    with open(STATE_FILE, 'w') as f:
        json.dump(raw, f)
        
    # 4. Try loading poisoned state
    sentinel.state = {}
    sentinel._load_state()
    assert sentinel.state == {}, f'Poisoned state should not load, got {sentinel.state}'
    print("[PASS] Poisoned state rejected.")

if __name__ == '__main__':
    # Make sure dirs exist
    os.makedirs(str(SENTINEL_DIR), exist_ok=True)
    run_test()
