# Gravity Omega Rust/Linux Rebuild Audit

Status: Phase 1 audit, not an implementation patch.

## Goal

Audit the current Gravity Omega application and define the target shape for a Linux-optimized Rust rebuild that preserves the app's useful identity while incorporating the non-redundant operating features of Codex.

## Evidence Sources

- Active repo: `/home/rage/apps/gravity-omega-v2`
- Historical repo: `/home/rage/apps/gravity-omega-v2-old`
- Existing rebuild spec: `/home/rage/Downloads/SPEC.md`
- Existing screenshot: `/home/rage/apps/gravity-omega-v2/screenshots/gravity_omega_dashboard.png`
- Existing technical/history docs:
  - `Gravity_Omega_Final_Monolithic_Technical_Manual_Walkthrough.md`
  - `Gravity_Omega_Comprehensive_History_v4_1_KI.md`
- Runtime log reviewed: `/home/rage/.gravity-omega/logs/gravity_omega.log`
- Codex Linux feature reference: `/home/rage/apps/codex-desktop-linux/README.md`

## Current Repo State

- Git branch: `main...origin/main`
- Existing dirty files before this audit:
  - `.sswp.json`
  - `gravity-omega.sswp.json`
- Audit-created files/directories:
  - `docs/`
  - `docs/GRAVITY_OMEGA_RUST_REBUILD_AUDIT.md`

The dirty `.sswp` files were present before this audit and should not be mixed into any future rebuild branch unless they become the explicit task.

## Current App Identity

Gravity Omega is not just an IDE. It is a dense operator console combining:

- Monaco code editor
- File explorer and text search
- PTY terminal tabs
- Right-side agent chat
- Local and cloud model provider routing
- Hermes ACP bridge
- MCP server surface
- Python module execution backend
- Veritas Vault search/context panels
- Security/sentinel panels
- Evolution/patch proposal queue
- Media/audiobook controls
- Document analyzer/report generator
- Plugin containers for adjacent Omega/VERITAS tools

The strongest product identity is a "sovereign operator terminal": dark, local-first, command-heavy, evidence-oriented, and designed around the Omega/VERITAS ecosystem.

## Static Size Snapshot

Shallow source/docs inventory found 193 source/doc/config files under the active repo, excluding `node_modules` and deep build outputs.

Largest active surfaces:

| File | Lines | Notes |
|---|---:|---|
| `renderer/app.js` | 7,277 | Main UI state machine, chat, editor, panels, media, vault, tools |
| `backend/web_server.py` | 2,495 | Flask backend, module registry, routes, vault, security, evolution |
| `omega/omega_agent.js` | 1,993 | Agent loop, Hermes routing, safety gates, command parsing |
| `renderer/styles/omega.css` | 1,966 | Primary visual system |
| `main.js` | 1,616 | Electron lifecycle, IPC, backend bridge, MCP startup, terminal/media |
| `omega/omega_mcp_server.js` | 1,341 | MCP tool server exposing IDE operations |

This is past the point where "fix Electron a little" is the right architectural move. The rewrite should preserve behavior contracts while replacing the runtime core.

## Current Architecture

### Shell

Current shell is Electron with:

- custom frameless titlebar
- single-instance lock
- crash logging to `/tmp/gravity_omega_crash.log`
- renderer crash-loop guard
- tray/global shortcut imports
- Monaco and xterm loaded from `node_modules`
- `contextIsolation: true`
- `nodeIntegration: false`
- `sandbox: true`
- `webviewTag: false`

### Bridge

The active `OmegaBridge` still spawns the Python backend through WSL:

- command path: `wsl -- bash -c ...`
- canonical backend path: `/mnt/c/Veritas_Lab/gravity-omega-v2/backend/web_server.py`
- fallback backend path: `~/gravity-omega-v2/backend/web_server.py`
- Python venv path: `/mnt/c/Veritas_Lab/gravity-omega-v2/.venv/bin/python`

This is the largest Linux blocker. The launcher can choose a Linux Electron binary, but the backend process model is still Windows/WSL-first.

### Backend

The backend is Flask on port 5000 with auth via `X-Omega-Token`.

Static route inventory found 62 `@app.route(...)` declarations, including:

- `/api/status`
- `/api/modules`
- `/api/modules/<module_id>/run`
- `/api/modules/<module_id>/describe`
- `/api/agent/think`
- `/vtp`
- `/api/vault/*`
- `/api/security/*`
- `/api/provenance/*`
- `/api/evolution/*`
- `/api/facebook/*`
- `/api/tts`
- `/api/analyze_document`

Important mismatch: the current code and spec disagree on health endpoints. The spec asks for `/health` or `/api/health`; the active backend exposes `/api/status`.

### IPC Surface

Static IPC inventory found 85 `ipcMain.handle(...)` channels, grouped as:

- file operations
- media/audiobook operations
- terminal operations
- watcher/search
- backend/module execution
- chat/TTS
- threads
- agent approval/Hermes
- provider management
- MCP calls/status
- hardware
- browser automation
- reports/tools
- security
- ledger/vault
- OCR

This should become an explicit Rust command contract instead of an organically grown IPC namespace.

## UI And Aesthetic Audit

### Visual Language

Current visual system:

- black/obsidian base: `#0a0a0a`, `#111111`, `#1a1a1a`
- gold accent: `#d4a843`, `#f0c040`, `#a0802a`
- semantic accents: red, green, blue, cyan, orange, purple
- primary fonts: Inter and JetBrains Mono
- branding fonts: Orbitron, Rajdhani, Georgia for Omega symbol
- 6px default radius, compact panels, dense layout
- left activity rail, center editor, bottom terminal, right chat

The screenshot confirms the identity: gold Omega mark in a large dark workspace, VS Code-like side rails, bottom terminal, and a persistent right command/chat strip.

### What Works

- The app immediately reads as a premium operator console.
- The Omega mark and gold/black palette are recognizable and should remain.
- The layout is correctly work-focused: no landing page, no marketing hero, no decorative fluff.
- The status bar, terminal panel, activity rail, and chat panel create a credible IDE feel.
- Dense controls match the target user better than a simplified consumer chat UI.

### What Needs Redesign

- The palette is too one-note if every interaction is gold-on-black. Keep the brand, but add stronger semantic color lanes for danger, auth, memory, tools, review, and runtime state.
- Several panels use inline emoji labels and inline styles. The rebuild should standardize iconography and component states.
- The right chat rail can feel cramped against the editor and bottom terminal. It needs collapsible width presets and better message/tool rendering.
- The current screenshot shows left media controls occupying the sidebar by default. Media is useful, but it should not dominate the main operator workflow.
- The app claims webviews are disabled in Electron, while HTML still contains `<webview>` elements for media. That contradiction should be eliminated.
- Monaco workers are disabled with a no-op worker. The rebuild should decide whether Monaco remains the editor engine or whether a lighter editor surface is acceptable.

## Functional Inventory

### Keep

- Omega/VERITAS branding and command-center identity
- Monaco-style editor with tabs and dirty-state tracking
- File explorer plus text search
- PTY terminals with tab management
- Agent chat with visible tool steps
- Thread persistence
- Provider management
- Human approval for gated/destructive operations
- MCP server/client surfaces
- Vault/context search
- Audit ledger and provenance concepts
- Security/sentinel posture panel
- Evolution proposal queue, but only with strong review gates
- Document analyzer/report generator
- Plugin/module ecosystem
- Mobile pairing concept, but not localtunnel as the default security model

### Rebuild Natively

- Electron `main.js` lifecycle and IPC
- `OmegaBridge` process management
- Python backend module registry and route layer
- Tool execution engine
- MCP server
- File watcher/search/indexing
- PTY runtime
- Provider secrets storage
- Audit log and approval gate
- Plugin runner
- Packaging/update path

### Remove Or Quarantine

- WSL-only process spawning
- `/mnt/c/Veritas_Lab` assumptions
- Windows AppData vault paths
- automatic `git pull --ff-only` at app startup
- claims of "no external dependency" while loading Google Fonts and QR server resources
- endpoints called by the UI/MCP but missing from Flask
- placeholder tools that look live but only return "pending", "requires integration", or empty arrays
- base64 fallback for provider API keys as anything other than an explicit insecure-dev mode
- unbounded self-healing that can silently revert source while a developer is editing

### Merge With Codex Concepts

Gravity Omega already has editor, terminal, chat, MCP, browser, files, and provider basics. The non-redundant Codex features to incorporate are operating model features, not another chat box.

High-value Codex features to build in:

- `AGENTS.md`/doctrine ingestion per workspace
- task planning before edits, including `tasks/todo.md` style checklists
- lessons capture after user correction
- diff shape inspection before claiming success
- test/log/manual verification evidence blocks
- explicit sandbox and approval model
- command prefix allowlists and escalation prompts
- precise patch application instead of broad file rewrites
- code-review mode with findings first and file/line references
- GitHub PR/CI triage workflows
- MCP/plugin/skill discovery and install flow
- first-class SSWP and Omega Stenographer lanes, because these are user-owned MCP subsystems rather than generic plugins
- connector-style integrations for GitHub, Gmail, Drive, calendar, docs, sheets, slides, Stripe, and browser sessions
- local memory with citations and durable rollups
- subagent orchestration with disjoint write scopes
- browser/computer-use stack using screenshots plus Linux accessibility trees
- automation/reminder/monitor jobs
- workspace dependency discovery for docs, sheets, slides, PDFs, and generated artifacts
- structured final status with evidence

