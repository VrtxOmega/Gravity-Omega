#!/usr/bin/env python3
"""Quick test: does /api/search/web return results after regex fix?"""
import urllib.request, json

payload = json.dumps({"query": "latest news today"}).encode()
req = urllib.request.Request('http://127.0.0.1:5000/api/search/web',
    data=payload, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        d = json.loads(resp.read())
        results = d.get('results', [])
        print(f"RESULTS: {len(results)}")
        for r in results[:3]:
            print(f"  - {r.get('title', '?')[:80]}")
        if len(results) == 0:
            print(f"RAW RESPONSE: {json.dumps(d)[:200]}")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()[:200]}")
except Exception as e:
    print(f"ERROR: {e}")
