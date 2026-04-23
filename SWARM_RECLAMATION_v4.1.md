# Gravity Omega v2 — Swarm Reclamation v4.1
## Objective: Full audit, bug hunt, and optimization across I-IV Legions with VERITAS pipeline shielding and Omega Brain sealing

**Supreme Command:** Rage Ω + Hermes
**Date:** 2026-04-23
**Toolset:** VERITAS 10-gate pipeline, Omega Brain SEAL chain, CLAEG state governance

---

## I LEGION — BACKEND (Python ACP Adapter)
### Squad 1-1: backend/web_server.py (2286 lines)
- Audit scope: Flask routes, subprocess calls, file I/O, URL fetching, eval/exec
- Hunt: shell=True, os.system, open(path) traversal, urllib.urlopen without validation
- Hunt: os._exit unclean kills, missing imports
### Squad 1-2: backend/provenance_stack.py
- Hunt: sqlite3 without WAL, missing os import, unprotected dict RMW
### Squad 1-3: backend/*.py (modules)
- Hunt: eval/exec, subprocess patterns, hardcoded secrets

## II LEGION — FRONTEND (Electron/Renderer)
### Squad 2-1: main.js (1326 lines)
- Hunt: unhandledRejection, duplicate ipcMain.on, event listener leaks, watcher cleanup, before-quit
### Squad 2-2: renderer/app.js (~1400 lines per read, 3013 total)
- Hunt: setInterval leaks, innerHTML, fetch without catch, terminal.dispose, EventSource, window.addEventListener
### Squad 2-3: preload.js
- Hunt: exposed APIs, context isolation gaps

## III LEGION — BRIDGE (Protocol & IPC)
### Squad 3-1: omega/hermes_channel.js (544 lines)
- Hunt: heartbeat logic, socket cleanup, IPC message validation
### Squad 3-2: omega/omega_agent.js (1859 lines)
- Hunt: MAX_ITERATIONS shadow, this.emit on non-EE, null guards on tool_calls, double function defs, aborted flag

## IV LEGION — SUPPORT (IDE Optimization)
### Squad 4-1: Monaco config, theming, terminal integration
- Hunt: performance profiling hooks, dark+gold branding consistency
- Verify: no Gemini/Ollama Cloud/Hermes agent dependencies (local-only)

---

## Swarm Protocol
1. **Wave 1**: Commander-led pattern recon (search_files) — highest-risk modules
2. **Wave 2**: Deep line-by-line audit of flagged patterns
3. **Wave 3**: Surgical fixes with syntax verification
4. **Wave 4**: VERITAS pipeline gate run + Omega Brain SEAL
5. **Wave 5**: Integration / end-to-end readiness verification

## Success Criteria
- ZERO unhandled exceptions in audited files
- Every async function has catch/try-catch
- Every event listener has a remove path
- Every subprocess/watcher has cleanup
- VERITAS pipeline PASS on all gates
- Omega Brain SEAL generated
- CLAEG state resolution: STABLE_CONTINUATION
- End-to-end test passes
