"""
The Coder's Bible — Knowledge Engine
Queries the 53,018-fragment Bible database via FTS5.
Language detection via regex fingerprints + source analysis.
"""

import re
import sqlite3
import os
from typing import Optional

# ─── Database Path ───────────────────────────────────────────
# Standalone Bible database — fully separated from Omega Brain
DB_PATH = os.environ.get(
    "BIBLE_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "coders_bible.db")
)

# ─── Language Fingerprints ───────────────────────────────────
# Each entry: (language, [regex patterns], priority)
FINGERPRINTS = [
    # Shell / Bash
    ("Bash", [
        r"^\s*#!/bin/(ba)?sh",
        r"^\s*(sudo|apt|yum|dnf|brew|pacman|chmod|chown|chgrp|mkdir|rmdir|cp|mv|rm|ls|cat|grep|awk|sed|find|xargs|tar|curl|wget|ssh|scp|rsync|systemctl|journalctl|crontab)\b",
        r"^\s*export\s+\w+=",
        r"\|\s*(grep|awk|sed|sort|uniq|wc|head|tail|cut|tr)\b",
        r"^\s*(if|then|fi|elif|else|for|do|done|while|case|esac)\b.*;\s*$",
        r"\$\{?\w+\}?",
        r"^\s*echo\s+",
    ], 10),

    # PowerShell
    ("PowerShell", [
        r"^\s*(Get-|Set-|New-|Remove-|Invoke-|Start-|Stop-|Write-|Read-|Test-|Import-|Export-|Select-|Where-|ForEach-)\w+",
        r"\$\w+\s*=\s*",
        r"\|\s*(Select-Object|Where-Object|ForEach-Object|Sort-Object|Group-Object|Measure-Object)\b",
        r"^\s*\[Parameter\(",
        r"^\s*param\s*\(",
        r"-\w+\s+\$",
    ], 10),

    # Python
    ("Python", [
        r"^\s*def\s+\w+\s*\(.*\)\s*(->\s*\w+)?\s*:",
        r"^\s*class\s+\w+(\(.*\))?\s*:",
        r"^\s*(import|from)\s+\w+",
        r"^\s*if\s+__name__\s*==\s*['\"]__main__['\"]",
        r"^\s*@\w+",
        r"^\s*(print|len|range|enumerate|zip|map|filter|lambda)\s*\(",
        r"^\s*(try|except|finally|raise|with|as|yield|async|await)\b",
        r"self\.\w+",
    ], 9),

    # JavaScript
    ("JavaScript", [
        r"^\s*(const|let|var)\s+\w+\s*=",
        r"^\s*function\s+\w+\s*\(",
        r"=>\s*\{",
        r"\bconsole\.(log|warn|error|info)\s*\(",
        r"^\s*(module\.exports|export\s+(default|const|function|class))\b",
        r"\b(document|window|addEventListener|querySelector|fetch)\b",
        r"^\s*import\s+.*\s+from\s+['\"]",
        r"\.then\s*\(|\.catch\s*\(|async\s+function",
    ], 8),

    # TypeScript
    ("TypeScript", [
        r":\s*(string|number|boolean|void|any|never|unknown|undefined)\b",
        r"^\s*interface\s+\w+",
        r"^\s*type\s+\w+\s*=",
        r"<\w+(\s*,\s*\w+)*>",
        r"^\s*(public|private|protected|readonly)\s+",
        r"\bas\s+(string|number|boolean|any|unknown)\b",
        r"^\s*enum\s+\w+\s*\{",
    ], 9),

    # Rust
    ("Rust", [
        r"^\s*fn\s+\w+\s*(<.*>)?\s*\(",
        r"^\s*(pub|mod|use|crate|extern|impl|trait|struct|enum)\b",
        r"\b(let\s+mut|&mut|&self|Self|Option<|Result<|Vec<|Box<|Rc<|Arc<)\b",
        r"^\s*#\[(derive|cfg|test|allow|warn|deny)\b",
        r"\b(unwrap|expect|match|Some|None|Ok|Err)\b",
        r"^\s*macro_rules!\s*\w+",
        r"::\s*new\s*\(",
    ], 9),

    # Go
    ("Go", [
        r"^\s*func\s+(\(\w+\s+\*?\w+\)\s+)?\w+\s*\(",
        r"^\s*package\s+\w+",
        r"^\s*import\s+\(",
        r"\b(fmt|os|io|net|http|json|sync|context|errors)\.\w+",
        r":=\s*",
        r"^\s*type\s+\w+\s+(struct|interface)\s*\{",
        r"\bgo\s+func\b|\bdefer\b|\bgoroutine\b",
        r"\bchan\s+\w+|\bselect\s*\{",
    ], 9),

    # Ruby
    ("Ruby", [
        r"^\s*def\s+\w+",
        r"^\s*class\s+\w+(\s*<\s*\w+)?",
        r"^\s*module\s+\w+",
        r"\b(puts|print|require|require_relative|attr_accessor|attr_reader|attr_writer)\b",
        r"^\s*end\s*$",
        r"\bdo\s*\|.*\|",
        r"\.(each|map|select|reject|reduce|inject|collect|detect|find)\b",
        r"^\s*gem\s+['\"]",
    ], 8),

    # PHP
    ("PHP", [
        r"<\?php",
        r"\$\w+\s*=",
        r"^\s*(function|class|interface|trait|namespace|use)\b",
        r"\b(echo|print_r|var_dump|isset|empty|unset|array|foreach|require_once|include)\b",
        r"->\w+\s*\(",
        r"::\w+\s*\(",
    ], 8),

    # Java
    ("Java", [
        r"^\s*(public|private|protected)\s+(static\s+)?(void|int|String|boolean|double|float|long|char)\s+\w+\s*\(",
        r"^\s*class\s+\w+(\s+extends\s+\w+)?(\s+implements\s+\w+)?\s*\{",
        r"^\s*import\s+java\.",
        r"\b(System\.out\.println|System\.err|new\s+\w+\()\b",
        r"^\s*@(Override|Test|Autowired|Component|Service|Repository|Controller)\b",
        r"\b(ArrayList|HashMap|LinkedList|TreeMap|StringBuilder)\b",
    ], 8),

    # SQL
    ("SQL", [
        r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|GRANT|REVOKE)\b",
        r"\b(FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|OFFSET)\b",
        r"\b(TABLE|INDEX|VIEW|TRIGGER|PROCEDURE|FUNCTION|DATABASE|SCHEMA)\b",
        r"\b(INT|VARCHAR|TEXT|BOOLEAN|TIMESTAMP|SERIAL|PRIMARY\s+KEY|FOREIGN\s+KEY|NOT\s+NULL)\b",
    ], 7),

    # Docker
    ("Docker", [
        r"^\s*(FROM|RUN|CMD|ENTRYPOINT|COPY|ADD|EXPOSE|ENV|ARG|WORKDIR|VOLUME|USER|LABEL|HEALTHCHECK)\b",
        r"^\s*docker\s+(build|run|exec|compose|pull|push|images|ps|stop|rm|logs|inspect)\b",
    ], 8),

    # Kubernetes
    ("Kubernetes", [
        r"^\s*apiVersion:\s*",
        r"^\s*kind:\s*(Pod|Deployment|Service|ConfigMap|Secret|Ingress|DaemonSet|StatefulSet)\b",
        r"^\s*kubectl\s+(get|apply|describe|delete|logs|exec|port-forward|scale)\b",
        r"^\s*metadata:\s*$",
        r"^\s*spec:\s*$",
    ], 8),

    # Nginx
    ("Nginx", [
        r"^\s*(server|location|upstream|http|events)\s*\{",
        r"\b(proxy_pass|listen|server_name|root|index|try_files|fastcgi_pass|ssl_certificate)\b",
        r"^\s*worker_processes\b",
        r"^\s*include\s+/etc/nginx/",
    ], 8),

    # systemd
    ("systemd", [
        r"^\s*\[(Unit|Service|Install|Timer|Socket|Mount|Path)\]",
        r"^\s*(ExecStart|ExecStop|ExecReload|Restart|WantedBy|After|Before|Requires|Description)\s*=",
        r"^\s*systemctl\s+(start|stop|restart|enable|disable|status|daemon-reload)\b",
    ], 8),

    # Git
    ("Git", [
        r"^\s*git\s+(init|clone|add|commit|push|pull|fetch|merge|rebase|checkout|branch|log|diff|stash|reset|tag|remote)\b",
        r"^\s*\.gitignore\b",
    ], 7),

    # Ansible
    ("Ansible", [
        r"^\s*-\s*(name|hosts|tasks|roles|vars|handlers|become|gather_facts):",
        r"\b(ansible|playbook|inventory|galaxy|vault)\b",
        r"^\s*\w+\.\w+\.\w+:",  # collection.module.name pattern
    ], 7),

    # YAML/Config
    ("YAML", [
        r"^\s*\w+:\s*$",
        r"^\s*-\s+\w+:",
        r"^\s*---\s*$",
    ], 3),

    # JSON
    ("JSON", [
        r'^\s*\{[\s\n]*"\w+"',
        r'^\s*\[[\s\n]*\{',
    ], 3),

    # CSS
    ("CSS", [
        r"^\s*[\.\#\w\[\*:]+\s*\{",
        r"\b(color|background|margin|padding|display|flex|grid|position|border|font|transition|animation|transform)\s*:",
        r"^\s*@(media|keyframes|import|font-face)\b",
    ], 6),

    # HTML
    ("HTML", [
        r"^\s*<(!DOCTYPE|html|head|body|div|span|p|a|img|form|input|button|script|style|link|meta)\b",
        r"<\/\w+>",
    ], 5),
]