Features that should not be duplicated because Gravity Omega already has a surface:

- basic model selector
- basic file tree
- basic terminal
- basic search
- basic chat panel
- generic provider API key modal

## Kimi Swarm Consolidation

The Kimi Worker A/B/C reports added enough evidence to change the rebuild plan from incremental stub expansion to command-surface consolidation:

- Worker A identified the parity load: 29 major UI features, 92 IPC handlers, 60 Flask backend routes, 52 registered modules, 24 tool entries, and 12 panel/sidebar areas.
- Worker B clarified that Codex should be integrated as the disciplined engineering runtime, Hermes as the orchestration companion, and joint CI as `plan -> delegate -> run -> compare evidence -> reconcile -> approve -> ship`.
- Worker C found the scaffold command debt: `src-tauri/src/commands.rs` is 124k lines with 304 generated stubs and must collapse toward about 20 real command families.

The rebuild now has a read-only `command_surface_collapse_board` command and a visible "Command Surface Collapse" UI panel that maps those findings into 20 target command families. This board keeps the next slices product-facing while live adapters, workspace writes, PTY/process spawn, desktop control, browser/media/Python sidecars, MCP calls, config reads, sockets, capture, export, and memory writes remain disabled.

The first implementation slice inside that collapse map is `workspace_edit(save_preview)`: a read-only workspace edit family command and UI panel that shows preflight, write approval policy, diff preview, atomic transaction, post-write verification, and rollback stages without reading file contents or enabling writes.

Worker D's UI/UX audit is now part of the scaffold through `ui_ux_test_matrix`. The scaffold also has the first static design-token pass: warning/info/memory/review semantic colors, focus-visible rings, motion tokens, shadow depth, layout width targets, and skeleton loading utility classes. This keeps the product-quality criteria tied to the same 20 command families as the architecture plan.

The finish-line replacement shell is now represented by `replacement_app_ship_readiness` and `sidecar_readiness_board`. These surfaces consolidate the 20-family readiness state and the highest-risk Worker A sidecar blockers: Python backend, browser automation, media/AAX/ffmpeg, terminal PTY/process supervision, and restricted security tools. They are read-only and keep sidecar launch, process spawn, PTY, browser automation, media playback, Python bridge, desktop control, config reads, sockets, live MCP calls, file writes, patch application, capture, export, memory writes, workspace writes, and execution disabled until launch policies, health probes, logs, allowlists, approvals, and failure UI exist.

The sidecar launch policy pass added `sidecar_launch_policy_manifest`, which makes those blockers concrete without spawning anything. Each high-risk sidecar now has an explicit binary strategy, cwd policy, argument policy, environment policy, log path, health probe, shutdown policy, approval gate, and failure UI requirement. The command remains read-only and keeps process spawn, PTY, browser automation, media playback, Python bridge, security action, config reads, sockets, file writes, patches, capture, export, memory writes, workspace writes, and execution disabled.

The sidecar health packet pass added `sidecar_health_packet_console`, which turns each launch policy into an operator-facing health packet with probe intent, success criteria, failure signals, evidence path, approval dependency, and launch blocker. It is still deliberately read-only: no live probe, sidecar launch, process spawn, PTY, browser automation, media playback, Python bridge, restricted security action, config read, socket, file write, patch, capture, export, memory write, workspace write, or execution is enabled.

The toolbar routing pass removed the weakest remaining live-toolbar fallbacks. File/new/open/workspace commands now open the workspace files and editor navigation surfaces; undo/redo opens workspace edit and mutation surfaces; window/app shell commands open native shell readiness; security refresh opens the security workbench; Codex Review opens the Codex/Hermes run view and integration launchpad. These routes are still non-mutating and do not enable dialogs, exits, fullscreen changes, scans, execution, writes, patches, desktop control, sockets, capture, export, or memory writes.

The activity rail navigation pass made the left rail functional. Command, Workspace, Vault, Security, Plugins, and Codex/Hermes CI now filter the top status panels and dashboard cards into focused operator areas with `aria-pressed` state and a visible active-area badge. This reduces the giant-scroll scaffold behavior without enabling file reads, writes, patches, MCP calls, config reads, sockets, process spawn, PTY allocation, desktop control, browser automation, media playback, sidecar launches, security scans, capture, export, memory writes, or execution.

The agent rail resize pass addressed the fixed chat rail from Worker D's UI/UX audit. The right rail now has an accessible separator with pointer drag and keyboard-arrow resizing, clamps to the audited 240-480px range, and persists the local browser preference. It remains layout-only and does not enable chat send, agent execution, process spawn, PTY allocation, desktop control, file reads, writes, patches, MCP calls, config reads, sockets, capture, export, memory writes, or execution.

## Current Breakpoints And Risks

### Linux Runtime

The active backend bridge still requires `wsl`. On a native Linux desktop, `OmegaBridge.start()` is expected to fail unless WSL compatibility exists. A Rust rebuild should start local sidecars directly with `std::process`/Tokio and XDG-native paths.

### Packaging

`package.json` still includes `launch.js` in the builder `files` list, but the active launcher is `launcher.js`. The package still has Windows build targets despite the Linux rebuild spec saying Linux-only.

### Missing Route Contracts

The main process calls routes that the static route list did not show:

- `/api/security/processes`
- `/api/security/ports`
- `/api/security/destroy`

The MCP server also calls `/api/modules/<module_id>/execute`, while the active backend exposes `/api/modules/<module_id>/run`.

The MCP server references `/api/image/generate` and `/api/veritas/assess`; those routes were not found in the active Flask route list.

### Webview Contradiction

Electron creates the BrowserWindow with `webviewTag: false`, but `renderer/index.html` includes two `<webview>` tags for media. The UI says media can expand into webviews, but Electron is configured to reject that tag.

### Security

The app has real positive security ideas:

- renderer sandbox
- context isolation
- no raw Node in renderer
- IPC path type checks
- auth token for backend requests
- approval gate concept
- restricted tool tier
- SSRF shield
- provenance stack

Risks:

- command execution still uses shell execution in several places
- command allowlist treats shells like `bash`, `sh`, `powershell`, `cmd`, and `wsl` as safe first tokens
- path validation blocks some system directories but allows broad home/filesystem edits
- provider key encryption falls back to base64 when Electron `safeStorage` is unavailable
- the startup code tries to read Gemini secrets via `gcloud`
- CSP allows `unsafe-inline`
- external font/QR resources are loaded despite local-first/no-telemetry positioning

### UX Honesty

Some controls are placeholders or partially wired:

- email/code review/report modules return static or pending data
- image generation reports that backend integration is required
- upload tools report backend integration required
- several security shield actions return status envelopes rather than proven system changes

Future UI must visually distinguish:

- live/verified
- configured but offline
- planned/not implemented
- dangerous/gated
- mock/sample

## Rust/Linux Rebuild Direction

### Recommended Shell

Use Tauri 2 with a Rust core and a web UI.

Reasoning:

- The app needs Monaco/xterm-style browser UI primitives.
- Tauri keeps the UI flexible while replacing Electron's large Node main process.
- Rust side handles process execution, PTY, file watching, search, SQLite, MCP, approval gates, and Linux desktop integration.
- Linux packaging can target `.deb`, `.rpm`, AppImage, and Nix without carrying the full Electron main process.

Alternative native UI options like Iced, egui, or GPUI are worth tracking, but Monaco-grade editor ergonomics and web-based plugin surfaces make Tauri the pragmatic first rebuild target.

### Proposed Process Model

```
gravity-ui
  Tauri web UI: editor, terminal, chat, panels, settings

gravity-core
  Rust command/runtime service inside Tauri:
  files, search, patching, terminal, approvals, provider config, audit logs

gravity-agent
  Rust agent orchestration:
  plan, tool schema, model routing, approval, transcript, Codex-style evidence loop

gravity-mcp
  Local MCP server exposing editor/runtime tools to Hermes/Codex/other agents
  First-class adapters for OmegaBrain, SSWP, and Omega Stenographer

gravity-modules
  Sidecar runners for Python or Rust modules, strongly typed and sandboxed
```

### Rust Building Blocks

- async runtime: `tokio`
- serialization: `serde`, `serde_json`
- app shell: `tauri`
- SQLite: `sqlx` or `rusqlite`
- file watching: `notify`
- search: `ignore`, `grep-searcher`, `regex`
- AST/code intelligence: `tree-sitter`
- PTY: `portable-pty` or equivalent Linux PTY crate
- HTTP/model calls: `reqwest` with `rustls`
- secrets: `keyring`, `zeroize`, optional libsecret backend
- logging: `tracing`, JSONL audit sink
- packaging: Tauri bundler plus distro-native scripts
- MCP: JSON-RPC over stdio/SSE with strict schemas

