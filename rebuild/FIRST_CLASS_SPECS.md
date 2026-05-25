# Gravity Omega Rust Rebuild — First-Class Feature Specs

## Scope

Inspected surfaces:
- `/home/rage/apps/gravity-omega-v2/omega/omega_mcp_server.js` — current MCP server implementation (SSE transport, tool definitions, session management)
- `/home/rage/apps/gravity-omega-v2/backend/mcp_client.py` — Python MCP client bridging to omega-command-center
- `/home/rage/apps/gravity-omega-v2/backend/web_server.py` — Flask backend with module registry, auth, vault, and security modules
- `/home/rage/apps/gravity-omega-v2/renderer/index.html` — UI panels hosting MCP/SSWP/Steno UI
- `/home/rage/apps/gravity-omega-v2/renderer/app.js` — panel switching, chat system, Trinity buttons (Seal/Witness/Attest), MCP health indicator
- `/home/rage/apps/gravity-omega-rust-rebuild/rebuild/gravity-omega-tauri/src-tauri/src/commands.rs` — Rust scaffold (124k lines, 304 commands, extensive stub structures for MCP, SSWP, Steno, Pet, Desktop, Terminal, Workspace)
- `/home/rage/apps/gravity-omega-v2/.sswp.json` and `gravity-omega.sswp.json` — existing SSWP attestations

---

## Findings

### 1. MCP First-Class Feature Specs

#### 1.1 Dashboard Design (What the User Sees)
The Rust rebuild must expose a **First-Class MCP Dashboard** (`first_class_mcp_dashboard` command already stubbed). The user sees:

- **Lane Cards**: One card per MCP subsystem (Omega Brain, SSWP, Stenographer, and any local MCPs discovered).
- **Health Dots**: Real-time status per MCP (green = healthy, yellow = degraded, red = down, gray = unknown).
- **Capability Contracts**: A scrollable list of tools/resources per MCP with their current availability state.
- **Activity Sparkline**: Recent call volume per MCP (last 60 minutes).
- **Last Seal Hash**: For Omega Brain, display the latest SEAL chain hash truncated to 16 chars.
- **Quick Actions**: "Probe Health", "Discover Capabilities", "View Audit Log" buttons per lane.

#### 1.2 Command List (Exact Commands/Tools Exposed)
The Rust backend must expose these **Tauri commands** (many already exist as stubs in `commands.rs`):

**Discovery & Health**
- `first_class_mcp_dashboard()` → `FirstClassMcpDashboard`
- `create_local_mcp_health_record_stub(request)` / `list_local_mcp_health_records()`
- `create_local_mcp_capability_discovery_policy_stub(request)` / `list_local_mcp_capability_discovery_policies()`
- `create_local_mcp_status_probe_preflight_stub(request)` / `list_local_mcp_status_probe_preflights()`

**Gated Execution**
- `create_local_mcp_gated_call_policy_stub(request)` / `list_local_mcp_gated_call_policies()`
- `create_local_mcp_call_approval_audit_stub(request)` / `list_local_mcp_call_approval_audits()`
- `create_local_mcp_consent_approval_decision_stub(request)` / `list_local_mcp_consent_approval_decisions()`
- `create_local_mcp_audit_outcome_stub(request)` / `list_local_mcp_audit_outcomes()`
- `create_local_mcp_recovery_precall_guard_stub(request)` / `list_local_mcp_recovery_precall_guards()`
- `create_local_mcp_final_call_approval_stub(request)` / `list_local_mcp_final_call_approvals()`
- `create_local_mcp_live_call_dry_run_stub(request)` / `list_local_mcp_live_call_dry_runs()`

**Typed Contracts**
- `create_local_mcp_typed_command_contract_stub(request)` / `list_local_mcp_typed_command_contracts()`
- `create_local_mcp_config_lookup_preflight_stub(request)` / `list_local_mcp_config_lookup_preflights()`
- `create_local_mcp_config_read_policy_stub(request)` / `list_local_mcp_config_read_policies()`

