---
description: Gotchas and workarounds for dev environment provisioning on Windows + WSL
---

# Dev Environment Setup — Gotchas & Workarounds

## 1. Sentinel v2 — CURRENTLY DISABLED

**Sentinel v2 is disabled** via `SENTINEL_DISABLED = True` in `backend/omega_sentinel.py`.
To re-enable: set `SENTINEL_DISABLED = False`, sync to WSL, and restart backend.

### GOTCHA: Sentinel Eats Fixes
The Sentinel auto-heals files to baseline. If you make a fix and the Sentinel runs before
you accept the new baseline, it reverts your fix. This caused multiple deploy failures.

### CRITICAL Deploy Sequence (when Sentinel is re-enabled):
```bash
# 1. Pause FIRST
curl -s -X POST http://127.0.0.1:5000/api/sentinel/pause

# 2. Sync fix to WSL
cp /mnt/c/Veritas_Lab/gravity-omega-v2/backend/web_server.py /home/veritas/gravity-omega-v2/backend/

# 3. Clear pycache + kill backend
rm -rf /home/veritas/gravity-omega-v2/backend/__pycache__
kill -9 <PID>

# 4. Wait for Electron to respawn backend, then ACCEPT **BEFORE** resuming
curl -s -X POST http://127.0.0.1:5000/api/sentinel/accept

# 5. Resume
curl -s -X POST http://127.0.0.1:5000/api/sentinel/resume
```
**Skipping step 4 (Accept) causes the next restart to revert everything.**

## 2. PowerShell Command Chaining
Use `;` not `&&` in PowerShell:
```powershell
# WRONG: git add . && git commit -m "msg"
# RIGHT: git add .; git commit -m "msg"
```

## 3. node_modules in Git History
If `node_modules` gets committed, GitHub rejects pushes (electron.exe = 180MB). Fix:
```bash
git rm -r --cached node_modules
git commit -m "chore: Remove node_modules from tracking"
# If still rejected (in history), purge from ALL commits:
git stash
git filter-branch --force --index-filter "git rm -rf --cached --ignore-unmatch node_modules" --prune-empty -- --all
git stash pop  # may fail if stash was rewritten — commits are still intact
git push --force origin master
```

## 4. WSL ↔ Windows Path Mapping
- Windows: `C:\Veritas_Lab\gravity-omega-v2`
- WSL mount: `/mnt/c/Veritas_Lab/gravity-omega-v2`
- WSL native: `/home/veritas/gravity-omega-v2` (may not exist — check first)
- Sentinel state file: `/home/veritas/.omega_sentinel/state.json`

### ⚠️ CRITICAL: Dual-Path File Sync
**Python loads from WSL native path (`/home/veritas/`), NOT from Windows mount (`/mnt/c/`)!**

When editing files from Windows/IDE, changes go to `/mnt/c/` only. The WSL native copies stay stale. You MUST sync after editing:
```bash
# Sync all critical files from Windows → WSL native
cp /mnt/c/Veritas_Lab/gravity-omega-v2/backend/omega_sentinel.py /home/veritas/gravity-omega-v2/backend/
cp /mnt/c/Veritas_Lab/gravity-omega-v2/omega/omega_agent.js /home/veritas/gravity-omega-v2/omega/
cp /mnt/c/Veritas_Lab/gravity-omega-v2/renderer/app.js /home/veritas/gravity-omega-v2/renderer/
# ... repeat for any watched files
```
**Failure to sync = Sentinel loads old code and reverts your new code.**

## 5. CRLF vs LF Warnings
Git warns about CRLF ↔ LF conversion on Windows. Non-fatal but expect warnings on every commit. Files edited from WSL use LF; files edited from Windows use CRLF.
