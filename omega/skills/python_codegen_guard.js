/**
 * PYTHON CODEGEN GUARD SKILL
 * Prevents common Python code-generation bugs when Omega generates scripts
 * for execution in WSL/Linux environments.
 *
 * Usage (from OmegaAgent):
 *   agent.skillManager.load('python_codegen_guard');
 *   // Injects Python codegen rules into system prompt.
 *
 * To unload:
 *   agent.skillManager.unload('python_codegen_guard');
 *
 * Created: 2026-05-03 — after HERMES_SHOWCASE crash analysis
 * Failure log:
 *   - Rule 1: `python` binary not found in WSL → use `python3`
 *   - Rule 2: CSS {braces} break Python .format() → use f-strings
 *   - Rule 3: CSV leading whitespace breaks DictReader → strip
 */

function getSkillText() {
    return `## [ACTIVE SKILL: PYTHON CODEGEN GUARD] When generating Python code for execution, follow these environment-aware rules without exception.

### Rule 1: Use python3 or sys.executable — NEVER bare "python"
This environment is Linux/WSL. "python" may not exist in PATH.
- CORRECT: subprocess.run(["python3", "-c", "..."])
- CORRECT: subprocess.run([sys.executable, "-c", "..."])
- WRONG: subprocess.run(["python", "-c", "..."])  # WILL FAIL

### Rule 2: Never use .format() on strings containing CSS/HTML
Python's str.format() treats { } as placeholder markers. CSS properties
like {font-family} or {background: #fff} will crash.
- CORRECT: f-strings with double braces: f"... style {{ color: red; }} ... {var}"
- CORRECT: .replace("{token}", value)
- WRONG: "... style { color: red; } ...".format(timestamp=ts)  # WILL CRASH

### Rule 3: Strip leading whitespace from embedded CSV/TSV data
Triple-quoted strings with leading newlines poison csv.DictReader headers.
- CORRECT:
    data = """product,sales,region
    tool_a,1500,north"""
- WRONG:
    data = """
    product,sales,region    # <-- leading \n breaks header parsing
    tool_a,1500,north"""

### Rule 4: Use os.path.join() — never hardcoded backslash paths
This is a WSL/Linux filesystem. Windows-style paths fail.
- CORRECT: path = os.path.join(os.path.dirname(__file__), "data")
- WRONG: path = "C:\\\\Users\\\\rlope\\\\Desktop\\\\hermes_demo"

### Rule 5: Always os.makedirs(path, exist_ok=True) before writing files
Don't assume directories exist. Create them defensively.

These rules are non-negotiable. Violating any of them causes immediate runtime failure.`;
}

module.exports = { name: 'python_codegen_guard', getSkillText };