**Live Call (High-Risk)**
- A single unified `mcp_execute(server, tool, args)` command must exist, gated behind the approval pipeline. It is **not** in the current 304-command manifest as a live executor; it must be added.

#### 1.3 Health Checks (How to Probe Each MCP)
Each MCP lane must be probed via its native `status` or `health` tool:
- **Omega Brain**: Call `omega_brain_status` (JSON health snapshot) and `omega_ecosystem_status` (unified health of Brain + SSWP + Stenographer).
- **SSWP**: Call `sswp_registry_health` (fleet board) and `sswp_ledger` (audit trail).
- **Stenographer**: Call `stenographer_get_brief` (live running notes) and `stenographer_compact_guard` (compression check).
- **Local MCPs**: Call their `initialize` handshake and list tools/resources.

Probe frequency: every 60s background poll, plus on-demand when user opens dashboard.

#### 1.4 Approval Gates (Which MCP Calls Require Approval)
All MCP calls that are **not** read-only health probes require approval. The approval hierarchy (already modeled in `commands.rs`) is:

1. **Capability Discovery** (read-only) → No approval.
2. **Health Probe** (read-only) → No approval.
3. **Config Read** (read-only, but reads local files) → Requires `LocalMcpConfigReadPolicy` approval.
4. **RAG Query / Vault Search** (read-only, but accesses memory) → Requires `LocalMcpGatedCallPolicy` approval.
5. **Ingest / Seal / Log Session** (write to Brain) → Requires `LocalMcpCallApprovalAudit` + `LocalMcpFinalCallApproval`.
6. **SSWP Witness / Bulk Witness** (write attestation) → Requires `LocalMcpFinalCallApproval` + operator confirmation.
7. **Live `mcp_execute` with side effects** (e.g., `omega_execute`, `sswp_witness`) → Requires full pipeline: `RecoveryPrecallGuard` → `GatedCallPolicy` → `LiveCallDryRun` → `FinalCallApproval`.

#### 1.5 Config Handling
- Config path: `$APP_CONFIG_DIR/mcp/servers.json`.
- Schema: array of `{name, transport, command, args, env, enabled, approval_tier}`.
- Transport types: `stdio` (spawn process), `sse` (connect to URL), `tauri-sidecar` (embedded binary).
- The Rust backend must validate config against a JSON Schema on load.
- Secrets (API keys) must be stored in the OS keyring (via `keyring` crate), referenced by key ID in config, never inline.

#### 1.6 Live-Call Prerequisites
Before any live MCP call is permitted:
- [ ] MCP server health probe returned `ok` within last 5 minutes.
- [ ] Capability discovery has confirmed the tool exists.
- [ ] Typed command contract has been generated for the (server, tool) pair.
- [ ] Gated call policy exists and is not in `blocked` state.
- [ ] If write-side: `RecoveryPrecallGuard` passed (checks for previous crash/uncommitted state).
- [ ] If write-side: `LiveCallDryRun` stub was created and validated.
- [ ] `FinalCallApproval` record exists with `approved: true` and not expired (15-minute TTL).

#### 1.7 Safe/Gated/Restricted Boundaries Per MCP
| MCP | Safe (no approval) | Gated (approval required) | Restricted (blocked by default) |
|-----|-------------------|--------------------------|--------------------------------|
| Omega Brain | `omega_brain_status`, `omega_ecosystem_status`, `omega_rag_query` | `omega_ingest`, `omega_seal_run`, `omega_log_session`, `omega_write_handoff` | `omega_execute` (Cortex-governed execution wrapper) |
| SSWP | `sswp_registry_health`, `sswp_node_search`, `sswp_ledger`, `sswp_check_repo` | `sswp_witness`, `sswp_bulk_witness`, `sswp_export_to_omega` | `sswp_analyze_deps` (requires Kimi K2 key) |
| Stenographer | `stenographer_get_brief`, `stenographer_compact_guard`, `stenographer_query_history` | `stenographer_ingest_exchange`, `stenographer_mark_milestone` | — |
| Local MCPs | `list_tools`, `list_resources`, `status` | Any tool call with side effects | Any tool that writes files outside workspace |

