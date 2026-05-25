# Gravity Omega Unified Rebuild Action Plan

Status: consolidated from Kimi Workers A/B/C and the Rust/Tauri scaffold audit.

## Goal

Ship the Rust/Tauri rebuild as a full Linux-native replacement for the current Electron Gravity Omega app while making Codex, Hermes, MCP, SSWP, Stenographer, the pet companion, terminal/process supervision, approvals/evidence, and Linux desktop control first-class product surfaces.

The plan is intentionally product-facing. The rebuild should stop growing one dry-run command per prerequisite and converge around about 20 real command families.

## Source Findings

### Worker A: Electron Parity

- 29 major UI features must be preserved or deliberately replaced.
- 92 Electron IPC handlers must become typed Rust/Tauri commands or sidecar contracts.
- 60 Flask backend routes and 52 registered modules must be managed as a Python sidecar first, then absorbed only where Rust is a better permanent owner.
- 24 tools across safe, gated, and restricted tiers must keep explicit boundaries.
- 12 sidebar/panel areas must remain discoverable in the native app.

Highest parity risks:

- PTY terminals need a Rust `portable-pty` style supervisor or a carefully bounded sidecar.
- Media playback needs a sidecar/library boundary for YouTube, local audio, AAX remux, ffmpeg/ffprobe, metadata, and cover art.
- Puppeteer/browser automation should remain sidecar-isolated instead of living inside the Rust core.
- The Flask backend should be launched as a managed sidecar before any route/module migration is attempted.

### Worker B: Codex/Hermes Parity

Codex should be the disciplined engineering runtime:

- exec
- review
- apply/patch discipline
- sandbox policy
- MCP/plugin awareness
- evidence-first final status

Hermes should be the orchestration companion:

- `chat -Q`
- oneshot
- profiles
- toolsets
- shell hooks
- checkpoints
- worktrees
- subagent delegation

Joint CI lifecycle:

```text
plan -> delegate -> run -> compare evidence -> reconcile -> approve -> ship
```

The shared `OmegaTaskRun` contract is the center of the runtime, with capability tier, approval policy, sandbox policy, status, artifacts, evidence, and seal hash recorded before any live mutation.

### Worker C: First-Class Omega Features

Critical scaffold finding:

- `src-tauri/src/commands.rs` is 124k lines with 304 stub commands and extreme command-name inflation.
- The target must collapse this into about 20 real command families.

First-class surfaces:

- MCP dashboard with health dots, capability contracts, activity sparklines, last seal hash, and staged approval from discovery through live execute.
- SSWP fleet health board, attestation timeline, witness workflow, bulk witness, and auto-witness prompts.
- Stenographer running notes, milestone capture, cross-session linking, and predictive compaction warnings.
- Pet companion tied to real task, MCP, Steno, and approval events.
- Linux desktop control released in stages: read-only, gated interaction, restricted full control.
- Terminal/process supervisor with transcript JSONL and a time-travel scrubber.
- Workspace edit adapter with preflight, approval policy, diff buffer, atomic transaction, verification, and rollback.

### Worker D: UI/UX And Test Matrix

Worker D adds the product-quality gates that decide whether a feature is usable, not merely present:

- Fix cramped chat/sidebar/bottom-panel proportions with explicit layout targets.
- Replace weak placeholder visuals with semantic warning/info/memory/review colors.
- Require keyboard focus rings, loading skeletons, hover previews, drag/drop feedback, and resize affordances.
- Cover all 20 feature families with unit tests, UI smoke tests, manual checks, and hard blocker gates.

## Command Surface Collapse Target

The rebuild should converge on these 20 command families:

