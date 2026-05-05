import sqlite3
c = sqlite3.connect("coders_bible.db")
deleted = c.execute("DELETE FROM fragments WHERE source LIKE 'thinking-indicator-implementation%'").rowcount
c.execute("INSERT INTO bible_fts(bible_fts) VALUES('rebuild')")
c.commit()
print(f"Deleted {deleted} thinking-indicator-implementation rows")
