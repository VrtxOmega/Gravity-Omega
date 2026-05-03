# Gravity Omega v2 — Swarm Reclamation v4.2
## Objective: Debug & Optimize — model routing, renderer safety, dead code removal

**Supreme Command:** Rage Ω + Hermes  
**Date:** 2026-04-23  
**Status:** Wave 1 deployed

---

## CONFIRMED BUGS

### 🔴 BUG-1: main.js `_ollamaChat` dead code with hardcoded model
**File:** `main.js` lines 1058-1162  
**Impact:** Dead function hardcodes `deepseek-v3.1:671b`. If ever reactivated, ignores user model selection.  
**Fix:** Remove dead code.

### 🔴 BUG-2: renderer/app.js evolution scan fetch missing error boundary
**File:** `renderer/app.js` line 4346  
**Impact:** Unhandled rejection if backend is down.  
**Fix:** Add try/catch around fetch.

### 🟡 BUG-3: renderer/app.js `innerHTML` overuse
**File:** `renderer/app.js` lines 766, 922, 1548, 1818, 1976, etc.  
**Impact:** 6773-line file uses innerHTML ~35 times. Many are static strings with no user input (safe). But using `textContent`/`createElement` is cleaner and faster.  
**Fix:** Convert safe static innerHTML uses to textContent or createElement pattern.

---

## OPTIMIZATIONS

### OP-1: `renderMarkdown` code blocks preserve entities correctly (no XSS)
**Status:** Safe — escape runs before code block insertion. No fix needed.

### OP-2: `omega_agent.js` `_resolveModel` has correct maps
**Status:** v5.2 model resolver is correct. No fix needed.

### OP-3: `main.js` cleanup: `before-quit` watcher close, `pty` cleanup
**Status:** Already fixed in v4.0. No fix needed.

### OP-4: `web_server.py` `sys.exit(0)` used in parent monitor daemon
**Status:** Correct usage (daemon thread, not web server process). No fix needed.

---

## FIX PRIORITY
1. Remove dead `_ollamaChat` from main.js
2. Add try/catch to evolution scan fetch in renderer/app.js
3. Convert safe innerHTML → textContent in renderer/app.js

## VERITAS PIPELINE
- Run intake, type, security, evidence gates after fixes
- Seal to Omega Brain
- End-to-end: syntax check all patched files

## SUCCESS CRITERIA
- [x] Recon complete with pattern searches
- [ ] Dead code removed
- [ ] Unhandled fetch wrapped
- [ ] Safe innerHTML converted
- [ ] Syntax checks pass (node -c, python -m py_compile)
- [ ] VERITAS seal generated
