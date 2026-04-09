"""
Correct fix: 
1. Revert .sidebar-panel to overflow-y: auto (let panel scroll naturally)
2. Remove max-height:180px from .reports-list inside sidebar panels
3. Remove the broken last-of-type rules (CSS bug: last-of-type matches div type, not class)
This lets content fill naturally — no empty space, no collapsed lists.
"""
import hashlib, json, shutil, re
from pathlib import Path

WSL_CSS  = Path('/home/veritas/gravity-omega-v2/renderer/styles/omega.css')
WIN_CSS  = Path('/mnt/c/Veritas_Lab/gravity-omega-v2/renderer/styles/omega.css')
BKP      = Path('/home/veritas/.omega_sentinel/baseline/renderer__styles__omega.css')
STATE    = Path('/home/veritas/.omega_sentinel/state.json')

content = WSL_CSS.read_text(encoding='utf-8')

# Fix 1: sidebar-panel back to overflow-y: auto
content = content.replace(
    '    overflow: hidden; min-height: 0;',
    '    overflow-y: auto; overflow-x: hidden; min-height: 0;'
)

# Fix 2: remove broken last-of-type rules
content = content.replace(
    '\n.sidebar-panel .reports-section:last-of-type { flex: 1; min-height: 0; }', ''
)
content = content.replace(
    '\n.sidebar-panel .reports-section:last-of-type .reports-list { max-height: none; flex: 1; overflow-y: auto; }', ''
)

# Fix 3: uncap reports-list inside sidebar panels — no max-height
content = content.replace(
    '.reports-list { padding: 4px 0 8px; overflow-y: auto; max-height: 180px; }',
    '.reports-list { padding: 4px 0 8px; }'
)

# Fix 4: reports-section-grow can still grow if explicitly set
content = content.replace(
    '.reports-section.reports-section-grow { flex: 1; min-height: 0; }',
    '.reports-section.reports-section-grow { flex: 1; min-height: 0; }\n.reports-section-grow .reports-list { overflow-y: auto; }'
)

WSL_CSS.write_text(content, encoding='utf-8')
shutil.copy2(WSL_CSS, WIN_CSS)
shutil.copy2(WSL_CSS, BKP)

new_hash = hashlib.sha256(WSL_CSS.read_bytes()).hexdigest()
state = json.loads(STATE.read_text())
old_hash = state['file_hashes'].get('renderer/styles/omega.css', '?')[:12]
state['file_hashes']['renderer/styles/omega.css'] = new_hash
STATE.write_text(json.dumps(state, indent=2))
print(f'✅ Patch applied: natural scroll layout')
print(f'✅ Sentinel: {old_hash} → {new_hash[:12]}')
