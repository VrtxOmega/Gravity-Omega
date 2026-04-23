# Security Posture Scanner Dashboard Plan

## Goal
Build an HTML dashboard to scan the `gravity-omega-v2` project for common security vulnerabilities and display findings by severity.

## Steps
1.  **Create `security_scanner_plan.md`**: (This file)
2.  **Create `security_scanner.py`**: Main Python script to orchestrate the scan.
    *   Define regex patterns for each vulnerability type.
    *   Walk through `gravity-omega-v2` directory, filtering for `.py`, `.js`, `.env`, `.json` files (excluding `node_modules`, `.git`, `__pycache__`, etc.).
    *   For each file, apply detection logic for:
        *   Hardcoded secrets (CRITICAL): `sk-`, `ghp_`, `AIza`, `Bearer `, `password`, `secret`, `api_key`, `token` (with assignments).
        *   Sensitive files (HIGH): `.env`, `config.json` (if containing credentials), private keys.
        *   Exposed network bindings (MEDIUM): `host='0.0.0.0'`.
        *   Eval/exec usage (MEDIUM): `eval(`, `exec(`, `subprocess.run(..., shell=True)`.
        *   Missing input validation (MEDIUM): Basic detection for direct `request.args`, `req.query`, `req.body` usage in route handlers without obvious sanitization.
    *   Redact detected secret values (first 4 chars + '***').
    *   Aggregate findings by severity.
3.  **Create `dashboard_template.html`**: HTML structure with placeholders for dynamic data.
4.  **Generate `security_dashboard.html`**: `security_scanner.py` will read `dashboard_template.html`, inject the collected data, and save the final HTML.
5.  **Open `security_dashboard.html`**: Launch the generated dashboard in the browser.

## File Structure
- `C:\Veritas_Lab\gravity-omega-v2\security_scanner_plan.md`
- `C:\Veritas_Lab\gravity-omega-v2\security_scanner.py`
- `C:\Veritas_Lab\gravity-omega-v2\dashboard_template.html`
- `C:\Veritas_Lab\gravity-omega-v2\security_dashboard.html` (generated output)

## Exclusions
- `node_modules/`, `.git/`, `dist/`, `build/`, `__pycache__/`, `.venv/`, `venv/`, `.next/`, `out/`, `coverage/`, `*.min.js`
- Comments and import statements for secret detection.