---

### 2. SSWP + Stenographer Product UX

#### 2.1 SSWP Workflow UI (Better Than Codex/Hermes)
The current v2 has a basic "Attest" Trinity button. The rebuild must make SSWP a **first-class panel**.

**SSWP Fleet Health Board**
- Full-screen panel (not a sidebar) showing every witnessed node.
- Columns: Name, Status (active/deprecated/archived), Last Witness, Risk %, Adversarial Risk %, Attestation Hash.
- Sortable by risk descending.
- Color coding: >50% risk = red row, 25-50% = yellow, <25% = green.
- **Better-than-parity**: Click any node to open its **Attestation Timeline** — a visual diff of every `.sswp.json` version, showing when risk scores changed and why.

**Witness Workflow**
1. User selects a repo path (or auto-detects from open workspace).
2. UI shows **Pre-Witness Checklist**: `sswp_check_repo` results (git present? package-lock? node_modules?).
3. If ready, user clicks "Witness". Backend runs `sswp_witness`.
4. UI streams progress: GIT_INTEGRITY → LOCKFILE → DETERMINISTIC_BUILD → TEST_PASS → LINT → typosquat probe → version anomaly probe → missing integrity probe.
5. Result: `.sswp.json` generated. UI shows SHA-256 signature, per-dependency risk breakdown, and a "Export to Omega SEAL" button (calls `sswp_export_to_omega` → `omega_seal_run`).
6. **Better-than-parity**: Auto-witness on git commit. A background sidecar watches `.git` and offers to re-witness when `package-lock.json` changes.

**Bulk Witness**
- Multi-select repos. Run sequential `sswp_bulk_witness`.
- Progress bar per repo. Final summary: X passed, Y failed, Z skipped.

#### 2.2 Omega Stenographer UI
**Current v2 gap**: Stenographer is only accessible via the "Witness" Trinity button fallback (`stenographer_compact_guard`). Rebuild must expose a **Stenographer Panel**.

**Running Notes (Live Brief)**
- Panel title: "Ω Stenographer — Session Memory"
- Always-visible brief: compressed summary of current session decisions, blockers, and milestones.
- Auto-updates every time `stenographer_ingest_exchange` is called (after every significant chat turn).
- **Better-than-parity**: Inline "Milestone" button in chat input. User or agent can flag a message as a milestone (tier-A priority), which calls `stenographer_mark_milestone`. Milestones appear as gold pins in the brief.

**Search & Recall**
- FTS5 search bar over all ingested exchanges.
- Results show: role (user/assistant), timestamp, content snippet, and a "Jump to Context" button that restores that session state into the chat panel.
- **Better-than-parity**: Cross-session thread linking. If a new task references a previous session (detected via `omega_preload_context` continuity_type = CONTINUATION), Stenographer auto-suggests the prior brief as context.

**Compact Guard Visualization**
- When context window pressure hits, show a gauge: "Context Pressure: 73%".
- Trigger `stenographer_compact_guard` automatically. Show before/after token counts.
- **Better-than-parity**: Predictive compaction. Warn user at 60% pressure with a "Compact Now" suggestion, rather than waiting for a hard limit.

---

### 3. Pet Companion Integration

#### 3.1 Purpose (Not Decorative)
The Codex pet (currently a concept in the v2 "Pet Companion" Trinity button) must become an **ambient task-progress agent**. It is not a chatbot; it is a visual + audio feedback system tied to real subsystem state.

