import sqlite3

def clean_vault():
    try:
        conn = sqlite3.connect('c:/Veritas_Lab/gravity-omega-v2/backend/vault.db')
        c = conn.cursor()
        
        # Check tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = c.fetchall()
        print(f"Tables: {tables}")
        
        for (table_name,) in tables:
            # Check what's inside
            try:
                c.execute(f"SELECT COUNT(*) FROM {table_name}")
                print(f"Rows in {table_name}: {c.fetchone()[0]}")
            except Exception as e:
                print(f"Count err: {e}")
                
            # Try to delete payload entries
            try:
                c.execute(f"DELETE FROM {table_name} WHERE content LIKE '%DETONATION%' OR content LIKE '%invisible ink%' OR content LIKE '%VRP%'")
                deleted = c.rowcount
                if deleted > 0:
                    print(f"Deleted {deleted} rows from {table_name} containing the PoC payload.")
            except Exception:
                # 'content' column might not exist
                pass

        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    clean_vault()
