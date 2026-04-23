#!/usr/bin/env python3
import urllib.request, json

# Test 1: DuckDuckGo via Flask API
try:
    payload = json.dumps({"query": "latest news today"}).encode()
    req = urllib.request.Request(
        'http://127.0.0.1:5000/api/search/web',
        data=payload,
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        d = json.loads(resp.read())
        print(f"DDG API: count={d.get('count',0)} error={d.get('error','none')}")
        if d.get('results'):
            print(f"  First: {d['results'][0].get('title','?')}")
except Exception as e:
    print(f"DDG API ERROR: {e}")

# Test 2: Direct HTTPS fetch
try:
    req2 = urllib.request.Request(
        'https://httpbin.org/get',
        headers={'User-Agent': 'OmegaTest/1.0'}
    )
    with urllib.request.urlopen(req2, timeout=10) as resp:
        print(f"Direct HTTPS: status={resp.status}")
except Exception as e:
    print(f"Direct HTTPS ERROR: {e}")