# ─── Domain Color Map ────────────────────────────────────────
DOMAIN_COLORS = {
    "Python": "#3776AB",
    "JavaScript": "#F7DF1E",
    "TypeScript": "#3178C6",
    "Rust": "#DEA584",
    "Go": "#00ADD8",
    "Ruby": "#CC342D",
    "PHP": "#777BB4",
    "Java": "#ED8B00",
    "Bash": "#4EAA25",
    "PowerShell": "#012456",
    "SQL": "#E38C00",
    "Docker": "#2496ED",
    "Kubernetes": "#326CE5",
    "Nginx": "#009639",
    "systemd": "#6C7A89",
    "Git": "#F05032",
    "Ansible": "#EE0000",
    "CSS": "#1572B6",
    "HTML": "#E34F26",
    "YAML": "#CB171E",
    "JSON": "#292929",
    "Terraform": "#7B42BC",
    "C#": "#239120",
    "Kotlin": "#7F52FF",
    "C/C++": "#00599C",
    "Swift": "#F05138",
    "Linux": "#FCC624",
    "Node.js": "#339933",
    "MySQL": "#4479A1",
    "PostgreSQL": "#336791",
    "Other": "#666666",
}

# ─── Language-to-Source Routing ───────────────────────────────
# Maps detected language to SQL LIKE patterns for source column
LANGUAGE_SOURCE_MAP = {
    "Python":     ["%python%", "%docs.python.org%"],
    "JavaScript": ["%nodejs%", "%npmjs%", "%node.js%"],
    "TypeScript":  ["%typescript%", "%typescriptlang%"],
    "Rust":       ["%rust%", "%doc.rust-lang%", "%docs.rs%"],
    "Go":         ["%golang%", "%go.dev%", "%pkg.go.dev%"],
    "Ruby":       ["%ruby%"],
    "PHP":        ["%php%"],
    "Java":       ["%java%"],
    "Bash":       ["%bash%", "%gnu.org/software/bash%", "%help:%", "%tldp.org%"],
    "PowerShell": ["%powershell%", "%microsoft.com/powershell%"],
    "SQL":        ["%mysql%", "%mariadb%", "%postgresql%", "%postgres%", "%sqlite%"],
    "Docker":     ["%docker%"],
    "Kubernetes": ["%kubernetes%", "%k8s%"],
    "Nginx":      ["%nginx%"],
    "systemd":    ["%systemd%", "%freedesktop.org%"],
    "Git":        ["%git-scm%", "%git/%"],
    "Ansible":    ["%ansible%"],
    "Terraform":  ["%terraform%"],
    "Linux":      ["%linux%", "%man7.org%", "%sourceware.org%"],
    "CSS":        ["%css%", "%w3.org%"],
    "HTML":       ["%html%", "%w3.org%"],
}

