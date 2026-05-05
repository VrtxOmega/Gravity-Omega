import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('coders_bible.db')
conn.row_factory = sqlite3.Row
total = conn.execute('SELECT COUNT(*) FROM fragments').fetchone()[0]
print(f'TOTAL FRAGMENTS: {total:,}')

SQL = """
SELECT
    CASE
        WHEN source LIKE 'python/%'      OR source LIKE '%docs.python.org%'                      THEN 'Python'
        WHEN source LIKE 'javascript/%'  OR source LIKE '%nodejs%' OR source LIKE '%npmjs%'      THEN 'JavaScript'
        WHEN source LIKE 'typescript/%'  OR source LIKE '%typescriptlang%'                       THEN 'TypeScript'
        WHEN source LIKE 'rust/%'        OR source LIKE '%doc.rust-lang%' OR source LIKE '%docs.rs%' THEN 'Rust'
        WHEN source LIKE 'golang/%'      OR source LIKE '%go.dev%' OR source LIKE '%pkg.go.dev%' THEN 'Go'
        WHEN source LIKE 'ruby/%'        OR source LIKE '%ruby%'                                 THEN 'Ruby'
        WHEN source LIKE 'php/%'         OR source LIKE '%php.net%'                              THEN 'PHP'
        WHEN source LIKE 'java/%'
             AND source NOT LIKE '%javascript%'
             AND source NOT LIKE '%typescript%'                                                   THEN 'Java'
        WHEN source LIKE 'bash/%'        OR source LIKE '%gnu.org/software/bash%'
                                         OR source LIKE '%tldp.org%'                             THEN 'Bash'
        WHEN source LIKE 'powershell/%'  OR source LIKE '%microsoft.com/powershell%'             THEN 'PowerShell'
        WHEN source LIKE 'sql/%'         OR source LIKE '%mysql%' OR source LIKE '%mariadb%'
                                         OR source LIKE '%postgresql%' OR source LIKE '%postgres%'
                                         OR source LIKE '%sqlite%'                               THEN 'SQL'
        WHEN source LIKE 'docker/%'      OR source LIKE '%docker.com%'                           THEN 'Docker'
        WHEN source LIKE 'kubernetes/%'  OR source LIKE '%k8s%'                                  THEN 'Kubernetes'
        WHEN source LIKE 'nginx/%'       OR source LIKE '%nginx.org%'                            THEN 'Nginx'
        WHEN source LIKE 'systemd/%'     OR source LIKE '%freedesktop.org%'                      THEN 'systemd'
        WHEN source LIKE 'git/%'         OR source LIKE '%git-scm%'                              THEN 'Git'
        WHEN source LIKE 'ansible/%'     OR source LIKE '%ansible.com%'                          THEN 'Ansible'
        WHEN source LIKE 'css/%'         OR source LIKE '%/CSS/%'                                THEN 'CSS'
        WHEN source LIKE 'html/%'        OR source LIKE '%/HTML/%'                               THEN 'HTML'
        WHEN source LIKE 'yaml/%'                                                                THEN 'YAML'
        WHEN source LIKE 'json/%'                                                                THEN 'JSON'
        WHEN source LIKE 'terraform/%'   OR source LIKE '%hashicorp%'                            THEN 'Terraform'
        WHEN source LIKE 'csharp/%'      OR source LIKE '%dotnet/csharp%'                        THEN 'C#'
        WHEN source LIKE 'kotlin/%'      OR source LIKE '%kotlinlang%'                           THEN 'Kotlin'
        WHEN source LIKE 'c/%'           OR source LIKE 'cpp/%' OR source LIKE '%cppreference%'  THEN 'C/C++'
        WHEN source LIKE 'swift/%'       OR source LIKE '%swift.org%'                            THEN 'Swift'
        WHEN source LIKE 'linux/%'       OR source LIKE '%linux%' OR source LIKE '%man7.org%'
                                         OR source LIKE '%sourceware.org%'                       THEN 'Linux'
        WHEN source LIKE 'node/%'        OR source LIKE '%node.js%'                              THEN 'Node.js'
        WHEN source LIKE 'mysql/%'                                                               THEN 'MySQL'
        WHEN source LIKE 'postgresql/%'  OR source LIKE '%postgres%'                             THEN 'PostgreSQL'
        WHEN source LIKE 'linux-tools/%' OR source LIKE '%binutils%'                             THEN 'Linux'
        ELSE 'Other'
    END as domain,
    COUNT(*) as count
FROM fragments
GROUP BY domain
ORDER BY count DESC
"""

rows = conn.execute(SQL).fetchall()
print()
print(f"{'DOMAIN':<20} {'COUNT':>8}")
print('-'*30)
covered = 0
for r in rows:
    d = r['domain']
    c = r['count']
    if d != 'Other':
        covered += c
    print(f"{d:<20} {c:>8,}")
print('-'*30)
print(f"{'Covered (non-Other)':<20} {covered:>8,}  ({100*covered/total:.1f}%)")
print(f"{'Total':<20} {total:>8,}")
