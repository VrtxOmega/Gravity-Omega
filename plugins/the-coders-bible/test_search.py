from backend.bible_engine import BibleEngine

e = BibleEngine()

# Test 1: Python fibonacci
print("=== TEST 1: Python fibonacci ===")
r = e.analyze("def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)")
print(f"Language: {r['language']['language']} ({r['language']['confidence']})")
print(f"Keywords: {r['keywords']}")
print(f"Results: {r['result_count']}")
for x in r['results'][:8]:
    print(f"  [{x['tier']}] {x['source'][:70]}")

# Test 2: Rust code
print("\n=== TEST 2: Rust struct ===")
r = e.analyze("fn main() {\n    let v: Vec<i32> = vec![1,2,3];\n    println!(\"{:?}\", v);\n}")
print(f"Language: {r['language']['language']} ({r['language']['confidence']})")
print(f"Keywords: {r['keywords']}")
print(f"Results: {r['result_count']}")
for x in r['results'][:5]:
    print(f"  [{x['tier']}] {x['source'][:70]}")

# Test 3: Docker
print("\n=== TEST 3: Dockerfile ===")
r = e.analyze("FROM python:3.11-slim\nRUN pip install flask\nCOPY . /app\nWORKDIR /app\nEXPOSE 5000\nCMD [\"python\", \"app.py\"]")
print(f"Language: {r['language']['language']} ({r['language']['confidence']})")
print(f"Keywords: {r['keywords']}")
print(f"Results: {r['result_count']}")
for x in r['results'][:5]:
    print(f"  [{x['tier']}] {x['source'][:70]}")

# Test 4: Nginx
print("\n=== TEST 4: Nginx config ===")
r = e.analyze("server {\n    listen 80;\n    server_name example.com;\n    location / {\n        proxy_pass http://localhost:3000;\n    }\n}")
print(f"Language: {r['language']['language']} ({r['language']['confidence']})")
print(f"Keywords: {r['keywords']}")
print(f"Results: {r['result_count']}")
for x in r['results'][:5]:
    print(f"  [{x['tier']}] {x['source'][:70]}")
