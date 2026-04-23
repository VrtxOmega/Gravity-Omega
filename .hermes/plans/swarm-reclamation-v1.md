# GRAVITY OMEGA — SWARM RECLAMATION v1.0
## Supreme Commander: Hermes / Rage Ω
## Objective: Audit every line, optimize IDE, close every loop, achieve deterministic execution

---

## I LEGION — BACKEND (Python)
### Squad 1-1: web_server.py
- Audit all Flask/FastAPI routes, middleware, CORS, auth boundaries
- Check for SSRF, command injection, path traversal
- Verify error handlers return structured JSON
- Verify graceful shutdown / SIGTERM handling

### Squad 1-2: provenance_stack.py + omega_seal_run.py
- Audit seal/ledger logic, SHA-256 chain integrity
- Verify session logging doesn't corrupt on concurrent access
- Check SQLite transaction boundaries

### Squad 1-3: omega_sentinel.py
- Audit auth, token validation, rate limiting
- Verify no hardcoded secrets or bypass paths
- Check JWT/secret lifecycle

### Squad 1-4: vtp_codec.py
- Audit VTP protocol codec for buffer overflows / malformed packet handling
- Verify encode/decode round-trip determinism

### Squad 1-5: goliath_hunter/ (6 modules)
- omega_break_layer, omega_lead_fetcher, omega_dossier, omega_province, omega_pattern_engine, omega_array, omega_conductor
- Audit for race conditions, unhandled exceptions, memory leaks
- Verify hunter orchestration (conductor → array → province)

### Squad 1-6: remaining modules (audit_ledger, recursive_evolution_engine, state_monitor, morning_brief)
- Verify module imports don't circular-reference
- Check thread safety for background monitors

## II LEGION — FRONTEND (Electron / Renderer)
### Squad 2-1: main.js
- Audit Electron main process: window lifecycle, IPC registration, menu bar, tray
- Verify no memory leaks in window recreation
- Check secondary window / popup handling

### Squad 2-2: preload.js
- Audit context isolation, exposed APIs, no privilege escalation
- Verify every exposed function has a corresponding main.js handler

### Squad 2-3: renderer/app.js (lines 1–4000)
- Audit UI state management, DOM rendering, chat panel
- Verify message streaming handles partial JSON correctly
- Check event listener cleanup

### Squad 2-4: renderer/app.js (lines 4001–8000)
- Audit file explorer, editor tabs, tab switching
- Verify Monaco instance lifecycle (dispose on tab close)
- Check for editor state desync

### Squad 2-5: renderer/app.js (lines 8001–end)
- Audit terminal panel, settings panel, music player
- Verify xterm.js / node-pty integration
- Check theme application consistency

### Squad 2-6: renderer/index.html + styles/omega.css + veritas_lab/index.html
- Audit DOM structure, CSS variables for theming
- Verify responsive layout breakpoints
- Check accessibility (keyboard nav, focus states)

## III LEGION — BRIDGE (Omega ↔ ACP)
### Squad 3-1: omega/omega_agent.js
- Audit _hermesGenerate, retry loops, tool_call conversion
- Verify MAX_ITERATIONS shadow bug (line ~1615)
- Check error recovery: stopHermes/startHermes doesn't deadlock
- Verify conversation history truncation logic

### Squad 3-2: omega/omega_bridge.js
- Audit inter-layer bridge: backend ↔ frontend message routing
- Verify no message loss on high-frequency events
- Check event emitter cleanup

### Squad 3-3: omega/hermes_channel.js (post-patch verification)
- Verify our Phase 2 fixes are semantically correct
- Audit remaining notification types: delta, status, error
- Verify _send timeout handling
- Check subprocess lifecycle (kill, spawn, stderr drain)

### Squad 3-4: ACP Adapter (server.py, session.py, entry.py)
- Post-patch verification: confirm fixes work under load
- Audit entry.py for subprocess spawn args / env propagation
- Verify session cache eviction doesn't leak memory
- Check JSON-RPC parse error handling (malformed requests)

## IV LEGION — SUPPORT (IDE Optimization)
### Squad 4-1: Monaco Editor
- Verify dark+gold theme is applied consistently
- Check language support (JS, Python, CSS, HTML, JSON, MD)
- Audit editor options: minimap, font ligatures, scrollbar
- Verify IntelliSense / diagnostics integration

### Squad 4-2: Terminal (node-pty + xterm.js)
- Verify pty process spawning, cwd tracking, env propagation
- Check terminal resize handling
- Audit scrollback buffer limits
- Verify color theme matches IDE dark+gold

### Squad 4-3: File Watcher (chokidar)
- Audit watcher initialization on project open
- Verify debounced change events (no thrashing)
- Check watcher cleanup on project switch / window close
- Verify symlink handling

### Squad 4-4: Performance & Profiling
- Run startup time analysis (main → renderer interactive)
- Profile renderer memory: check for detached DOM nodes
- Audit app.js bundle size (if bundled) or script load order
- Identify heavy synchronous operations in main thread

## V LEGION — INTEGRATION (End-to-End)
### Squad 5-1: Hermes Mode E2E
- Start Gravity Omega, switch to Hermes ACP
- Send "Create a test file in /tmp/gravity_test.txt"
- Verify file created, response contains confirmation
- Send second prompt referencing the file
- Verify stateful conversation works (no empty response)

### Squad 5-2: VERITAS Pipeline
- Verify omega_seal_run.py produces valid seal hashes
- Check provenance_stack logs every session modification
- Run a seal, verify chain link is unbroken

---

## Swarm Protocol
1. **Wave 1**: Deploy Squads 1-1, 1-2, 1-3, 2-1, 2-2, 3-1, 3-2 (7 concurrent)
2. **Wave 2**: Deploy Squads 1-4, 1-5, 1-6, 2-3, 2-4, 3-3, 3-4 (7 concurrent)
3. **Wave 3**: Deploy Squads 2-5, 2-6, 4-1, 4-2, 4-3, 4-4 (6 concurrent)
4. **Wave 4**: Deploy Squads 5-1, 5-2 (integration testing)
5. **Consolidation**: Supreme Commander reviews all reports, triages fixes, dispatches fix squads

## Success Criteria
- ZERO unhandled exceptions in any audited file
- Every async function has a catch or try/catch
- Every event listener is removed when component disposes
- Every subprocess/PTY/watcher has a cleanup path
- Hermes mode produces non-empty responses on consecutive prompts
- IDE theme consistent dark+gold across all panels
- Seal chain unbroken after any operation