# ─── Syntax Noise Filter (all 20 domains) ────────────────────
# These are language keywords, NOT searchable concepts.
# FTS5 matching "def" in "--output-def" or "i-def" is pure noise.
SYNTAX_NOISE = {
    # Universal
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'must', 'shall',
    'not', 'and', 'or', 'but', 'so', 'yet', 'nor',
    'if', 'else', 'elif', 'then', 'fi', 'end', 'done',
    'for', 'while', 'in', 'of', 'to', 'from', 'with', 'as',
    'true', 'false', 'null', 'none', 'nil', 'void', 'undefined',
    # Python
    'def', 'class', 'import', 'return', 'pass', 'break', 'continue',
    'try', 'except', 'finally', 'raise', 'with', 'yield', 'async',
    'await', 'lambda', 'global', 'nonlocal', 'assert', 'del',
    'self', 'cls', 'print', 'len', 'range', 'type', 'list', 'dict',
    'set', 'tuple', 'int', 'str', 'bool', 'float', 'bytes',
    # JavaScript / TypeScript
    'var', 'let', 'const', 'function', 'new', 'this', 'super',
    'typeof', 'instanceof', 'switch', 'case', 'default', 'throw',
    'catch', 'export', 'extends', 'implements', 'interface',
    'enum', 'abstract', 'static', 'readonly', 'public', 'private',
    'protected', 'string', 'number', 'boolean', 'any', 'never',
    'unknown', 'object', 'symbol', 'console', 'log', 'module',
    # Rust
    'fn', 'pub', 'mod', 'use', 'crate', 'extern', 'impl', 'trait',
    'struct', 'match', 'mut', 'ref', 'move', 'unsafe', 'where',
    'loop', 'Some', 'None', 'Ok', 'Err', 'unwrap', 'expect',
    # Go
    'func', 'package', 'chan', 'select', 'defer', 'go', 'map',
    'make', 'append', 'fmt', 'err', 'error', 'nil',
    # Ruby
    'puts', 'require', 'attr', 'begin', 'rescue', 'ensure',
    'unless', 'until', 'when', 'defined',
    # PHP
    'echo', 'isset', 'empty', 'unset', 'array', 'foreach',
    'include', 'namespace', 'php',
    # Java
    'void', 'main', 'args', 'System', 'out', 'println',
    'extends', 'implements', 'throws', 'final', 'native',
    # Shell / Bash
    'fi', 'esac', 'done', 'do', 'then', 'elif',
    'exit', 'shift', 'source', 'eval', 'exec',
    # SQL
    'select', 'insert', 'update', 'delete', 'create', 'alter',
    'drop', 'table', 'index', 'view', 'where', 'join', 'left',
    'right', 'inner', 'outer', 'group', 'order', 'having',
    'limit', 'offset', 'values', 'into', 'column',
    # Docker
    'run', 'cmd', 'copy', 'add', 'expose', 'env', 'arg',
    'workdir', 'volume', 'user', 'label', 'entrypoint',
    # Kubernetes
    'kind', 'spec', 'metadata', 'name', 'containers',
    'image', 'ports', 'replicas',
    # Nginx
    'server', 'location', 'upstream', 'listen', 'root',
    'proxy', 'http', 'events', 'worker',
    # Git
    'git', 'commit', 'push', 'pull', 'fetch', 'merge',
    'rebase', 'checkout', 'branch', 'remote', 'origin',
    # Ansible
    'hosts', 'tasks', 'roles', 'vars', 'handlers', 'become',
    'playbook', 'inventory',
    # Terraform
    'resource', 'variable', 'output', 'provider', 'data',
    'module', 'locals', 'terraform',
    # CSS / HTML
    'div', 'span', 'body', 'head', 'html', 'style', 'script',
    'color', 'background', 'margin', 'padding', 'display',
    'flex', 'grid', 'position', 'border', 'font',
}

# ─── Safety Classification ───────────────────────────────────
DANGEROUS_PATTERNS = [
    (r"\brm\s+-rf\b", "Recursive forced deletion — can destroy entire directory trees"),
    (r"\b(dd\s+if=|mkfs|fdisk|parted)\b", "Disk-level operations — can wipe drives"),
    (r"\b(chmod\s+777|chmod\s+-R\s+777)\b", "World-writable permissions — security risk"),
    (r"\b(eval|exec)\s*\(", "Dynamic code execution — injection risk if input is untrusted"),
    (r"\b(DROP\s+TABLE|DROP\s+DATABASE|TRUNCATE)\b", "Destructive database operation — data loss"),
    (r"\b(curl|wget).*\|\s*(bash|sh)\b", "Piping remote script to shell — arbitrary code execution risk"),
    (r">\s*/dev/sd[a-z]", "Writing directly to block device — will destroy filesystem"),
    (r"\b(:(){.*};)\b", "Fork bomb — will crash the system"),
]

SAFE_PATTERNS = [
    (r"^\s*(ls|pwd|whoami|hostname|date|uptime|cat|head|tail|wc|echo)\b", "Read-only / informational command"),
    (r"^\s*(git\s+(status|log|diff|branch))\b", "Read-only Git operation"),
    (r"^\s*(SELECT|SHOW|DESCRIBE|EXPLAIN)\b", "Read-only database query"),
    (r"^\s*(print|console\.log|puts|echo|fmt\.Println)\b", "Output/display operation"),
]


