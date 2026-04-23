# GRAVITY OMEGA — FULL RECONSTRUCTION BATTLE PLAN
## Command: VERITAS Ω-CODE v5.0 | Seal: ACTIVE | Brain: Hermes

---

## EXECUTIVE SUMMARY

Gravity Omega is **6,765 files** across an Electron frontend (~5,778 JS files), Python Flask
backend (~225 Python files), and embedded tooling. It is bleeding from two wounds:

1. **ACP Integration Hemorrhage** — The streaming race fix is documented but not applied
   or not working at runtime. Every LLM call through Hermes ACP returns empty/null because
   `asyncio.sleep(0)` isn't flushing the executor callbacks before the response is sent.
   This is a **single-line fix** that needs immediate deployment.

2. **Architectural Fragmentation** — No integration tests, no contract validation between
   layers, and broken tool call mapping from Hermes → Omega. The "broken code" responses
   happen because the ACP adapter either returns nothing, or returns malformed tool call
   data that falls through error paths.

3. **Broken Retry Logic** — The `startHermes()` retry in `omega_agent.js` is on the right
   track but doesn't actually flush the corrupted session state. Result: "LLM returned
   with no response" on the second attempt.

---

## CHAIN OF COMMAND — 7 BATTALIONS

```
             HERMES (You) — Supreme Commander
                    ↓
    ┌───────────────┼───────────────┬───────────────┐
    ↓               ↓               ↓               ↓
 BACK-END         FRONT-END      INTEGRATION     SUPPORT
 BATTALION      BATTALION       BRIDGE          BATTALION
 (Python)        (Electron/JS)   BATTALION       (DevEx/QA)
    │               │               │
    ↓               ↓               ↓
 Captains         Captains        Captains
 ├─ Alpha:        ├─ Gamma:        ├─ Kappa:
 │  Flask API     │  Main Proc    │  ACP Protocol
 │  (app.py)      │  (main.js)    │  (hermes_channel.js)
 ├─ Bravo:        ├─ Delta:       ├─ Lambda:
 │  Agent Logic   │  Renderer     │  Tool Mapping
 │  (server.py)   │  (app.js)     │  (omega_tools.js)
 └─ Charlie:      └─ Echo:        └─ Mu:
    Omega Brain      Omega Agent     Session/State
    (backend/)     (omega_agent.js) (conversation_store.js)
                   └─ Zeta: Agent Tools (omega_tools.js)
```

---

## BATTLE PHASES

### PHASE 0 — STOP THE BLEEDING (T+0 to T+30min)
> **Immediate tactical deployment.** Deploys to fix the empty response bug RIGHT NOW so
> Gravity Omega is usable while we rebuild. This is a live field repair.

| Task | Squad | Action |
|------|-------|--------|
| T+0 | Hermes (Me) | Apply `await asyncio.sleep(0)` fix to `acp_adapter/server.py` line ~520 |
| T+5 | Lambda-1 | Patch `_buildOmegaToolCall` mapping table — fix `kind` field lookup |
| T+10 | Kappa-1 | Fix `_send()` timeout race in `hermes_channel.js` — change default 300s |
| T+15 | Mu-1 | Patch `omega_agent.js` retry — properly clear `_hermesChannel` before `startHermes()` retry |

**Deliverable:** Gravity Omega works end-to-end for basic prompts within 30 minutes.

---

### PHASE 1 — AUDIT & CATALOGUE (T+30min to T+4hrs)
> **Reconnaissance.** Every squad scans its sector and produces a damage report.

| Battalion | Captain | Mission |
|-----------|---------|---------|
| Alpha | `app.py` — API surface, route health, CORS, error handling |
| Bravo | `server.py` + `session.py` — full ACP method audit |
| Charlie | `backend/` modules — which load, which crash on import |
| Gamma | `main.js` — IPC contract, window lifecycle, crash logs |
| Delta | `renderer/app.js` — UI event flow, chat state machine |
| Echo | `omega_agent.js` — full agent loop trace, tool call mapping |
| Zeta | `omega_tools.js` — tool registry completeness |
| Kappa | `hermes_channel.js` — JSON-RPC contract, all method pairs |
| Lambda | Cross-layer: Hermes tool name → Omega tool name map |
| Mu | `conversation_store.js` + SQLite schema integrity |

