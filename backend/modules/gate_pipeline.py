"""
Omega Claw — 5-Gate Static Analysis Pipeline
==============================================
Deterministic. No LLM. No network. Pure AST + heuristic.

Gate 1 — SYNTAX:        Valid Python AST parse
Gate 2 — SECURITY:      Dangerous patterns (eval, exec, os.system, secrets)
Gate 3 — DEPENDENCIES:  All imports resolvable
Gate 4 — AUTHORIZATION: Structural policy checks
Gate 5 — BOUNDARY:      Size, complexity metrics

Each gate returns a GateResult(gate, verdict, detail).
Verdict is PASS, WARN, or FAIL.

IMPORTANT: This pipeline governs the FORGE EXIT.
Inside Antigravity scratch, Omega observes but does NOT restrict.
The whole purpose of Antigravity is unrestricted creation.
Gates fire ONLY on promotion / compile triggers.
"""

import ast
import hashlib
import importlib.util
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Tuple, Optional


# ══════════════════════════════════════════════════════════════
# GATE RESULT
# ══════════════════════════════════════════════════════════════

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


@dataclass(frozen=True)
class GateResult:
    """Immutable result from a single gate."""
    gate: str           # G1_SYNTAX, G2_SECURITY, etc.
    verdict: str        # PASS | WARN | FAIL
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ══════════════════════════════════════════════════════════════
# GATE 1 — SYNTAX (AST Parse)
# ══════════════════════════════════════════════════════════════

def gate_syntax(source: str, filename: str = "<code>") -> GateResult:
    """Parse source as Python AST. Fail if SyntaxError."""
    try:
        ast.parse(source, filename=filename)
        return GateResult(gate="G1_SYNTAX", verdict=PASS, detail="AST parse OK")
    except SyntaxError as e:
        return GateResult(
            gate="G1_SYNTAX", verdict=FAIL,
            detail=f"SyntaxError at line {e.lineno}: {e.msg}"
        )


# ══════════════════════════════════════════════════════════════
# GATE 2 — SECURITY SCAN
# ══════════════════════════════════════════════════════════════

# Dangerous built-in calls
_DANGEROUS_CALLS = {
    "eval", "exec", "compile", "__import__",
    "getattr",  # only flagged if used on os/sys/subprocess
}

# Dangerous module patterns
_DANGEROUS_PATTERNS = [
    # Shell injection
    re.compile(r"\bos\.system\s*\("),
    re.compile(r"\bos\.popen\s*\("),
    re.compile(r"\bsubprocess\.call\s*\(.*shell\s*=\s*True", re.DOTALL),
    re.compile(r"\bsubprocess\.Popen\s*\(.*shell\s*=\s*True", re.DOTALL),
    re.compile(r"\bsubprocess\.run\s*\(.*shell\s*=\s*True", re.DOTALL),

    # Code injection
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),

    # Network exfiltration (only outside Antigravity)
    re.compile(r"\brequests\.(get|post|put|delete|patch)\s*\("),
    re.compile(r"\burllib\.request\.urlopen\s*\("),
    re.compile(r"\bhttpx\.(get|post|put|delete|patch)\s*\("),
]

# Hardcoded secret patterns
_SECRET_PATTERNS = [
    re.compile(r"""(?:api[_-]?key|secret|token|password|passwd|credential)\s*=\s*['"][^'"]{8,}['"]""", re.IGNORECASE),
    re.compile(r"""['"](?:sk-|pk-|ghp_|gho_|AIza)[A-Za-z0-9_-]{20,}['"]"""),
    re.compile(r"""-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"""),
]


