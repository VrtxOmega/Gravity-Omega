import sqlite3
conn = sqlite3.connect('coders_bible.db')
c = conn.cursor()
for domain in ['swift', 'terraform', 'sql']:
    c.execute(f"SELECT count(*) FROM fragments WHERE source LIKE '{domain}%'")
    print(f"{domain.capitalize()}: {c.fetchone()[0]}")
c.execute("SELECT count(*) FROM fragments")
print(f"Total: {c.fetchone()[0]}")