**Deliverable:** 10 damage reports (one per squad), each with:
- Broken lines/files
- Missing error handlers
- Contract violations between layers
- Red-priority (blocks launch), Orange, Yellow classification

---

### PHASE 2 — FIXTURE & CONTRACT HARDENING (T+4hrs to T+12hrs)
> **Build the foundation.** Every layer gets validated contracts so nothing can silently fail.

| Task | Squad | Action |
|------|-------|--------|
| Alpha-1 | Add JSON Schema validation to ALL Flask endpoints |
| Alpha-2 | Add structured error payloads (no more bare `return "error"`) |
| Bravo-1 | Add ACP response contract validator (every method must return expected shape) |
| Bravo-2 | Add `finally` blocks around ALL executor calls so the event loop always yields |
| Kappa-1 | Rewrite `hermes_channel.js` with typed RPC wrapper — every method asserts response type |
| Lambda-1 | Build centralized `HERMES_TO_OMEGA_TOOL_MAP` in shared config |
| Echo-1 | Rewrite `_hermesGenerate()` with explicit state machine (idle → streaming → done → error) |
| Gamma-1 | Add IPC contract assertions in `main.js` for every `webContents.send()` |
| Delta-1 | Add boundary tests for UI → renderer → main → bridge → backend |
| Support-1 | Build test harness that spins up full stack and drives end-to-end prompts |

**Deliverable:** All contracts are machine-validated. No more silent failures.

---

### PHASE 3 — FEATURE REPAIR & OPTIMIZATION (T+12hrs to T+24hrs)
> **Make it better than it was.** IDE optimization, tool integration, swarm features.

| Task | Squad | Action |
|------|-------|--------|
| Delta-1 | **Optimize Monaco** — tree-sitter parsers where available, lazy load language modes |
| Delta-2 | Add inline LLM completion (ghost text) à la Copilot |
| Delta-3 | Monaco diff view for AI code rewrites |
| Echo-1 | Implement real tool call streaming (currently fake/batched) |
| Echo-2 | Add `/ensemble` and `/axiom` slash commands to OmegaAgent |
| Echo-3 | Implement Omega Swarm mode (coordinated multi-file edits) |
| Zeta-1 | Expand tool registry — add `git diff`, `lint`, `typecheck` |
| Zeta-2 | Add "SAFE/DANGEROUS" tool categorization with UI confirmation gates |
| Charlie-1 | Integrate Omega Brain RAG for context-aware agent responses |
| Support-1 | Write integration tests that validate each new feature |

**Deliverable:** Features verified working with integration tests. No broken code paths.

---

### PHASE 4 — DETERMINISTIC QUALITY GATES (T+24hrs to T+36hrs)
> **The VERITAS standard.** Every change gated. Every feature proven.

| Task | Squad | Action |
|------|-------|--------|
| Support-1 | Set up `pytest` + `jest` test runner in CI |
| Support-2 | Build VERITAS Intake Gate integration — every tool call gets validated before execution |
| Support-3 | Build Omega Seal pipeline — every build produces a SHA-256 sealed manifest |
| Support-4 | Build automated crash replay from `gravity_omega_crash.log` |
| Support-5 | Build agent loop circuit breaker (if 3 consecutive tool calls fail → pause for review) |
| All Captains | Final cross-battalion integration sweep |

**Deliverable:** Every build is sealed. Every launch is deterministic.

---

## SWARM ORCHESTRATION PROTOCOL

This is how the subagents talk to each other:

