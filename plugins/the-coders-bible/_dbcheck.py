import sqlite3
c = sqlite3.connect("coders_bible.db")
google = c.execute(
    "SELECT COUNT(*) FROM fragments WHERE "
    "source LIKE 'gemini/%' OR source LIKE 'vertexai/%' OR "
    "source LIKE 'gcloud/%' OR source LIKE 'firebase/%' OR "
    "source LIKE 'tensorflow/%' OR source LIKE 'jax/%' OR source LIKE 'android/%'"
).fetchone()[0]
total = c.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
domains = c.execute(
    "SELECT source, COUNT(*) as n FROM fragments GROUP BY "
    "CASE "
    "  WHEN source LIKE 'git/%' THEN 'git' "
    "  WHEN source LIKE 'bash/%' THEN 'bash' "
    "  WHEN source LIKE 'docker/%' THEN 'docker' "
    "  WHEN source LIKE 'kubernetes/%' OR source LIKE 'k8s/%' THEN 'kubernetes' "
    "  WHEN source LIKE 'cpp/%' OR source LIKE 'c/%' THEN 'c/c++' "
    "  WHEN source LIKE 'html/%' OR source LIKE 'css/%' OR source LIKE 'mdn/%' THEN 'css/html' "
    "  WHEN source LIKE 'java/%' THEN 'java' "
    "  WHEN source LIKE 'terraform/%' THEN 'terraform' "
    "  WHEN source LIKE 'csharp/%' OR source LIKE 'dotnet/%' THEN 'c#' "
    "  WHEN source LIKE 'sql/%' THEN 'sql' "
    "  WHEN source LIKE 'kotlin/%' THEN 'kotlin' "
    "  WHEN source LIKE 'swift/%' THEN 'swift' "
    "  ELSE 'other' END "
    "ORDER BY n DESC LIMIT 15"
).fetchall()
c.close()
print(f"total={total}  google_partial={google}")
print("Domain breakdown (by source prefix):")
for d in domains:
    print(f"  {d[0][:60]:60s} {d[1]:,}")
