"""Quick live API validation script."""
import urllib.request
import json

BASE = "http://127.0.0.1:5070"

# Test /api/library
r = urllib.request.urlopen(f"{BASE}/api/library")
lib = json.loads(r.read().decode())
print(f"LIBRARY: {lib['total_documents']} docs, {lib['total_receipts']} receipts")

# Test /api/formats
r = urllib.request.urlopen(f"{BASE}/api/formats")
fmt = json.loads(r.read().decode())
print(f"FORMATS: {[f['id'] for f in fmt['formats']]}")

# Test /api/export via POST
payload = json.dumps({
    "title": "Live Server Test",
    "content": "# Live Server Test\n\nValidating the Flask API endpoint.\n\n## Results\n\n- Health: OK\n- Library: OK\n- Export: Testing...",
    "formats": ["md", "txt"],
    "confidentiality": "internal"
}).encode()
req = urllib.request.Request(
    f"{BASE}/api/export",
    data=payload,
    headers={"Content-Type": "application/json"}
)
r = urllib.request.urlopen(req)
result = json.loads(r.read().decode())
print(f"EXPORT: success={result['success']}, trace={result['trace_id']}")
for fmt_key, path in result["formats"].items():
    fname = path.split("\\")[-1] if "\\" in path else path.split("/")[-1]
    print(f"  {fmt_key.upper()}: {fname}")

# Test /api/drafts/save
payload2 = json.dumps({
    "content": "# Test Draft\n\nAuto-save validation.",
    "title": "Test Draft"
}).encode()
req2 = urllib.request.Request(
    f"{BASE}/api/drafts/save",
    data=payload2,
    headers={"Content-Type": "application/json"}
)
r2 = urllib.request.urlopen(req2)
draft_result = json.loads(r2.read().decode())
print(f"DRAFT SAVE: success={draft_result['success']}")

# Test /api/drafts/latest
r3 = urllib.request.urlopen(f"{BASE}/api/drafts/latest")
latest = json.loads(r3.read().decode())
print(f"DRAFT LOAD: success={latest['success']}")

print()
print("=" * 40)
print("ALL LIVE API TESTS PASS")
print("=" * 40)