### Linux Path Model

Use XDG and explicit environment config:

- config: `$XDG_CONFIG_HOME/gravity-omega/` or `~/.config/gravity-omega/`
- data: `$XDG_DATA_HOME/gravity-omega/` or `~/.local/share/gravity-omega/`
- cache: `$XDG_CACHE_HOME/gravity-omega/` or `~/.cache/gravity-omega/`
- logs: `$XDG_STATE_HOME/gravity-omega/logs/` or `~/.local/state/gravity-omega/logs/`

Do not use `/mnt/c`, `AppData`, or WSL detection as the default path.

## Phased Rebuild Plan

### Phase 0: Freeze The Current Contract

- Create feature matrix from the current app.
- Mark every feature as live, partial, placeholder, broken, or deprecated.
- Write route/IPC/tool contract tests against the current repo.
- Decide which Python modules survive.

### Phase 1: Rust/Tauri Skeleton

- Create new branch for rebuild only.
- Scaffold Tauri app with the existing Omega visual identity.
- Implement XDG dirs, logging, settings, and provider secrets.
- Add a command contract equivalent to the current IPC list.

### Phase 2: Core IDE Surface

- Read-only workspace inspection readiness before live traversal
- Read-only file tree/read-preview records before live content reads
- Scoped file tree metadata traversal before opening file contents
- Guarded read-only file content previews before editor tabs or saves
- Read-only editor tab state before edit buffers or saves
- Disabled edit-intent and save-gate preflights before writable editor behavior
- Write approval policy records before editable buffers or save operations
- Workspace write approval evidence before writable buffers or save operations
- Disabled writable-buffer draft records before dirty state or save operations
- Disabled dirty-transition preflights before dirty editor state
- Disabled mutable-buffer transaction records before editable text materialization
- Disabled editor-buffer materialization policy before editable text attachment
- Disabled editor-buffer attachment records before editable buffer state
- Disabled editor-buffer editable-state preflights before visible editable state
- Disabled editable-buffer view binding records before any visible editable surface
- Disabled editable-text viewport materialization records before rendering editable text
- Disabled editable-text attachment verification records before attaching text to the editable model
- Disabled editable-text model handle records before editable model text storage
- Disabled editable-text model storage preflight records before any model holds text
- Disabled editable-text model text snapshot records before model-held text content
- File tree and open/save
- Monaco editor tabs
- Search
- Terminal tabs
- Status bar
- Command palette
- Diff view
- Patch application

### Phase 3: Codex-Grade Agent Runtime

- Read-only Codex/Hermes/MCP capability inventory records, with Omega Brain,
  SSWP, Omega Stenographer, and the Codex pet marked as first-class surfaces
  before any live runtime probes, MCP calls, terminal control, desktop control,
  process spawning, or workspace mutation.
- Read-only first-class integration readiness records for Omega Brain, SSWP,
  Omega Stenographer, the Codex pet, and joint Codex/Hermes CI before per-lane
  health checks, live MCP calls, asset inspection, terminal control, desktop
  control, process spawning, or workspace mutation.
- Workspace doctrine reader
- Plan/todo enforcement
- Tool registry with safe/gated/restricted tiers
- Approval prompts with audit log
- Patch-only file edits
- Test/log/diff evidence tracking
- Thread transcripts
- Transcript redaction, retention, consent, and export policy gates
- Lessons capture

### Phase 4: MCP And Plugin System

- Gravity MCP server
- MCP client health surface
- Read-only local MCP lane capability contracts for Omega Brain, SSWP, and
  Omega Stenographer before live probes, capability discovery, gated calls,
  captures, exports, memory writes, process spawning, terminal control, desktop
  control, or workspace mutation.
- Read-only local MCP health preflight records that require those contracts
  before config lookup, process health probes, capability discovery, live calls,
  captures, exports, memory writes, or execution.
- Disabled local MCP health records linked to health preflight evidence for
  Omega Brain, SSWP, and Omega Stenographer before any live probe or call.
- Disabled local MCP capability discovery policy records linked to ready health
  evidence before live manifest discovery, MCP calls, capture, export, memory
  writes, or execution.
- Disabled local MCP gated-call policy records linked to capability discovery
  policies before Omega Brain, SSWP, or Omega Stenographer MCP calls can run.
- Disabled local MCP call approval/audit request records linked to gated-call
  policies before consent, approval, audit completion, or live MCP calls exist.
- Disabled local MCP consent/approval decision records linked to call
  approval/audit requests before audit outcomes or live MCP calls exist.
- Disabled local MCP audit outcome records linked to consent/approval decisions
  before recovery records, final call approval, or live MCP calls exist.
- Disabled local MCP recovery/pre-call guard records linked to audit outcome
  evidence before final call approval or live MCP calls exist.
- Disabled final local MCP call approval records linked to recovery/pre-call
  guard evidence before live MCP call dry-runs or real MCP calls exist.
- Disabled local MCP live-call dry-run records linked to final approval
  evidence before config/socket/manifest reads, typed lane contracts, status
  probes, or real MCP calls exist.
- Disabled local MCP typed command contract records linked to live-call dry-run
  evidence for Omega Brain, SSWP, and Omega Stenographer before any read-only
  MCP status probe, config/socket/manifest read, capture/export, memory write,
  or real MCP call exists.
- Disabled local MCP status probe preflight records linked to typed command
  contracts before any MCP config read, socket connection, live manifest read,
  live status probe, capture/export, memory write, or real MCP call exists.
- Disabled local MCP config lookup preflight records linked to status probe
  preflight evidence before any config path resolution, config file read,
  socket connection, live manifest read, status probe, or real MCP call exists.
- Disabled local MCP config read policy records linked to config lookup
  preflight evidence before any config file can be opened, parsed, inspected,
  or used for socket, manifest, probe, or real MCP call setup.
- Disabled local MCP config path allowlist records linked to config read policy
  evidence before any config path can be resolved, opened, parsed, or used for
  socket, manifest, probe, or real MCP call setup.
- Disabled local MCP config path resolution request records linked to path
  allowlist evidence before any config path can be normalized, statted, opened,
  parsed, or used for socket, manifest, probe, or real MCP call setup.
- Disabled local MCP config path resolution approval records linked to path
  resolution request evidence before any config path can be normalized,
  statted, opened, parsed, or used for socket, manifest, probe, or real MCP call
  setup.
- Disabled local MCP config path resolution dry-run records linked to path
  resolution approval evidence before any real path value can be captured,
  normalized, statted, opened, parsed, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP config path materialization request records linked to path
  resolution dry-run evidence before any real path value can be captured,
  normalized, statted, opened, parsed, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP config path materialization approval records linked to
  materialization request evidence before any real path value can be captured,
  normalized, statted, opened, parsed, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP config path materialization final dry-run records linked to
  materialization approval evidence before any real path value can be captured,
  normalized, statted, opened, parsed, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP config path read preflight request records linked to
  materialization final dry-run evidence before any real path value can be
  opened, read, parsed, hashed, captured, or used for socket, manifest, probe,
  or real MCP call setup.
- Disabled local MCP config path read preflight approval records linked to read
  preflight request evidence before any real path value can be opened, read,
  parsed, hashed, captured, or used for socket, manifest, probe, or real MCP
  call setup.
- Disabled local MCP config path read preflight final dry-run records linked to
  read preflight approval evidence before any real path value can be opened,
  read, parsed, hashed, captured, or used for socket, manifest, probe, or real
  MCP call setup.
- Disabled local MCP config path controlled read request records linked to read
  preflight final dry-run evidence before any real path value can be opened,
  read, parsed, hashed, captured, or used for socket, manifest, probe, or real
  MCP call setup.
- Disabled local MCP config path controlled read approval records linked to
  controlled read request evidence before any real path value can be opened,
  read, parsed, hashed, captured, or used for socket, manifest, probe, or real
  MCP call setup.
- Disabled local MCP config path controlled read final dry-run records linked to
  controlled read approval evidence before any real path value can be opened,
  read, parsed, hashed, captured, or used for socket, manifest, probe, or real
  MCP call setup.
- Disabled local MCP config path sealed read request records linked to
  controlled read final dry-run evidence before any real path value can be
  opened, read, parsed, hashed, redacted, schema-validated, captured, or used
  for socket, manifest, probe, or real MCP call setup.
- Disabled local MCP config path sealed read approval records linked to sealed
  read request evidence before any real path value can be opened, read, parsed,
  hashed, redacted, schema-validated, captured, or used for socket, manifest,
  probe, or real MCP call setup.
- Disabled local MCP config path sealed read final dry-run records linked to
  sealed read approval evidence before any real path value or config content
  can be opened, read, parsed, hashed, redacted, schema-validated, captured, or
  used for socket, manifest, probe, or real MCP call setup.
- Disabled local MCP config path sealed content redaction/schema preflight
  records linked to sealed read final dry-run evidence before any real config
  content can be opened, read, parsed, hashed, redacted, schema-validated,
  captured, or used for socket, manifest, probe, or real MCP call setup.
