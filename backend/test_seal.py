#!/usr/bin/env python3
"""Quick test: POST to /api/provenance/seal without run_id and verify the fix."""
import urllib.request
import json

url = 'http://127.0.0.1:5000/api/provenance/seal'
body = json.dumps({
    'context': {
        'task': 'GOLIATH Master Living Report 110-Fact Provenance Seal',
        'fact_count': 110,
        'tier_a': 89,
        'tier_b': 21,
        'session_id': '5475dc2c-fc97-4f49-a0a6-9185a4c76400',
        'files': [
            'C:\\GOLIATH_WORKSPACE\\INTEL\\MASTER_LIVING_REPORT.md',
            'C:\\GOLIATH_WORKSPACE\\INTEL\\GOLIATH2\\THREAD4_GEOSPATIAL_ANALYSIS.md',
        ],
        'key_facts': {
            'constructive_knowledge': 'UCMR5 Nov 1 2023 PFOS above MCL at IL American-Peoria 811 days before S-4',
            'geospatial': 'TIER A subsurface feature 315 Tolle Lane 5 temporal data points Oct 2009-2022',
            's4_breach': "O Neill Exhibit 3.00 confirms 16-20 IAW systems vs threshold of 15",
        }
    },
    'response': 'GOLIATH Master Living Report v1.3 — 110 confirmed facts. AWK/WTRG PFAS merger securities disclosure gap Rule 10b-5. Constructive knowledge November 1 2023. O Neill Exhibit 3.00 confirms 16-20 IAW systems. Thread 4 TIER A subsurface feature 315 Tolle Lane Oct 2009 to 2022. 89 TIER A 21 TIER B 72 triggers. Sealed 2026-03-25. Ready for SEC Form TCR.'
}).encode('utf-8')

req = urllib.request.Request(
    url,
    data=body,
    headers={
        'Content-Type': 'application/json',
        'Authorization': 'Bearer sentinel',
    },
    method='POST'
)

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
        print('SUCCESS:')
        print(json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    body_err = e.read().decode()
    print(f'HTTP ERROR {e.code}: {body_err}')
except Exception as ex:
    print(f'ERROR: {ex}')