class BibleEngine:
    """Core engine for the The Coder's Bible knowledge base."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # ─── Language Detection ──────────────────────────────────
    # ─── Known CLI Binaries for Confidence Boosting ────────────
    # When the leading token of a snippet matches a known binary,
    # we apply a deterministic confidence floor of 0.70 — because
    # we KNOW what this is, even on short inputs.
    KNOWN_BINARIES = {
        # Shell / Unix
        'chmod': ('Bash', 'Changes file permissions (read/write/execute) for users, groups, or everyone.'),
        'chown': ('Bash', 'Changes the owner and/or group of a file or directory.'),
        'chgrp': ('Bash', 'Changes the group ownership of a file or directory.'),
        'mkdir': ('Bash', 'Creates a new directory (folder) at the specified path.'),
        'rmdir': ('Bash', 'Removes an empty directory.'),
        'cp': ('Bash', 'Copies files or directories from one location to another.'),
        'mv': ('Bash', 'Moves or renames files and directories.'),
        'rm': ('Bash', 'Deletes files or directories. Use with caution.'),
        'ls': ('Bash', 'Lists the contents of a directory.'),
        'cat': ('Bash', 'Displays the contents of a file.'),
        'grep': ('Bash', 'Searches for text patterns inside files.'),
        'awk': ('Bash', 'Processes and transforms structured text data.'),
        'sed': ('Bash', 'Edits text in a stream or file using pattern matching.'),
        'find': ('Bash', 'Searches for files and directories matching specified criteria.'),
        'tar': ('Bash', 'Creates or extracts compressed archive files.'),
        'curl': ('Bash', 'Transfers data to or from a server using URLs.'),
        'wget': ('Bash', 'Downloads files from the internet.'),
        'ssh': ('Bash', 'Opens a secure remote shell connection to another machine.'),
        'scp': ('Bash', 'Copies files securely between machines over SSH.'),
        'rsync': ('Bash', 'Synchronizes files between directories or machines efficiently.'),
        'sudo': ('Bash', 'Runs a command with administrator (root) privileges.'),
        'apt': ('Bash', 'Installs, updates, or removes packages on Debian/Ubuntu systems.'),
        'yum': ('Bash', 'Installs, updates, or removes packages on RHEL/CentOS systems.'),
        'dnf': ('Bash', 'Installs, updates, or removes packages on Fedora systems.'),
        'brew': ('Bash', 'Installs, updates, or removes packages on macOS.'),
        'pacman': ('Bash', 'Installs, updates, or removes packages on Arch Linux.'),
        'systemctl': ('Bash', 'Controls system services (start, stop, enable, disable).'),
        'journalctl': ('Bash', 'Views system logs from the journal.'),
        'crontab': ('Bash', 'Schedules commands to run automatically at specified times.'),
        'echo': ('Bash', 'Prints text to the terminal output.'),
        'export': ('Bash', 'Sets an environment variable for the current session.'),
        # Git
        'git': ('Git', 'Runs a Git version control operation.'),
        # Docker
        'docker': ('Docker', 'Runs a Docker container management command.'),
        'docker-compose': ('Docker', 'Manages multi-container Docker applications.'),
        # Kubernetes
        'kubectl': ('Kubernetes', 'Sends commands to a Kubernetes cluster.'),
        'helm': ('Kubernetes', 'Manages Kubernetes application packages (charts).'),
        # Python
        'python': ('Python', 'Runs a Python script or starts the Python interpreter.'),
        'python3': ('Python', 'Runs a Python 3 script or starts the Python 3 interpreter.'),
        'pip': ('Python', 'Installs or manages Python packages.'),
        'pip3': ('Python', 'Installs or manages Python 3 packages.'),
        # Node
        'node': ('JavaScript', 'Runs a JavaScript file in the Node.js runtime.'),
        'npm': ('JavaScript', 'Manages Node.js packages and runs scripts.'),
        'npx': ('JavaScript', 'Runs a Node.js package without installing it globally.'),
        'yarn': ('JavaScript', 'Manages Node.js packages (alternative to npm).'),
        # Rust
        'cargo': ('Rust', 'Builds, tests, or manages Rust projects and dependencies.'),
        'rustc': ('Rust', 'Compiles Rust source code into a binary.'),
        # Go
        'go': ('Go', 'Runs a Go toolchain command (build, run, test, etc.).'),
        # Terraform
        'terraform': ('Terraform', 'Manages infrastructure as code (plan, apply, destroy).'),
        # Ansible
        'ansible': ('Ansible', 'Runs Ansible automation tasks on remote machines.'),
        'ansible-playbook': ('Ansible', 'Executes an Ansible playbook for configuration management.'),
        # Nginx
        'nginx': ('Nginx', 'Controls the Nginx web server.'),
    }

    def detect_language(self, snippet: str) -> dict:
        """Detect the programming language/tool from a code snippet.
        Uses fingerprint pattern matching with rule-based confidence boosting
        for known CLI binaries to prevent underscoring short inputs."""
        scores = {}
        lines = snippet.strip().split("\n")

        # ── High-Signal Syntax Patterns ──
        # Patterns so definitive that matching even one guarantees a confidence floor.
        # These are NOT the same as KNOWN_BINARIES (which handle CLI commands).
        # These handle structural language syntax that is unambiguous.
        HIGH_SIGNAL_PATTERNS = {
            "Python": [
                r"^\s*def\s+\w+\s*\(.*\)\s*(->\s*\w+)?\s*:",    # def function():
                r"^\s*class\s+\w+(\(.*\))?\s*:",                  # class Foo(Bar):
                r"^\s*if\s+__name__\s*==\s*['\"]__main__['\"]",    # if __name__ == '__main__'
                r"^\s*(import|from)\s+\w+",                        # import/from
            ],
            "JavaScript": [
                r"^\s*function\s+\w+\s*\(",                        # function foo(
                r"^\s*(const|let|var)\s+\w+\s*=",                  # const x =
                r"\bconsole\.(log|warn|error|info)\s*\(",          # console.log(
                r"^\s*(module\.exports|export\s+(default|const|function|class))\b",
            ],
            "TypeScript": [
                r"^\s*interface\s+\w+",                            # interface Foo
                r"^\s*type\s+\w+\s*=",                             # type Foo =
                r":\s*(string|number|boolean|void|any|never|unknown)\b",
            ],
            "Rust": [
                r"^\s*fn\s+\w+\s*(<.*>)?\s*\(",                   # fn main(
                r"^\s*(pub|mod|use|impl|trait|struct|enum)\b",     # pub struct
                r"^\s*#\[(derive|cfg|test)\b",                     # #[derive(
            ],
            "Go": [
                r"^\s*func\s+(\(\w+\s+\*?\w+\)\s+)?\w+\s*\(",   # func main(
                r"^\s*package\s+\w+",                              # package main
            ],
            "SQL": [
                r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b",
            ],
            "Docker": [
                r"^\s*(FROM|RUN|CMD|ENTRYPOINT|COPY|ADD|EXPOSE|ENV|ARG|WORKDIR)\b",
            ],
            "Kubernetes": [
                r"^\s*apiVersion:\s*",                             # apiVersion:
                r"^\s*kind:\s*(Pod|Deployment|Service|ConfigMap|Secret|Ingress)\b",
            ],
            "Java": [
                r"^\s*(public|private|protected)\s+(static\s+)?(void|int|String|boolean)\s+\w+\s*\(",
                r"^\s*import\s+java\.",
            ],
            "PHP": [
                r"<\?php",                                         # <?php
            ],
            "Ruby": [
                r"\b(puts|require|require_relative|attr_accessor|attr_reader)\b",
            ],
        }

        for lang, patterns, priority in FINGERPRINTS:
            score = 0
            matched_patterns = []
            for pattern in patterns:
                for line in lines:
                    if re.search(pattern, line, re.IGNORECASE):
                        score += priority
                        matched_patterns.append(pattern)
                        break  # one match per pattern is enough
            if score > 0:
                # Base confidence from pattern density
                base_confidence = min(1.0, len(matched_patterns) / max(3, len(patterns) * 0.5))

                # High-signal boost: if any matched pattern is definitively identifying,
                # enforce a minimum confidence floor of 0.65
                high_sigs = HIGH_SIGNAL_PATTERNS.get(lang, [])
                has_high_signal = False
                if high_sigs:
                    for mp in matched_patterns:
                        for hs in high_sigs:
                            if mp == hs:
                                has_high_signal = True
                                break
                        if has_high_signal:
                            break

                if has_high_signal:
                    base_confidence = max(base_confidence, 0.65)

                scores[lang] = {
                    "score": score,
                    "matches": len(matched_patterns),
                    "matched_patterns": matched_patterns,
                    "total_patterns": len(patterns),
                    "confidence": base_confidence
                }

        # ── Rule-based binary boost ──
        # Extract leading token to check against known binaries
        first_line = snippet.strip().split("\n")[0].strip()
        # Strip leading shebang, comments, sudo
        clean_first = re.sub(r'^(#!.*\n|\s*sudo\s+)', '', first_line).strip()
        lead_token = clean_first.split()[0] if clean_first.split() else ''
        # Normalize: strip paths like /usr/bin/chmod -> chmod
        lead_token = lead_token.rsplit('/', 1)[-1].lower()

        binary_hit = self.KNOWN_BINARIES.get(lead_token)
        if binary_hit:
            binary_lang, binary_summary = binary_hit
            # Boost: if this language already matched, raise its confidence floor
            if binary_lang in scores:
                scores[binary_lang]["confidence"] = max(
                    scores[binary_lang]["confidence"], 0.70
                )
            else:
                # Inject a synthetic match for the known binary
                scores[binary_lang] = {
                    "score": 10,
                    "matches": 1,
                    "matched_patterns": [f"binary:{lead_token}"],
                    "total_patterns": 1,
                    "confidence": 0.75
                }

        if not scores:
            return {
                "language": "Unknown",
                "confidence": 0,
                "confidence_label": "UNVERIFIED",
                "reasoning": "No structural or semantic syntax signatures were detected.",
                "context": "Agnostic",
                "color": "#666666",
                "alternatives": []
            }

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
        primary = ranked[0]
        confidence = round(primary[1]["confidence"], 2)
        
        # Confidence label mapping
        if confidence >= 0.8:
            conf_label = "HIGH_AUTHORITY"
        elif confidence >= 0.5:
            conf_label = "VERIFIED_DOMAIN"
        else:
            conf_label = "LOW_CONFIDENCE"
            
        reasoning = f"Matched {primary[1]['matches']} deterministic syntax fingerprints (e.g., {primary[1]['matched_patterns'][0]})." if primary[1]['matches'] else "Inferred via secondary heuristics."
        
        # Context Mapping
        context_map = {
            "Python": "Standard Library / CPython",
            "Bash": "Unix Shell Environment",
            "PowerShell": "Windows Management Framework",
            "SQL": "Relational Database Engine",
            "JavaScript": "Browser Engine / Node.js Runtime",
            "Docker": "Container Daemon",
            "Kubernetes": "Cluster Control Plane",
            "Git": "Version Control System",
            "Rust": "Rustc Compilation Environment"
        }

        return {
            "language": primary[0],
            "confidence": confidence,
            "confidence_label": conf_label,
            "reasoning": reasoning,
            "context": context_map.get(primary[0], f"{primary[0]} Runtime Environment"),
            "color": DOMAIN_COLORS.get(primary[0], "#C9A84C"),
            "alternatives": [
                {"language": lang, "confidence": round(data["confidence"], 2)}
                for lang, data in ranked[1:4]
            ]
        }

    # ─── Safety Check ────────────────────────────────────────
    # Grounded safety descriptions — actionable, not abstract.
    SAFETY_CONTEXT = {
        'chmod': 'This command modifies file permissions. Safe in most cases, but ensure the file is trusted before executing.',
        'chown': 'This changes file ownership. Requires appropriate privileges and affects who can access the file.',
        'chgrp': 'This changes group ownership of a file. Safe when targeting known files.',
        'rm': 'This deletes files. Double-check the target path before running — deletion is usually permanent.',
        'mv': 'This moves or renames files. The original location will no longer contain the file.',
        'cp': 'This copies files. Safe operation — originals are preserved.',
        'mkdir': 'This creates a new directory. Safe, non-destructive operation.',
        'git': 'This is a Git version control operation. Most Git commands are safe and reversible.',
        'docker': 'This runs a Docker container command. Container changes are isolated from your host system.',
        'kubectl': 'This sends a command to a Kubernetes cluster. Verify you are targeting the correct cluster and namespace.',
        'pip': 'This installs or manages Python packages. Packages are installed into your current environment.',
        'pip3': 'This installs or manages Python packages. Packages are installed into your current environment.',
        'npm': 'This manages Node.js packages. Packages are installed into the project or global directory.',
        'yarn': 'This manages Node.js packages. Packages are installed into the project directory.',
        'apt': 'This installs or modifies system packages. May require sudo and affects system-wide state.',
        'brew': 'This installs or manages macOS packages. Packages install into the Homebrew prefix directory.',
        'sudo': 'This runs the following command with elevated privileges. Ensure you trust the operation before proceeding.',
        'curl': 'This transfers data to/from a URL. Safe for reading; inspect the response before piping to other commands.',
        'wget': 'This downloads a file from the internet. Verify the URL is from a trusted source.',
        'ssh': 'This opens a secure shell connection. Ensure the target host is trusted.',
        'systemctl': 'This controls system services. Starting/stopping services affects system behavior.',
        'terraform': 'This manages cloud infrastructure. Plan first — apply changes can create or destroy real resources.',
        'ansible': 'This runs automation tasks on remote machines. Changes will be applied to the targeted hosts.',
        'ansible-playbook': 'This executes an Ansible playbook. Changes will be applied to the targeted hosts.',
        'cargo': 'This manages a Rust project. Build and test operations are safe; publish is permanent.',
        'go': 'This runs a Go toolchain command. Build and test operations are safe.',
        'node': 'This runs JavaScript in Node.js. The script will have access to your filesystem.',
        'python': 'This runs a Python script. The script will have access to your filesystem.',
        'python3': 'This runs a Python 3 script. The script will have access to your filesystem.',
    }

    def check_safety(self, snippet: str) -> dict:
        """Evaluate snippet safety with grounded, actionable descriptions."""
        warnings = []
        for pattern, desc in DANGEROUS_PATTERNS:
            if re.search(pattern, snippet, re.IGNORECASE):
                warnings.append({"level": "danger", "message": desc})

        safe_notes = []
        for pattern, desc in SAFE_PATTERNS:
            if re.search(pattern, snippet, re.IGNORECASE):
                safe_notes.append(desc)

        if warnings:
            return {"level": "DESTRUCTIVE", "warnings": warnings, "safe_notes": []}
        elif safe_notes:
            return {"level": "SAFE", "warnings": [], "safe_notes": safe_notes}
        else:
            # Generate grounded context instead of abstract warning
            first_line = snippet.strip().split("\n")[0].strip()
            clean = re.sub(r'^\s*sudo\s+', '', first_line).strip()
            lead = clean.split()[0].rsplit('/', 1)[-1].lower() if clean.split() else ''
            grounded = self.SAFETY_CONTEXT.get(lead,
                'This operation does not match any known safe or dangerous pattern. '
                'Review the command and verify the target before executing.'
            )
            return {"level": "CAUTION", "warnings": [], "safe_notes": [grounded]}

    # ─── FTS5 Search ─────────────────────────────────────────
    def _format_tier(self, raw_tier: str) -> str:
        t = (raw_tier or "").upper()
        if "A" in t or "OFFICIAL" in t:
            return "Tier A (Official)"
        elif "B" in t or "MAN" in t:
            return "Tier B (Man Pages)"
        elif "C" in t or "DERIVED" in t:
            return "Tier C (Derived/Community)"
        return "Tier C (Derived)"

    def search(self, query: str, limit: int = 20, language: str = None) -> list:
        """Search the Bible via FTS5 with optional language-domain filtering."""
        clean_query = self._sanitize_fts_query(query)
        if not clean_query:
            return []

        # If language is detected, run a two-tier search:
        #   Tier 1: domain-matched results (prioritized)
        #   Tier 2: global FTS results (fallback)
        results = []
        seen_ids = set()

        if language and language in LANGUAGE_SOURCE_MAP:
            domain_results = self._search_domain(clean_query, language, limit)
            for r in domain_results:
                if not r.get("tier"):
                    r["tier"] = self._map_source_to_tier(r.get("source", ""))
                results.append(r)
                seen_ids.add(r["id"])

        # Global FTS search for remaining slots
        remaining = limit - len(results)
        if remaining > 0:
            global_results = self._search_fts(clean_query, remaining + 10)
            for r in global_results:
                if r["id"] not in seen_ids:
                    results.append(r)
                    seen_ids.add(r["id"])
                    if len(results) >= limit:
                        break

        return results[:limit]

    def _search_domain(self, fts_query: str, language: str, limit: int) -> list:
        """Search FTS5 filtered to a specific language domain."""
        patterns = LANGUAGE_SOURCE_MAP.get(language, [])
        if not patterns:
            return []

        # Build source filter
        source_clauses = " OR ".join([f"f.source LIKE ?" for _ in patterns])
        try:
            cursor = self.conn.execute(f"""
                SELECT f.id, f.content, f.source, f.tier, rank
                FROM bible_fts fts
                JOIN fragments f ON f.rowid = fts.rowid
                WHERE bible_fts MATCH ?
                  AND ({source_clauses})
                ORDER BY rank
                LIMIT ?
            """, (fts_query, *patterns, limit))
            return [
                {
                    "id": row["id"],
                    "content": row["content"][:500],
                    "source": row["source"],
                    "tier": row["tier"] if row["tier"] else self._map_source_to_tier(row["source"]),
                    "relevance": round(abs(row["rank"]), 4)
                }
                for row in cursor
            ]
        except sqlite3.OperationalError:
            return []

    def _map_source_to_tier(self, source: str) -> str:
        """Deterministically map source URLs to evidence tiers."""
        source_lower = source.lower()
        if any(x in source_lower for x in ["docs.python.org", "developer.mozilla.org", "man7.org", "gnu.org", "postgresql.org/docs"]):
            return "Official"
        elif any(x in source_lower for x in ["man page", "man", "tldr"]):
            return "Man"
        else:
            return "Derived"

    def _search_fts(self, fts_query: str, limit: int) -> list:
        """Raw FTS5 search without domain filter."""
        try:
            cursor = self.conn.execute("""
                SELECT f.id, f.content, f.source, f.tier, rank
                FROM bible_fts fts
                JOIN fragments f ON f.rowid = fts.rowid
                WHERE bible_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (fts_query, limit))
            return [
                {
                    "id": row["id"],
                    "content": row["content"][:500],
                    "source": row["source"],
                    "tier": row["tier"],
                    "relevance": round(abs(row["rank"]), 4)
                }
                for row in cursor
            ]
        except sqlite3.OperationalError:
            return []

    def _fallback_search(self, query: str, limit: int) -> list:
        """LIKE-based fallback if FTS5 query fails."""
        cursor = self.conn.execute("""
            SELECT id, content, source, tier
            FROM fragments
            WHERE content LIKE ? OR source LIKE ?
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        return [
            {
                "id": row["id"],
                "content": row["content"][:500],
                "source": row["source"],
                "tier": self._format_tier(row["tier"]),
                "relevance": 0.5
            }
            for row in cursor
        ]

    def _sanitize_fts_query(self, query: str) -> str:
        """Clean a query string for FTS5 safety — strips syntax noise."""
        tokens = re.findall(r'[a-zA-Z_][\w]*', query)
        if not tokens:
            return ""
        # Filter out syntax noise across all languages
        meaningful = [t for t in tokens if t.lower() not in SYNTAX_NOISE and len(t) > 1]
        if not meaningful:
            # If ALL tokens were noise, use original (avoid empty query)
            meaningful = [t for t in tokens if len(t) > 2][:3]
        if not meaningful:
            return ""
        return " OR ".join(meaningful[:10])

    # ─── Extract Keywords from Snippet ───────────────────────
    def extract_keywords(self, snippet: str) -> list:
        """Extract searchable keywords from a code snippet.
        Strips all syntax keywords from every supported language."""
        # Remove comments and string literals
        cleaned = re.sub(r'#.*$', '', snippet, flags=re.MULTILINE)
        cleaned = re.sub(r'//.*$', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'["\'].*?["\']', '', cleaned)

        # Extract identifiers
        tokens = re.findall(r'[a-zA-Z_][\w.]*', cleaned)

        meaningful = []
        seen = set()
        for token in tokens:
            lower = token.lower()
            if lower not in SYNTAX_NOISE and lower not in seen and len(token) > 1:
                meaningful.append(token)
                seen.add(lower)

        return meaningful[:15]

    # ─── Concept Extraction ────────────────────────────────────
    CONCEPT_PATTERNS = [
        (r'\b(\w+)\s*\(.*\b\1\b', 'recursion'),
        (r'\bfor\b.*\bin\b|\bwhile\b', 'iteration loop'),
        (r'\bclass\b.*\(.*\)', 'inheritance'),
        (r'\btry\b.*\b(except|catch)\b', 'error handling exception'),
        (r'\basync\b|\bawait\b', 'asynchronous concurrency'),
        (r'\blambda\b|=>', 'lambda anonymous function'),
        (r'\bsort\b|\bsorted\b', 'sorting algorithm'),
        (r'\b(open|read|write|close)\s*\(', 'file io'),
        (r'\b(get|post|put|delete|fetch|request)\b', 'http request api'),
        (r'\b(connect|cursor|execute|query)\b', 'database query'),
        (r'\b(import|require|use|include)\b.*\b(json|yaml|xml|csv)\b', 'serialization parsing'),
        (r'\b(re\.|regex|match|search|findall)\b', 'regular expression pattern'),
        (r'\b(thread|process|pool|concurrent|parallel)\b', 'concurrency threading'),
        (r'\b(socket|listen|bind|accept)\b', 'networking socket'),
        (r'\b(encrypt|decrypt|hash|hmac|sha|md5)\b', 'cryptography security'),
        (r'\b(test|assert|expect|mock)\b', 'testing unit test'),
    ]

    def decompose_snippet(self, snippet: str) -> list:
        """Decompose the snippet into semantic chunks (Breakdown)."""
        breakdown = []
        lines = snippet.strip().split("\n")
        
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            
            matched_concept = None
            for pattern, concept in self.CONCEPT_PATTERNS:
                if re.search(pattern, line_str, re.IGNORECASE):
                    matched_concept = concept
                    break
                    
            if matched_concept:
                breakdown.append({"code": line_str, "concept": matched_concept.title()})
            elif len(line_str) > 3 and not line_str.startswith(("#", "//", "/*")):
                breakdown.append({"code": line_str, "concept": "Operation / Declaration"})
        
        return breakdown

    def _extract_concepts(self, snippet: str) -> list:
        """Extract high-level programming concepts from code structure."""
        concepts = []
        for pattern, concept in self.CONCEPT_PATTERNS:
            if re.search(pattern, snippet, re.IGNORECASE | re.DOTALL):
                concepts.append(concept)
        return concepts

    # ─── Full Analysis ───────────────────────────────────────
    def analyze(self, snippet: str) -> dict:
        """Full analysis pipeline: detect language, extract keywords,
        search Bible with domain-aware routing."""
        if not snippet or not snippet.strip():
            return {"error": "Empty input"}

        # 1. Detect language
        detection = self.detect_language(snippet)
        detected_lang = detection["language"]
        lang_param = detected_lang if detected_lang != "Unknown" else None

        # 2. Extract keywords (syntax noise already filtered)
        keywords = self.extract_keywords(snippet)

        # 3. Extract concepts from code structure
        concepts = self._extract_concepts(snippet)

        # 4. Build search query — keywords + concepts
        search_terms = keywords[:6] + concepts[:3]
        search_query = " OR ".join(search_terms) if search_terms else ""
        results = self.search(search_query, limit=15, language=lang_param) if search_query else []

        # 5. If few results, also search with syntax terms inside domain
        #    (e.g., "def" is noise globally but relevant in Python docs)
        if len(results) < 5 and lang_param:
            raw_tokens = re.findall(r'[a-zA-Z_][\w]*', snippet)
            syntax_in_domain = [t for t in raw_tokens if t.lower() in SYNTAX_NOISE and len(t) > 2]
            if syntax_in_domain:
                # Combine with meaningful keywords for domain-specific search
                domain_q = " OR ".join(list(set(syntax_in_domain))[:5] + keywords[:3])
                domain_results = self._search_domain(
                    self._sanitize_fts_query(domain_q) or domain_q,
                    lang_param, 10
                )
                seen = {r["id"] for r in results}
                for r in domain_results:
                    if r["id"] not in seen:
                        results.append(r)
                        seen.add(r["id"])

        # 6. Final fallback: raw identifiers > 3 chars
        if not results:
            raw_tokens = re.findall(r'[a-zA-Z_][\w]*', snippet)
            raw_meaningful = [t for t in raw_tokens if len(t) > 3][:5]
            if raw_meaningful:
                fallback_q = " OR ".join(raw_meaningful)
                results = self.search(fallback_q, limit=10, language=lang_param)

        # 7. Safety check
        safety = self.check_safety(snippet)

        # 8. Compile first line summary
        first_line = snippet.strip().split("\n")[0].strip()
        if len(first_line) > 80:
            first_line = first_line[:77] + "..."

        # 9. Quick Understanding — one-line plain-English explanation
        quick_understanding = self._generate_quick_understanding(
            snippet, detected_lang, first_line
        )

        return {
            "input": first_line,
            "language": detection,
            "safety": safety,
            "keywords": keywords + concepts,
            "breakdown": self.decompose_snippet(snippet),
            "quick_understanding": quick_understanding,
            "results": results[:15],
            "result_count": len(results),
            "total_fragments": self._get_total_count(),
        }

    def _generate_quick_understanding(self, snippet: str, lang: str, first_line: str) -> str:
        """Generate a one-line plain-English explanation of what the snippet does.
        Uses known binary summaries first, then falls back to decomposition."""
        # 1. Check known binary — instant clarity
        clean = re.sub(r'^\s*(#!.*\n|\s*sudo\s+)', '', snippet.strip()).strip()
        tokens = clean.split()
        lead = tokens[0].rsplit('/', 1)[-1].lower() if tokens else ''

        binary_hit = self.KNOWN_BINARIES.get(lead)
        if binary_hit:
            _, base_summary = binary_hit
            # Enhance with specific arguments if available
            return self._enhance_binary_summary(lead, tokens, base_summary)

        # 2. Multi-line: summarize by concept pattern count
        lines = snippet.strip().split('\n')
        if len(lines) == 1:
            return f"A single {lang or 'code'} statement."

        concepts_found = set()
        for line in lines:
            for pattern, concept in self.CONCEPT_PATTERNS:
                if re.search(pattern, line.strip(), re.IGNORECASE):
                    concepts_found.add(concept)
                    break

        if concepts_found:
            concept_list = ', '.join(sorted(concepts_found)[:3])
            return f"A {lang} snippet covering {concept_list} across {len(lines)} lines."

        return f"A {len(lines)}-line {lang or 'code'} snippet."

    def _enhance_binary_summary(self, binary: str, tokens: list, base: str) -> str:
        """Add argument-specific detail to a known binary's summary."""
        args = tokens[1:] if len(tokens) > 1 else []
        if not args:
            return base

        if binary == 'chmod':
            # e.g. chmod +x deploy.sh -> "Makes deploy.sh executable so it can be run as a script."
            flags = [a for a in args if a.startswith(('+', '-')) or a.isdigit()]
            files = [a for a in args if not a.startswith(('-', '+')) and not a.isdigit()]
            if '+x' in flags and files:
                return f"Makes {files[-1]} executable so it can be run as a script."
            elif '777' in ' '.join(flags):
                return f"Sets full read/write/execute permissions for everyone on {files[-1] if files else 'the target'}."
            elif files:
                return f"Changes file permissions on {files[-1]}."
        elif binary == 'git':
            sub = args[0] if args else ''
            sub_map = {
                'clone': f"Downloads a copy of a remote repository to your machine.",
                'commit': f"Saves your staged changes as a new commit in the repository.",
                'push': f"Uploads your local commits to the remote repository.",
                'pull': f"Downloads and merges remote changes into your current branch.",
                'add': f"Stages files for the next commit.",
                'status': f"Shows which files have been modified, staged, or are untracked.",
                'log': f"Displays the commit history of the repository.",
                'diff': f"Shows the differences between your working files and the last commit.",
                'merge': f"Combines another branch's changes into your current branch.",
                'rebase': f"Replays your commits on top of another branch's history.",
                'checkout': f"Switches to a different branch or restores files.",
                'branch': f"Lists, creates, or deletes branches.",
                'stash': f"Temporarily saves uncommitted changes so you can work on something else.",
                'reset': f"Undoes commits or unstages files, depending on the flags used.",
                'init': f"Creates a new Git repository in the current directory.",
                'fetch': f"Downloads remote changes without merging them.",
                'tag': f"Creates a named marker for a specific commit (like a version label).",
                'remote': f"Manages the list of remote repositories linked to this project.",
            }
            return sub_map.get(sub, f"Runs a Git '{sub}' operation.")
        elif binary == 'docker':
            sub = args[0] if args else ''
            sub_map = {
                'build': 'Builds a container image from a Dockerfile.',
                'run': 'Creates and starts a new container from an image.',
                'exec': 'Runs a command inside a running container.',
                'compose': 'Manages multi-container applications defined in docker-compose.yml.',
                'pull': 'Downloads a container image from a registry.',
                'push': 'Uploads a container image to a registry.',
                'ps': 'Lists currently running containers.',
                'stop': 'Stops a running container.',
                'rm': 'Removes a stopped container.',
                'logs': 'Shows the output logs of a container.',
                'images': 'Lists all downloaded container images.',
            }
            return sub_map.get(sub, f"Runs a Docker '{sub}' command.")
        elif binary == 'kubectl':
            sub = args[0] if args else ''
            sub_map = {
                'get': 'Retrieves information about Kubernetes resources.',
                'apply': 'Creates or updates resources from a configuration file.',
                'delete': 'Removes resources from the cluster.',
                'describe': 'Shows detailed information about a specific resource.',
                'logs': 'Displays logs from a container in a pod.',
                'exec': 'Runs a command inside a container in a pod.',
                'scale': 'Changes the number of replicas for a deployment.',
                'port-forward': 'Forwards a local port to a port on a pod.',
            }
            return sub_map.get(sub, f"Runs a kubectl '{sub}' operation on the cluster.")
        elif binary in ('pip', 'pip3'):
            sub = args[0] if args else ''
            if sub == 'install':
                pkgs = [a for a in args[1:] if not a.startswith('-')]
                if pkgs:
                    return f"Installs the Python package{'s' if len(pkgs)>1 else ''} {', '.join(pkgs[:3])}."
                return 'Installs Python packages.'
            elif sub == 'uninstall':
                return 'Removes a Python package from the current environment.'
            elif sub == 'freeze':
                return 'Lists all installed Python packages and their versions.'
        elif binary in ('npm', 'yarn'):
            sub = args[0] if args else ''
            if sub == 'install' or sub == 'add':
                pkgs = [a for a in args[1:] if not a.startswith('-')]
                if pkgs:
                    return f"Installs the package{'s' if len(pkgs)>1 else ''} {', '.join(pkgs[:3])} into the project."
                return 'Installs project dependencies from package.json.'
            elif sub == 'run':
                script = args[1] if len(args) > 1 else 'a'
                return f"Runs the '{script}' script defined in package.json."
            elif sub == 'init':
                return 'Creates a new package.json file for the project.'

        return base

    def _get_total_count(self) -> int:
        """Get total fragment count."""
        try:
            row = self.conn.execute("SELECT COUNT(*) as c FROM fragments").fetchone()
            return row["c"]
        except Exception:
            return 0

    # ─── Stats ───────────────────────────────────────────────
    def get_stats(self) -> dict:
        """Get Bible database statistics — uses canonical normalized source prefixes."""
        try:
            total = self._get_total_count()
            # NOTE: normalize_sources.py has rewritten source prefixes to canonical
            # labels (e.g. 'typescript/', 'ansible/', 'powershell/').  This CASE
            # statement checks canonical prefixes FIRST, then falls back to URL
            # pattern matching for any fragments not yet normalized.
            domains = self.conn.execute("""
                SELECT
                    CASE
                        -- ── Canonical normalized prefixes (post-normalize_sources.py) ──
                        WHEN source LIKE 'python/%'      OR source LIKE '%docs.python.org%'                      THEN 'Python'
                        WHEN source LIKE 'javascript/%'  OR source LIKE '%nodejs%' OR source LIKE '%npmjs%'      THEN 'JavaScript'
                        WHEN source LIKE 'typescript/%'  OR source LIKE '%typescriptlang%'                       THEN 'TypeScript'
                        WHEN source LIKE 'rust/%'        OR source LIKE '%doc.rust-lang%' OR source LIKE '%docs.rs%' THEN 'Rust'
                        WHEN source LIKE 'golang/%'      OR source LIKE '%go.dev%' OR source LIKE '%pkg.go.dev%' THEN 'Go'
                        WHEN source LIKE 'ruby/%'        OR source LIKE '%ruby%'                                 THEN 'Ruby'
                        WHEN source LIKE 'php/%'         OR source LIKE '%php.net%'                              THEN 'PHP'
                        WHEN source LIKE 'java/%'        AND source NOT LIKE '%javascript%'
                                                         AND source NOT LIKE '%typescript%'                      THEN 'Java'
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
            """).fetchall()

            # Filter out 'Other' if it's tiny (< 1% of total) — cosmetic cleanliness
            threshold = max(50, int(total * 0.005))
            filtered = [
                {"name": row["domain"], "count": row["count"],
                 "color": DOMAIN_COLORS.get(row["domain"], "#666")}
                for row in domains
                if row["count"] >= threshold or row["domain"] != "Other"
            ]

            return {
                "total_fragments": total,
                "domains": filtered,
            }
        except Exception as e:
            return {"error": str(e), "total_fragments": 0, "domains": []}