- Disabled local MCP config path sealed content final redaction/schema dry-run
  records linked to sealed content preflight evidence before any real config
  content can be opened, read, parsed, hashed, redacted, schema-validated,
  captured, or used for socket, manifest, probe, or real MCP call setup.
- Disabled local MCP config path sealed config content read approval records
  linked to sealed content final dry-run evidence before any real config
  content can be opened, read, parsed, hashed, redacted, schema-validated,
  captured, or used for socket, manifest, probe, or real MCP call setup.
- Disabled local MCP sealed config content read final dry-run records linked
  to sealed config content read approval evidence before any real config
  content can be opened, read, parsed, hashed, redacted, schema-validated,
  captured, or used for socket, manifest, probe, or real MCP call setup.
- Disabled local MCP sealed config content read execution-preflight records
  linked to sealed config content read final dry-run evidence before any real
  config content can be opened, read, parsed, hashed, redacted,
  schema-validated, captured, or used for socket, manifest, probe, or real MCP
  call setup.
- Disabled local MCP sealed config content read audit/recovery pre-execution
  records linked to execution-preflight evidence before any real config content
  can be opened, read, parsed, hashed, redacted, schema-validated, captured,
  exported, or used for socket, manifest, probe, or real MCP call setup.
- Disabled local MCP sealed config content read final approval records linked
  to audit/recovery pre-execution evidence before any real config content can
  be opened, read, parsed, hashed, redacted, schema-validated, captured,
  exported, or used for socket, manifest, probe, or real MCP call setup.
- Disabled local MCP sealed config content read final execution dry-run
  records linked to final approval evidence before any real config content can
  be opened, read, materialized, parsed, hashed, redacted, schema-validated,
  captured, exported, or used for socket, manifest, probe, or real MCP call
  setup.
- Disabled local MCP sealed config content read redaction/schema validation
  dry-run records linked to final execution dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read parse/hash dry-run records
  linked to redaction/schema validation dry-run evidence before any real config
  content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read content-shape policy dry-run
  records linked to parse/hash dry-run evidence before any real config content
  can be opened, read, materialized, parsed, hashed, redacted, schema-validated,
  captured, exported, or used for socket, manifest, probe, or real MCP call
  setup.
- Disabled local MCP sealed config content read structural-intent dry-run
  records linked to content-shape policy dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read field-inventory dry-run
  records linked to structural-intent dry-run evidence before any real config
  content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read key-presence dry-run records
  linked to field-inventory dry-run evidence before any real config content can
  be opened, read, materialized, parsed, hashed, redacted, schema-validated,
  captured, exported, or used for socket, manifest, probe, or real MCP call
  setup.
- Disabled local MCP sealed config content read key-requirement dry-run records
  linked to key-presence dry-run evidence before any real config content can be
  opened, read, materialized, parsed, hashed, redacted, schema-validated,
  captured, exported, or used for socket, manifest, probe, or real MCP call
  setup.
- Disabled local MCP sealed config content read key-value-shape dry-run records
  linked to key-requirement dry-run evidence before any real config content can
  be opened, read, materialized, parsed, hashed, redacted, schema-validated,
  captured, exported, or used for socket, manifest, probe, or real MCP call
  setup.
- Disabled local MCP sealed config content read value-contract dry-run records
  linked to key-value-shape dry-run evidence before any real config content can
  be opened, read, materialized, parsed, hashed, redacted, schema-validated,
  captured, exported, or used for socket, manifest, probe, or real MCP call
  setup.
- Disabled local MCP sealed config content read value-redaction-map dry-run records
  linked to value-contract dry-run evidence before any real config content can
  be opened, read, materialized, parsed, hashed, redacted, schema-validated,
  captured, exported, or used for socket, manifest, probe, or real MCP call
  setup.
- Disabled local MCP sealed config content read schema-key-map dry-run records
  linked to value-redaction-map dry-run evidence before any real config content
  can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-binding dry-run records
  linked to schema-key-map dry-run evidence before any real config content can
  be opened, read, materialized, parsed, hashed, redacted, schema-validated,
  captured, exported, or used for socket, manifest, probe, or real MCP call
  setup.
- Disabled local MCP sealed config content read schema-validation-plan dry-run
  records linked to schema-binding dry-run evidence before any real config
  content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture dry-run
  records linked to schema-validation-plan dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-coverage dry-run
  records linked to schema-validation-fixture dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, or used for socket, manifest, probe, or
  real MCP call setup.
- SSWP health, capability, gated-call, and recovery lane
- Disabled local MCP sealed config content read schema-validation-fixture-coverage-report dry-run
  records linked to schema-validation-fixture-coverage dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-report-archive dry-run
  records linked to schema-validation-fixture-coverage-report dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, archived, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-archive-retention dry-run
  records linked to schema-validation-fixture-report-archive dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, archived, retained, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-review dry-run
  records linked to schema-validation-fixture-archive-retention dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, archived, retained, reviewed, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-signoff dry-run
  records linked to schema-validation-fixture-retention-review dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, archived, retained, reviewed, signed off, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-signoff-finalization dry-run
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-gate dry-run
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-approval dry-run
  records linked to schema-validation-fixture-retention-release-gate dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, archived, retained, reviewed, signed off, finalized, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-gate dry-run
  records linked to schema-validation-fixture-retention-release-approval dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, archived, retained, reviewed, signed off, finalized, released, release-approved, publication-gated, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-approval dry-run
  records linked to schema-validation-fixture-retention-release-publication-gate dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, archived, retained, reviewed, signed off, finalized, released, release-approved, publication-gated, publication-approved, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-finalization dry-run
  records linked to schema-validation-fixture-retention-release-publication-approval dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, archived, retained, reviewed, signed off, finalized, released, release-approved, publication-approved, publication-finalized, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-gate dry-run
  records linked to schema-validation-fixture-retention-release-publication-finalization dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, archived, retained, reviewed, signed off, finalized, released, release-approved, publication-approved, publication-finalized, publication-release-gated, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-approval dry-run
  records linked to schema-validation-fixture-retention-release-publication-release-gate dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, archived, retained, reviewed, signed off, finalized, released, release-approved, publication-approved, publication-finalized, publication-release-gated, publication-release-approved, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-finalization dry-run
  records linked to schema-validation-fixture-retention-release-publication-release-approval dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, archived, retained, reviewed, signed off, finalized, released, release-approved, publication-approved, publication-finalized, publication-release-gated, publication-release-approved, publication-release-finalized, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-completion-review dry-run
  records linked to schema-validation-fixture-retention-release-publication-release-finalization dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, archived, retained, reviewed, signed off, finalized, released, release-approved, publication-approved, publication-finalized, publication-release-gated, publication-release-approved, publication-release-finalized, publication-release-completion-reviewed, or used for socket, manifest, probe, or
  real MCP call setup.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-review dry-run
  records linked to schema-validation-fixture-retention-release-publication-release-completion-review dry-run evidence before any real
  config content can be opened, read, materialized, parsed, hashed, redacted,
  schema-validated, captured, exported, archived, retained, reviewed, signed off, finalized, released, release-approved, publication-approved, publication-finalized, publication-release-gated, publication-release-approved, publication-release-finalized, publication-release-closure-reviewed, or used for socket, manifest, probe, or
  real MCP call setup.
- SSWP health, capability, gated-call, and recovery lane
- SSWP health, capability, gated-call, and recovery lane
- Omega Stenographer capture, search, transcript evidence, and export-policy lane
- Local MCP health ledgers that separate configured, probed, callable, failed, and recovery-required states
- Plugin manifest format
- Skill registry
- Connector adapters
- Browser and Linux Computer Use integration

### Phase 5: Omega/VERITAS Module Migration

- Port high-value modules to Rust where stable.
- Keep complex Python modules as sandboxed sidecars at first.
- Require explicit capability manifests for each module.
- Replace placeholder endpoints with real implementation or hidden disabled states.

### Phase 6: Security Hardening

- Capability-scoped filesystem access
- Command prefix allowlist with user approval
- Libsecret-backed key storage
- Tailscale-first remote access model
- No external assets by default
- Deterministic audit log and replay
- Gated self-modification only

### Phase 7: Packaging And QA

- Native `.deb`, `.rpm`, AppImage, and optional Nix
- Golden screenshot checks
- Route/command contract tests
- PTY smoke tests
- MCP smoke tests
- Manual Linux desktop workflow tests
- Installer/uninstaller validation

## Recommended First Implementation Branch

Branch purpose: create the Rust/Tauri skeleton and port only the visual shell plus the command contract stubs.

Allowed first files:

- new Rust/Tauri project files
- `docs/` architecture docs
- minimal frontend shell
- no migration of Python modules yet
- no changes to current Electron app files unless needed to document contract extraction

Why this first:

- It avoids polluting the existing working app.
- It proves Linux-native packaging early.
- It lets the current app remain a reference implementation.
- It forces route/IPC/tool contracts to be explicit before feature migration.

## Open Questions For The Next Phase

