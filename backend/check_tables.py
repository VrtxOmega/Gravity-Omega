import sqlite3

conn = sqlite3.connect('backend/data/vault.db')
c = conn.cursor()
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("Tables:", tables)

for t in tables:
    c.execute(f"PRAGMA table_info({t})")
    print(t, [col[1] for col in c.fetchall()])
