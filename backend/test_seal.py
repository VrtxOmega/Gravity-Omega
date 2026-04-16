import asyncio
import os
from datetime import datetime, timezone
import hashlib
from omega_sentinel import OmegaSentinel
from vtp_codec import VTPRouter
from provenance_stack import TraceSealer

def test_seal_verification():
    sealer = TraceSealer(seal_dir="test_seals")
    
    run_id = "test_run_123"
    compiled_context = {
        'query': 'test query',
        'chain_head': hashlib.sha256(run_id.encode()).hexdigest(),
        'fragments': [
            {'content_hash': 'frag1'},
            {'content_hash': 'frag2'}
        ]
    }
    
    # Manually compute chain head with fragments
    expected_chain_head = compiled_context['chain_head']
    for f in compiled_context['fragments']:
        expected_chain_head = hashlib.sha256(f"{expected_chain_head}:{f['content_hash']}".encode()).hexdigest()
    
    compiled_context['chain_head'] = expected_chain_head
    llm_response = 'test response'
    
    trace = sealer.seal_trace(run_id, compiled_context, llm_response)
    print("Generated Trace:", trace)
    
    verify_res = sealer.verify_seal(run_id)
    print("Verification:", verify_res)
    assert verify_res['valid']

    # Test broken chain
    seal_path = sealer.seal_dir / f'{run_id}.seal.json'
    import json
    broken_trace = json.loads(seal_path.read_text())
    broken_trace['fragment_hashes'][-1] = 'frag3'
    # Recalculate overall seal hash to bypass the second check and hit the chain check
    broken_trace.pop('seal_hash', None)
    new_seal_hash = hashlib.sha256(json.dumps(broken_trace, sort_keys=True).encode()).hexdigest()
    broken_trace['seal_hash'] = new_seal_hash
    seal_path.write_text(json.dumps(broken_trace, indent=2))
    
    verify_res2 = sealer.verify_seal(run_id)
    print("Broken Chain Verification:", verify_res2)
    assert not verify_res2['valid']
    assert verify_res2['error'] == 'S.E.A.L. chain truncation detected'

    print("SEAL verification passed!")

if __name__ == '__main__':
    test_seal_verification()