- Should the rebuild live inside this repo as `rust/` or in a fresh repo/branch?
- Should Monaco remain mandatory, or can the first Rust build ship with a simpler editor and add Monaco later?
- Which modules are truly valuable enough to port versus archive?
- Should Omega Brain be the canonical memory store, replacing the local `backend/data/vault.db` split? Current rebuild direction says yes unless live evidence forces a split.
- Which SSWP and Omega Stenographer capabilities should ship first: health/status, search, capture, export policy, or full gated calls?
- Should mobile pairing be Tailscale-only from day one?
- Should the media player remain inside Gravity Omega or become a plugin?

## Audit Verdict

Gravity Omega has a compelling product identity and a large amount of useful capability, but the current implementation is a Windows/WSL Electron/Python system with partial Linux patches. The rebuild should preserve the Omega command-center experience and the VERITAS evidence posture while moving execution, approvals, files, terminals, MCP, SSWP, Omega Stenographer, memory, and packaging into a native Rust/Linux core.

The right next move is not to patch every broken endpoint in place. The right next move is to freeze the contract, create a Rust/Tauri shell, and migrate features in verified slices.

- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-approval dry-run
  - Added closure-approval dry-run evidence records linked to ready publication-release-closure-review evidence. The slice keeps real config reads, content capture/materialization, parse/hash/redact/schema validation, archive/retention/review/signoff/finalization/release/publication/release-closure-approval/export/socket/live-call/write/execution gates disabled.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-finalization dry-run
  - Added closure-finalization dry-run evidence records linked to ready publication-release-closure-approval evidence. The slice keeps real config reads, content capture/materialization, parse/hash/redact/schema validation, archive/retention/review/signoff/finalization/release/publication/release-closure-finalization/export/socket/live-call/write/execution gates disabled.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-completion-review dry-run
  - Added closure-completion-review dry-run evidence records linked to ready publication-release-closure-finalization evidence. The slice keeps real config reads, content capture/materialization, parse/hash/redact/schema validation, archive/retention/review/signoff/finalization/release/publication/release-closure-completion-review/export/socket/live-call/write/execution gates disabled.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-readiness dry-run
  - Added closure-release-readiness dry-run evidence records linked to ready publication-release-closure-completion-review evidence. The slice keeps real config reads, content capture/materialization, parse/hash/redact/schema validation, archive/retention/review/signoff/finalization/release/publication/release-closure-release-readiness/export/socket/live-call/write/execution gates disabled.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-approval dry-run
  - Added closure-release-approval dry-run evidence records linked to ready publication-release-closure-release-readiness evidence. The slice keeps real config reads, content capture/materialization, parse/hash/redact/schema validation, archive/retention/review/signoff/finalization/release/publication/release-closure-release-approval/export/socket/live-call/write/execution gates disabled.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-finalization dry-run
  - Added closure-release-finalization dry-run evidence records linked to ready publication-release-closure-release-approval evidence. The slice keeps real config reads, content capture/materialization, parse/hash/redact/schema validation, archive/retention/review/signoff/finalization/release/publication/release-closure-release-finalization/export/socket/live-call/write/execution gates disabled.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-completion-review dry-run
  - Added closure-release-completion-review dry-run evidence records linked to ready publication-release-closure-release-finalization evidence. The slice keeps real config reads, content capture/materialization, parse/hash/redact/schema validation, archive/retention/review/signoff/finalization/release/publication/release-closure-release-completion-review/export/socket/live-call/write/execution gates disabled.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-release-readiness dry-run
  - Added closure-release-release-readiness dry-run evidence records linked to ready publication-release-closure-release-completion-review evidence. The slice keeps real config reads, content capture/materialization, parse/hash/redact/schema validation, archive/retention/review/signoff/finalization/release/publication/release-closure-release-release-readiness/export/socket/live-call/write/execution gates disabled.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-release-approval dry-run
  - Added closure-release-release-approval dry-run evidence records linked to ready publication-release-closure-release-release-readiness evidence. The slice keeps real config reads, content capture/materialization, parse/hash/redact/schema validation, archive/retention/review/signoff/finalization/release/publication/release-closure-release-release-approval/export/socket/live-call/write/execution gates disabled.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization dry-run
  - Added closure-release-release-finalization dry-run evidence records linked to ready publication-release-closure-release-release-approval evidence. The slice keeps real config reads, content capture/materialization, parse/hash/redact/schema validation, archive/retention/review/signoff/finalization/release/publication/release-closure-release-release-finalization/export/socket/live-call/write/execution gates disabled.
- Disabled local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-release-completion-review dry-run
  - Added closure-release-release-completion-review dry-run evidence records linked to ready publication-release-closure-release-release-finalization evidence. The slice keeps real config reads, content capture/materialization, parse/hash/redact/schema validation, archive/retention/review/signoff/finalization/release/publication/release-closure-release-release-completion-review/export/socket/live-call/write/execution gates disabled.
- Replacement app foundation scorecard
  - Added a read-only scorecard that keeps the non-redundant replacement-app foundation visible across Codex, Hermes, Omega Brain, SSWP, Omega Stenographer, Codex pet, workspace/editor, terminal/process, approval/evidence, and Linux desktop lanes. It is intentionally not another config-read dry-run layer: live probes, MCP calls, capture, export, desktop control, terminal/process spawning, file writes, patch application, memory writes, and execution all remain disabled.
- Replacement app work queue
  - Added a compact read-only work queue that ranks the next safe slices from the foundation scorecard: workspace/editor, Codex/Hermes run view, first-class MCP dashboard, Steno evidence, pet companion, terminal supervisor, approval/evidence spine, and Linux desktop control. The queue is a product navigation primitive only; live probes, MCP calls, capture, export, desktop control, process spawning, file writes, patch application, memory writes, and execution remain disabled.
- Codex/Hermes run view dashboard
  - Added a product-facing read-only run view that groups existing task runs, approvals, runner readiness, joint plans, artifact preview status, transcript bundles, export/protection policies, and typed event logs into one Codex/Hermes operator surface. It creates no records and keeps process spawn, terminal control, live MCP calls, file writes, patch application, desktop control, capture, export, memory writes, and execution disabled.
- Codex/Hermes run detail timeline
  - Added a product-facing read-only per-run timeline that binds the active task run to linked approvals, runner readiness, joint plans, artifact preview, typed event logs, transcript bundles, export policies, and protection policies. It creates no records and keeps process spawn, terminal control, live MCP calls, file writes, patch application, desktop control, capture, export, memory writes, and execution disabled.
- Codex/Hermes run selection comparison
  - Added a product-facing read-only run selection and comparison board that lists task-run options and compares active-run Codex, Hermes, and Gravity Omega evidence lanes across planned phases, runner readiness, process plans, typed events, transcript bundles, export policies, and protection policies. It creates no records, changes no selected run state, and keeps process spawn, terminal control, live MCP calls, file writes, patch application, desktop control, capture, export, memory writes, and execution disabled.
- Codex/Hermes evidence diff board
  - Added a product-facing read-only evidence diff board that turns the run selection comparison into Codex-vs-Hermes parity gaps across planned phases, runner readiness, process plans, typed events, transcript bundles, export policies, protection policies, and total ready evidence. It creates no records, changes no selected run state, and keeps process spawn, terminal control, live MCP calls, file writes, patch application, desktop control, capture, export, memory writes, and execution disabled.
- Codex/Hermes reconciliation checklist
  - Added a product-facing read-only reconciliation checklist that consumes evidence diff records, marks balanced metrics ready, marks gaps action-required, and includes Gravity Omega reconciliation evidence. It creates no records, resolves no gaps, changes no selected run state, and keeps process spawn, terminal control, live MCP calls, file writes, patch application, desktop control, capture, export, memory writes, and execution disabled.
- Codex/Hermes reconciliation action plan
  - Added a product-facing read-only reconciliation action plan that consumes action-required checklist items, ranks close-gap actions, and shows missing evidence counts plus blocked operator next steps. It creates no records, assigns no actions, resolves no gaps, changes no selected run state, and keeps process spawn, terminal control, live MCP calls, file writes, patch application, desktop control, capture, export, memory writes, and execution disabled.
- Codex/Hermes evidence attachment preview
  - Added a product-facing read-only evidence attachment preview that consumes reconciliation action-plan records and lists blocked Hermes-side evidence attachments by source action, metric, attachment kind, and missing proof count. It attaches no evidence, uploads nothing, creates no records, resolves no gaps, changes no selected run state, and keeps process spawn, terminal control, live MCP calls, config reads, sockets, file writes, patch application, desktop control, capture, export, memory writes, and execution disabled.
- Codex/Hermes evidence attachment approval packet
  - Added a product-facing read-only evidence attachment approval packet that consumes blocked attachment previews and maps each Hermes-side proof need to an explicit operator approval requirement. It creates no approval records, resolves no approvals, attaches no evidence, uploads nothing, creates no records, changes no selected run state, and keeps process spawn, terminal control, live MCP calls, config reads, sockets, file writes, patch application, desktop control, capture, export, memory writes, and execution disabled.
- Codex/Hermes evidence intake workbench
  - Added a product-facing read-only evidence intake workbench that consumes approval packets and previews disabled intake forms, required fields, missing proof counts, and blocked submit state for each Hermes-side gap. It submits no forms, creates no approval records, resolves no approvals, attaches no evidence, uploads nothing, creates no records, changes no selected run state, and keeps process spawn, terminal control, live MCP calls, config reads, sockets, file writes, patch application, desktop control, capture, export, memory writes, and execution disabled.