### Shared Battlefield: `~/.hermes/gravity-omega-rebuild/`
```
gravity-omega-rebuild/
├── plans/              ← I write these. Command orders.
├── audits/             ← Each squad drops its damage report here
├── contracts/          ← Shared JSON schemas, tool maps, IPC contracts
├── fixes/              ← Each squad stages its patches here
├── tests/              ← Integration tests that run across battalions
├── manifest.json       ← Live ledger: what's broken, who's fixing it, status
└── comms/              ← Squad updates, cross-talk, blockers
```

### Communication Protocol
1. **Orders** — I write a plan file in `plans/`. Subagent loads it on spawn.
2. **Reports** — Each subagent writes to `audits/<squad>-report.md` when done.
3. **Blockers** — If a squad hits a dependency on another battalion, it writes
   to `comms/BLOCKER-<squad>.md` and I route it.
4. **Integration** — When a squad finishes, it writes to `manifest.json`. The
   Integration Bridge Battalion runs tests against the combined codebase.
5. **No DMs** — Subagents NEVER call each other directly. Everything goes through
   the filesystem ledger so I can see the state.

### Subagent Spawn Pattern
Each squad gets a fresh `delegate_task` with ALL context needed:
```
Goal: "Audit Alpha Squad sector: app.py Flask API surface"
Context:
  - File paths to analyze
  - What the contract SHOULD be
  - Report template to fill out
  - Where to write the report
Toolsets: ['terminal', 'file']
Max iterations: 50
```

---

## OPERATIONAL PARAMETERS

- **Max concurrent subagents:** 15 (my actual limit, not 300 — that's aspirational)
- **Max depth:** 2 (orchestrator → squad captain → worker)
- **Timeout per task:** 15 minutes for audits, 30 minutes for fixes
- **Checkpoint interval:** Every 2 hours I seal status to Omega Brain
- **User check-in:** I'll ping you at T+30min (Phase 0 done) and T+12hrs (Phase 3 done)

---

## WHAT YOU SAID YOU WANTED

> "I want you to orchestrate a swarm of up to 300 sub agents"

I can run **up to 15 concurrently** with my current `delegate_task` depth. But here's
why that's actually an advantage: each of those 15 IS a squad of lieutenants. When
I dispatch "Alpha-1: Audit Flask API", that subagent is doing 50+ file reads and
analysis steps inside its own 50-turn budget. It's a squad in a trenchcoat.

> "They need to talk to each other"

They talk through the shared filesystem ledger (`manifest.json`, squad reports,
blocker files). This is BETTER than direct messaging — it's durable, auditable,
and I can see the whole battlefield at once. No whispered conversations I can't hear.

> "Make sure all of it works"

VERITAS pipeline gates (Intake → Type → Dependency → Evidence → Math → Cost →
Incentive → Security → Adversary → Trace/Seal) will be applied to every build.
No feature ships without running the gauntlet. Period.

> "If anything breaks, close the loops"

Phase 2's contract hardening and Phase 4's circuit breakers are EXACTLY this.
Every layer validates its inputs before executing. If validation fails, the loop
is closed with a typed error that propagates up — no more silent "no response".

---

## NEXT ACTION

**I need your go-ahead to execute Phase 0 (Stop the Bleeding) immediately.**

I will:
1. Apply the `asyncio.sleep(0)` streaming race fix to `acp_adapter/server.py`
2. Fix the Omega tool call mapping in `hermes_channel.js`
3. Patch the retry logic in `omega_agent.js`
4. Restart Gravity Omega's ACP subprocess

That gets you a working Gravity Omega in ~30 minutes. Then we commence full
reconstruction with the battalions.

**Say "execute Phase 0" and I start the field surgery.**
Say "show me the full battalion roster" and I break down every squad assignment.
Say "start the full rebuild" and I launch Phase 0+1+2 in parallel where safe.

I've got you, Rage. Let's make this thing bulletproof.

— Hermes
Ω-CODE v5.0 | Build Gate: SEALED
