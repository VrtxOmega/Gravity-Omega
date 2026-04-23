# API Route Intelligence Map Plan

## Goal
Generate an API Route Intelligence Map for `gravity-omega-v2` by performing a two-pass cross-language analysis (Python backend, JavaScript frontend) and presenting the findings in a styled HTML dashboard.

## Phase 1: Backend Analysis (Python)
1.  **Script: `extract_flask_routes.py`**
    *   Read `C:\Veritas_Lab\gravity-omega-v2\backend\web_server.py`.
    *   Identify Flask route decorators (`@app.route(...)`).
    *   For each route, extract:
        *   URL pattern (e.g., `/api/status`)
        *   HTTP method (GET, POST, etc. - default to GET if not specified)
        *   Python function name
        *   Line number of the route decorator
        *   Presence of `try:` block within 20 lines of the function start (for error handling).
        *   Presence of authentication keywords (`token`, `auth`, `api_key`, `verify`, `hmac`) within the function body.
    *   Store extracted data in `backend_routes.json`.

## Phase 2: Frontend Analysis (JavaScript)
1.  **Script: `extract_frontend_calls.py`**
    *   Recursively scan `.js` files in `C:\Veritas_Lab\gravity-omega-v2\renderer` and `C:\Veritas_Lab\gravity-omega-v2\omega`.
    *   Exclude common dependency directories (`node_modules`, `.git`, `dist`, `build`, `__pycache__`, `.venv`, `venv`, `.next`, `out`, `coverage`).
    *   Identify `fetch(` and `axios.` calls.
    *   Extract the endpoint URL string from these calls. Focus on direct string literals for simplicity.
    *   Store extracted URLs in `frontend_calls.json`.

## Phase 3: Cross-Reference Analysis & Dashboard Generation
1.  **Template: `api_dashboard_template.html`**
    *   Create an HTML template file with placeholders for dynamic data.
    *   Apply VERITAS black-and-gold brand palette and styling rules.
2.  **Script: `generate_api_dashboard.py`**
    *   Load `backend_routes.json` and `frontend_calls.json`.
    *   Perform the following analyses:
        *   **Total API surface area:** Count of all backend routes.
        *   **Auth coverage:** Percentage of backend routes with authentication checks.
        *   **Error handling coverage:** Percentage of backend routes with `try/except`.
        *   **Dead endpoints:** List backend routes whose URL patterns are not matched by any frontend call.
        *   **Orphan calls:** List frontend call URLs that do not match any backend route pattern.
    *   Populate `api_dashboard_template.html` with the analysis results.
    *   Save the final dashboard as `api_intelligence_dashboard.html`.

## Phase 4: Output
1.  Open `api_intelligence_dashboard.html` in the browser for review.
