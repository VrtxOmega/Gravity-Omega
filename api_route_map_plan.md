# API Route Intelligence Map Plan

## Goal
Generate an HTML dashboard providing an intelligence map of API routes for `gravity-omega-v2`, including backend Flask routes, frontend JavaScript calls, and cross-reference analysis (auth/error coverage, dead endpoints, orphan calls).

## Steps

### 1. Backend Route Analysis (Pass 1)
- **Script**: `backend_analyzer.py`
- **Input**: `C:\Veritas_Lab\gravity-omega-v2\backend\web_server.py`
- **Output**: `api_routes_backend.json`
- **Details**:
    - Parse Flask `@app.route` decorators to extract URL pattern, HTTP method.
    - Extract Python function name and line number.
    - Scan function body (within 20 lines of route definition) for `try:` / `except` blocks to detect error handling.
    - Scan function body for authentication keywords (`token`, `auth`, `api_key`, `verify`, `hmac`).

### 2. Frontend Call Analysis (Pass 2)
- **Script**: `frontend_analyzer.py`
- **Input Directories**:
    - `C:\Veritas_Lab\gravity-omega-v2\renderer`
    - `C:\Veritas_Lab\gravity-omega-v2\omega`
- **Output**: `api_calls_frontend.json`
- **Details**:
    - Recursively find all `.js` files in specified directories.
    - Scan each `.js` file for `fetch(` and `axios.` calls.
    - Extract the URL endpoint from these calls.

### 3. Cross-Reference Analysis & HTML Dashboard Generation
- **Script**: `dashboard_generator.py`
- **Inputs**:
    - `api_routes_backend.json`
    - `api_calls_frontend.json`
    - `api_route_map_template.html` (HTML template for dashboard)
- **Output**: `api_route_map_dashboard.html`
- **Details**:
    - Load backend routes and frontend calls.
    - Calculate:
        - Total API surface area (count of backend routes).
        - Auth coverage (percentage of backend routes with auth checks).
        - Error handling coverage (percentage of backend routes with try/except).
        - Dead endpoints (backend routes not called by frontend).
        - Orphan calls (frontend calls not matching any backend route).
    - Populate `api_route_map_template.html` with the collected data and metrics.
    - Ensure VERITAS black-and-gold palette is used for styling.

### 4. Open Dashboard
- **Command**: `Start-Process "C:\Veritas_Lab\gravity-omega-v2\api_route_map_dashboard.html"`
- **Details**: Open the generated HTML file in the default web browser.