def gate_security(source: str) -> GateResult:
    """Scan for dangerous patterns + hardcoded secrets."""
    findings = []

    for i, pat in enumerate(_DANGEROUS_PATTERNS):
        matches = pat.findall(source)
        if matches:
            findings.append(f"DANGEROUS_PATTERN_{i}: {matches[0][:60]}")

    for pat in _SECRET_PATTERNS:
        matches = pat.findall(source)
        if matches:
            findings.append(f"HARDCODED_SECRET: {matches[0][:30]}...")

    if not findings:
        return GateResult(gate="G2_SECURITY", verdict=PASS, detail="No dangerous patterns")

    # Classify: secrets and shell injection are FAIL; others are WARN
    has_critical = any("SECRET" in f or "DANGEROUS_PATTERN_0" in f or
                       "DANGEROUS_PATTERN_1" in f for f in findings)
    verdict = FAIL if has_critical else WARN
    return GateResult(
        gate="G2_SECURITY", verdict=verdict,
        detail=f"{len(findings)} finding(s): " + "; ".join(findings[:5])
    )


# ══════════════════════════════════════════════════════════════
# GATE 3 — DEPENDENCY AUDIT
# ══════════════════════════════════════════════════════════════

# Standard library modules (Python 3.10+ subset) — extend as needed
_STDLIB_MODULES = {
    "abc", "argparse", "ast", "asyncio", "base64", "bisect", "builtins",
    "calendar", "cgi", "cmd", "codecs", "collections", "colorsys",
    "concurrent", "configparser", "contextlib", "copy", "csv", "ctypes",
    "dataclasses", "datetime", "decimal", "difflib", "dis", "email",
    "enum", "errno", "fcntl", "filecmp", "fnmatch", "fractions",
    "ftplib", "functools", "gc", "getpass", "gettext", "glob",
    "gzip", "hashlib", "heapq", "hmac", "html", "http", "importlib",
    "inspect", "io", "ipaddress", "itertools", "json", "keyword",
    "linecache", "locale", "logging", "lzma", "math", "mimetypes",
    "mmap", "msvcrt", "multiprocessing", "numbers", "operator", "os",
    "pathlib", "pdb", "pickle", "pkgutil", "platform", "plistlib",
    "posixpath", "pprint", "profile", "pstats", "pty", "pwd",
    "queue", "quopri", "random", "re", "readline", "reprlib",
    "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
    "selectors", "shelve", "shlex", "shutil", "signal", "site",
    "smtplib", "socket", "socketserver", "sqlite3", "ssl", "stat",
    "statistics", "string", "struct", "subprocess", "sys", "sysconfig",
    "syslog", "tabnanny", "tarfile", "tempfile", "termios", "test",
    "textwrap", "threading", "time", "timeit", "tkinter", "token",
    "tokenize", "tomllib", "trace", "traceback", "tracemalloc", "tty",
    "turtle", "types", "typing", "unicodedata", "unittest", "urllib",
    "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
    "winreg", "winsound", "wsgiref", "xml", "xmlrpc", "zipapp",
    "zipfile", "zipimport", "zlib", "_thread", "__future__",
}


