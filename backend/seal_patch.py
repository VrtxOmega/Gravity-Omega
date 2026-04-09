#!/usr/bin/env python3
"""
Targeted patch: inject run_id, query, chain_head, fragments into api_provenance_seal
before calling stack.seal_response() to fix the KeyError: 'run_id' on line 333 of provenance_stack.py
"""
import sys

path = '/home/veritas/gravity-omega-v2/backend/web_server.py'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the function
start = None
end = None
for i, line in enumerate(lines):
    if 'def api_provenance_seal' in line and 'seals' not in line:
        start = i
    if start and i > start and line.startswith('@app.route'):
        end = i
        break

if start is None:
    print('ERROR: function not found')
    sys.exit(1)

print(f'Found api_provenance_seal at lines {start+1}-{end}')

# Replacement function body
replacement = '''def api_provenance_seal():
    """v4.0: Seal a completed agentic run via S.E.A.L. cryptographic chain."""
    import hashlib as _hlib, time as _t
    try:
        data = request.json or {}
        context = data.get('context')
        response_text = data.get('response', '')
        if not context:
            return jsonify({'error': 'context required'}), 400
        # FIX: TraceSealer.seal_run() does hard key access on these fields.
        # Inject defaults if MCP sends a raw context without them.
        if 'run_id' not in context:
            context['run_id'] = _hlib.sha256(str(_t.time()).encode()).hexdigest()[:16]
        if 'query' not in context:
            context['query'] = context.get('task', 'agentic_run')
        if 'chain_head' not in context:
            context['chain_head'] = _hlib.sha256(context['run_id'].encode()).hexdigest()
        if 'fragments' not in context:
            context['fragments'] = []
        stack = get_provenance_stack()
        seal = stack.seal_response(context, response_text)
        _ledger_append('provenance', 'seal', {
            'run_id': context.get('run_id'),
            'seal_hash': seal.get('seal_hash', '')[:16],
        })
        return jsonify(seal)
    except Exception as e:
        log.error(f'Provenance seal error: {e}')
        return jsonify({'error': str(e)}), 500
'''

new_lines = lines[:start] + [replacement] + lines[end:]

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'PATCH APPLIED: replaced lines {start+1}-{end} with patched function')
print('Verify:')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
if 'run_id not in context' in content:
    print('OK: run_id injection confirmed in patched file')
else:
    print('ERROR: patch verification failed')
