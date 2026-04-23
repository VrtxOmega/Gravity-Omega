#!/usr/bin/env python3
"""
Direct line-number patch for web_server.py.
Inserts run_id injection block after the 'if not context: return ...' guard (line 1494).
No string matching — pure line number surgery.
"""
import sys

path = '/home/veritas/gravity-omega-v2/backend/web_server.py'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Verify correct targeting
target_check = '        if not context:\n'
target_return = "            return jsonify({'error': 'context required'}), 400\n"

# Find the insertion point — after 'return jsonify context required' inside provenance seal
insert_after = None
for i in range(1480, min(1510, len(lines))):
    if target_check in lines[i] and target_return in lines[i+1]:
        insert_after = i + 1  # line after the return
        break

if insert_after is None:
    # Fallback: try known line 1494
    if '400' in lines[1493]:  # 0-indexed line 1494 = index 1493
        insert_after = 1493
    else:
        print(f'ERROR: could not find insertion point')
        print(f'Lines 1490-1500:')
        for j in range(1489, 1500):
            print(f'  {j+1}: {lines[j].rstrip()}')
        sys.exit(1)

print(f'Inserting after line {insert_after + 1} (0-indexed {insert_after})')
print(f'  Current line: {lines[insert_after].rstrip()}')
print(f'  Next line:    {lines[insert_after + 1].rstrip()}')

# Check not already patched
already = any('run_id' in l and 'not in context' in l for l in lines[1480:1520])
if already:
    print('ALREADY PATCHED — run_id injection already present')
    sys.exit(0)

# Build the injection block
injection = [
    "        # FIX: TraceSealer.seal_run() does hard key access — inject defaults\n",
    "        import hashlib as _hlib, time as _t\n",
    "        if 'run_id' not in context:\n",
    "            context['run_id'] = _hlib.sha256(str(_t.time()).encode()).hexdigest()[:16]\n",
    "        if 'query' not in context:\n",
    "            context['query'] = context.get('task', 'agentic_run')\n",
    "        if 'chain_head' not in context:\n",
    "            context['chain_head'] = _hlib.sha256(context['run_id'].encode()).hexdigest()\n",
    "        if 'fragments' not in context:\n",
    "            context['fragments'] = []\n",
]

# Insert after insert_after
new_lines = lines[:insert_after + 1] + injection + lines[insert_after + 1:]

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# Verify
with open(path, 'r', encoding='utf-8') as f:
    verify = f.read()

if "'run_id' not in context" in verify:
    print(f'PATCH VERIFIED OK — run_id injection at line ~{insert_after + 2}')
else:
    print('PATCH WRITE FAILED — verification string not found')
    sys.exit(1)