| # | Family | Purpose |
|---:|---|---|
| 1 | `runtime` | App identity, XDG paths, health, version, docs/about |
| 2 | `command_registry` | Toolbar readiness, command palette, manifest, release boards |
| 3 | `task_run` | OmegaTaskRun create/query/timeline/artifacts/events |
| 4 | `approval_evidence` | Approvals, dry-runs, rollback, audit, evidence previews |
| 5 | `workspace_read` | Workspace tree, search, file preview, tabs, find |
| 6 | `workspace_edit` | Save, save-as, replace, diff, patch, atomic transactions |
| 7 | `process_supervisor` | PTY, shell commands, lifecycle, streams, transcripts |
| 8 | `codex_run` | Codex review/exec/apply under sandbox and evidence gates |
| 9 | `hermes_run` | Hermes chat/oneshot/profile/toolset/checkpoint/worktree runs |
| 10 | `joint_ci_run` | Codex/Hermes compare, reconcile, approve, ship loop |
| 11 | `mcp` | MCP discovery, health, typed contracts, gated calls |
| 12 | `sswp` | Supply-chain witness, fleet, risk, attestation timeline |
| 13 | `steno` | Running notes, milestones, search, compaction, recall |
| 14 | `pet_state` | Companion state, animation events, task/MCP/Steno reactions |
| 15 | `desktop` | Window list, screenshot, accessibility tree, approved actions |
| 16 | `media` | Audio library, playback, AAX remux, metadata, cover art |
| 17 | `browser` | Browser automation sidecar, screenshots, OCR/browser evidence |
| 18 | `module_sidecar` | Managed Python backend and module registry |
| 19 | `security` | Sentinel, shields, scans, processes, ports, restricted controls |
| 20 | `settings` | Providers, secrets, themes, pairing, native preferences |

## Execution Order

1. Freeze the 20-family map in the scaffold UI and tests.
2. Implement `workspace_edit(save_preview)` inside the family shape instead of adding more single-purpose stubs.
3. Convert terminal/process records into a `process_supervisor` contract before PTY allocation.
4. Move Codex and Hermes into `OmegaTaskRun` records with evidence comparison.
5. Collapse local MCP config-read chains into one staged `mcp` family.
6. Promote SSWP, Steno, and pet companion panels from readiness surfaces into usable first-class panels.
7. Add managed sidecar wrappers for Python backend, browser automation, and media before attempting live parity.
8. Gate all write, execution, config-read, desktop-control, socket, capture, export, and memory-write actions through the approval/evidence family.

## Safety Rules

- No live workspace writes until `workspace_edit` has preflight, preview, approval, atomic write, verification, and rollback evidence.
- No PTY or process spawn until `process_supervisor` has allowlist, transcript, output-tail, lifecycle, and exit summary records.
- No live MCP calls until health, discovery, typed contract, dry-run, and final approval are present.
- No desktop action beyond read-only inventory until approval toast, screenshot target, stale-tree checks, and cancellation behavior exist.
- No provider secret read/write outside Linux keyring-backed settings.
- No sidecar launch without command allowlist, lifecycle, logs, and operator-visible failure state.

## Status

The current scaffold has enough parity information to stop adding prerequisite-only command stubs. The next implementation slices should land inside the 20 command families and retire redundant generated commands as each family becomes real.

First family-shaped slice started:

- `workspace_edit(save_preview)` now models the six-stage workspace edit pipeline as one command-family surface.
- It is read-only and keeps file reads, writes, save/save-as, replace, patch apply, process spawn, dialogs, and execution disabled.

UI/UX quality slice started:

- `ui_ux_test_matrix` now exposes Worker D's 20-family quality gates in the scaffold.
- The scaffold CSS now has warning/info/memory/review semantic colors, focus-visible rings, motion tokens, shadow depth, layout width tokens, and skeleton utilities.

Finish-line shell pass started:

- `replacement_app_ship_readiness` now consolidates the 20 command families into one product-facing finish-line blocker map.
- `sidecar_readiness_board` now names the highest Worker A parity blockers as one board: Python backend, browser automation, media/AAX/ffmpeg, terminal PTY/process supervision, and restricted security tools.
- `sidecar_launch_policy_manifest` turns those blockers into explicit launch policies with binary, cwd, argument, environment, log, health, shutdown, approval, and failure-UI requirements.
- `sidecar_health_packet_console` converts those policies into health packets with probe intent, success criteria, failure signals, evidence path, approval dependency, and launch blockers.
- These surfaces remain read-only and keep live health probes, sidecar launches, process spawn, PTY, browser automation, media playback, Python bridge, desktop control, config reads, sockets, live MCP calls, file writes, patches, capture, export, memory writes, and execution disabled until health probes, logs, allowlists, approvals, and failure UI exist.