#### 3.2 Behaviors
| State | Pet Behavior | Trigger |
|-------|-------------|---------|
| Idle | Slow breathing animation, occasional blink | No active task runs |
| Working | Fast tail wag, focused eyes, small hops | Active task run in progress |
| Thinking | Pacing animation, question mark bubble | Agent generating response |
| Warning | Ears back, red pulse, growl sound | SSWP risk >50%, or security finding |
| Success | Backflip, sparkle burst, happy chirp | Task run completed, or seal succeeded |
| Error | Shaking, tears, sad whine | Task run failed, or MCP health down |
| Reminder | Tapping foot, clock bubble | Milestone overdue (from Stenographer) |

#### 3.3 Agent Activity Tie-Ins
- **Task Progress**: Pet sits next to the task run timeline. Its animation speed maps to task run stage progress (0-100%).
- **MCP Health**: If any MCP dot turns red, pet runs to the MCP dashboard and points at the failing lane.
- **Voice/Steno**: When voice is enabled, pet lip-syncs to TTS output. When Stenographer compacts, pet "squeezes" into a tiny ball then expands (visual metaphor for compression).
- **Desktop Control**: When desktop automation is active, pet wears a "pilot helmet" and mimics mouse movements at a smaller scale on screen.

#### 3.4 Emotional Feedback Rules
- Pet mood is derived from a **weighted sentiment score** of recent events (last 10 minutes):
  - +10 per success, -10 per error, +5 per milestone, -5 per warning.
  - Mood >30 = Happy, -30 to 30 = Neutral, <-30 = Sad.
- Pet reacts to user typing speed: fast typing = excited pet; idle = sleepy pet.
- **Better-than-parity**: Pet can be "petted" (clicked). This triggers a micro-interaction (purring sound, heart particles) and logs a positive reinforcement event to Stenographer, which influences future agent tone.

---

### 4. Linux Desktop Control Plan

#### 4.1 Capabilities (Staged Release)
**Stage 1 — Read-Only (Safe, No Approval)**
- `window_list`: List all X11/Wayland windows (title, PID, geometry).
- `screenshot`: Capture full screen or specific window.
- `active_window`: Get currently focused window info.
- `accessibility_tree`: Read AT-SPI2 tree (element names, roles, bounds).

**Stage 2 — Targeted Interaction (Gated, Approval Required)**
- `click_element(x, y)` or `click_element(accessibility_id)`.
- `type_text(text, target)` — type into focused window or specific element.
- `scroll(x, y, delta)`.
- `focus_window(window_id)`.

**Stage 3 — Full Control (Restricted, Multi-Factor Approval)**
- `keyboard_shortcut(keys)` — e.g., Ctrl+Alt+T to open terminal.
- `mouse_drag(start, end)`.
- `launch_application(command)`.
- `close_window(window_id)`.

#### 4.2 Safe Release Stages
1. **Stage 1** is enabled by default after `linux_desktop_control_readiness_dashboard()` returns `ready` for all read-only items.
2. **Stage 2** requires:
   - User toggles "Enable Desktop Interaction" in Settings.
   - `desktop_capture_action_approval_policy_dashboard()` shows all policies green.
   - Operator confirmation dry run passed (`desktop_capture_action_operator_confirmation_dry_runs`).
3. **Stage 3** requires:
   - Stage 2 has been active for >7 days with no incidents.
   - `desktop_capture_action_final_preaction_dry_runs()` passed.
   - `linux_desktop_readiness_release_checklist()` all items checked.
   - Physical key confirmation (user must press a specific key combo within 10 seconds of request).

#### 4.3 User Approval UX
- For Stage 2/3 actions, a **non-blocking toast** appears: "Omega wants to click 'Submit' in Firefox. Allow? [Yes] [No] [Always for this app]"
- The toast shows a **mini-screenshot** of the target area with a red circle highlighting where the click will occur.
- "Always for this app" creates a persistent approval record stored in `desktop_capture_action_approval_records`.
- **Better-than-parity**: "Ghost mode" — before executing, show a semi-transparent preview of the action (e.g., a ghost cursor moving to the target) for 2 seconds, allowing the user to cancel.

