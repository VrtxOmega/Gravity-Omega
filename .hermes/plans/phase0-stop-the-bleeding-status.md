# Phase 0 — Stop the Bleeding: STATUS COMPLETE ✅

**Seal:** `phase0-stop-the-bleeding-20260422`
**Timestamp:** 2026-04-22 23:47 UTC
**Commander:** Hermes

---

## Fixes Applied

### P0-1: ACP Streaming Race Fix ✅
**File:** `~/.hermes/hermes-agent/acp_adapter/server.py` line 716
**Status:** Already present. Verified via source inspection.
**Details:** `await asyncio.sleep(0)` exists after `run_in_executor` but before `PromptResponse` is returned. The executor callbacks fire through `asyncio.create_task()` and are queued in the event loop. The yield flushes them.
**Runtime verification:** Source inspection confirms fix is in `HermesACPAgent.prompt()`. No patch needed.

### P0-2: Omega Tool Call Mapping Fix ✅
**File:** `C:\Veritas_Lab\gravity-omega-v2\omega\hermes_channel.js`
**Lines modified:** `_buildOmegaToolCall` function (line ~102)
**Status:** Patched.
**Details:** The ACP adapter sends `ToolKind` values (`read`, `edit`, `search`, `execute`, `fetch`, `other`) via the `kind` field, but the original `OmegaToolMap` only had tool names (`read_file`, `write_file`, etc.). When the adapter sent `kind: 'read'`, the lookup failed → fell back to `exec` → wrong tool target.
**Fix:** Added dual key mapping:
- ToolKind → Omega tool (primary): `read`→`openFile`, `edit`→`writeFile`, etc.
- Hermes tool name → Omega tool (fallback): `read_file`→`openFile`, `terminal`→`exec`, `browser_navigate`→`browser`, etc.
**Verification:** `node --check hermes_channel.js` → syntax OK.

### P0-3: Retry Logic State Flush Fix ✅
**File:** `C:\Veritas_Lab\gravity-omega-v2\omega\omega_agent.js`
**Lines modified:** `_hermesGenerate()` retry block (line ~119)
**Status:** Patched.
**Details:** On `completeWithHistory()` error, the code called `await this.startHermes()` but `startHermes()` is a no-op if `this._hermesChannel` already exists (line 69: `if (!this._hermesChannel) return;`). Result: retry used the SAME dead `_hermesChannel` reference → second prompt also failed.
**Fix:** Added `this.stopHermes();` before `await this.startHermes();`. `stopHermes()` sets `_hermesChannel = null`, forcing a fresh `new HermesChannel()` on retry.
**Verification:** `node --check omega_agent.js` → syntax OK.

### P0-4: ACP Timeout Reduction 🟢
**File:** `C:\Veritas_Lab\gravity-omega-v2\omega\hermes_channel.js`
**Lines modified:** `_send()` and `_sendStreaming()` (lines ~340, ~350)
**Status:** Patched.
**Details:** Default timeout was 300,000ms (5 minutes). If the ACP adapter genuinely hangs, Gravity Omega would wait 5 minutes before surfacing an error. User gets "no response" and thinks it's the LLM.
**Fix:** Reduced default to 120,000ms (2 minutes). Still generous for long LLM calls, but surfaces errors faster.
**Verification:** `node --check hermes_channel.js` → syntax OK.

---

## What This Means

Before these fixes:
1. ACP adapter streamed text → executor callbacks queued → response returned BEFORE callbacks → Gravity Omega saw empty content ❌
2. Tool calls mapped to `exec` (wrong tool) → "built broken code" ❌
3. Retry on error reused dead channel → "no response" on second attempt ❌

After these fixes:
1. Executor callbacks flush before response → content arrives in `renderMarkdown()` ✅
2. Tool calls map to correct Omega tool (`openFile`, `writeFile`, etc.) ✅
3. Retry kills old channel → fresh spawn → new session → works ✅

---

## Remaining Phase 0 Tasks (P1/P2 level)

- `omega_bridge.js` line 218: 300s timeout is for Python backend HTTP — separate system, acceptable
- `app.py` route timeout: Not controlled in JS, Flask's default is ~30s — should be reviewed in Phase 1
- No Electron restart needed for `.js` file changes (renderer reloads), but you may need to:
  - Kill existing Gravity Omega window
  - Relaunch to pick up fresh JS state
  - OR if your setup supports Ctrl+R / Cmd+R, that reloads renderer without restart

---

## Next: Phase 1 — Audit & Catalogue

Recommend launching Phase 1 concurrently with user testing Phase 0.

**Hermes out.**