- Codex/Hermes evidence validation summary
  - Added a product-facing read-only evidence validation summary that consumes intake workbench forms and previews missing field values, missing evidence records, approval state, evidence presence, validation readiness, and blocked submit eligibility for each Hermes-side gap. It validates no live evidence, submits no forms, creates no approval records, resolves no approvals, attaches no evidence, uploads nothing, creates no records, changes no selected run state, and keeps process spawn, terminal control, live MCP calls, config reads, sockets, file writes, patch application, desktop control, capture, export, memory writes, and execution disabled.
- Codex/Hermes evidence operator confirmation dry-runs
  - Added a product-facing read-only evidence operator confirmation dry-run surface that consumes validation summaries and previews required acknowledgements, missing acknowledgement counts, validation readiness, missing proof totals, and blocked confirmation state for each Hermes-side gap. It records no confirmations, validates no live evidence, submits no forms, creates no approval records, resolves no approvals, attaches no evidence, uploads nothing, creates no records, changes no selected run state, and keeps process spawn, terminal control, live MCP calls, config reads, sockets, file writes, patch application, desktop control, capture, export, memory writes, and execution disabled.
- First-class MCP dashboard
  - Added a product-facing read-only MCP dashboard that groups Omega Brain, SSWP, and Omega Stenographer into native lanes with expected command ids, evidence depth, ready evidence counts, and current disabled status across existing local MCP ledgers. It creates no records and keeps live MCP calls, probes, config reads, sockets, Steno capture, export, file writes, patch application, process/terminal control, desktop control, memory writes, and execution disabled.
- Steno pet companion dashboard
  - Added a product-facing read-only Steno and Codex pet dashboard that groups transcript bundles, transcript export/protection policies, Omega Stenographer MCP evidence, agent capability inventory, and pet readiness into one operator surface. It creates no records and keeps Steno capture, transcript export, pet asset inspection/loading, live MCP calls, config reads, sockets, file writes, patch application, process/terminal control, desktop control, memory writes, and execution disabled.
- Terminal process lane dashboard
  - Added a product-facing read-only terminal/process dashboard that groups runner invocations, runner adapters, command plans, stream initialization, lifecycle, control policies, supervisor preflights, heartbeats, exit summaries, and output-tail evidence into one operator surface. It creates no records and keeps terminal writes, process spawning, stream reads, live tailing, process control, file writes, patch application, desktop control, live MCP calls, config reads, capture, export, memory writes, and execution disabled.
- Approval evidence spine dashboard
  - Added a product-facing read-only approval/evidence dashboard that unifies approval records, persisted gate decisions, artifact previews, typed event logs, local MCP call audits, consent/approval decisions, MCP audit outcomes, transcript export/protection policies, and terminal/process lane evidence. It creates no records and keeps mutation, file writes, patch application, process spawning, terminal control, desktop control, live MCP calls, sockets, config reads, capture, export, memory writes, and execution disabled.
- Linux desktop control readiness dashboard
  - Added a product-facing read-only Linux desktop control readiness dashboard that groups foundation/work-queue desktop lanes, agent capability inventory, first-class readiness, approval/evidence spine prerequisites, and browser/computer-use command-surface evidence. It creates no records and keeps screenshot capture, OCR, target-window actions, element actions, sockets, process spawning, terminal control, file writes, patch application, live MCP calls, config reads, export, memory writes, desktop control, and execution disabled.
- Desktop capture action approval policy dashboard
  - Added a product-facing read-only desktop capture/action approval policy dashboard that groups Linux desktop readiness, approval spine prerequisites, sandbox restrictions, browser/computer-use command-surface evidence, screenshot/OCR/window/action policy areas, and operator confirmation gates. It creates no records and keeps screenshot capture, OCR, target-window control, element actions, sockets, process spawning, terminal control, file writes, patch application, live MCP calls, config reads, export, memory writes, desktop control, and execution disabled.
- Desktop capture action approval records
  - Added product-facing read-only screenshot, OCR, target-window, and element-action approval records with required approval, evidence, operator confirmation, redaction, and retention metadata. They create no live approvals or desktop artifacts and keep capture, OCR, target-window control, element actions, sockets, process/terminal control, file writes, patch application, live MCP calls, config reads, export, memory writes, desktop control, and execution disabled.
- Desktop operator-confirmation dry-runs
  - Added product-facing read-only operator-confirmation dry-run records for screenshot, OCR, target-window, and element-action policies, including prompt text, dry-run summaries, required evidence, redaction, and retention metadata. They record no real approvals, inspect no desktop state, and keep capture, OCR, target-window control, element actions, sockets, process/terminal control, file writes, patch application, live MCP calls, config reads, export, memory writes, desktop control, and execution disabled.
- Desktop final pre-action dry-runs
  - Added product-facing read-only final pre-action dry-run records for screenshot, OCR, target-window, and element-action policies, making confirmed operator evidence the explicit blocker before any live desktop capability can be considered. They record no confirmed evidence, inspect no desktop state, and keep capture, OCR, target-window control, element actions, sockets, process/terminal control, file writes, patch application, live MCP calls, config reads, export, memory writes, desktop control, and execution disabled.
- Desktop action safety summary
  - Added a compact product-facing read-only summary tying the desktop policy dashboard, approval records, operator-confirmation dry-runs, final pre-action dry-runs, and per-capability safety matrix into one operator view. It records no confirmed evidence, inspects no desktop state, and keeps capture, OCR, target-window control, element actions, sockets, process/terminal control, file writes, patch application, live MCP calls, config reads, export, memory writes, desktop control, and execution disabled.
- Linux desktop readiness release checklist
  - Added a product-facing read-only release checklist tying Linux desktop readiness, desktop action safety, approval evidence, sandbox restricted policy, confirmed-operator evidence, and final release decision state into one operator view. It records no confirmed evidence, inspects no desktop state, and keeps capture, OCR, target-window control, element actions, sockets, process/terminal control, file writes, patch application, live MCP calls, config reads, export, memory writes, desktop control, and execution disabled.
- Workspace editor navigation lane
  - Added a compact read-only navigation surface that links existing workspace inspection, preview, tree metadata, file preview, editor tab, edit/save preflight, write policy, approval, buffer draft, and dirty-state preflight records. It only counts persisted records and keeps config reads, live MCP calls, capture, export, desktop control, terminal/process spawning, file writes, patch application, memory writes, and execution disabled.
- Workspace editor shell layout
  - Added a read-only editor-shell layout model that turns the navigation lane into workspace tree, file preview, tab buffer, and mutation-gate panels. It is derived from persisted record counts only and keeps sockets, config reads, live MCP calls, capture, export, desktop control, terminal/process spawning, file writes, patch application, memory writes, and execution disabled.
- Workspace editor shell bindings
  - Added read-only bindings from shell panels to existing summary and ledger UI element ids, including cross-panel dependency metadata. The bindings create no records and keep sockets, config reads, live MCP calls, capture, export, desktop control, terminal/process spawning, file writes, patch application, memory writes, and execution disabled.
- Workspace editor shell focus model
  - Added a read-only focus model that chooses the active editor-shell navigation target from existing bindings, preferring tab buffer, then file preview, workspace tree, and mutation gates. The model returns metadata only and keeps sockets, config reads, live MCP calls, capture, export, desktop control, terminal/process spawning, file writes, patch application, memory writes, and execution disabled.
- Workspace editor keyboard navigation map
  - Added a read-only keyboard traversal map derived from the focus model, including previous/next panel targets and reserved key hints for `Alt+Up`, `Alt+Down`, `Home`, and `End`. The map installs no key listeners, moves no focus, creates no records, and keeps sockets, config reads, live MCP calls, capture, export, desktop control, terminal/process spawning, file writes, patch application, memory writes, and execution disabled.
- Workspace editor command palette map
  - Added a read-only command palette map derived from keyboard navigation, listing disabled panel-scoped command intents for tab buffer, file preview, workspace tree, and mutation gates. The palette binds no hotkeys or actions, creates no records, and keeps sockets, config reads, live MCP calls, capture, export, desktop control, terminal/process spawning, file writes, patch application, memory writes, and execution disabled.
- Workspace editor command search map
  - Added a read-only grouped command discovery map derived from the palette, covering editor buffer, preview, workspace tree, and safety gate command groups with static search tokens. The search map binds no query inputs, hotkeys, or actions, creates no records, and keeps sockets, config reads, live MCP calls, capture, export, desktop control, terminal/process spawning, file writes, patch application, memory writes, and execution disabled.
- Workspace files dashboard
  - Added a product-facing read-only workspace files dashboard that consumes workspace inspections, previews, tree metadata, file previews, editor tabs, edit/save preflights, write policy and approval evidence, buffer drafts, dirty-state preflights, and mutable-buffer transaction evidence. It turns the contracted `workspace-files` lane into a scaffolded surface for scoped boundary, list, read, search-contract, watcher, and write/patch readiness while keeping live search, watchers, sockets, config reads, live MCP calls, capture, export, desktop control, terminal/process spawning, file writes, patch application, memory writes, workspace writes, and execution disabled.
