import sqlite3

def clean():
    conn = sqlite3.connect('c:/Veritas_Lab/gravity-omega-v2/backend/data/vault.db')
    c = conn.cursor()
    c.execute("DELETE FROM entries WHERE content LIKE '%DETONATION%' OR content LIKE '%invisible ink%'")
    print("Deleted rows dealing with DETONATION_POC from entries:", c.rowcount)
    c.execute("DELETE FROM entries_fts WHERE content LIKE '%DETONATION%' OR content LIKE '%invisible ink%'")
    print("Deleted rows from entries_fts:", c.rowcount)
    conn.commit()

if __name__ == "__main__":
    clean()