#### 4.4 Accessibility Checks
- Before any element interaction, verify the element is still present in the AT-SPI2 tree and its bounds have not changed by >10%.
- If the tree is stale, re-scan and re-validate the target.
- If validation fails, block the action and notify the user with a screenshot of the current state vs. expected state.

---

### 5. Terminal/Process Adapter Spec

#### 5.1 Backend Contract
The Rust backend must manage PTY/process lifecycle via a **Process Supervisor** sidecar (or native Tauri plugin).

**Data Model**
```rust
struct ProcessHandle {
    id: String,               // UUID
    cwd: String,              // Current working directory
    env: HashMap<String, String>,
    shell: String,            // e.g., "/bin/bash"
    pty_fd: Option<RawFd>,    // Linux PTY file descriptor
    child_pid: Option<u32>,
    status: ProcessStatus,    // Init, Running, Suspended, Exited(i32), Killed
    created_at: u64,
    sandbox_allowlist: Vec<String>, // Allowed command prefixes
}

struct ProcessStreamChunk {
    process_id: String,
    stream: StreamType,       // Stdout, Stderr, PtyData
    data: String,
    timestamp: u64,
}

struct ProcessExitSummary {
    process_id: String,
    exit_code: Option<i32>,
    signal: Option<String>,   // e.g., "SIGTERM"
    duration_ms: u64,
    stdout_tail: String,      // Last 2KB
    stderr_tail: String,
    transcript_path: String,
}
```

**Commands (already stubbed in `commands.rs`)**
- `build_process_command_plan_stub(request)` / `list_process_command_plans()`
- `initialize_process_streams_stub(request)` / `list_process_stream_inits()`
- `create_process_lifecycle_stub(request)` / `list_process_lifecycles()`
- `create_process_control_policy_stub(request)` / `list_process_control_policies()`
- `create_process_supervisor_preflight_stub(request)` / `list_process_supervisor_preflights()`
- `create_process_supervisor_heartbeat_stub(request)` / `list_process_supervisor_heartbeats()`
- `create_process_supervisor_exit_summary_stub(request)` / `list_process_supervisor_exit_summaries()`
- `create_process_output_tail_summary_stub(request)` / `list_process_output_tail_summaries()`

**Live Commands (to be added)**
- `terminal_create(shell, cwd, env)` → `ProcessHandle`
- `terminal_write(process_id, input)` → `Result<()>`
- `terminal_resize(process_id, cols, rows)` → `Result<()>`
- `terminal_kill(process_id, signal)` → `ProcessExitSummary`
- `terminal_read(process_id, offset)` → `Vec<ProcessStreamChunk>`

#### 5.2 Sandbox Allowlist
Every process must be spawned with a sandbox policy:
- `command_allowlist`: e.g., `["git", "cargo", "npm", "python", "rustc"]`.
- `path_allowlist`: e.g., `[/home/rage/workspace, /tmp]`.
- `network_policy`: `localhost_only`, `none`, or `full`.
- If the user types a command not in the allowlist, the terminal shows: `[BLOCKED] "curl" is not in the sandbox allowlist. [Override] [Edit Policy]`.

#### 5.3 Transcript & Rollback
- Every terminal session is recorded to `$APP_DATA_DIR/transcripts/<process_id>.jsonl`.
- Format: `{"t": 1234567890, "s": "stdout", "d": "..."}`.
- **Rollback**: If a command fails (non-zero exit), the UI offers "Rollback suggestions" based on the transcript (e.g., "You created files X, Y. Delete them? [Yes]").
- **Better-than-parity**: "Time-travel scrubber" — a slider in the terminal panel that lets the user scroll back through the session visually, with stdout/stderr toggles.

---

### 6. Workspace Edit Adapter Spec

#### 6.1 Exact Flow (Preview → Approval → Buffer Draft → Diff → Rollback → Atomic Write → Verification)
The current v2 has basic file write/patch via `gravity_write_file` and `gravity_patch_file`. The rebuild must make edits **governed and reversible**.