- Core feature status reconciliation
  - Reconciled the feature migration contract with verified product-facing scaffold surfaces: `terminal`, `codex-operating-loop`, `mcp-and-plugins`, `sswp`, `omega-stenographer`, and `security-and-approvals` are marked `scaffolded` because they have read-only dashboards, contracts, tests, and disabled-gate evidence. The remaining VERITAS module lane is handled by the dashboard slice below. This does not enable terminal writes, process spawning, live MCP/SSWP/Steno calls, config reads, sockets, capture, export, desktop control, file writes, patch application, memory writes, workspace writes, or execution.
- VERITAS modules dashboard
  - Added a product-facing read-only VERITAS module migration dashboard that classifies the Flask/Python registry, describe endpoint, run route, document analyzer, vault context, security/Sentinel panels, provenance/evolution proposals, and media/tool modules as Rust-port, sandboxed-sidecar, or archive-review candidates. It records the `/execute` versus `/run` route mismatch while keeping module execution, Python bridge, sidecar spawn, MCP execute, config reads, sockets, file writes, patches, terminal/process control, desktop control, capture, export, memory writes, workspace writes, and execution disabled.
- Toolbar missing command closure
  - Reclassified the two remaining missing toolbar controls, `security.refresh` and `mobile.qr`, as explicit native command targets. `security.refresh` now maps to `security_scan` readiness through the live read-only toolbar intent surface and `mobile.qr` maps to gated `mobile_pairing_qr` readiness, so the toolbar registry has no unknown command holes while security scans, pairing QR generation, sockets, tunnels, writes, patches, terminal/process control, desktop control, capture, export, memory writes, workspace writes, and execution remain disabled.
- Toolbar dry-run actions
  - Added a dry-run button to every toolbar registry row. Each button resolves the toolbar command through the Rust `execute_command_stub` bridge in Tauri, or through a browser-preview fallback outside Tauri, and updates the Command Dry Run panel with blocked/gated evidence. This makes every toolbar row clickable and inspectable while live command execution, security scans, pairing QR generation, writes, patches, terminals, processes, MCP calls, desktop control, capture, export, memory writes, workspace writes, and execution remain disabled.
- Bundled docs and About panels
  - Promoted `help.docs` and `help.about` to live safe toolbar functions backed by Rust `docs_open` and `about_open` commands. They render static in-app metadata for doctrine, command contracts, rebuild audit, toolbar registry, feature registry, runtime identity, scaffold scope, and disabled safety gates while keeping external openers, browser launches, network, file/config reads, MCP calls, sockets, writes, patches, terminals, processes, desktop control, capture, export, memory writes, workspace writes, and execution disabled.
- Live command palette surface
  - Promoted `command.palette` to a live safe toolbar function backed by Rust `command_palette_open`. The new in-app panel lists command groups and all 33 toolbar commands with targets, states, safety tiers, and reasons while keeping command execution, hotkeys, selection mutation, searches, file/config reads, MCP calls, sockets, writes, patches, terminals, processes, desktop control, capture, export, memory writes, workspace writes, and execution disabled.
- Live terminal panel toggle
  - Promoted `terminal.toggle` to a live safe toolbar function backed by Rust `terminal_toggle`. It opens the existing terminal/process lane as a read-only evidence panel and reuses dashboard metadata while keeping PTY creation, terminal writes, stream reads, live tailing, signals, process spawn, terminal resize/kill, config reads, MCP calls, sockets, writes, patches, desktop control, capture, export, memory writes, workspace writes, and execution disabled.
- Live Find panel
  - Promoted `search.find` to a live safe toolbar function backed by Rust `editor_find`. It opens an in-app Find panel with static search scopes for current buffer, open tabs, workspace preview, and command registry while keeping query binding, focus movement, buffer reads, live workspace search, replace, file/config reads, MCP calls, sockets, writes, patches, desktop control, capture, export, memory writes, workspace writes, and execution disabled.
- Live SSWP status panel
  - Promoted `mcp.sswp_status` to a live safe toolbar function backed by Rust `sswp_status`. It narrows the first-class MCP dashboard to the SSWP evidence lane and renders SSWP evidence counts, expected command ids, readiness status, and disabled-gate posture while keeping live MCP probes, SSWP calls, capability discovery, config reads, sockets, capture, export, writes, patches, memory writes, desktop control, terminal/process control, workspace writes, and execution disabled.
- Live Steno Search panel
  - Promoted `steno.search` to a live safe toolbar function backed by Rust `steno_search`. It reuses the Steno/pet companion dashboard to render transcript-bundle readiness, transcript-protection readiness, Omega Stenographer evidence, and disabled-gate posture while keeping transcript reads, live transcript indexing/search, query binding, Steno capture, transcript export, MCP calls, config reads, sockets, writes, patches, memory writes, desktop control, terminal/process control, workspace writes, and execution disabled.
- Toolbar action readiness center
  - Added `toolbar_action_readiness`, a read-only Rust bridge and UI panel that makes every remaining non-live toolbar row clickable as a readiness surface. It classifies the command family, shows target mapping, verification contract, approval/evidence prerequisites, and sealed gates while keeping target command execution, approvals, audit writes, file pickers, workspace file reads, writes, patches, terminal/process control, desktop control, MCP calls, config reads, sockets, capture, export, memory writes, workspace writes, and execution disabled.
- Safe toolbar intent promotion
  - Promoted safe disabled toolbar rows to live read-only intent surfaces through the readiness center: `file.new`, `window.new`, `file.open`, `workspace.open_folder`, `app.exit`, `edit.undo`, `edit.redo`, `window.fullscreen`, `security.refresh`, and `agent.codex_review`. These buttons now open readiness evidence while keeping file/folder pickers, buffer creation, app exit, undo/redo mutation, fullscreen mutation, native security scans, Codex execution, writes, patches, workspace reads, terminal/process control, desktop control, MCP calls, config reads, sockets, capture, export, memory writes, workspace writes, and execution disabled.
- First-class integration launchpad
  - Promoted the final four disabled first-class toolbar rows, `agent.hermes_companion`, `agent.joint_ci`, `mcp.sswp_call`, and `steno.capture`, to live read-only launchpad surfaces backed by `first_class_integration_launchpad`. The launchpad makes Hermes companion, Joint Codex/Hermes CI, SSWP calls, and Steno capture inspectable from the toolbar while keeping Hermes process start, Codex/Hermes execution, SSWP live MCP calls, Steno capture, transcript reads, config reads, sockets, terminal/process control, desktop control, file reads, writes, patches, export, memory writes, workspace writes, and execution disabled.
- Gated action release board
  - Added `gated_action_release_board`, a read-only product-facing release board for the remaining 12 gated toolbar actions. It groups save/save-as/replace, terminal creation, devtools, Gravity Shield/Void/Basilisk controls, and mobile pairing QR generation by release lane with approval, dry-run, rollback, and evidence requirements while keeping approvals, file saves, text replacement, terminal creation, devtools mutation, security actions, QR generation, config reads, sockets, MCP calls, desktop control, capture, export, memory writes, workspace writes, patches, and execution disabled.
- Gated adapter release pipeline
  - Added `gated_adapter_release_queue`, `create_gated_adapter_release_packet_stub`, and `list_gated_adapter_release_packets`. The queue ranks all 12 remaining gated toolbar rows across workspace mutation, terminal/process, security shield, and native shell/pairing into concrete adapter candidates, and the packet recorder writes durable XDG app-state evidence while keeping live adapters, workspace writes, PTYs, process spawning, terminal input, shield actions, devtools toggles, QR/token generation, desktop control, MCP calls, config reads, sockets, capture, export, memory writes, patches, and execution disabled.
- Workspace mutation workbench
  - Added `workspace_mutation_workbench`, a read-only product-facing operator workflow for `file.save`, `file.save_as`, and `search.replace`. It exposes preview, approval policy, approval evidence, writable-buffer draft, dirty-transition preflight, mutable-buffer transaction, diff/rollback, and final-confirmation stages while keeping workspace file reads, approvals, audit writes, file saves, text replacement, dialogs, patches, terminal/process control, desktop control, MCP calls, config reads, sockets, capture, export, memory writes, workspace writes, and execution disabled.
- Terminal process workbench
  - Added `terminal_process_workbench`, a read-only product-facing operator workflow for `terminal.new`. It exposes command plan, sandbox match, approval evidence, PTY allocation policy, stream initialization, lifecycle, control policy, supervisor heartbeat, output evidence, and exit-summary stages while keeping PTY allocation, terminal input, process spawning, stream reads, live tailing, process control, kill/resize actions, file writes, patches, desktop control, MCP calls, config reads, sockets, capture, export, memory writes, workspace writes, and execution disabled.
