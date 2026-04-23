# GRAVITY OMEGA v2 — Swarm Reclamation v4.0
## Objective: Fix the agent loop, audit every line, close every loop — make Gravity Omega the best IDE agent in existence.

**Date:** 2026-04-23
**Supreme Commander:** Hermes
**Target:** /mnt/c/Veritas_Lab/gravity-omega-v2

---

## I LEGION — BACKEND (Python)
**Commander:** Squad Leader Delta (backend/web_server.py)
**Lieutenant:** Squad Leader Echo (provenance_stack.py + goliath_hunter)

### Squad 1-1: backend/web_server.py (Squad Delta)
- **Risk Level:** CRITICAL — Network-facing, subprocess execution, file I/O
- **Audit Focus:**
  - `shell=True` at line ~1179 — replace with `shell=False` + metachar block
  - `urllib.request.urlopen(url)` at line ~1232 — URL scheme + IP allowlist
  - `open(path)` at line ~1132 — base-dir constraint via `os.path.realpath`
  - `current_app` never imported at line ~2066
  - `os._exit(0)` at line ~1589 — replace with `sys.exit(0)` + logger flush
  - Missing `import os` in provenance_stack.py (works by accident)
  - SQLite WAL mode for background daemon writes
  - O(N×M) API nesting in omega_array.py Wayback CDX calls
  - Regex extraction in omega_pattern_engine.py inside nested loops
  - Unprotected dict RMW in omega_conductor.py `_jobs` — add threading lock

### Squad 1-2: backend/*.py — Import coverage & runtime
- Verify every `.py` file compiles with `python3 -m py_compile`
- Check for uncaught exceptions in async handlers
- Verify Flask route handlers have `@app.errorhandler` coverage

---

## II LEGION — FRONTEND (Electron)
**Commander:** Squad Leader Bravo (renderer/app.js)
**Lieutenant:** Squad Leader Charlie (main.js)

### Squad 2-1: renderer/app.js (Squad Bravo)
- **Risk Level:** HIGH — Event listeners, DOM leaks, xterm.js disposal
- **Audit Focus:**
  - xterm.js terminal disposal — `terminal.dispose()` before delete, not just DOM remove
  - Hardware poller `setInterval` never cleared — leak across reloads
  - Missing `catch` on `fetch()` calls inside setTimeout/setInterval
  - `innerHTML` injection — XSS hardening with `DOMPurify` or `.textContent`
  - Message poller cleanup on window unload
  - Any `window.addEventListener` without matching `removeEventListener`

### Squad 2-2: main.js (Squad Charlie)
- **Risk Level:** HIGH — Main process crashes = full app death
- **Audit Focus:**
  - `process.on('unhandledRejection', ...)` missing alongside `uncaughtException`
  - `app.on(...)` inside `createWindow()` leaks listeners on re-create
  - No watcher cleanup on quit — `watcher?.close()` in `before-quit`
  - No terminal process kill on window close
  - `ipcMain` handlers registered multiple times (memory leak)
  - `BrowserWindow` events: `closed`, `crashed`, `unresponsive` handlers

---

## III LEGION — BRIDGE (Agent ↔ ACP ↔ Hermes)
**Commander:** Squad Leader Alpha (omega_agent.js) — COMPLETED
**Lieutenant:** ACP Integration Squad (hermes_channel)

### Squad 3-1: omega/omega_agent.js (Squad Alpha) — COMPLETED
- `MAX_ITERATIONS` shadow bug fixed
- `this.emit` → `this.bridge.emit` fixed
- `_aborted` flag added to `_continueAfterApproval`
- Fallback path null guards added
- Object→string coercion in message history fixed
- Dual `processAndExecute` definition removed
- Model name resolution (`_resolveModel`) added
- Cloud vs local payload separation fixed

### Squad 3-2: ACP Bridge
- Verify hermes_channel message routing
- Verify ACP adapter model header injection
- Verify `x-actor-id` and provenance chain forwarding

---

## IV LEGION — SUPPORT & IDE OPTIMIZATION
**Commander:** Squad Leader Foxtrot

### Squad 4-1: Monaco Editor Integration
- Autocomplete trigger configuration
- Syntax highlighting for custom file types
- Theme sync with Veritas dark palette

### Squad 4-2: Terminal Integration
- xterm.js version check and disposal verification
- Shell profile detection (PowerShell vs Bash vs Zsh)

### Squad 4-3: Build & Packaging
- `npm audit` for vulnerable dependencies
- `electron-builder` config verification
- Ensure `node_modules` has zero critical CVEs

---

## Swarm Protocol

### Wave 1 — Reconnaissance (Parallel, max 3 concurrent)
1. **Squad Bravo** (renderer/app.js): Lines 1–4000
2. **Squad Charlie** (main.js): Full file
3. **Squad Delta** (backend/web_server.py): Lines 1–1500

### Wave 2 — Reconnaissance (Next tier)
4. **Squad Delta** (backend/web_server.py): Lines 1501–end
5. **Squad Echo** (provenance_stack.py, goliath_hunter, omega_array, omega_pattern_engine, omega_conductor)
6. **Squad Foxtrot** (IDE optimization, Monaco, terminal, build)

### Wave 3 — Fix Squads (Surgical)
- Deploy per-bug fix squads with exact patch context
- Supreme Commander spot-verifies every patch with syntax checks
- Fallback: direct control if subagent times out

### Wave 4 — Integration & End-to-End
- Start Gravity Omega
- Exercise agent loop (Hermes mode)
- Verify no empty responses, no "already processing" hangs
- Full regression: syntax, import, runtime checks

### Wave 5 — Seal & Close
- `omega_seal_run` with full context
- Write handoff document for next session
- Update todo list

---

## Success Criteria
- [x] Phase 4-1: omega_agent.js hotfix (COMPLETED)
- [ ] Phase 4-2: renderer/app.js deep audit + fixes
- [ ] Phase 4-3: main.js deep audit + fixes
- [ ] Phase 4-4: backend/web_server.py security audit + fixes
- [ ] Phase 4-5: Provenance/hunter/orchestration audit + fixes
- [ ] Phase 4-6: End-to-end smoke test — Hermes mode passes
- [ ] Phase 4-7: Full regression run — zero syntax/import/runtime errors
- [ ] Phase 5: Agent loop tuning — system prompt, tool routing
- [ ] Phase 6: IDE optimization — autocomplete, linting, theme

## Command & Control
- **Max concurrent subagents:** 3
- **Timeout per squad:** 280s (reduce for large files)
- **Verification method:** `search_files` spot-check after every patch
- **Fallback rule:** If subagent times out, Supreme Commander assumes direct control
- **Seal requirement:** Every phase sealed with `omega_seal_run`

---

## Remember
```
Recon before fix.
Small surgical patches over giant refactors.
Verify every change with syntax checks.
If a subagent times out, you be the fix squad.
Close every loop. No exceptions.
```