**Stage 1 — Edit Preflight**
1. User or agent requests an edit (write, patch, or delete).
2. Backend creates a `WorkspaceEditPreflightRecord`.
3. Preflight checks:
   - Does the file exist? (If not, is the parent dir in the workspace?)
   - Is the file currently open in the editor? (If yes, warn about dirty state.)
   - Is the file in `.gitignore` or a sensitive path (e.g., `.env`)?
   - Compute SHA-256 of current file content (if exists).

**Stage 2 — Write Approval Policy**
1. If the preflight passes, check `WorkspaceWriteApprovalPolicy`.
2. Policy defines:
   - `auto_approve_extensions`: e.g., `["rs", "js", "md"]` — edits to these are auto-approved if <100 lines changed.
   - `require_approval_extensions`: e.g., `["json", "toml", "lock"]` — always require approval.
   - `require_approval_paths`: regex patterns for sensitive files.
   - `max_auto_approve_line_count`: 100.

**Stage 3 — Buffer Draft**
1. If approval is required, create a `WorkspaceWritableBufferDraftRecord`.
2. The draft is stored in `$APP_DATA_DIR/drafts/<draft_id>.tmp`.
3. The Monaco editor opens the draft in a **read-only diff view** (original on left, draft on right).
4. User can:
   - Approve (proceed to Stage 4)
   - Reject (delete draft, log rejection reason)
   - Edit the draft further (creates a new draft revision)

**Stage 4 — Mutable Buffer Transaction**
1. On approval, create a `WorkspaceMutableBufferTransactionRecord`.
2. The transaction:
   - Writes the draft to a **temporary file** next to the target (e.g., `file.rs.tmp.<tx_id>`).
   - Runs any post-write verification (syntax check, `cargo check` for Rust, `eslint` for JS).
   - If verification fails, the transaction is aborted. The temp file is deleted. The user sees the error.
   - If verification passes, the temp file is **atomically renamed** over the target (`fs::rename` is atomic on Linux).

**Stage 5 — Post-Write Verification**
1. Re-read the file and verify SHA-256 matches the expected draft hash.
2. If mismatch, alert user and offer to restore from draft.
3. Log the edit to the Stenographer as a milestone (`stenographer_mark_milestone`).
4. Update Git status in UI (show "M" badge on file in explorer).

**Stage 6 — Rollback**
1. Every transaction stores the original file content in `$APP_DATA_DIR/snapshots/<file_hash>.snap`.
2. User can right-click any file in the explorer and select "Rollback Last Edit".
3. Rollback creates a new transaction that restores the snapshot.

**Commands (already stubbed in `commands.rs`)**
- `create_workspace_edit_preflight_stub(request)` / `list_workspace_edit_preflights()`
- `create_workspace_write_approval_policy_stub(request)` / `list_workspace_write_approval_policies()`
- `create_workspace_write_approval_stub(request)` / `list_workspace_write_approvals()`
- `create_workspace_writable_buffer_draft_stub(request)` / `list_workspace_writable_buffer_drafts()`
- `create_workspace_dirty_transition_preflight_stub(request)` / `list_workspace_dirty_transition_preflights()`
- `create_workspace_mutable_buffer_transaction_stub(request)` / `list_workspace_mutable_buffer_transactions()`
- `create_workspace_editor_buffer_materialization_policy_stub(request)` / `list_workspace_editor_buffer_materialization_policies()`
- `create_workspace_editable_text_model_text_snapshot_stub(request)` / `list_workspace_editable_text_model_text_snapshots()`

**Live Commands (to be added)**
- `workspace_request_edit(path, new_content, source)` → `WorkspaceEditPreflightResult`
- `workspace_approve_edit(preflight_id)` → `WorkspaceMutableBufferTransactionResult`
- `workspace_rollback_edit(transaction_id)` → `WorkspaceMutableBufferTransactionResult`