- Security shield workbench
  - Added `security_shield_workbench`, a read-only product-facing operator workflow for Gravity Shield, Infinite Void, and Basilisk gated controls. It exposes host-impact, operator/YubiKey confirmation, privilege-boundary, rollback, audit-evidence, post-action verification, and final-release stages while keeping shield start/stop, containment changes, privileged commands, sudo/YubiKey prompts, terminal/process control, desktop control, file writes, patches, MCP calls, config reads, sockets, capture, export, memory writes, workspace writes, and execution disabled.
- Native shell pairing workbench
  - Added `native_shell_pairing_workbench`, a read-only product-facing operator workflow for `developer.devtools` and `mobile.qr`. It exposes operator intent, release policy, session indicator, token/scope policy, audit evidence, revocation/cleanup, and final-release stages while keeping devtools toggles, debug shell exposure, QR generation, pairing token generation, sockets, mobile pairing, config reads, terminal/process control, desktop control, file writes, patches, MCP calls, capture, export, memory writes, workspace writes, and execution disabled.
- Agent composer draft run
  - Replaced the dead right-rail composer placeholder with an enabled draft surface that records blocked `joint_ci` OmegaTaskRun stubs through `create_task_run_stub`, refreshes the task-run ledger, artifact preview, Codex/Hermes run view, and command resolution panel, and shows explicit draft-only status. It keeps live Codex/Hermes execution, shell/terminal/process spawning, MCP calls, file reads, file writes, patches, sockets, desktop control, capture, export, memory writes, workspace writes, and execution disabled.
- Resizable bottom evidence dock
  - Added a sticky bottom evidence dock with pointer and keyboard resizing, persisted 100-400px height, task-run mirror, artifact-tail preview, and a sync action. It directly addresses the fixed bottom-panel UX problem while keeping PTY allocation, terminal input, process spawning, live artifact streaming, file reads, file writes, patches, MCP calls, config reads, sockets, desktop control, capture, export, memory writes, workspace writes, and execution disabled.
- Activity rail icon system
  - Replaced the temporary `C/W/V/S/P/R` activity rail letters with local line-icon controls, screen-reader-only labels, explicit `aria-label` values, focus-visible support, and active-state rails. The existing area switching is preserved while command execution, file operations, MCP calls, terminal/process control, desktop control, capture, export, memory writes, workspace writes, and execution remain disabled.
- Toolbar registry search
  - Added a client-side toolbar registry search input that filters already-loaded toolbar commands by id, label, current action, target command, state, capability tier, reason, and verification text while preserving each row's safe dry-run/open button. It performs no workspace search, file reads, config reads, MCP calls, network fetches, terminal/process control, desktop control, capture, export, memory writes, workspace writes, patches, or execution.
- Global command search shortcut
  - Added `Ctrl+K` / `Cmd+K` as an ergonomic shortcut that switches to the Command area and focuses/selects the toolbar registry search input. It only navigates local UI state and searches already-loaded command metadata; it does not dispatch commands, search workspace files, read config, call MCP servers, spawn terminals/processes, control the desktop, capture, export, write memory, write workspace files, apply patches, or execute anything.
- Finish Pass 1 runtime probe substrate
  - Added `runtime_probe_board`, a real bounded Rust/Tauri probe bridge for local Python, Node, ffmpeg, ffprobe, Cargo, Codex, Hermes, and Chrome version checks. The UI exposes manual Runtime Probes controls and evidence rows with required-runtime blockers while keeping sidecar launches, PTYs, terminal input, arbitrary shell execution, workspace reads/writes, config reads, MCP calls, sockets, desktop control, capture, export, memory writes, patches, and task execution disabled.
- Finish Pass 2 runtime launch packet pipeline
  - Added `create_runtime_launch_packet_stub` and `list_runtime_launch_packets`, converting passing bounded runtime probes into persisted XDG launch-packet evidence records for approval review. The UI now records and lists Runtime Launch Packets while keeping Codex, Hermes, Python, browser, media, terminal, MCP, SSWP, Steno, desktop, pet sidecars, PTYs, terminal input, arbitrary shell execution, workspace reads/writes, config reads, MCP calls, sockets, desktop control, capture, export, memory writes, patches, and task execution disabled.
- Finish Pass 3 joint run packet bridge
  - Added `create_joint_runtime_run_packet_stub` and `list_joint_runtime_run_packets`, linking OmegaTaskRun drafts with Codex/Hermes runtime launch packets into persisted joint run envelopes. Missing runtime packets are surfaced as blockers in the Joint Run Packet Ledger while Codex/Hermes execution, PTYs, shell commands, MCP calls, workspace reads/writes, patches, sockets, desktop control, capture, export, memory writes, and sidecar launches remain disabled.
- Finish Pass 4 runner evidence spine
  - Added `create_runner_evidence_spine_stub` and `list_runner_evidence_spines`, collapsing task, approval, runner, joint plan, typed events, workspace lease, runner adapter, Codex/Hermes process plans, stream files, lifecycles, control policies, supervisor heartbeats, exit summaries, output-tail summaries, transcript bundles, export policies, and protection policies into one product-facing Runner Spine Ledger action. It records complete Codex and Hermes pre-execution evidence while process spawn, sidecar launch, PTY/terminal control, live output streaming, workspace reads/writes, patches, sockets, MCP calls, desktop control, capture, export, memory writes, and execution remain disabled.
- Finish Pass 5 supervised runtime runner
  - Added `run_supervised_runtime_smoke` and `list_supervised_runtime_smokes`, moving the process-supervisor lane from pre-execution evidence into real bounded process supervision. The command may spawn only existing hard-coded runtime probe targets, clamps timeout to 500-10000ms, records PID/exit/timeout/duration evidence, and captures stdout/stderr transcripts under XDG app state. It keeps arbitrary shell execution, Codex/Hermes task execution, sidecar launch, PTY/terminal control, workspace reads/writes, patches, sockets, MCP calls, desktop control, capture, export, memory writes, and writes disabled.
- Finish Pass 6 live workspace explorer
  - Added `workspace_explorer_snapshot`, turning the workspace lane into a real scoped read-only explorer. It lists the rebuild workspace tree, skips `node_modules`, `target`, `.git`, and `.sswp` files, validates root containment inside the rebuild workspace, previews one UTF-8 text file with byte caps, and renders the live tree/preview in the UI while writes, patches, live search, watchers, process/terminal control, MCP calls, desktop control, sockets, config reads, capture, export, memory writes, and execution remain disabled.
- Finish Pass 7 Codex/Hermes transcript sessions
  - Added `run_agent_transcript_session` and `list_agent_transcript_sessions`, turning the agent lane into a supervised Codex/Hermes transcript surface. The command runs only fixed allowlisted `codex --version`, `codex --help`, `hermes --version`, and `hermes --help` sessions, captures PID/exit/timeout/duration plus stdout/stderr transcript files under XDG app state, and renders a product-facing Agent Session Ledger while arbitrary prompts, `codex exec`, `hermes chat`, sidecar launch, PTY/terminal control, workspace reads/writes, patches, live MCP calls, config reads, sockets, desktop control, capture, export, memory writes, and task execution remain disabled.
- Finish Pass 8 release candidate self-audit
  - Extended `replacement_app_ship_readiness` with a read-only release artifact audit for `target/release/gravity-omega-native`. The app now reports whether the release binary exists, its path, size, modified timestamp, artifact readiness, and remaining package/desktop-launcher/install gates in the finish-line UI while package generation, desktop entry creation, app launch, file writes, patches, terminal/process control, desktop control, sockets, exports, memory writes, and execution remain disabled.
- Finish Pass 9 Linux launcher package template
  - Added `packaging/gravity-omega-native.desktop` and `packaging/install-local-desktop-entry.sh` inside the rebuild scaffold. The launcher points at the verified release binary and bundled icon, and the install script can deliberately copy it into the user applications directory later. Validation now checks the launcher/template fields while desktop installation, GUI launch, package generation, current Electron app changes, `.sswp` writes, and execution remain disabled.
- Finish Pass 10 live launch smoke
  - Verified the release binary opens a real Linux desktop window under a bounded timeout. The compositor reported `title="Gravity Omega Native"` and `app_id="Gravity-omega-native"` while the process was live. No app controls were clicked and no desktop launcher was installed.
- Finish Pass 11 operator-unlocked agent prompt runner
  - Added `run_unlocked_agent_prompt_session` and `list_unlocked_agent_prompt_sessions`, plus UI buttons for Codex Write and Hermes real prompt runs. The runner accepts composer prompt text, spawns Codex workspace-write, Codex read-only, or Hermes quiet chat through fixed argv construction with stdin closed and bounded timeout, captures PID/exit/timeout/duration and stdout/stderr transcript files under XDG app state, and renders the Unlocked Agent Ledger. Codex Write intentionally enables workspace-write under the rebuild workspace; shell interpolation, `danger-full-access`, `codex apply`, desktop control, live MCP calls, config reads, transcript export, and memory writes are still not used.
- Finish Pass 12 app control unlock and launch
  - Promoted the release artifact lane from blocked launch readiness to operator-unlocked launch readiness when the release binary exists. The ship-readiness command now reports the desktop launcher template ready and launch/process/desktop-control/execution enabled for the release artifact while keeping installer execution separate and leaving the current Electron app untouched.
