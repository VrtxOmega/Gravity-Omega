import sqlite3, os

DB = os.path.join(os.path.dirname(__file__), "coders_bible.db")
conn = sqlite3.connect(DB)

for col, definition in [("ftype", "TEXT DEFAULT 'doc'"), ("lang_version", "TEXT")]:
    try:
        conn.execute(f"ALTER TABLE fragments ADD COLUMN {col} {definition}")
        print(f"  + added column: {col}")
    except Exception as e:
        print(f"  - {col} already exists: {e}")

conn.commit()
conn.close()
print("Schema migration complete.")