---

## Recommended Work (Prioritized)

1. **P0 — Prune Scaffold**: The current `commands.rs` is 124k lines with extreme name-length inflation (e.g., `local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_closure_release_release_finalization_dry_run_stub`). This must be collapsed into ~20 real commands with generic parameters. The scaffold is useful as a spec, but it will not compile performantly or maintainably.
2. **P0 — Live MCP Executor**: Implement a single `mcp_execute(server, tool, args)` command that actually spawns MCP clients (via `mcp-sdk-rs` or sidecar) and returns results. Gate it behind the approval records already modeled.
3. **P1 — SSWP Panel**: Build the Tauri frontend panel for SSWP fleet health, witness workflow, and attestation timeline. Wire to `sswp_witness` and `sswp_bulk_witness` via the live executor.
4. **P1 — Stenographer Panel**: Build the session memory panel with brief, search, and compact guard visualization. Wire to `stenographer_ingest_exchange` after every chat turn.
5. **P1 — Terminal/Process Adapter**: Replace stubs with real PTY management (via `portable-pty` or `tokio-pty-process`). Implement sandbox allowlist and transcript recording.
6. **P2 — Workspace Edit Adapter**: Implement the full 6-stage edit pipeline with diff view, atomic rename, and rollback.
7. **P2 — Pet Companion**: Add the ambient agent visualization (Canvas/WebGL overlay) with state machine tied to task runs and MCP health.
8. **P3 — Linux Desktop Control**: Implement Stage 1 (read-only) first. Stage 2/3 gated behind the readiness dashboard.

---

## Risks

1. **Scaffold Complexity Drift**: The 124k-line stub file creates an illusion of progress. If not pruned, it will become a maintenance nightmare. Risk: developers add more stubs instead of real implementations.
2. **MCP Transport Mismatch**: Current v2 uses SSE (Node) and stdio (Python). Rust rebuild must support both. Risk: SSE keep-alive and session management in Rust are non-trivial.
3. **Approval Fatigue**: If every write requires 5+ approval records, users will disable gates. Risk: UX must make approvals feel fast (pre-computed policies, one-click approve with preview).
4. **Desktop Control Security**: Screenshot and input injection are high-risk. Risk: a compromised agent could exfiltrate data or perform unauthorized actions. Mitigation: Stage 1 only for MVP; physical key confirmation for Stage 3.
5. **Pet Companion Scope Creep**: Ambient visualization can become a time sink. Risk: keep it simple (CSS animations + emoji) for MVP; WebGL later.
6. **SSWP Attestation Staleness**: Auto-witness on commit sounds good, but `npm install` can change `node_modules` without changing `package-lock.json`. Risk: witness may miss runtime drift.

---

## Done Criteria

This spec slice is complete when:
- [ ] This document (`FIRST_CLASS_SPECS.md`) is reviewed and accepted by the lead architect.
- [ ] The 304-command stub scaffold in `commands.rs` has been pruned to a manageable set of real commands (target: <50 commands for MVP).
- [ ] A live `mcp_execute` command exists and can successfully call at least one MCP tool (e.g., `omega_brain_status`) end-to-end.
- [ ] The Tauri frontend has placeholder panels for MCP Dashboard, SSWP Fleet, Stenographer Memory, and Terminal/Process, even if backend is stubbed.
- [ ] The Workspace Edit Adapter can perform at least one atomic write with rollback capability.
- [ ] No live host/security actions, secrets, or config reads were performed during this spec-writing phase (read-only audit confirmed).

---

## Do Not Touch

- Current Electron `.sswp.json` files in `/home/rage/apps/gravity-omega-v2/`.
- Live host/security actions (shields, sentinels, process identity traps).
- Secrets, API keys, or `OMEGA_AUTH_TOKEN`.
- Config reads from live systems.
- Running terminals, sockets, or MCP calls.
- Any file writes outside of this spec document.