def _extract_imports(source: str) -> List[str]:
    """Extract top-level imported module names from source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module.split(".")[0])
    return list(set(modules))


def gate_dependencies(source: str) -> GateResult:
    """Check all imports are resolvable (stdlib or installed)."""
    imports = _extract_imports(source)
    if not imports:
        return GateResult(gate="G3_DEPS", verdict=PASS, detail="No imports")

    unresolved = []
    for mod in imports:
        if mod in _STDLIB_MODULES:
            continue
        # Check if installable / findable
        spec = importlib.util.find_spec(mod)
        if spec is None:
            unresolved.append(mod)

    if not unresolved:
        return GateResult(gate="G3_DEPS", verdict=PASS,
                          detail=f"{len(imports)} imports, all resolved")
    return GateResult(
        gate="G3_DEPS", verdict=WARN,
        detail=f"Unresolved: {', '.join(unresolved)}"
    )


# ══════════════════════════════════════════════════════════════
# GATE 4 — AUTHORIZATION (Structural Policy)
# ══════════════════════════════════════════════════════════════

# Banned structural patterns for promoted code
_AUTH_BANNED = [
    # No file deletion in promoted code
    re.compile(r"\bos\.remove\s*\("),
    re.compile(r"\bos\.unlink\s*\("),
    re.compile(r"\bshutil\.rmtree\s*\("),
    # No environment variable mutation
    re.compile(r"\bos\.environ\["),
    re.compile(r"\bos\.putenv\s*\("),
    # No sys.exit in library code
    re.compile(r"\bsys\.exit\s*\("),
    re.compile(r"\bexit\s*\("),
]


def gate_authorization(source: str) -> GateResult:
    """Check structural authorization policies for promoted code."""
    violations = []
    for pat in _AUTH_BANNED:
        if pat.search(source):
            violations.append(pat.pattern[:40])

    if not violations:
        return GateResult(gate="G4_AUTH", verdict=PASS,
                          detail="No policy violations")

    return GateResult(
        gate="G4_AUTH", verdict=FAIL,
        detail=f"{len(violations)} violation(s): " + "; ".join(violations[:3])
    )


# ══════════════════════════════════════════════════════════════
# GATE 5 — BOUNDARY (Size + Complexity)
# ══════════════════════════════════════════════════════════════

MAX_FILE_LINES = 2000
MAX_FILE_BYTES = 200_000
MAX_FUNCTION_COUNT = 80
MAX_CYCLOMATIC_APPROX = 50   # per function


def _count_branches(node: ast.AST) -> int:
    """Approximate cyclomatic complexity for a function node."""
    count = 1  # base path
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            count += 1
        elif isinstance(child, ast.BoolOp):
            # each and/or adds a branch
            count += len(child.values) - 1
    return count


def gate_boundary(source: str) -> GateResult:
    """Check file size, function count, and complexity."""
    lines = source.count("\n") + 1
    size = len(source.encode("utf-8"))

    issues = []
    if lines > MAX_FILE_LINES:
        issues.append(f"lines={lines} > {MAX_FILE_LINES}")
    if size > MAX_FILE_BYTES:
        issues.append(f"bytes={size} > {MAX_FILE_BYTES}")

    try:
        tree = ast.parse(source)
        funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if len(funcs) > MAX_FUNCTION_COUNT:
            issues.append(f"functions={len(funcs)} > {MAX_FUNCTION_COUNT}")

        for fn in funcs:
            cc = _count_branches(fn)
            if cc > MAX_CYCLOMATIC_APPROX:
                issues.append(f"{fn.name}: cc={cc} > {MAX_CYCLOMATIC_APPROX}")
    except SyntaxError:
        pass  # G1 catches this

    if not issues:
        return GateResult(gate="G5_BOUNDARY", verdict=PASS,
                          detail=f"{lines} lines, {size} bytes")

    verdict = FAIL if any(">" in i for i in issues[:2]) else WARN
    return GateResult(
        gate="G5_BOUNDARY", verdict=verdict,
        detail="; ".join(issues[:5])
    )


# ══════════════════════════════════════════════════════════════
# FILE HASH
# ══════════════════════════════════════════════════════════════

def compute_file_hash(source: str) -> str:
    """SHA-256 of source content."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════
# FULL PIPELINE
# ══════════════════════════════════════════════════════════════

def run_gate_pipeline(source: str, filename: str = "<code>") -> Tuple[List[GateResult], str]:
    """Run the full 5-gate pipeline.

    Returns:
        (gate_results, file_hash)

    NOTE: This pipeline is for FORGE EXIT assessment only.
    Inside Antigravity, Omega is an observer — unbound, creative, free.
    The gates exist to classify code LEAVING the sandbox, not to restrict
    creation within it.
    """
    results: List[GateResult] = []

    # Gate 1: Syntax
    g1 = gate_syntax(source, filename)
    results.append(g1)

    # Gate 2: Security
    g2 = gate_security(source)
    results.append(g2)

    # Gate 3: Dependencies
    g3 = gate_dependencies(source)
    results.append(g3)

    # Gate 4: Authorization
    g4 = gate_authorization(source)
    results.append(g4)

    # Gate 5: Boundary
    g5 = gate_boundary(source)
    results.append(g5)

    file_hash = compute_file_hash(source)
    return results, file_hash
