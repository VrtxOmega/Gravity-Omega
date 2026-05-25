# Rust/Tauri Command Contract

Status: phase-2 scaffold contract.

## Purpose

The current Electron app exposes a large IPC surface directly from `main.js` to `preload.js` and the renderer. The rebuild converts that surface into explicit Rust commands with safety tiers, feature phases, and approval requirements.

The canonical machine-readable draft is:

```text
rebuild/gravity-omega-tauri/web/contracts/commands.v0.json
```

## Contract Rules

- Every command has a safety tier: `safe`, `gated`, or `restricted`.
- A command that mutates files, executes processes, changes providers, sends data, or controls the desktop cannot be `safe`.
- Destructive operations require an approval record before execution.
- File commands must be workspace-scoped unless the user grants broader access.
- Runtime paths must use Linux XDG directories. No Windows, WSL, `/mnt/c`, or AppData defaults.
- UI copy must distinguish `live`, `configured`, `offline`, `placeholder`, and `planned` states.
- Every migrated command needs a test or manual verification note before being marked live.

## Initial Migration Buckets

| Bucket | Current Surface | Target |
|---|---|---|
| File operations | `file:*` IPC | Rust workspace-scoped file commands |
| Terminal | `terminal:*` IPC with `node-pty` | Rust PTY service |
| Search/watch | `watcher:*`, `search:text` | Rust notify plus ignore-aware search |
| Agent | `chat:*`, `agent:*` | Codex-grade operating loop |
| Providers | `provider:*` | keyring-backed provider registry |
| MCP/plugins | `mcp:*`, `backend:*` | Rust MCP server/client registry |
| SSWP | local SSWP MCP | First-class local MCP lane with health, capability, gated call, and audit states |
| Omega Stenographer | omega-stenographer MCP and transcript workflows | First-class capture/search/transcript evidence lane tied to consent, redaction, retention, and export policy |
| Vault/ledger | `vault:*`, `ledger:*` | OmegaBrain-first memory adapter |
| Security | `security:*` | Linux-native status and gated actions |
| Browser/desktop | `browser:*`, OCR, hardware | Browser plus Linux Computer Use capability |
| Reports/media/tools | reports, tools, media IPC | plugin lanes unless proven core |

## Command Surface Collapse

Worker C found that the scaffold had grown to a 124k-line Rust command file with 304 generated stubs. That shape is now treated as temporary scaffolding debt, not the target architecture.

The canonical forward map is `command_surface_collapse_board`, exposed in the scaffold UI as "Command Surface Collapse" and documented in `docs/GRAVITY_OMEGA_UNIFIED_ACTION_PLAN.md`.

Target: collapse the rebuild into 20 command families:

1. `runtime`
2. `command_registry`
3. `task_run`
4. `approval_evidence`
5. `workspace_read`
6. `workspace_edit`
7. `process_supervisor`
8. `codex_run`
9. `hermes_run`
10. `joint_ci_run`
11. `mcp`
12. `sswp`
13. `steno`
14. `pet_state`
15. `desktop`
16. `media`
17. `browser`
18. `module_sidecar`
19. `security`
20. `settings`

Future slices should add behavior inside these families instead of adding more single-purpose dry-run command chains.

## Workspace Edit Family

`workspace_edit` is the first command implemented in the collapsed family shape.

Current mode:

- `save_preview`

Current behavior:

- returns a six-stage read-only plan: edit preflight, write approval policy, buffer diff preview, atomic transaction plan, post-write verification, and rollback snapshot
- accepts source command, target path label, estimated line delta, and operator note
- does not read file contents
- does not write files
- does not save/save-as
- does not apply patches
- does not spawn processes
- does not open file dialogs
- does not execute anything

Future write-capable modes must stay blocked until approval evidence, bounded diff preview, atomic transaction, post-write verification, and rollback records exist.

## UI/UX Test Matrix

`ui_ux_test_matrix` is a read-only command that binds Worker D's UI/UX audit to the same 20 command families as the architecture collapse plan.

It records:

- per-family blocker gates
- unit test scope
- UI smoke test scope
- manual check scope
- semantic color lane
- keyboard, loading, hover, drag/drop, resize, and icon requirements
- layout targets for activity rail, sidebar, chat rail, and bottom panel

This command does not install packages, launch browsers, capture screenshots, control the desktop, or enable live resizing. It is a product-readiness map and validator target.

## Finish-Line Readiness Commands

`replacement_app_ship_readiness` is the finish-line dashboard. It consolidates the 20 command families into one product-readiness map with readiness percentages, blocker counts, critical blocker text, and the next action for each family.

`sidecar_readiness_board` owns the highest Worker A parity risks: Python backend, browser automation, media/AAX/ffmpeg, terminal PTY/process supervision, and restricted security tools.

`sidecar_launch_policy_manifest` turns those sidecar risks into explicit launch policies: binary strategy, cwd policy, argument policy, env policy, log path, health probe, shutdown policy, approval gate, and failure UI.

`sidecar_health_packet_console` converts the launch policies into operator-facing health packets: probe intent, success criteria, failure signals, evidence path, approval dependency, and launch blocker per sidecar.

These commands are read-only. They keep live health probes, sidecar launch, process spawn, PTY, browser automation, media playback, Python bridge, desktop control, file writes, patch apply, config reads, sockets, live MCP calls, capture, export, memory writes, and execution disabled until health probes, logs, allowlists, approval evidence, and failure UI exist.

## First Live Command Candidates

1. `runtime_health`
2. `command_manifest`
3. `agent_runtime_status`

## Toolbar Routing

The web shell now routes every remaining live toolbar target into a concrete in-app surface instead of falling through to generic readiness text:

- `file_new`, `file_pick`, and `workspace_open` open the workspace files dashboard plus editor navigation lane.
- `editor_undo` and `editor_redo` open the workspace edit preview and mutation workbench.
- `window_new`, `window_toggle_fullscreen`, and `app_exit` open the native shell readiness workbench.
- `security_scan` opens the security shield workbench.
- `codex_review` opens the Codex/Hermes run view and first-class integration launchpad.

These routes do not enable native dialogs, fullscreen changes, app exit, file mutation, undo/redo mutation, security scans, Codex execution, process spawn, desktop control, MCP calls, sockets, writes, patches, capture, export, memory writes, or execution.

## Activity Rail

The left activity rail now switches the visible operator surface:

- Command focuses foundation, command registry, readiness, docs, and shell metadata.
- Workspace focuses file/workspace/editor/find/mutation surfaces.
- Vault focuses MCP, SSWP, Steno, pet, local MCP, memory, and vault lanes.
- Security focuses shields, restricted controls, desktop/capture policy, and safety gates.
- Plugins focuses sidecars, VERITAS modules, integration launchpads, and extension readiness.
- Codex/Hermes CI focuses task runs, evidence, agents, runners, terminals/processes, transcripts, and reconciliation.

The rail only filters existing in-app panels. It does not enable file reads, writes, patches, MCP calls, config reads, sockets, process spawn, PTY allocation, desktop control, browser automation, media playback, sidecar launches, security scans, capture, export, memory writes, or execution.

## Agent Rail Resize

The right agent rail now has an accessible resize separator. Pointer drag and keyboard arrows adjust `--chat-width` within the audited 240-480px range and persist the preference in local browser storage. The separator exposes `aria-valuemin`, `aria-valuemax`, and `aria-valuenow`.

This is a layout-only feature. It does not enable chat send, agent execution, process spawn, PTY allocation, desktop control, file reads, writes, patches, MCP calls, config reads, sockets, capture, export, memory writes, or execution.
4. `task_run_templates`
5. `command_registry`
6. `execute_command_stub`
7. `create_task_run_stub`
8. `list_task_runs`
9. `create_approval_record_stub`
10. `list_approval_records`
11. `resolve_approval_record_stub`
12. `task_run_artifact_preview`
13. `sandbox_policy_manifest`
14. `evaluate_execution_gate`
15. `prepare_runner_invocation_stub`
16. `list_runner_invocations`
17. `create_joint_agent_plan_stub`
18. `list_joint_agent_plans`
19. `create_agent_capability_inventory_stub`
20. `list_agent_capability_inventories`
21. `create_first_class_integration_readiness_stub`
22. `list_first_class_integration_readiness`
23. `append_agent_event_stub`
24. `agent_event_log_preview`
25. `create_workspace_lease_stub`
26. `list_workspace_leases`
27. `prepare_runner_adapter_stub`
28. `list_runner_adapters`
29. `build_process_command_plan_stub`
30. `list_process_command_plans`
31. `initialize_process_streams_stub`
32. `list_process_stream_inits`
33. `create_process_lifecycle_stub`
34. `list_process_lifecycles`
35. `create_process_control_policy_stub`
36. `list_process_control_policies`
37. `create_process_supervisor_preflight_stub`
38. `list_process_supervisor_preflights`
39. `create_process_supervisor_heartbeat_stub`
40. `list_process_supervisor_heartbeats`
41. `create_process_supervisor_exit_summary_stub`
42. `list_process_supervisor_exit_summaries`
43. `create_process_output_tail_summary_stub`
44. `list_process_output_tail_summaries`
45. `create_run_transcript_bundle_stub`
46. `list_run_transcript_bundles`
47. `create_transcript_export_policy_stub`
48. `list_transcript_export_policies`
49. `create_transcript_protection_policy_stub`
50. `list_transcript_protection_policies`
51. `create_local_mcp_lane_capability_contract_stub`
52. `list_local_mcp_lane_capability_contracts`
53. `create_local_mcp_health_preflight_stub`
54. `list_local_mcp_health_preflights`
55. `create_local_mcp_health_record_stub`
56. `list_local_mcp_health_records`
57. `create_local_mcp_capability_discovery_policy_stub`
58. `list_local_mcp_capability_discovery_policies`
59. `create_local_mcp_gated_call_policy_stub`
60. `list_local_mcp_gated_call_policies`
61. `create_local_mcp_call_approval_audit_stub`
62. `list_local_mcp_call_approval_audits`
63. `create_local_mcp_consent_approval_decision_stub`
64. `list_local_mcp_consent_approval_decisions`
65. `create_local_mcp_audit_outcome_stub`
66. `list_local_mcp_audit_outcomes`
67. `create_local_mcp_recovery_precall_guard_stub`
68. `list_local_mcp_recovery_precall_guards`
69. `create_local_mcp_final_call_approval_stub`
70. `list_local_mcp_final_call_approvals`
71. `create_local_mcp_live_call_dry_run_stub`
72. `list_local_mcp_live_call_dry_runs`
73. `create_local_mcp_typed_command_contract_stub`
74. `list_local_mcp_typed_command_contracts`
75. `create_local_mcp_status_probe_preflight_stub`
76. `list_local_mcp_status_probe_preflights`
77. `create_local_mcp_config_lookup_preflight_stub`
78. `list_local_mcp_config_lookup_preflights`
79. `create_workspace_inspection_record_stub`
80. `list_workspace_inspection_records`
81. `create_workspace_preview_record_stub`
82. `list_workspace_preview_records`
83. `create_workspace_tree_metadata_record_stub`
84. `list_workspace_tree_metadata_records`
85. `create_workspace_file_content_preview_record_stub`
86. `list_workspace_file_content_preview_records`
87. `create_workspace_editor_tab_state_stub`
88. `list_workspace_editor_tab_states`
89. `create_workspace_edit_preflight_stub`
90. `list_workspace_edit_preflights`
91. `create_workspace_write_approval_policy_stub`
92. `list_workspace_write_approval_policies`
93. `create_workspace_write_approval_stub`
94. `list_workspace_write_approvals`
95. `create_workspace_writable_buffer_draft_stub`
96. `list_workspace_writable_buffer_drafts`
97. `create_workspace_dirty_transition_preflight_stub`
98. `list_workspace_dirty_transition_preflights`
99. `create_workspace_mutable_buffer_transaction_stub`
100. `list_workspace_mutable_buffer_transactions`
101. `create_workspace_editor_buffer_materialization_policy_stub`
102. `list_workspace_editor_buffer_materialization_policies`
103. `create_workspace_editor_buffer_attachment_stub`
104. `list_workspace_editor_buffer_attachments`
105. `create_workspace_editor_buffer_editable_state_preflight_stub`
106. `list_workspace_editor_buffer_editable_state_preflights`
107. `create_workspace_editable_buffer_view_binding_stub`
108. `list_workspace_editable_buffer_view_bindings`
109. `create_workspace_editable_text_viewport_materialization_stub`
110. `list_workspace_editable_text_viewport_materializations`
111. `create_workspace_editable_text_attachment_verification_stub`
112. `list_workspace_editable_text_attachment_verifications`
113. `create_workspace_editable_text_model_handle_stub`
114. `list_workspace_editable_text_model_handles`
115. `create_workspace_editable_text_model_storage_preflight_stub`
116. `list_workspace_editable_text_model_storage_preflights`
117. `create_workspace_editable_text_model_text_snapshot_stub`
118. `list_workspace_editable_text_model_text_snapshots`
119. `workspace_search_text`
120. `file_read`
121. `workspace_diff`
122. `create_local_mcp_config_read_policy_stub`
123. `list_local_mcp_config_read_policies`
124. `create_local_mcp_config_path_allowlist_stub`
125. `list_local_mcp_config_path_allowlists`
126. `create_local_mcp_config_path_resolution_request_stub`
127. `list_local_mcp_config_path_resolution_requests`
128. `create_local_mcp_config_path_resolution_approval_stub`
129. `list_local_mcp_config_path_resolution_approvals`
130. `create_local_mcp_config_path_resolution_dry_run_stub`
131. `list_local_mcp_config_path_resolution_dry_runs`
132. `create_local_mcp_config_path_materialization_request_stub`
133. `list_local_mcp_config_path_materialization_requests`
134. `create_local_mcp_config_path_materialization_approval_stub`
135. `list_local_mcp_config_path_materialization_approvals`
136. `create_local_mcp_config_path_materialization_final_dry_run_stub`
137. `list_local_mcp_config_path_materialization_final_dry_runs`
138. `create_local_mcp_config_path_read_preflight_request_stub`
139. `list_local_mcp_config_path_read_preflight_requests`
140. `create_local_mcp_config_path_read_preflight_approval_stub`
141. `list_local_mcp_config_path_read_preflight_approvals`
142. `create_local_mcp_config_path_read_preflight_final_dry_run_stub`
143. `list_local_mcp_config_path_read_preflight_final_dry_runs`
144. `create_local_mcp_config_path_controlled_read_request_stub`
145. `list_local_mcp_config_path_controlled_read_requests`
146. `create_local_mcp_config_path_controlled_read_approval_stub`
147. `list_local_mcp_config_path_controlled_read_approvals`
148. `create_local_mcp_config_path_controlled_read_final_dry_run_stub`
149. `list_local_mcp_config_path_controlled_read_final_dry_runs`
150. `create_local_mcp_config_path_sealed_read_request_stub`
151. `list_local_mcp_config_path_sealed_read_requests`
152. `create_local_mcp_config_path_sealed_read_approval_stub`
153. `list_local_mcp_config_path_sealed_read_approvals`
154. `create_local_mcp_config_path_sealed_read_final_dry_run_stub`
155. `list_local_mcp_config_path_sealed_read_final_dry_runs`
156. `create_local_mcp_config_path_sealed_content_preflight_stub`
157. `list_local_mcp_config_path_sealed_content_preflights`
158. `create_local_mcp_config_path_sealed_content_final_dry_run_stub`
159. `list_local_mcp_config_path_sealed_content_final_dry_runs`
160. `create_local_mcp_config_path_sealed_config_content_read_approval_stub`
161. `list_local_mcp_config_path_sealed_config_content_read_approvals`
162. `create_local_mcp_config_path_sealed_config_content_read_final_dry_run_stub`
163. `list_local_mcp_config_path_sealed_config_content_read_final_dry_runs`
164. `create_local_mcp_config_path_sealed_config_content_read_execution_preflight_stub`
165. `list_local_mcp_config_path_sealed_config_content_read_execution_preflights`
166. `create_local_mcp_config_path_sealed_config_content_read_audit_recovery_preexecution_stub`
167. `list_local_mcp_config_path_sealed_config_content_read_audit_recovery_preexecutions`
168. `create_local_mcp_config_path_sealed_config_content_read_final_approval_stub`
169. `list_local_mcp_config_path_sealed_config_content_read_final_approvals`
170. `create_local_mcp_config_path_sealed_config_content_read_final_execution_dry_run_stub`
171. `list_local_mcp_config_path_sealed_config_content_read_final_execution_dry_runs`
172. `create_local_mcp_config_path_sealed_config_content_read_redaction_schema_dry_run_stub`
173. `list_local_mcp_config_path_sealed_config_content_read_redaction_schema_dry_runs`
174. `create_local_mcp_config_path_sealed_config_content_read_parse_hash_dry_run_stub`
175. `list_local_mcp_config_path_sealed_config_content_read_parse_hash_dry_runs`
176. `create_local_mcp_config_path_sealed_config_content_read_content_shape_policy_dry_run_stub`
177. `list_local_mcp_config_path_sealed_config_content_read_content_shape_policy_dry_runs`
178. `create_local_mcp_config_path_sealed_config_content_read_structural_intent_dry_run_stub`
179. `list_local_mcp_config_path_sealed_config_content_read_structural_intent_dry_runs`
180. `create_local_mcp_config_path_sealed_config_content_read_field_inventory_dry_run_stub`
181. `list_local_mcp_config_path_sealed_config_content_read_field_inventory_dry_runs`
182. `create_local_mcp_config_path_sealed_config_content_read_key_presence_dry_run_stub`
183. `list_local_mcp_config_path_sealed_config_content_read_key_presence_dry_runs`
184. `create_local_mcp_config_path_sealed_config_content_read_key_requirement_dry_run_stub`
185. `list_local_mcp_config_path_sealed_config_content_read_key_requirement_dry_runs`
186. `create_local_mcp_config_path_sealed_config_content_read_key_value_shape_dry_run_stub`
187. `list_local_mcp_config_path_sealed_config_content_read_key_value_shape_dry_runs`
188. `create_local_mcp_config_path_sealed_config_content_read_value_contract_dry_run_stub`
189. `list_local_mcp_config_path_sealed_config_content_read_value_contract_dry_runs`
190. `create_local_mcp_config_path_sealed_config_content_read_value_redaction_map_dry_run_stub`
191. `list_local_mcp_config_path_sealed_config_content_read_value_redaction_map_dry_runs`
192. `create_local_mcp_config_path_sealed_config_content_read_schema_key_map_dry_run_stub`
193. `list_local_mcp_config_path_sealed_config_content_read_schema_key_map_dry_runs`
194. `create_local_mcp_config_path_sealed_config_content_read_schema_binding_dry_run_stub`
195. `list_local_mcp_config_path_sealed_config_content_read_schema_binding_dry_runs`
196. `create_local_mcp_config_path_sealed_config_content_read_schema_validation_plan_dry_run_stub`
197. `list_local_mcp_config_path_sealed_config_content_read_schema_validation_plan_dry_runs`
198. `create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_dry_run_stub`
199. `list_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_dry_runs`
200. `create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_coverage_dry_run_stub`
201. `list_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_coverage_dry_runs`
202. `create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_coverage_report_dry_run_stub`
203. `list_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_coverage_report_dry_runs`

These are low-risk and provide enough surface area to prove the Tauri command path before migrating writes, terminals, and model execution.

## Codex/Hermes Task Runs

Codex and Hermes execution must flow through an `OmegaTaskRun` contract before any live automation is enabled. The first scaffold exposes templates only:

- `codex_review`: planned command shape is `codex review --uncommitted`.
- `codex_exec`: planned command shape is bounded `codex exec --json` with explicit sandbox and approval policy.
- `hermes_chat`: planned command shape is `hermes chat -Q --source tool -t terminal,file,search,skills`.
- `joint_ci`: planned coordinator that runs Codex and Hermes in phases, compares outputs, and blocks overlapping writes.

The scaffold intentionally returns blocked task-run stubs until XDG log storage, approval records, sandbox policy, and artifact streaming are implemented.

The first persistence slice writes blocked `OmegaTaskRun` records under:

```text
$XDG_STATE_HOME/gravity-omega-native/task-runs/
```

If `XDG_STATE_HOME` is unset, the fallback is:

```text
~/.local/state/gravity-omega-native/task-runs/
```

These records are evidence placeholders only. They do not launch Codex, Hermes,
shells, browsers, terminals, MCP tools, or desktop-control commands.

Approval records use the sibling directory:

```text
$XDG_STATE_HOME/gravity-omega-native/approvals/
```

An approval can be requested and resolved in the scaffold, but the resolved
record still has `execution_enabled: false`. Approval evidence is a prerequisite
for future execution, not execution itself.

## Sandbox And Allowlist Gate

The sandbox policy contract lives at:

```text
rebuild/gravity-omega-tauri/web/contracts/sandbox.v0.json
```

The first policy slice defines:

- read-only inspection commands such as `git status`, `git diff`, `rg`, `node --check`, `cargo check`, `cargo test`, `codex review`, and `hermes mcp list`
- gated workspace-write candidates such as `npm run build`, bounded `codex exec --json`, and `hermes chat -Q`
- restricted commands and blocked tokens such as `sudo`, `rm`, package managers, network fetchers, SSH, and secret-related terms

`evaluate_execution_gate` only evaluates proposed argv vectors. It does not run
them. Even allowlisted commands return `execution_enabled: false` until a future
runner connects sandbox policy, approval records, artifact streaming, and
non-overlapping write coordination.

## Disabled Runner Interface

Runner invocation records use the sibling directory:

```text
$XDG_STATE_HOME/gravity-omega-native/runner-invocations/
```

`prepare_runner_invocation_stub` consumes four evidence sources before it records
a runner attempt:

- an `OmegaTaskRun` record
- a resolved approval record linked to that task run and command
- a sandbox gate decision for the requested argv
- the task-run artifact preview

The result can reach `ready_but_execution_disabled` when all prerequisites are
present, but it still returns `accepted: false` and `execution_enabled: false`.
This gives the future Codex/Hermes runner one mandatory prerequisite gate without
introducing process execution in the scaffold.

## Joint Codex/Hermes Coordinator

Joint coordinator plan records use:

```text
$XDG_STATE_HOME/gravity-omega-native/joint-agent-plans/
```

`create_joint_agent_plan_stub` requires an existing `OmegaTaskRun` record, then
records a disabled four-phase plan:

1. Codex review
2. Hermes companion analysis
3. Reconciliation of both findings
4. Evidence report

Every phase has `writes_allowed: false` and `execution_enabled: false`. The
coordinator contract exists so the future CI lane can make Codex and Hermes
work from the same evidence trail before any process spawning or write-capable
automation is added.

## Read-Only Agent Capability Inventory Records

Agent capability inventory records use:

```text
$XDG_STATE_HOME/gravity-omega-native/agent-capability-inventories/
```

`create_agent_capability_inventory_stub` records the non-redundant Codex,
Hermes, MCP, SSWP, Omega Stenographer, pet, approval, workspace, terminal, and
Linux desktop-control features that should become first-class Gravity Omega
surfaces. This is an inventory checkpoint only: it does not probe runtimes,
call MCP tools, spawn agent processes, control the desktop, write files, apply
patches, or claim parity.

The inventory marks these user-owned lanes as first-class targets:

- SSWP workflow capture
- Omega Stenographer transcript and dictation lane
- Codex pet companion surface
- Omega Brain shared memory
- Joint Codex/Hermes CI coordination

The inventory model keeps all execution gates closed:

- `read_only_inventory: true`
- `live_runtime_probe_enabled: false`
- `mcp_calls_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

## Local MCP Config Path Read Preflight Request Records

Local MCP config path read preflight request records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-read-preflight-requests/
```

`create_local_mcp_config_path_read_preflight_request_stub` requires a ready
local MCP config path materialization final dry-run record. If no final dry-run
id is provided, it uses the latest ready final dry-run evidence.

The read preflight request record is an evidence checkpoint before any future
path open or config read approval. It does not open files, read config bytes,
parse configs, hash config contents, inspect secrets, connect sockets, read
manifests, run probes, or call MCP.

The config path read preflight request model keeps all live gates closed:

- `path_read_preflight_request_recorded: true` only with ready final dry-run evidence
- `path_read_preflight_requested: true` means the request evidence exists, not that reading is enabled
- `path_read_preflight_enabled: false`
- `path_open_approved: false`
- `config_read_approved: false`
- `config_content_captured: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

## Local MCP Config Path Read Preflight Approval Records

Local MCP config path read preflight approval records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-read-preflight-approvals/
```

`create_local_mcp_config_path_read_preflight_approval_stub` requires a ready
local MCP config path read preflight request record. If no request id is
provided, it uses the latest ready read preflight request evidence.

The read preflight approval record requires exact confirmation text
`APPROVE LOCAL MCP CONFIG READ PREFLIGHT`. This approval records evidence for
the next dry-run checkpoint only. It does not open files, read config bytes,
parse configs, hash config contents, inspect secrets, connect sockets, read
manifests, run probes, or call MCP.

The config path read preflight approval model keeps all live gates closed:

- `path_read_preflight_approval_recorded: true` only with ready request evidence and exact confirmation
- `path_read_preflight_approved: true` means the approval evidence exists, not that reading is enabled
- `path_read_preflight_enabled: false`
- `path_open_approved: false`
- `config_read_approved: false`
- `config_content_captured: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

## Local MCP Config Path Read Preflight Final Dry-Run Records

Local MCP config path read preflight final dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-read-preflight-final-dry-runs/
```

`create_local_mcp_config_path_read_preflight_final_dry_run_stub` requires a
ready local MCP config path read preflight approval record. If no approval id
is provided, it uses the latest ready read preflight approval evidence.

The read preflight final dry-run record is the last evidence checkpoint before
any future controlled config read request. It does not open files, read config
bytes, parse configs, hash config contents, inspect secrets, connect sockets,
read manifests, run probes, or call MCP.

The config path read preflight final dry-run model keeps all live gates closed:

- `path_read_preflight_final_dry_run_recorded: true` only with ready approval evidence
- `path_read_preflight_final_dry_run_ready: true` means the dry-run evidence exists, not that reading is enabled
- `path_read_preflight_enabled: false`
- `path_open_approved: false`
- `config_read_approved: false`
- `config_content_captured: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates a durable feature map for later readiness slices before any live
Codex, Hermes, MCP, SSWP, Steno, pet, terminal, desktop-control, or workspace
mutation behavior is enabled.

## Local MCP Config Path Controlled Read Request Records

Local MCP config path controlled read request records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-controlled-read-requests/
```

`create_local_mcp_config_path_controlled_read_request_stub` requires a ready
local MCP config path read preflight final dry-run record. If no final dry-run
id is provided, it uses the latest ready read preflight final dry-run evidence.

The controlled read request record is request evidence only. It records that
Omega Brain, SSWP, and Omega Stenographer have reached the read-request gate,
but it does not open files, read config bytes, parse configs, hash contents,
inspect secrets, connect sockets, read manifests, run probes, or call MCP.

The controlled read request model keeps all live gates closed:

- `controlled_read_request_recorded: true` only with ready final dry-run evidence
- `controlled_read_requested: true` records intent only
- `controlled_read_enabled: false`
- `path_open_approved: false`
- `config_read_approved: false`
- `config_content_captured: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This keeps the Codex/Hermes/MCP bridge moving toward real config reads without
letting path materialization evidence become runtime file access by accident.

## Local MCP Config Path Controlled Read Approval Records

Local MCP config path controlled read approval records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-controlled-read-approvals/
```

`create_local_mcp_config_path_controlled_read_approval_stub` requires a ready
local MCP config path controlled read request record. If no request id is
provided, it uses the latest ready controlled read request evidence.

The controlled read approval record requires exact confirmation text:

```text
APPROVE LOCAL MCP CONFIG CONTROLLED READ
```

The approval records can mark `controlled_read_approved: true` as evidence, but
they still do not open files, read config bytes, parse configs, hash contents,
inspect secrets, connect sockets, read manifests, run probes, or call MCP.

The controlled read approval model keeps all live gates closed:

- `controlled_read_approval_recorded: true` only with ready request evidence
- `controlled_read_approved: true` only with supported approve decision and exact confirmation text
- `controlled_read_enabled: false`
- `path_open_approved: false`
- `config_read_approved: false`
- `config_content_captured: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates an approval record for future final dry-run work without allowing
approval evidence to become live config access.

## Local MCP Config Path Controlled Read Final Dry-Run Records

Local MCP config path controlled read final dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-controlled-read-final-dry-runs/
```

`create_local_mcp_config_path_controlled_read_final_dry_run_stub` requires a
ready local MCP config path controlled read approval record. If no approval id
is provided, it uses the latest ready controlled read approval evidence.

The controlled read final dry-run record is another dry-run checkpoint before
any future sealed read/capture design. It does not open files, read config
bytes, parse configs, hash config contents, inspect secrets, connect sockets,
read manifests, run probes, or call MCP.

The controlled read final dry-run model keeps all live gates closed:

- `controlled_read_final_dry_run_recorded: true` only with ready approval evidence
- `controlled_read_final_dry_run_ready: true` means the dry-run evidence exists, not that reading is enabled
- `controlled_read_enabled: false`
- `path_open_approved: false`
- `config_read_approved: false`
- `config_content_captured: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This lets the app prove the full request and approval chain before a later
slice defines any real, redacted, schema-bound config read behavior.

## Local MCP Config Path Sealed Read Request Records

Local MCP config path sealed read request records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-read-requests/
```

`create_local_mcp_config_path_sealed_read_request_stub` requires a ready local
MCP config path controlled read final dry-run record. If no dry-run id is
provided, it uses the latest ready controlled read final dry-run evidence.

The sealed read request record is still a request checkpoint, not a read. It
does not open files, read config bytes, parse configs, hash config contents,
redact secrets, schema-validate contents, connect sockets, read manifests, run
probes, or call MCP.

The sealed read request model keeps all live gates closed:

- `sealed_read_request_recorded: true` only with ready controlled read final dry-run evidence
- `sealed_read_requested: true` means the request record exists, not that reading is enabled
- `sealed_read_enabled: false`
- `controlled_read_enabled: false`
- `path_open_approved: false`
- `config_read_approved: false`
- `config_content_captured: false`
- `config_parse_enabled: false`
- `config_hash_enabled: false`
- `secret_redaction_enabled: false`
- `schema_validation_enabled: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This lets a later approval slice decide whether a sealed read may ever advance
without letting the request itself become config access.

## Local MCP Config Path Sealed Read Approval Records

Local MCP config path sealed read approval records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-read-approvals/
```

`create_local_mcp_config_path_sealed_read_approval_stub` requires a ready local
MCP config path sealed read request record. If no request id is provided, it
uses the latest ready sealed read request evidence. The approval command also
requires `approval_decision` to be `approve` or `deny`, and `approve` only
records approval evidence when the confirmation text is exactly:

```text
APPROVE LOCAL MCP CONFIG SEALED READ
```

The sealed read approval record is still approval evidence, not a read. It does
not open files, read config bytes, parse configs, hash config contents, redact
secrets, schema-validate contents, connect sockets, read manifests, run probes,
or call MCP.

The sealed read approval model keeps all live gates closed:

- `sealed_read_approval_recorded: true` only with ready sealed request evidence and exact approval confirmation
- `sealed_read_approved: true` means approval evidence exists, not that reading is enabled
- `sealed_read_enabled: false`
- `controlled_read_enabled: false`
- `path_open_approved: false`
- `config_read_approved: false`
- `config_content_captured: false`
- `config_parse_enabled: false`
- `config_hash_enabled: false`
- `secret_redaction_enabled: false`
- `schema_validation_enabled: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This lets a later final dry-run slice consume sealed read approval evidence
without letting approval become config access.

## Local MCP Config Path Sealed Read Final Dry-Run Records

Local MCP config path sealed read final dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-read-final-dry-runs/
```

`create_local_mcp_config_path_sealed_read_final_dry_run_stub` requires a ready
local MCP config path sealed read approval record. If no approval id is
provided, it uses the latest ready sealed read approval evidence.

The sealed read final dry-run record is the last evidence-only checkpoint
before any future content redaction/schema preflight. It consumes the sealed
approval chain and records that Omega Brain, SSWP, and Omega Stenographer lanes
are aligned, but it still does not open files, read config bytes, parse configs,
hash config contents, redact secrets, schema-validate contents, connect sockets,
read manifests, run probes, or call MCP.

The sealed read final dry-run model keeps all live gates closed:

- `sealed_read_final_dry_run_recorded: true` only with ready sealed read approval evidence
- `sealed_read_final_dry_run_ready: true` means dry-run evidence exists, not that reading is enabled
- `sealed_read_enabled: false`
- `controlled_read_enabled: false`
- `path_read_preflight_enabled: false`
- `path_materialization_enabled: false`
- `path_resolution_enabled: false`
- `path_normalization_enabled: false`
- `path_stat_enabled: false`
- `symlink_follow_enabled: false`
- `path_open_approved: false`
- `resolved_path_materialized: false`
- `real_path_values_captured: false`
- `config_read_approved: false`
- `config_content_captured: false`
- `config_parse_enabled: false`
- `config_hash_enabled: false`
- `secret_redaction_enabled: false`
- `schema_validation_enabled: false`
- `mcp_config_lookup_enabled: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This lets a later sealed content redaction/schema preflight slice consume final
dry-run evidence without letting dry-run evidence become config access.

## Local MCP Config Path Sealed Content Preflight Records

Local MCP config path sealed content preflight records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-content-preflights/
```

`create_local_mcp_config_path_sealed_content_preflight_stub` requires a ready
local MCP config path sealed read final dry-run record. If no final dry-run id
is provided, it uses the latest ready sealed read final dry-run evidence.

The sealed content preflight records the intended redaction and schema profiles
without executing either one. Supported redaction profiles are
`secrets_and_paths`, `secrets_only`, and `none_required`. Supported schema
profiles are `mcp_config_minimal_shape`, `mcp_config_runtime_shape`, and
`none_required`.

The sealed content preflight model keeps all live gates closed:

- `sealed_content_preflight_recorded: true` only with ready sealed read final dry-run evidence and supported profiles
- `redaction_required` and `schema_validation_required` are planning flags, not execution flags
- `sealed_read_enabled: false`
- `path_open_approved: false`
- `config_read_approved: false`
- `config_content_captured: false`
- `config_parse_enabled: false`
- `config_hash_enabled: false`
- `secret_redaction_enabled: false`
- `schema_validation_enabled: false`
- `mcp_config_lookup_enabled: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This lets a later sealed content final redaction/schema dry-run slice consume
preflight evidence without letting preflight evidence become config access or
content processing.

## Local MCP Config Path Sealed Content Final Dry-Run Records

Local MCP config path sealed content final dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-content-final-dry-runs/
```

`create_local_mcp_config_path_sealed_content_final_dry_run_stub` requires a
ready local MCP config path sealed content preflight record. If no preflight id
is provided, it uses the latest ready sealed content preflight evidence.

The final dry-run records the last redaction/schema planning checkpoint before
any sealed config content read approval can exist. It copies the supported
redaction and schema profiles from the preflight record, links the upstream
approval chain, and still performs no config access or content processing.

The sealed content final dry-run model keeps all live gates closed:

- `sealed_content_final_dry_run_recorded: true` only with ready sealed content preflight evidence
- `redaction_required` and `schema_validation_required` remain planning flags, not execution flags
- `sealed_read_enabled: false`
- `path_open_approved: false`
- `config_read_approved: false`
- `config_content_captured: false`
- `config_parse_enabled: false`
- `config_hash_enabled: false`
- `secret_redaction_enabled: false`
- `schema_validation_enabled: false`
- `mcp_config_lookup_enabled: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This lets a later sealed config content read approval slice consume final
redaction/schema dry-run evidence without letting that evidence become config
access, secret redaction, schema validation, capture, or runtime setup.

## Local MCP Config Path Sealed Config Content Read Approval Records

Local MCP config path sealed config content read approval records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-approvals/
```

`create_local_mcp_config_path_sealed_config_content_read_approval_stub`
requires a ready local MCP config path sealed content final dry-run record. If
no final dry-run id is provided, it uses the latest ready sealed content final
dry-run evidence.

The approval record captures an explicit approval decision and exact
confirmation text:

```text
APPROVE LOCAL MCP SEALED CONFIG CONTENT READ
```

This is still an approval checkpoint only. The record may set
`sealed_config_content_read_approved: true`, but actual content access remains
closed because `config_read_approved`, `config_content_captured`, parsing,
hashing, redaction, schema validation, and every live gate stay false.

The sealed config content read approval model keeps all live gates closed:

- `sealed_config_content_read_approval_recorded: true` only with ready sealed content final dry-run evidence, supported decision, and exact confirmation
- `sealed_config_content_read_approved` is approval evidence, not a content-read execution gate
- `sealed_read_enabled: false`
- `path_open_approved: false`
- `config_read_approved: false`
- `config_content_captured: false`
- `config_parse_enabled: false`
- `config_hash_enabled: false`
- `secret_redaction_enabled: false`
- `schema_validation_enabled: false`
- `mcp_config_lookup_enabled: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This lets a later sealed config content read final dry-run slice consume
approval evidence without letting approval evidence become config access,
secret redaction, schema validation, capture, or runtime setup.

Local MCP sealed config content read final dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-final-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_final_dry_run_stub`
requires a ready sealed config content read approval record. If no approval id
is provided, it uses the latest ready approval evidence.

The final dry-run record is the last disabled checkpoint before any future
execution preflight could be considered. It links approval evidence through
the sealed content final dry-run, sealed content preflight, sealed read,
controlled read, read preflight, materialization, resolution, allowlist,
config policy, lookup/status/typed-command, live-call dry-run, and final-call
approval records.

This is still a dry run only. The record may set
`sealed_config_content_read_final_dry_run_recorded: true`, but actual content
access remains closed because `config_read_approved`,
`config_content_captured`, parsing, hashing, redaction, schema validation,
sockets, live calls, capture, export, memory writes, process spawning, file
writes, patch application, and execution remain false.

This lets a later sealed config content read execution-preflight slice consume
final dry-run evidence without letting dry-run evidence become config access,
secret redaction, schema validation, capture, or runtime setup.

Local MCP sealed config content read execution-preflight records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-execution-preflights/
```

`create_local_mcp_config_path_sealed_config_content_read_execution_preflight_stub`
requires a ready sealed config content read final dry-run record. If no final
dry-run id is provided, it uses the latest ready final dry-run evidence.

The execution-preflight record is still a disabled checkpoint. It records that
the final dry-run evidence is structurally ready for a future execution gate,
but it does not open paths, read config bytes, parse, hash, redact,
schema-validate, capture, connect sockets, call MCP servers, write files,
apply patches, spawn processes, or execute anything.

This lets a later audit/recovery pre-execution slice consume execution
preflight evidence without letting preflight evidence become config access,
secret redaction, schema validation, capture, or runtime setup.

Local MCP sealed config content read audit/recovery pre-execution records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-audit-recovery-preexecutions/
```

`create_local_mcp_config_path_sealed_config_content_read_audit_recovery_preexecution_stub`
requires a ready sealed config content read execution-preflight record. If no
execution-preflight id is provided, it uses the latest ready execution-preflight
evidence. Supported audit/recovery decisions are `ready` and `hold`.

The audit/recovery pre-execution record is still a disabled checkpoint. It can
record per-lane audit and recovery pre-execution evidence for Omega Brain,
SSWP, and Omega Stenographer, but it does not approve or perform real config
reads, content capture, parsing, hashing, redaction, schema validation, export,
socket connections, MCP calls, process spawning, file writes, patch
application, or execution.

This lets a later final sealed config content read approval slice consume
audit/recovery evidence without letting that evidence become config access,
secret inspection, schema validation, capture, export, or runtime setup.

Local MCP sealed config content read final approval records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-final-approvals/
```

`create_local_mcp_config_path_sealed_config_content_read_final_approval_stub`
requires a ready sealed config content read audit/recovery pre-execution record
and the confirmation phrase
`CONFIRM SEALED CONFIG CONTENT READ FINAL APPROVAL`. If no audit/recovery id is
provided, it uses the latest ready audit/recovery pre-execution evidence.
Supported final approval decisions are `approve` and `deny`.

The final approval record can record explicit per-lane final approval evidence
for Omega Brain, SSWP, and Omega Stenographer, but it still does not grant real
config read access or perform content capture, parsing, hashing, redaction,
schema validation, export, socket connections, MCP calls, process spawning,
file writes, patch application, or execution.

This lets a later final dry-run execution slice consume approval evidence
without letting that approval become config access, secret inspection, schema
validation, capture, export, or runtime setup.

Local MCP sealed config content read final execution dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-final-execution-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_final_execution_dry_run_stub`
requires a ready sealed config content read final approval record. If no final
approval id is provided, it uses the latest ready final approval evidence.
Supported dry-run modes are `plan` and `recovery`.

The final execution dry-run record can record per-lane dry-run evidence for
Omega Brain, SSWP, and Omega Stenographer, but it still refuses to open config
paths, read bytes, materialize config content, parse, hash, redact, schema
validate, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later redaction/schema validation dry-run slices consume final
execution dry-run evidence without turning a plan into real config access,
secret inspection, capture, export, or runtime setup.

Local MCP sealed config content read redaction/schema validation dry-run
records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-redaction-schema-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_redaction_schema_dry_run_stub`
requires a ready sealed config content read final execution dry-run record. If
no final execution dry-run id is provided, it uses the latest ready final
execution dry-run evidence. Supported dry-run modes are `plan` and `audit`.

The redaction/schema dry-run record can record per-lane redaction and schema
validation planning evidence for Omega Brain, SSWP, and Omega Stenographer,
but it still does not execute redaction, execute schema validation, open config
paths, read bytes, materialize config content, parse, hash, export, connect
sockets, call MCP servers, spawn processes, write files, apply patches, or
execute anything.

This lets later parse/hash or validation-policy slices consume planning
evidence without turning redaction/schema intent into real config access,
secret inspection, content capture, export, or runtime setup.

Local MCP sealed config content read parse/hash dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-parse-hash-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_parse_hash_dry_run_stub`
requires a ready sealed config content read redaction/schema validation dry-run
record. If no redaction/schema dry-run id is provided, it uses the latest ready
redaction/schema evidence. Supported dry-run modes are `plan` and `audit`.

The parse/hash dry-run record can record per-lane parse and hash planning
evidence for Omega Brain, SSWP, and Omega Stenographer, but it still does not
execute parsing, execute hashing, execute redaction, execute schema validation,
open config paths, read bytes, materialize config content, capture content,
export, connect sockets, call MCP servers, spawn processes, write files, apply
patches, or execute anything.

This lets later content-shape policy slices consume parse/hash planning
evidence without turning parse/hash intent into real config access, secret
inspection, content capture, export, or runtime setup.

Local MCP sealed config content read content-shape policy dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-content-shape-policy-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_content_shape_policy_dry_run_stub`
requires a ready sealed config content read parse/hash dry-run record. If no
parse/hash dry-run id is provided, it uses the latest ready parse/hash
evidence. Supported dry-run modes are `plan` and `audit`.

The content-shape policy dry-run record can record per-lane content-shape
policy planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it
still does not execute parsing, execute hashing, execute redaction, execute
schema validation, open config paths, read bytes, materialize config content,
capture content, export, connect sockets, call MCP servers, spawn processes,
write files, apply patches, or execute anything.

This lets later structural-intent slices consume content-shape policy evidence
without turning shape-policy intent into real config access, secret inspection,
content capture, export, or runtime setup.

Local MCP sealed config content read structural-intent dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-structural-intent-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_structural_intent_dry_run_stub`
requires a ready sealed config content read content-shape policy dry-run
record. If no content-shape policy dry-run id is provided, it uses the latest
ready content-shape policy evidence. Supported dry-run modes are `plan` and
`audit`.

The structural-intent dry-run record can record per-lane structural-intent
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later field-inventory slices consume structural-intent evidence
without turning intent mapping into real config access, secret inspection,
content capture, export, or runtime setup.

Local MCP sealed config content read field-inventory dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-field-inventory-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_field_inventory_dry_run_stub`
requires a ready sealed config content read structural-intent dry-run record.
If no structural-intent dry-run id is provided, it uses the latest ready
structural-intent evidence. Supported dry-run modes are `plan` and `audit`.

The field-inventory dry-run record can record per-lane field-inventory planning
evidence for Omega Brain, SSWP, and Omega Stenographer, but it still does not
execute parsing, execute hashing, execute redaction, execute schema validation,
open config paths, read bytes, materialize config content, capture content,
export, connect sockets, call MCP servers, spawn processes, write files, apply
patches, or execute anything.

This lets later key-presence slices consume field-inventory evidence without
turning planned field enumeration into real config access, secret inspection,
content capture, export, or runtime setup.

Local MCP sealed config content read key-presence dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-key-presence-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_key_presence_dry_run_stub`
requires a ready sealed config content read field-inventory dry-run record. If
no field-inventory dry-run id is provided, it uses the latest ready
field-inventory evidence. Supported dry-run modes are `plan` and `audit`.

The key-presence dry-run record can record per-lane key-presence planning
evidence for Omega Brain, SSWP, and Omega Stenographer, but it still does not
execute parsing, execute hashing, execute redaction, execute schema validation,
open config paths, read bytes, materialize config content, capture content,
export, connect sockets, call MCP servers, spawn processes, write files, apply
patches, or execute anything.

This lets later key-requirement slices consume key-presence evidence without
turning planned key checks into real config access, secret inspection, content
capture, export, or runtime setup.

Local MCP sealed config content read key-requirement dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-key-requirement-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_key_requirement_dry_run_stub`
requires a ready sealed config content read key-presence dry-run record. If no
key-presence dry-run id is provided, it uses the latest ready key-presence
evidence. Supported dry-run modes are `plan` and `audit`.

The key-requirement dry-run record can record per-lane key-requirement planning
evidence for Omega Brain, SSWP, and Omega Stenographer, but it still does not
execute parsing, execute hashing, execute redaction, execute schema validation,
open config paths, read bytes, materialize config content, capture content,
export, connect sockets, call MCP servers, spawn processes, write files, apply
patches, or execute anything.

This lets later key-value-shape slices consume key-requirement evidence without
turning planned key requirements into real config access, secret inspection,
content capture, export, or runtime setup.

Local MCP sealed config content read key-value-shape dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-key-value-shape-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_key_value_shape_dry_run_stub`
requires a ready sealed config content read key-requirement dry-run record. If
no key-requirement dry-run id is provided, it uses the latest ready
key-requirement evidence. Supported dry-run mode is `plan`.

The key-value-shape dry-run record can record per-lane key-value-shape planning
evidence for Omega Brain, SSWP, and Omega Stenographer, but it still does not
execute parsing, execute hashing, execute redaction, execute schema validation,
open config paths, read bytes, materialize config content, capture content,
export, connect sockets, call MCP servers, spawn processes, write files, apply
patches, or execute anything.

This lets later value-contract slices consume key-value-shape evidence without
turning planned value-shape checks into real config access, secret inspection,
content capture, export, or runtime setup.

Local MCP sealed config content read value-contract dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-value-contract-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_value_contract_dry_run_stub`
requires a ready sealed config content read key-value-shape dry-run record. If
no key-value-shape dry-run id is provided, it uses the latest ready
key-value-shape evidence. Supported dry-run mode is `plan`.

The value-contract dry-run record can record per-lane value-contract planning
evidence for Omega Brain, SSWP, and Omega Stenographer, but it still does not
execute parsing, execute hashing, execute redaction, execute schema validation,
open config paths, read bytes, materialize config content, capture content,
export, connect sockets, call MCP servers, spawn processes, write files, apply
patches, or execute anything.

This lets later value-redaction-map slices consume value-contract evidence
without turning planned value contract checks into real config access, secret
inspection, content capture, export, or runtime setup.

Local MCP sealed config content read value-redaction-map dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-value-redaction-map-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_value_redaction_map_dry_run_stub`
requires a ready sealed config content read value-contract dry-run record. If
no value-contract dry-run id is provided, it uses the latest ready
value-contract evidence. Supported dry-run mode is `plan`.

The value-redaction-map dry-run record can record per-lane value-redaction-map
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-key-map slices consume value-redaction-map evidence
without turning planned redaction mapping into real config access, secret
inspection, content capture, export, or runtime setup.

Local MCP sealed config content read schema-key-map dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-key-map-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_key_map_dry_run_stub`
requires a ready sealed config content read value-redaction-map dry-run record. If
no value-redaction-map dry-run id is provided, it uses the latest ready
value-redaction-map evidence. Supported dry-run mode is `plan`.

The schema-key-map dry-run record can record per-lane schema-key-map planning
evidence for Omega Brain, SSWP, and Omega Stenographer, but it still does not
execute parsing, execute hashing, execute redaction, execute schema validation,
open config paths, read bytes, materialize config content, capture content,
export, connect sockets, call MCP servers, spawn processes, write files, apply
patches, or execute anything.

This lets later schema-binding slices consume schema-key-map evidence without
turning planned schema key mapping into real config access, secret inspection,
content capture, export, or runtime setup.

Local MCP sealed config content read schema-binding dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-binding-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_binding_dry_run_stub`
requires a ready sealed config content read schema-key-map dry-run record. If
no schema-key-map dry-run id is provided, it uses the latest ready schema-key-map
evidence. Supported dry-run mode is `plan`.

The schema-binding dry-run record can record per-lane schema-binding planning
evidence for Omega Brain, SSWP, and Omega Stenographer, but it still does not
execute parsing, execute hashing, execute redaction, execute schema validation,
open config paths, read bytes, materialize config content, capture content,
export, connect sockets, call MCP servers, spawn processes, write files, apply
patches, or execute anything.

This lets later schema-validation-plan slices consume schema-binding evidence
without turning planned schema binding into real config access, secret
inspection, content capture, export, or runtime setup.

Local MCP sealed config content read schema-validation-plan dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-plan-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_plan_dry_run_stub`
requires a ready sealed config content read schema-binding dry-run record. If
no schema-binding dry-run id is provided, it uses the latest ready schema-binding
evidence. Supported dry-run mode is `plan`.

The schema-validation-plan dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture slices consume schema-validation-plan
evidence without turning planned schema validation into real config access,
secret inspection, content capture, export, or runtime setup.


Local MCP sealed config content read schema-validation-fixture dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_dry_run_stub`
requires a ready sealed config content read schema-validation-plan dry-run record. If
no schema-validation-plan dry-run id is provided, it uses the latest ready schema-validation-plan
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-coverage slices consume
schema-validation-fixture evidence without turning planned schema validation
fixtures into real config access, secret inspection, content capture, export, or
runtime setup.


Local MCP sealed config content read schema-validation-fixture-coverage dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-coverage-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_coverage_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture dry-run record. If
no schema-validation-fixture dry-run id is provided, it uses the latest ready schema-validation-fixture
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-coverage dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-coverage-report slices consume
schema-validation-fixture-coverage evidence without turning planned fixture
coverage into real config access, secret inspection, content capture, export, or
runtime setup.


Local MCP sealed config content read schema-validation-fixture-coverage-report dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-coverage-report-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_coverage_report_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-coverage dry-run record. If
no schema-validation-fixture-coverage dry-run id is provided, it uses the latest ready schema-validation-fixture-coverage
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-coverage-report dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-report-archive slices consume
schema-validation-fixture-coverage-report evidence without turning planned
coverage reports into real config access, secret inspection, content capture,
export, or runtime setup.


Local MCP sealed config content read schema-validation-fixture-report-archive dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-report-archive-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_report_archive_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-coverage-report dry-run record. If
no schema-validation-fixture-coverage-report dry-run id is provided, it uses the latest ready schema-validation-fixture-coverage-report
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-report-archive dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-archive-retention slices consume
schema-validation-fixture-report-archive evidence without turning planned
report archives into real config access, secret inspection, content capture,
export, or runtime setup.


Local MCP sealed config content read schema-validation-fixture-archive-retention dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-archive-retention-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_archive_retention_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-report-archive dry-run record. If
no schema-validation-fixture-report-archive dry-run id is provided, it uses the latest ready schema-validation-fixture-report-archive
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-archive-retention dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-review slices consume
schema-validation-fixture-archive-retention evidence without turning planned
archive-retention plans into real config access, secret inspection, content capture,
export, or runtime setup.

Local MCP sealed config content read schema-validation-fixture-retention-review dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-review-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_review_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-archive-retention dry-run record. If
no schema-validation-fixture-archive-retention dry-run id is provided, it uses the latest ready schema-validation-fixture-archive-retention
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-review dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-signoff slices consume
schema-validation-fixture-retention-review evidence without turning planned
retention-review records into real config access, secret inspection, content capture,
archive inspection, retention mutation, export, or runtime setup.

Local MCP sealed config content read schema-validation-fixture-retention-signoff dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-signoff-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_signoff_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-review dry-run record. If
no schema-validation-fixture-retention-review dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-review
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-signoff dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-signoff-finalization slices consume
schema-validation-fixture-retention-signoff evidence without turning planned
retention-signoff records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, export, or runtime setup.

Local MCP sealed config content read schema-validation-fixture-retention-signoff-finalization dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-signoff-finalization-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_signoff_finalization_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-signoff dry-run record. If
no schema-validation-fixture-retention-signoff dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-signoff
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-signoff-finalization dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-gate slices consume
schema-validation-fixture-retention-signoff-finalization evidence without turning planned
retention-signoff-finalization records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, export, or runtime setup.

Local MCP sealed config content read schema-validation-fixture-retention-release-gate dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-gate-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_gate_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-signoff-finalization dry-run record. If
no schema-validation-fixture-retention-signoff-finalization dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-signoff-finalization
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-gate dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-approval slices consume
schema-validation-fixture-retention-release-gate evidence without turning planned
retention-release-gate records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, export, or runtime setup.

Local MCP sealed config content read schema-validation-fixture-retention-release-approval dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-approval-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_approval_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-gate dry-run record. If
no schema-validation-fixture-retention-release-gate dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-gate
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-approval dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-gate slices consume
schema-validation-fixture-retention-release-approval evidence without turning planned
retention-release-approval records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, export, or runtime setup.

Local MCP sealed config content read schema-validation-fixture-retention-release-publication-gate dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-gate-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_gate_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-approval dry-run record. If
no schema-validation-fixture-retention-release-approval dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-approval
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-gate dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-approval slices consume
schema-validation-fixture-retention-release-publication-gate evidence without turning planned
retention-release-publication-gate records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication gate, export, or runtime setup.

Local MCP sealed config content read schema-validation-fixture-retention-release-publication-approval dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-approval-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_approval_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-gate dry-run record. If
no schema-validation-fixture-retention-release-publication-gate dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-gate
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-approval dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-finalization slices consume
schema-validation-fixture-retention-release-publication-approval evidence without turning planned
retention-release-publication-approval records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication gate, publication approval, export, or runtime setup.







Local MCP sealed config content read schema-validation-fixture-retention-release-publication-finalization dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-finalization-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_finalization_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-approval dry-run record. If
no schema-validation-fixture-retention-release-publication-approval dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-approval
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-finalization dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-gate slices consume
schema-validation-fixture-retention-release-publication-finalization evidence without turning planned
retention-release-publication-finalization records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication approval, publication finalization, export, or runtime setup.









Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-gate dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-gate-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_gate_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-finalization dry-run record. If
no schema-validation-fixture-retention-release-publication-finalization dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-finalization
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-gate dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-approval slices consume
schema-validation-fixture-retention-release-publication-release-gate evidence without turning planned
retention-release-publication-release-gate records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication finalization, publication release gate, export, or runtime setup.



Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-approval dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-approval-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_approval_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-gate dry-run record. If
no schema-validation-fixture-retention-release-publication-release-gate dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-gate
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-approval dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-finalization slices consume
schema-validation-fixture-retention-release-publication-release-approval evidence without turning planned
retention-release-publication-release-approval records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release gate, publication release approval, export, or runtime setup.



Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-finalization dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-finalization-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_finalization_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-approval dry-run record. If
no schema-validation-fixture-retention-release-publication-release-approval dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-approval
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-finalization dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-completion-review slices consume
schema-validation-fixture-retention-release-publication-release-finalization evidence without turning planned
retention-release-publication-release-finalization records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, export, or runtime setup.



Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-completion-review dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-completion-review-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_completion_review_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-finalization dry-run record. If
no schema-validation-fixture-retention-release-publication-release-finalization dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-finalization
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-completion-review dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-closure-review slices consume
schema-validation-fixture-retention-release-publication-release-completion-review evidence without turning planned
retention-release-publication-release-completion-review records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, publication release completion review, export, or runtime setup.











## First-Class Integration Readiness Records

First-class integration readiness records use:

```text
$XDG_STATE_HOME/gravity-omega-native/first-class-integration-readiness/
```

`create_first_class_integration_readiness_stub` requires an existing agent
capability inventory record. It then records read-only readiness rows for:

- Omega Brain shared memory
- SSWP workflow capture
- Omega Stenographer transcript and dictation lane
- Codex pet companion surface
- Joint Codex/Hermes CI coordination

The readiness record is still a contract checkpoint only. It does not inspect
Omega Brain databases, SSWP state, Steno transcripts, pet assets, Codex, Hermes,
MCP sockets, terminal sessions, desktop sessions, or workspace contents.

The readiness model keeps all live gates closed:

- `read_only_readiness: true` only after the inventory prerequisite exists
- `live_runtime_probe_enabled: false`
- `mcp_calls_enabled: false`
- `asset_inspection_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This prepares per-lane health and capability contracts before any live Omega
Brain, SSWP, Omega Stenographer, pet, Codex/Hermes CI, MCP-call, runtime-probe,
terminal-control, desktop-control, or workspace-mutation behavior is enabled.

## Typed Agent Event Logs

Typed event logs use:

```text
$XDG_STATE_HOME/gravity-omega-native/agent-events/
```

`append_agent_event_stub` requires an existing `OmegaTaskRun` record before it
can append a JSONL event. Each event records:

- task-run id
- source runtime, such as `codex`, `hermes`, or `gravity-omega`
- event type, level, sequence, and message
- optional structured payload
- `execution_enabled: false`

`agent_event_log_preview` reads the recent typed event envelope for UI/debug
inspection. This is the log shape the future live runner should stream into; it
does not capture stdout, stderr, spawn processes, or grant agent execution.

## Workspace Lease Coordination

Workspace lease records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-leases/
```

`create_workspace_lease_stub` requires an existing `OmegaTaskRun` record, then
records the owner runtime, workspace path, intended write scopes, requested
mode, and any same-workspace overlapping lease ids.

The lease model is evidence-only in this scaffold:

- `writes_allowed: false`
- `execution_enabled: false`
- overlapping leases are reported as conflicts, not enforced OS locks

Future Codex/Hermes execution must route write-capable phases through this lease
surface before any runner can patch files or coordinate parallel agents.

## Read-Only Workspace Inspection Records

Workspace inspection records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-inspections/
```

`create_workspace_inspection_record_stub` accepts a workspace path, query text,
and ignore patterns. It records the intended file-tree, file-read, search, and
diff surfaces for the core IDE, but does not traverse the workspace or read file
contents.

The inspection model is read-only in this scaffold:

- `read_only: true`
- `file_tree_enabled: true`
- `file_read_enabled: true`
- `search_enabled: true`
- `diff_enabled: true`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the UI a concrete IDE-surface readiness checkpoint before live file
tree traversal, file reads, ignore-aware search, diffs, patches, terminals, or
agent edits are enabled.

## Read-Only Workspace Preview Records

Workspace preview records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-previews/
```

`create_workspace_preview_record_stub` requires an existing workspace inspection
record. It records a sanitized, ignore-aware list of candidate file paths for the
core IDE file tree/read-preview surface, but does not traverse directories or
read file contents.

The preview model is metadata-only in this scaffold:

- `tree_preview_enabled: true`
- `metadata_preview_enabled: true`
- `file_content_read_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the UI a concrete preview ledger before live directory traversal,
file content previews, file writes, patch application, terminals, or agent edits
are enabled.

## Scoped Workspace Tree Metadata Records

Workspace tree metadata records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-tree-metadata/
```

`create_workspace_tree_metadata_record_stub` requires an existing workspace
preview record. It performs capped metadata traversal under the preview root and
records relative path, kind, depth, size, modified time, readonly state, and
symlink state. It obeys ignore patterns and skips symlink traversal.

The tree metadata model is still content-safe in this scaffold:

- `metadata_traversal_enabled: true`
- `file_content_read_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This is the first live filesystem read slice, but it only reads directory
entries and file metadata. File contents, editor tabs, search, patching,
terminals, and agent edits remain separate gated migrations.

## Guarded File Content Preview Records

File content preview records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-file-previews/
```

`create_workspace_file_content_preview_record_stub` requires an existing
workspace tree metadata record. It reads only a bounded byte sample for a
relative path already present in that tree metadata as a regular non-symlink
file. Ignored paths, symlinks, paths outside the preview root, missing files,
binary content, and invalid UTF-8 do not store text previews.

The file preview model is read-only and text-only:

- `file_content_read_enabled: true` only for successful UTF-8 text previews
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the UI a bounded text preview before editor tabs, dirty tracking,
save gates, patch application, terminals, or agent edits are enabled.

## Read-Only Editor Tab State Records

Editor tab state records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-editor-tabs/
```

`create_workspace_editor_tab_state_stub` requires an existing successful
workspace file content preview record. It records a read-only tab title, relative
path, preview buffer snapshot, cursor/selection defaults, and dirty/save gates.
It does not reread files or create an editable buffer.

The editor tab model is display-only in this scaffold:

- `editor_tab_enabled: true`
- `buffer_attached: true`
- `dirty: false`
- `editable: false`
- `file_content_read_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the UI a real tab ledger before edit buffers, dirty transitions,
save approvals, patch application, terminals, or agent edits are enabled.

## Disabled Edit And Save Preflight Records

Edit/save preflight records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-edit-preflights/
```

`create_workspace_edit_preflight_stub` requires an existing ready read-only
editor tab state. It records a user intent to edit or save, the proposed summary,
the target tab identity, and the disabled write gates. It does not mutate the
buffer, mark the tab dirty, save the file, or apply patches.

The preflight model is intent-only in this scaffold:

- `edit_intent_recorded: true` for edit intent
- `save_gate_recorded: true` for save/save-as intent
- `edit_enabled: false`
- `buffer_mutation_enabled: false`
- `dirty_transition_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates the audit checkpoint needed before future editable buffers, dirty
state transitions, approval prompts, atomic saves, patches, terminals, or agent
edits are enabled.

## Write Approval Policy Records

Write approval policy records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-write-approval-policies/
```

`create_workspace_write_approval_policy_stub` requires an existing ready
edit/save preflight. It records the approval policy required for a future
writable buffer or save path, including approval tier, diff preview requirement,
clean-base requirement, backup snapshot requirement, and atomic write/path
confirmation requirements for saves.

The write policy model is still non-mutating in this scaffold:

- `approval_required: true`
- `approval_record_required: true`
- `approval_record_found: false`
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `dirty_transition_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This makes approval requirements explicit before editable buffers, dirty
transitions, save operations, patch application, terminals, or agent edits are
enabled.

## Workspace Write Approval Evidence

Workspace write approval evidence records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-write-approvals/
```

`create_workspace_write_approval_stub` requires two existing records:

- a ready workspace write approval policy
- a resolved approval record whose subject is the policy id and whose command is
  `workspace.write_buffer` or `workspace.save_file`

The evidence record confirms whether the approval exists, matches the policy,
and was resolved with the required confirmation phrase. It still keeps every
mutating gate closed:

- `approval_evidence_recorded: true` only for a matching resolved approval
- `approval_record_found: true` only when the approval ledger record exists
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `dirty_transition_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates the explicit approval-evidence checkpoint needed before future
writable buffer drafts, dirty transitions, atomic saves, patch application,
terminals, or agent edits are enabled.

## Writable Buffer Draft Records

Writable buffer draft records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-writable-buffer-drafts/
```

`create_workspace_writable_buffer_draft_stub` requires existing resolved write
approval evidence for an edit action. Save-action approval evidence is blocked
from this path because saves need a separate atomic-write draft.

The draft record captures metadata about the approved future edit without
materializing editable content:

- `writable_buffer_draft_recorded: true` only for ready edit approval evidence
- `source_snapshot_metadata_attached: true` only for a ready draft checkpoint
- `draft_content_materialized: false`
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `dirty_after: false`
- `dirty_transition_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This is the checkpoint before the future editor can create a real writable
buffer model. The scaffold still does not mutate text, mark a tab dirty, write
files, apply patches, spawn terminals, or execute agent edits.

## Dirty Transition Preflight Records

Dirty transition preflight records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-dirty-transition-preflights/
```

`create_workspace_dirty_transition_preflight_stub` requires an existing ready
writable-buffer draft. It records that a future dirty-state transaction would
need to happen next, but it does not mark the tab dirty.

The preflight keeps all mutating gates closed:

- `dirty_transition_preflight_recorded: true` only for a ready draft checkpoint
- `dirty_transition_allowed: false`
- `dirty_after: false`
- `dirty_transition_enabled: false`
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the editor a mandatory audit checkpoint before any tab can become
dirty. The future dirty-state implementation must still be a separate explicit
transaction with its own verification.

## Mutable Buffer Transaction Records

Mutable buffer transaction records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-mutable-buffer-transactions/
```

`create_workspace_mutable_buffer_transaction_stub` requires an existing ready
dirty-transition preflight. It records that a future mutable-buffer transaction
has reached the final checkpoint before editable text could be materialized, but
the scaffold still does not materialize editable text.

The transaction record keeps all mutating gates closed:

- `mutable_buffer_transaction_recorded: true` only for a ready dirty preflight
- `mutable_buffer_transaction_allowed: false`
- `editable_text_materialized: false`
- `draft_content_materialized: false`
- `dirty_after: false`
- `dirty_transition_enabled: false`
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates a final explicit checkpoint before future editable text, dirty
state, saves, patches, terminals, or agent edits can be implemented.

## Editor Buffer Materialization Policy Records

Editor buffer materialization policy records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-editor-buffer-materialization-policies/
```

`create_workspace_editor_buffer_materialization_policy_stub` requires an
existing ready mutable-buffer transaction. It records the policy checkpoint that
must exist before any future editable text can be attached to an editor buffer,
but the scaffold keeps attachment disabled.

The policy record keeps all mutating gates closed:

- `materialization_policy_recorded: true` only for a ready mutable transaction
- `materialization_policy_required: true`
- `editor_buffer_attachment_allowed: false`
- `editable_text_materialized: false`
- `draft_content_materialized: false`
- `dirty_after: false`
- `dirty_transition_enabled: false`
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This is still a policy checkpoint only. The future buffer materialization
implementation must be a separate command with explicit state verification.

## Editor Buffer Attachment Records

Editor buffer attachment records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-editor-buffer-attachments/
```

`create_workspace_editor_buffer_attachment_stub` requires an existing ready
editor-buffer materialization policy. It records that the attachment checkpoint
has been reached, but the scaffold still keeps the editor buffer non-editable
and leaves editable text unattached.

The attachment record keeps all mutating gates closed:

- `editor_buffer_attachment_recorded: true` only for a ready materialization policy
- `editor_buffer_attachment_allowed: false`
- `buffer_appears_editable: false`
- `editable_text_attached: false`
- `editable_text_materialized: false`
- `draft_content_materialized: false`
- `dirty_after: false`
- `dirty_transition_enabled: false`
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This separates future visual editor attachment from the later point where text
can become editable, dirty, saved, patched, or executed.

## Editor Buffer Editable-State Preflight Records

Editor buffer editable-state preflight records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-editor-buffer-editable-state-preflights/
```

`create_workspace_editor_buffer_editable_state_preflight_stub` requires an
existing ready editor-buffer attachment record. It records the preflight that a
future command must pass before visually making a buffer editable, but the
scaffold keeps the buffer non-editable and leaves editable text unattached.

The editable-state preflight record keeps all mutating gates closed:

- `editable_state_preflight_recorded: true` only for a ready attachment
- `editable_state_transition_required: true`
- `editable_state_transition_allowed: false`
- `editor_buffer_attachment_allowed: false`
- `buffer_appears_editable: false`
- `editable_text_attached: false`
- `editable_text_materialized: false`
- `draft_content_materialized: false`
- `dirty_after: false`
- `dirty_transition_enabled: false`
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates a separate visible-editability gate before later editable text,
dirty state, save, patch, terminal, or agent execution work.

## Editable Buffer View Binding Records

Editable buffer view binding records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-editor-buffer-view-bindings/
```

`create_workspace_editable_buffer_view_binding_stub` requires an existing ready
editor-buffer editable-state preflight. It records that the view-binding
checkpoint has been reached, but the scaffold still refuses to bind a visible
editor surface as editable.

The view binding record keeps all mutating gates closed:

- `editable_buffer_view_binding_recorded: true` only for a ready editable-state preflight
- `visible_editor_surface_binding_required: true`
- `editable_buffer_view_binding_allowed: false`
- `visible_editor_surface_bound: false`
- `buffer_appears_editable: false`
- `editable_text_attached: false`
- `editable_text_materialized: false`
- `draft_content_materialized: false`
- `dirty_after: false`
- `dirty_transition_enabled: false`
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This keeps the visual editor switch separate from later editable text, dirty
state, save, patch, terminal, or agent execution work.

## Editable Text Viewport Materialization Records

Editable text viewport materialization records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-editable-text-viewport-materializations/
```

`create_workspace_editable_text_viewport_materialization_stub` requires an
existing ready editable-buffer view binding. It records that the future text
viewport checkpoint has been reached, but the scaffold still refuses to render
text into an editable surface.

The viewport materialization record keeps all mutating gates closed:

- `viewport_materialization_recorded: true` only for a ready view binding
- `editable_text_viewport_materialization_required: true`
- `editable_text_viewport_materialization_allowed: false`
- `visible_editor_surface_bound: false`
- `buffer_appears_editable: false`
- `editable_text_attached: false`
- `editable_text_rendered: false`
- `editable_text_materialized: false`
- `draft_content_materialized: false`
- `dirty_after: false`
- `dirty_transition_enabled: false`
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This keeps viewport text rendering separate from later editable text attachment,
dirty state, save, patch, terminal, or agent execution work.

## Editable Text Attachment Verification Records

Editable text attachment verification records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-editable-text-attachment-verifications/
```

`create_workspace_editable_text_attachment_verification_stub` requires an
existing ready editable-text viewport materialization. It records that the text
attachment checkpoint has been reached, but the scaffold still refuses to attach
text to the editable model.

The attachment verification record keeps all mutating gates closed:

- `editable_text_attachment_verification_recorded: true` only for a ready viewport materialization
- `editable_text_attachment_required: true`
- `editable_text_attachment_allowed: false`
- `visible_editor_surface_bound: false`
- `buffer_appears_editable: false`
- `editable_text_attached: false`
- `editable_text_rendered: false`
- `editable_text_materialized: false`
- `draft_content_materialized: false`
- `dirty_after: false`
- `dirty_transition_enabled: false`
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This keeps editable text attachment separate from dirty state, save, patch,
terminal, or agent execution work.

## Editable Text Model Handle Records

Editable text model handle records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-editable-text-model-handles/
```

`create_workspace_editable_text_model_handle_stub` requires an existing ready
editable-text attachment verification. It records that the future editable model
handle checkpoint has been reached, but the scaffold still refuses to let the
model hold text.

The model handle record keeps all mutating gates closed:

- `editable_text_model_handle_recorded: true` only for a ready attachment verification
- `editable_text_model_handle_required: true`
- `editable_text_model_handle_allowed: false`
- `editable_text_model_holds_text: false`
- `editable_text_attachment_allowed: false`
- `visible_editor_surface_bound: false`
- `buffer_appears_editable: false`
- `editable_text_attached: false`
- `editable_text_rendered: false`
- `editable_text_materialized: false`
- `draft_content_materialized: false`
- `dirty_after: false`
- `dirty_transition_enabled: false`
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This keeps editable model text storage separate from dirty state, save, patch,
terminal, or agent execution work.

## Editable Text Model Storage Preflight Records

Editable text model storage preflight records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-editable-text-model-storage-preflights/
```

`create_workspace_editable_text_model_storage_preflight_stub` requires an
existing ready editable-text model handle. It records that the future editable
model storage checkpoint has been reached, but the scaffold still refuses to let
the model hold text.

The model storage preflight record keeps all mutating gates closed:

- `editable_text_model_storage_preflight_recorded: true` only for a ready model handle
- `editable_text_model_storage_preflight_required: true`
- `editable_text_model_storage_allowed: false`
- `editable_text_model_holds_text: false`
- `editable_text_model_handle_allowed: false`
- `editable_text_attachment_allowed: false`
- `visible_editor_surface_bound: false`
- `buffer_appears_editable: false`
- `editable_text_attached: false`
- `editable_text_rendered: false`
- `editable_text_materialized: false`
- `draft_content_materialized: false`
- `dirty_after: false`
- `dirty_transition_enabled: false`
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This keeps editable model text storage separate from dirty state, save, patch,
terminal, or agent execution work.

## Editable Text Model Text Snapshot Records

Editable text model text snapshot records use:

```text
$XDG_STATE_HOME/gravity-omega-native/workspace-editable-text-model-text-snapshots/
```

`create_workspace_editable_text_model_text_snapshot_stub` requires an existing
ready editable-text model storage preflight. It records that the future model
text snapshot checkpoint has been reached, but the scaffold still refuses to
store snapshot text or let the model hold text.

The model text snapshot record keeps all mutating gates closed:

- `editable_text_model_text_snapshot_recorded: true` only for a ready storage preflight
- `editable_text_model_text_snapshot_required: true`
- `editable_text_model_text_snapshot_allowed: false`
- `editable_text_model_text_snapshot_contains_text: false`
- `model_text_snapshot_bytes: 0`
- `editable_text_model_storage_allowed: false`
- `editable_text_model_holds_text: false`
- `editable_text_model_handle_allowed: false`
- `editable_text_attachment_allowed: false`
- `visible_editor_surface_bound: false`
- `buffer_appears_editable: false`
- `editable_text_attached: false`
- `editable_text_rendered: false`
- `editable_text_materialized: false`
- `draft_content_materialized: false`
- `dirty_after: false`
- `dirty_transition_enabled: false`
- `edit_enabled: false`
- `writable_buffer_enabled: false`
- `buffer_mutation_enabled: false`
- `save_enabled: false`
- `save_as_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This keeps actual model-held text separate from dirty state, save, patch,
terminal, or agent execution work.

## Read-Only Runner Adapter Readiness

Runner adapter readiness records use:

```text
$XDG_STATE_HOME/gravity-omega-native/runner-adapters/
```

`prepare_runner_adapter_stub` requires four existing evidence records:

- task run
- runner invocation
- joint Codex/Hermes plan
- workspace lease

It also reads the typed agent event preview for the task run. The readiness
record blocks if any required evidence is missing, mismatched to the task run,
or if the selected workspace lease has conflicts. A successful readiness record
is still only `ready_read_only_execution_disabled`; it records
`process_spawn_enabled: false`, `writes_allowed: false`, and
`execution_enabled: false`.

This is the adapter interface for future read-only Codex/Hermes process streaming,
but no process spawning, stdout/stderr capture, MCP calls, desktop control, or
write-capable behavior is enabled here.

## Process Command Plans

Process command plan records use:

```text
$XDG_STATE_HOME/gravity-omega-native/process-command-plans/
```

`build_process_command_plan_stub` requires an existing `OmegaTaskRun` record and
a ready read-only runner adapter record. It generates exact command vectors and
stream destination paths for supported runtimes while keeping execution disabled:

- Codex: `codex review --uncommitted`
- Hermes: `hermes chat -Q --source tool -t terminal,file,search,skills <task review prompt>`

The record includes cwd, argv, typed event log path, planned stdout/stderr JSONL
stream paths, and the adapter status. It always records
`process_spawn_enabled: false`, `writes_allowed: false`, and
`execution_enabled: false`.

## Process Stream Initialization

Stream initialization records use:

```text
$XDG_STATE_HOME/gravity-omega-native/process-stream-inits/
```

`initialize_process_streams_stub` accepts only a process command plan id. It
loads the plan, verifies that the planned stdout/stderr paths are owned by the
scaffold process-command-plans directory, and creates those two files as empty
JSONL artifacts.

The initialization record is separate from the stream files and records:

- process command plan id
- task-run id and runtime
- stdout/stderr paths
- whether each stream file exists
- stream file byte sizes
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

No command output is written to the stream files in this slice.

## Disabled Process Lifecycle

Process lifecycle records use:

```text
$XDG_STATE_HOME/gravity-omega-native/process-lifecycles/
```

`create_process_lifecycle_stub` accepts a process command plan id and stream
initialization id. It verifies that:

- the process command plan exists and is `planned_process_spawn_disabled`
- the stream initialization belongs to that process command plan
- initialized stdout/stderr files still exist
- all process, write, and execution flags remain disabled

The lifecycle records a fixed disabled state sequence:

1. `planned`
2. `stream-ready`
3. `spawn-blocked`

The final status is `spawn_blocked_execution_disabled`. This gives the future
runner a visible lifecycle model without adding cancellation, retry, stdout or
stderr writes, process spawning, or desktop control.

## Disabled Process Control Policies

Process control policy records use:

```text
$XDG_STATE_HOME/gravity-omega-native/process-control-policies/
```

`create_process_control_policy_stub` accepts a process lifecycle id and a
requested action. The first supported actions are:

- `cancel`
- `retry`

The command requires the lifecycle to exist and to be
`spawn_blocked_execution_disabled`. It records the requested action but keeps
the control path inert:

- `signal_enabled: false`
- `retry_spawn_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the UI a real control ledger before any process supervisor, signal
delivery, retry spawn, or command execution is implemented.

## Disabled Supervisor Preflights

Process supervisor preflight records use:

```text
$XDG_STATE_HOME/gravity-omega-native/process-supervisor-preflights/
```

`create_process_supervisor_preflight_stub` accepts a process lifecycle id. It
requires:

- the lifecycle to exist and remain `spawn_blocked_execution_disabled`
- the referenced process command plan to remain non-executable
- the referenced stream initialization to still point at present stdout/stderr
  artifacts
- at least one process control policy record for the lifecycle

The preflight can report `supervisor_preflight_ready_execution_disabled`, but it
still keeps every live-control flag disabled:

- `supervisor_enabled: false`
- `signal_enabled: false`
- `retry_spawn_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the future process supervisor a concrete evidence checklist before
any monitoring loop, signal delivery, retry spawn, or command execution exists.

## Disabled Supervisor Heartbeats

Process supervisor heartbeat records use:

```text
$XDG_STATE_HOME/gravity-omega-native/process-supervisor-heartbeats/
```

`create_process_supervisor_heartbeat_stub` accepts a supervisor preflight id
and a requested state. The first supported recorded-only states are:

- `queued`
- `running`
- `exited`

The command requires the supervisor preflight to exist and remain
`supervisor_preflight_ready_execution_disabled`. It can record a state ledger,
but it does not attach a PID, start a monitor loop, send signals, retry, spawn,
or write process output:

- `pid_attached: false`
- `supervisor_enabled: false`
- `monitor_loop_enabled: false`
- `signal_enabled: false`
- `retry_spawn_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the UI a visible queued/running/exited state model before any live
process supervisor, stream reader, or process control loop exists.

## Disabled Supervisor Exit Summaries

Process supervisor exit summary records use:

```text
$XDG_STATE_HOME/gravity-omega-native/process-supervisor-exit-summaries/
```

`create_process_supervisor_exit_summary_stub` accepts a supervisor heartbeat id.
It requires an `exited` heartbeat with status
`exited_state_recorded_no_process`, then links the summary back to:

- the supervisor preflight
- the process lifecycle
- the task run
- the heartbeat sequence
- the heartbeat and preflight log paths

Because no process has actually run, the summary explicitly records absence
instead of inventing execution evidence:

- `process_started: false`
- `exit_code: null`
- `exit_code_captured: false`
- `pid_attached: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the UI final-state, duration, and log-linkage structure before any
real PID, exit-code capture, stream reading, or process monitoring exists.

## Disabled Output Tail Summaries

Process output tail summary records use:

```text
$XDG_STATE_HOME/gravity-omega-native/process-output-tail-summaries/
```

`create_process_output_tail_summary_stub` accepts a supervisor exit summary id.
It resolves the linked preflight, lifecycle, stream initialization, and
scaffold-owned stdout/stderr artifact paths. The first implementation only
summarizes initialized empty artifacts:

- stdout/stderr file presence
- stdout/stderr byte sizes
- empty stdout/stderr tail line arrays
- linked task run, lifecycle, stream initialization, and exit summary ids

It explicitly does not tail a live process or read a live stream:

- `live_tail_enabled: false`
- `stream_reader_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the UI output-preview structure before any bounded tail reader,
stream-following loop, or real command output parsing exists.

## Disabled Transcript Bundles

Run transcript bundle records use:

```text
$XDG_STATE_HOME/gravity-omega-native/run-transcript-bundles/
```

`create_run_transcript_bundle_stub` accepts an output tail summary id. It
resolves the linked task run, process command plan, stream initialization,
lifecycle, supervisor preflight, supervisor exit summary, output tail summary,
and task-run artifact preview.

The bundle records:

- evidence ids
- evidence statuses
- evidence record paths
- evidence log paths
- stdout/stderr artifact paths and byte sizes
- disabled export/execution flags

It explicitly does not export files or execute anything:

- `bundle_export_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the UI one reviewable evidence packet before any transcript export,
agent execution, process spawn, or external destination is implemented.

## Disabled Transcript Export Policies

Transcript export policy records use:

```text
$XDG_STATE_HOME/gravity-omega-native/transcript-export-policies/
```

`create_transcript_export_policy_stub` accepts a run transcript bundle id and a
requested destination. The scaffold currently recognizes destination policy
records for:

- `local_file`
- `clipboard`
- `share_sheet`

The policy record resolves the transcript bundle and records:

- requested destination
- normalized destination kind
- planned destination label
- bundle status
- evidence count
- consent requirement
- disabled export/write/share gates

It explicitly does not export data, write files outside the state root, touch the
clipboard, open a share sheet, spawn a process, or execute anything:

- `consent_required: true`
- `export_enabled: false`
- `bundle_export_enabled: false`
- `clipboard_write_enabled: false`
- `share_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the UI a destination and consent ledger before transcript export,
redaction, retention, clipboard writes, or platform share integration exists.

## Disabled Transcript Protection Policies

Transcript protection policy records use:

```text
$XDG_STATE_HOME/gravity-omega-native/transcript-protection-policies/
```

`create_transcript_protection_policy_stub` accepts a transcript export policy id,
a requested redaction profile, and a requested retention tier. The scaffold
currently recognizes:

- redaction profiles: `secrets_and_paths`, `secrets_only`, `none_required`
- retention tiers: `local_7_days`, `local_30_days`, `manual_review`

The policy record resolves the export policy and records:

- linked transcript export policy id
- linked transcript bundle and task-run ids
- destination kind
- redaction profile
- retention tier and retention-day intent
- consent requirement
- disabled redaction/deletion/export/write/share gates

It explicitly does not redact content, delete records, export data, write files
outside the state root, touch the clipboard, open a share sheet, spawn a process,
or execute anything:

- `redaction_applied: false`
- `retention_enforced: false`
- `deletion_scheduled: false`
- `export_enabled: false`
- `bundle_export_enabled: false`
- `clipboard_write_enabled: false`
- `share_enabled: false`
- `process_spawn_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the UI a required redaction and retention checkpoint before any live
transcript export, content scan, deletion schedule, or external destination is
allowed.

## Local MCP Lane Capability Contracts

Local MCP lane capability contract records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-lane-capability-contracts/
```

`create_local_mcp_lane_capability_contract_stub` requires an existing
first-class integration readiness record. It records the expected command ids,
required contracts, consent gates, approval gates, audit gates, recovery gates,
and disabled live behavior for:

- Omega Brain
- SSWP
- Omega Stenographer

The contract record explicitly does not inspect local MCP configs, sockets,
processes, databases, captures, transcripts, or secrets. It also does not call
MCP tools, capture audio, export transcripts, write memory, spawn processes,
control terminals, control the desktop, patch files, write files, or execute
anything:

- `live_probe_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives SSWP, Omega Stenographer, and Omega Brain a named capability contract
before live health probes, capability discovery, gated calls, captures, exports,
or memory writes are enabled.

## Local MCP Health Preflight Records

Local MCP health preflight records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-health-preflights/
```

`create_local_mcp_health_preflight_stub` requires an existing local MCP lane
capability contract. It records the disabled health-check prerequisites for
Omega Brain, SSWP, and Omega Stenographer:

- config lookup still required but not performed
- process health still required but not probed
- capability discovery still required but not run
- consent, approval, audit, and recovery gates remain required

The preflight record explicitly does not inspect configs, sockets, processes,
databases, captures, transcripts, or secrets. It also does not call tools,
discover live capabilities, capture, export, write memory, spawn processes,
control terminals, control the desktop, patch files, write files, mutate
workspaces, or execute anything:

- `live_probe_enabled: false`
- `live_call_enabled: false`
- `capability_discovery_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates the checkpoint that future live local MCP health records must
consume before probing or discovering capabilities.

## Disabled Local MCP Health Records

Local MCP health records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-health/
```

`create_local_mcp_health_record_stub` accepts a first-class local MCP subsystem
and requires an existing local MCP health preflight record. The scaffold
currently recognizes:

- `omega_brain`
- `sswp`
- `omega_stenographer`

The health record captures:

- display name and current surface
- planned health source
- expected config surfaces
- expected command ids
- capability summary
- linked health preflight id and readiness state
- capability-manifest, approval, audit, and recovery requirements
- disabled live probe/call/write/execution gates

It explicitly does not inspect config files, probe process health, call MCP
tools, repair native packages, write configs, spawn processes, or execute
anything:

- `live_probe_enabled: false`
- `live_call_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This gives the UI a durable readiness ledger for Omega Brain, SSWP, and Omega
Stenographer before live MCP startup health, capability discovery, or gated tool
calls are enabled.

## Local MCP Capability Discovery Policies

Local MCP capability discovery policy records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-capability-discovery-policies/
```

`create_local_mcp_capability_discovery_policy_stub` requires ready
preflight-linked health records for:

- Omega Brain
- SSWP
- Omega Stenographer

The policy records expected command ids and the manifest, approval, audit,
consent, and recovery gates that must exist before live capability discovery or
tool calls can be enabled.

The policy explicitly does not probe MCP servers, discover live manifests, call
tools, capture transcripts, export data, write memory, spawn processes, control
terminals, control the desktop, patch files, write files, mutate workspaces, or
execute anything:

- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates the final disabled policy checkpoint before a future gated-call
policy can define exactly how live MCP discovery and calls are allowed.

## Local MCP Gated-Call Policies

Local MCP gated-call policy records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-gated-call-policies/
```

`create_local_mcp_gated_call_policy_stub` requires an existing recorded local
MCP capability discovery policy with ready Omega Brain, SSWP, and Omega
Stenographer lanes. If no id is provided, it uses the latest ready discovery
policy.

The policy records the future command allowlists and the consent, approval,
audit, and recovery requirements that must exist before any live MCP call path
can be wired. It still keeps every live gate disabled:

- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates the disabled call-policy checkpoint before future per-call
approval, audit, and recovery records exist.

## Local MCP Call Approval Audit Records

Local MCP call approval/audit request records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-call-approval-audits/
```

`create_local_mcp_call_approval_audit_stub` requires a ready local MCP
gated-call policy and an allowlisted subsystem command. If no policy id is
provided, it uses the latest ready gated-call policy.

The request records which local MCP command would need consent, approval, audit,
and recovery evidence before any live call can happen. It does not grant consent
or approval and does not mark audit complete:

- `consent_recorded: false`
- `approval_recorded: false`
- `audit_recorded: false`
- `call_approved: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates the disabled approval/audit checkpoint before future explicit
consent, approval decisions, audit outcomes, or live MCP calls exist.

## Local MCP Consent Approval Decisions

Local MCP consent/approval decision records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-consent-approval-decisions/
```

`create_local_mcp_consent_approval_decision_stub` requires a recorded local MCP
call approval/audit request and the confirmation phrase
`CONFIRM LOCAL MCP DECISION`.

The record can capture explicit consent and approval decisions, but it still
does not mark the call approved because audit and recovery outcome records do
not exist yet:

- `consent_recorded: true` only for a confirmed decision
- `approval_recorded: true` only for a confirmed decision
- `audit_recorded: false`
- `recovery_recorded: false`
- `call_approved: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates explicit decision evidence before future audit outcome records or
live MCP calls exist.

## Local MCP Audit Outcome Records

Local MCP audit outcome records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-audit-outcomes/
```

`create_local_mcp_audit_outcome_stub` requires a recorded local MCP
consent/approval decision. If no decision id is provided, it uses the latest
ready consent/approval decision. Supported outcomes are `ready` and `defer`.

The record can capture audit outcome evidence, but recovery, final call
approval, and the live MCP call still do not exist:

- `audit_outcome_recorded: true` only for a supported outcome with ready decision evidence
- `audit_recorded: true` only when the audit outcome is recorded
- `recovery_recorded: false`
- `call_approved: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates audit outcome evidence before future recovery/pre-call guard
records or live MCP calls exist.

## Local MCP Recovery Pre-Call Guard Records

Local MCP recovery/pre-call guard records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-recovery-precall-guards/
```

`create_local_mcp_recovery_precall_guard_stub` requires a recorded local MCP
audit outcome. If no audit outcome id is provided, it uses the latest ready
audit outcome. Supported guard decisions are `ready` and `hold`.

The record can capture recovery/pre-call guard evidence, but final call
approval and the live MCP call still do not exist:

- `guard_recorded: true` only for a supported guard decision with ready audit evidence
- `recovery_guard_recorded: true` only when the guard is recorded
- `pre_call_guard_recorded: true` only when the guard is recorded
- `recovery_recorded: true` only when the guard is recorded
- `final_call_approval_required: true`
- `call_approved: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates recovery/pre-call guard evidence before future final call approval
records or live MCP calls exist.

## Final Local MCP Call Approval Records

Final local MCP call approval records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-final-call-approvals/
```

`create_local_mcp_final_call_approval_stub` requires a ready recovery/pre-call
guard and the confirmation phrase `CONFIRM LOCAL MCP FINAL CALL APPROVAL`. If no
guard id is provided, it uses the latest ready recovery/pre-call guard.
Supported decisions are `approve` and `deny`.

The record can capture final approval evidence, but the live MCP call still
does not exist:

- `final_approval_recorded: true` only for a supported decision with ready guard evidence and exact confirmation
- `call_approved: true` only for a confirmed `approve` decision
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates final approval evidence before future live-call dry-run records or
real MCP calls exist.

## Local MCP Live-Call Dry-Run Records

Local MCP live-call dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-live-call-dry-runs/
```

`create_local_mcp_live_call_dry_run_stub` requires a ready final local MCP call
approval. If no approval id is provided, it uses the latest ready final
approval. Supported dry-run modes are `plan` and `blocked`.

The record can capture the intended call envelope and payload summary, but it
does not read MCP config, connect to an MCP socket, read a live manifest, or
call an MCP server:

- `dry_run_recorded: true` only for a supported dry-run mode with ready final approval evidence
- `call_approved: true` can be carried from final approval evidence
- `dry_run_only: true`
- `payload_materialized: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates disabled dry-run evidence before typed lane contracts, read-only
status probes, or any real MCP calls exist.

## Local MCP Typed Command Contract Records

Local MCP typed command contract records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-typed-command-contracts/
```

`create_local_mcp_typed_command_contract_stub` requires a ready local MCP
live-call dry-run record. If no dry-run id is provided, it uses the latest ready
dry-run evidence.

The record captures typed request and response envelope contracts for first-class
Omega Brain, SSWP, and Omega Stenographer command lanes. It records shape only:
no MCP config is read, no socket is connected, no status probe runs, no live
manifest is read, and no MCP call is made.

The current command-contract set is:

- Omega Brain: `omega_brain_status`, `omega_brain_search`, `omega_brain_cite`, `omega_brain_memory_policy`
- SSWP: `sswp_status`, `sswp_capabilities`, `sswp_plan`, `sswp_call`
- Omega Stenographer: `steno_status`, `steno_search`, `steno_capture_policy`, `steno_export_policy`

The typed command contract model keeps all live gates closed:

- `typed_command_contract_recorded: true` only with ready dry-run evidence
- `read_only_status_probe_enabled: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates typed lane envelopes before future read-only MCP status probe
preflights or any real MCP calls exist.

## Local MCP Status Probe Preflight Records

Local MCP status probe preflight records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-status-probe-preflights/
```

`create_local_mcp_status_probe_preflight_stub` requires a ready typed local MCP
command contract record. If no typed contract id is provided, it uses the latest
ready contract evidence.

The record captures the prerequisite shape for read-only status probes for:

- Omega Brain: `omega_brain_status`
- SSWP: `sswp_status`
- Omega Stenographer: `steno_status`

This is still a preflight only. It marks config lookup and socket connection as
future requirements, but does not read config, connect sockets, read live
manifests, run a status probe, call MCP, capture/export, write memory, spawn
processes, control the terminal/desktop, mutate files, or execute.

The status probe preflight model keeps all live gates closed:

- `status_probe_preflight_recorded: true` only with ready typed command contracts
- `read_only_preflight: true` only when all first-class status lanes are present
- `read_only_status_probe_enabled: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates the final preflight layer before future local MCP config lookup
records or any real status probes exist.

## Local MCP Config Lookup Preflight Records

Local MCP config lookup preflight records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-lookup-preflights/
```

`create_local_mcp_config_lookup_preflight_stub` requires a ready local MCP
status probe preflight record. If no status preflight id is provided, it uses
the latest ready status preflight evidence.

The record names future config source ids for Omega Brain, SSWP, and Omega
Stenographer and records the checks that must exist before a config file can be
opened. It does not resolve paths, read files, parse config, inspect secrets,
connect sockets, read manifests, run status probes, or call MCP.

The config lookup preflight model keeps all live gates closed:

- `config_lookup_preflight_recorded: true` only with ready status preflight evidence
- `mcp_config_lookup_enabled: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates config lookup evidence before future explicit config-read policies
or any local MCP config file access exists.

## Local MCP Config Read Policy Records

Local MCP config read policy records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-read-policies/
```

`create_local_mcp_config_read_policy_stub` requires a ready local MCP config
lookup preflight record. If no config lookup preflight id is provided, it uses
the latest ready config lookup preflight evidence.

The record names the future config sources for Omega Brain, SSWP, and Omega
Stenographer and records the policy gates that must exist before any config file
can be opened or parsed: explicit approval, path allowlisting, minimum-scope
access, schema validation, secret redaction, and audit evidence. It does not
resolve real paths, expand env vars, open files, parse configs, inspect secrets,
connect sockets, read manifests, run probes, or call MCP.

The config read policy model keeps all live gates closed:

- `config_read_policy_recorded: true` only with ready config lookup preflight evidence
- `config_read_approval_required: true`
- `config_read_approval_recorded: false`
- `config_read_approved: false`
- `mcp_config_lookup_enabled: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates explicit policy evidence before future path allowlist and config
read request records, while still preventing any local MCP config file access.

## Local MCP Config Path Allowlist Records

Local MCP config path allowlist records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-allowlists/
```

`create_local_mcp_config_path_allowlist_stub` requires a ready local MCP config
read policy record. If no config read policy id is provided, it uses the latest
ready config read policy evidence.

The record stores scope labels for the future Omega Brain, SSWP, and Omega
Stenographer config paths, not real filesystem paths. It records that path
allowlisting, explicit approval, schema validation, secret redaction, and audit
evidence are required before any config path can be resolved, opened, parsed, or
used for runtime setup. It does not normalize paths, stat files, follow
symlinks, expand env vars, open files, parse configs, inspect secrets, connect
sockets, read manifests, run probes, or call MCP.

The config path allowlist model keeps all live gates closed:

- `config_path_allowlist_recorded: true` only with ready config read policy evidence
- `path_allowlist_recorded: true` for scope labels only
- `path_resolution_enabled: false`
- `path_open_approved: false`
- `config_read_approved: false`
- `mcp_config_lookup_enabled: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates explicit scope evidence before future config path resolution request
records while still preventing local MCP config path access.

## Local MCP Config Path Resolution Request Records

Local MCP config path resolution request records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-resolution-requests/
```

`create_local_mcp_config_path_resolution_request_stub` requires a ready local
MCP config path allowlist record. If no allowlist id is provided, it uses the
latest ready config path allowlist evidence.

The record requests future path resolution against the allowlist scope labels
for Omega Brain, SSWP, and Omega Stenographer. It does not materialize real
paths, normalize paths, stat files, follow symlinks, expand env vars, open
files, parse configs, inspect secrets, connect sockets, read manifests, run
probes, or call MCP.

The config path resolution request model keeps all live gates closed:

- `config_path_resolution_request_recorded: true` only with ready config path allowlist evidence
- `path_resolution_requested: true`
- `path_resolution_enabled: false`
- `path_normalization_enabled: false`
- `path_stat_enabled: false`
- `symlink_follow_enabled: false`
- `path_open_approved: false`
- `resolved_path_materialized: false`
- `config_read_approved: false`
- `mcp_config_lookup_enabled: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates explicit request evidence before future config path resolution
approval records while still preventing local MCP config path access.

## Local MCP Config Path Resolution Approval Records

Local MCP config path resolution approval records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-resolution-approvals/
```

`create_local_mcp_config_path_resolution_approval_stub` requires a ready local
MCP config path resolution request record. If no request id is provided, it uses
the latest ready config path resolution request evidence.

The record stores an explicit approval decision and confirmation phrase for the
future path-resolution step. Even when approval is recorded, it does not
materialize real paths, normalize paths, stat files, follow symlinks, expand env
vars, open files, parse configs, inspect secrets, connect sockets, read
manifests, run probes, or call MCP.

The config path resolution approval model keeps all live gates closed:

- `path_resolution_approval_recorded: true` only with ready path resolution request evidence
- `path_resolution_approved: true` only for an approved, confirmed decision
- `path_resolution_enabled: false`
- `path_normalization_enabled: false`
- `path_stat_enabled: false`
- `symlink_follow_enabled: false`
- `path_open_approved: false`
- `resolved_path_materialized: false`

## Local MCP Config Path Resolution Dry-Run Records

Local MCP config path resolution dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-resolution-dry-runs/
```

`create_local_mcp_config_path_resolution_dry_run_stub` requires a ready local
MCP config path resolution approval record. If no approval id is provided, it
uses the latest ready path resolution approval evidence.

The dry-run record proves the future path-resolution lane can consume approval
evidence without touching a real path. It does not capture real path values,
materialize resolved paths, normalize paths, stat files, follow symlinks,
expand env vars, open files, parse configs, inspect secrets, connect sockets,
read manifests, run probes, or call MCP.

The config path resolution dry-run model keeps all live gates closed:

- `path_resolution_dry_run_recorded: true` only with ready approval evidence
- `path_resolution_dry_run_ready: true` means the dry-run evidence exists, not that path access is enabled
- `real_path_values_captured: false`
- `path_resolution_enabled: false`
- `path_normalization_enabled: false`
- `path_stat_enabled: false`
- `symlink_follow_enabled: false`
- `path_open_approved: false`
- `resolved_path_materialized: false`

## Local MCP Config Path Materialization Request Records

Local MCP config path materialization request records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-materialization-requests/
```

`create_local_mcp_config_path_materialization_request_stub` requires a ready
local MCP config path resolution dry-run record. If no dry-run id is provided,
it uses the latest ready dry-run evidence.

The materialization request record proves the future path-materialization lane
can consume dry-run evidence without touching a real path. It does not capture
real path values, materialize resolved paths, normalize paths, stat files,
follow symlinks, expand env vars, open files, parse configs, inspect secrets,
connect sockets, read manifests, run probes, or call MCP.

The config path materialization request model keeps all live gates closed:

- `path_materialization_request_recorded: true` only with ready dry-run evidence
- `path_materialization_requested: true` records intent, not enabled behavior
- `path_materialization_enabled: false`
- `real_path_values_captured: false`
- `path_resolution_enabled: false`
- `path_normalization_enabled: false`
- `path_stat_enabled: false`
- `symlink_follow_enabled: false`
- `path_open_approved: false`
- `resolved_path_materialized: false`

## Local MCP Config Path Materialization Approval Records

Local MCP config path materialization approval records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-materialization-approvals/
```

`create_local_mcp_config_path_materialization_approval_stub` requires a ready
local MCP config path materialization request record. If no request id is
provided, it uses the latest ready materialization request evidence.

The approval record stores an explicit approval decision and confirmation phrase
for the future path-materialization step. Even when approval is recorded, it
does not capture real path values, materialize resolved paths, normalize paths,
stat files, follow symlinks, expand env vars, open files, parse configs,
inspect secrets, connect sockets, read manifests, run probes, or call MCP.

The config path materialization approval model keeps all live gates closed:

- `path_materialization_approval_recorded: true` only with ready materialization request evidence
- `path_materialization_approved: true` only for an approved, confirmed decision
- `path_materialization_enabled: false`
- `real_path_values_captured: false`
- `path_resolution_enabled: false`
- `path_normalization_enabled: false`
- `path_stat_enabled: false`
- `symlink_follow_enabled: false`
- `path_open_approved: false`
- `resolved_path_materialized: false`

## Local MCP Config Path Materialization Final Dry-Run Records

Local MCP config path materialization final dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-materialization-final-dry-runs/
```

`create_local_mcp_config_path_materialization_final_dry_run_stub` requires a
ready local MCP config path materialization approval record. If no approval id
is provided, it uses the latest ready materialization approval evidence.

The final dry-run record is the last evidence checkpoint before any future path
materialization implementation. It does not capture real path values,
materialize resolved paths, normalize paths, stat files, follow symlinks, expand
env vars, open files, parse configs, inspect secrets, connect sockets, read
manifests, run probes, or call MCP.

The config path materialization final dry-run model keeps all live gates closed:

- `path_materialization_final_dry_run_recorded: true` only with ready materialization approval evidence
- `path_materialization_final_dry_run_ready: true` means the dry-run evidence exists, not that path access is enabled
- `path_materialization_enabled: false`
- `real_path_values_captured: false`
- `path_resolution_enabled: false`
- `path_normalization_enabled: false`
- `path_stat_enabled: false`
- `symlink_follow_enabled: false`
- `path_open_approved: false`
- `resolved_path_materialized: false`
- `config_read_approved: false`
- `mcp_config_lookup_enabled: false`
- `mcp_config_read_enabled: false`
- `mcp_socket_connect_enabled: false`
- `live_manifest_read_enabled: false`
- `live_probe_enabled: false`
- `capability_discovery_enabled: false`
- `live_call_enabled: false`
- `capture_enabled: false`
- `export_enabled: false`
- `memory_write_enabled: false`
- `desktop_control_enabled: false`
- `terminal_enabled: false`
- `process_spawn_enabled: false`
- `file_write_enabled: false`
- `patch_apply_enabled: false`
- `writes_allowed: false`
- `execution_enabled: false`

This creates explicit approval evidence before future disabled path-resolution
dry-run records while still preventing local MCP config path access.


Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-review dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-review-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_closure_review_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-completion-review dry-run record. If
no schema-validation-fixture-retention-release-publication-release-completion-review dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-completion-review
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-closure-review dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-closure-approval slices consume
schema-validation-fixture-retention-release-publication-release-closure-review evidence without turning planned
retention-release-publication-release-closure-review records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, publication release completion review, publication release closure review, export, or runtime setup.


Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-approval dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-approval-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_closure_approval_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-closure-review dry-run record. If
no schema-validation-fixture-retention-release-publication-release-closure-review dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-closure-review
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-closure-approval dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-closure-finalization slices consume
schema-validation-fixture-retention-release-publication-release-closure-approval evidence without turning planned
retention-release-publication-release-closure-approval records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, publication release closure review, publication release closure approval, export, or runtime setup.


Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-finalization dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-finalization-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_closure_finalization_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-closure-approval dry-run record. If
no schema-validation-fixture-retention-release-publication-release-closure-approval dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-closure-approval
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-closure-finalization dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-closure-completion-review slices consume
schema-validation-fixture-retention-release-publication-release-closure-finalization evidence without turning planned
retention-release-publication-release-closure-finalization records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, publication release closure approval, publication release closure finalization, export, or runtime setup.


Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-completion-review dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-completion-review-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_closure_completion_review_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-closure-finalization dry-run record. If
no schema-validation-fixture-retention-release-publication-release-closure-finalization dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-closure-finalization
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-closure-completion-review dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-closure-release-readiness slices consume
schema-validation-fixture-retention-release-publication-release-closure-completion-review evidence without turning planned
retention-release-publication-release-closure-completion-review records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, publication release closure finalization, publication release closure completion review, export, or runtime setup.

Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-readiness dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-readiness-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_closure_release_readiness_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-closure-completion-review dry-run record. If
no schema-validation-fixture-retention-release-publication-release-closure-completion-review dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-closure-completion-review
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-closure-release-readiness dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-closure-release-approval slices consume
schema-validation-fixture-retention-release-publication-release-closure-release-readiness evidence without turning planned
retention-release-publication-release-closure-release-readiness records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, publication release closure completion review, publication release closure release readiness, export, or runtime setup.

Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-approval dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-approval-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_closure_release_approval_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-readiness dry-run record. If
no schema-validation-fixture-retention-release-publication-release-closure-release-readiness dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-closure-release-readiness
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-closure-release-approval dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-closure-release-finalization slices consume
schema-validation-fixture-retention-release-publication-release-closure-release-approval evidence without turning planned
retention-release-publication-release-closure-release-approval records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, publication release closure release readiness, publication release closure release approval, export, or runtime setup.

Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-finalization dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-finalization-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_closure_release_finalization_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-approval dry-run record. If
no schema-validation-fixture-retention-release-publication-release-closure-release-approval dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-closure-release-approval
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-closure-release-finalization dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-closure-release-completion-review slices consume
schema-validation-fixture-retention-release-publication-release-closure-release-finalization evidence without turning planned
retention-release-publication-release-closure-release-finalization records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, publication release closure release approval, publication release closure release finalization, export, or runtime setup.

Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-completion-review dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-completion-review-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_closure_release_completion_review_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-finalization dry-run record. If
no schema-validation-fixture-retention-release-publication-release-closure-release-finalization dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-closure-release-finalization
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-closure-release-completion-review dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-closure-release-release-readiness slices consume
schema-validation-fixture-retention-release-publication-release-closure-release-completion-review evidence without turning planned
retention-release-publication-release-closure-release-completion-review records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, publication release closure release finalization, publication release closure release completion review, export, or runtime setup.

Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-release-readiness dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-readiness-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_closure_release_release_readiness_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-completion-review dry-run record. If
no schema-validation-fixture-retention-release-publication-release-closure-release-completion-review dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-closure-release-completion-review
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-closure-release-release-readiness dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-closure-release-release-approval slices consume
schema-validation-fixture-retention-release-publication-release-closure-release-release-readiness evidence without turning planned
retention-release-publication-release-closure-release-release-readiness records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, publication release closure release completion review, publication release closure release release readiness, export, or runtime setup.

Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-release-approval dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-approval-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_closure_release_release_approval_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-release-readiness dry-run record. If
no schema-validation-fixture-retention-release-publication-release-closure-release-release-readiness dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-closure-release-release-readiness
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-closure-release-release-approval dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization slices consume
schema-validation-fixture-retention-release-publication-release-closure-release-release-approval evidence without turning planned
retention-release-publication-release-closure-release-release-approval records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, publication release closure release release readiness, publication release closure release release approval, export, or runtime setup.


Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_closure_release_release_finalization_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-release-approval dry-run record. If
no schema-validation-fixture-retention-release-publication-release-closure-release-release-approval dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-closure-release-release-approval
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization slices consume
schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization evidence without turning planned
retention-release-publication-release-closure-release-release-finalization records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, publication release closure release release approval, publication release closure release release finalization, export, or runtime setup.


Local MCP sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-release-completion-review dry-run records use:

```text
$XDG_STATE_HOME/gravity-omega-native/local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-completion-review-dry-runs/
```

`create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_retention_release_publication_release_closure_release_release_completion_review_dry_run_stub`
requires a ready sealed config content read schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization dry-run record. If
no schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization dry-run id is provided, it uses the latest ready schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization
evidence. Supported dry-run mode is `plan`.

The schema-validation-fixture-retention-release-publication-release-closure-release-release-completion-review dry-run record can record per-lane schema-validation
planning evidence for Omega Brain, SSWP, and Omega Stenographer, but it still
does not execute parsing, execute hashing, execute redaction, execute schema
validation, open config paths, read bytes, materialize config content, capture
content, export, connect sockets, call MCP servers, spawn processes, write
files, apply patches, or execute anything.

This lets later schema-validation-fixture-retention-release-publication-release-closure-release-release-completion-review slices consume
schema-validation-fixture-retention-release-publication-release-closure-release-release-completion-review evidence without turning planned
retention-release-publication-release-closure-release-release-completion-review records into real config access, secret inspection, content capture,
archive inspection, retention mutation, review mutation, release approval, publication release approval, publication release finalization, publication release closure release release finalization, publication release closure release release completion review, export, or runtime setup.

## Replacement App Foundation Scorecard

`replacement_app_foundation_scorecard` is a read-only command that reports the
current non-redundant replacement-app foundation lanes:

- Codex operating loop
- Hermes joint CI
- Omega Brain
- SSWP
- Omega Stenographer
- Codex pet
- workspace/editor/diff/patch
- terminal/process supervision
- approval/evidence spine
- Linux desktop computer-use

The command does not persist records and does not read local MCP config content.
It is meant to prevent roadmap drift by keeping the rebuild oriented around
world-class app surfaces instead of endlessly extending release dry-run chains.
Every returned lane keeps live probes, MCP calls, capture, export, desktop
control, terminal/process spawning, file writes, patch application, memory
writes, and execution disabled.

## Replacement App Work Queue

`replacement_app_work_queue` is a read-only command that turns the foundation
scorecard into an ordered next-slice queue. It ranks the current safest
replacement-app lanes:

1. workspace/editor shell
2. Codex/Hermes run view
3. first-class MCP dashboard
4. Steno transcript evidence
5. Codex pet companion
6. terminal/process supervisor
7. approval/evidence spine
8. Linux desktop computer-use

The command does not persist records, read local MCP config content, inspect
assets, capture transcripts, call MCP servers, spawn processes, apply patches,
write files, control the desktop, export data, write memory, or execute
anything. It exists so Gravity Omega can pick meaningful replacement-app slices
from the scorecard without drifting back into redundant dry-run suffix chains.

## Codex/Hermes Run View Dashboard

`codex_hermes_run_view_dashboard` is a read-only command that turns existing
Codex/Hermes evidence ledgers into one operator surface. It groups:

- task runs
- approvals
- runner readiness
- joint Codex/Hermes plans
- stored artifact previews
- transcript bundles
- transcript export and protection policies
- typed event log previews

The dashboard derives counts and statuses from existing records only. It does
not create task, approval, runner, joint plan, artifact, transcript, export,
protection, or event records. It also does not spawn processes, control
terminals, call live MCP tools, read live config, write files, apply patches,
control the desktop, capture media, export data, write memory, or execute
anything. This gives the Codex/Hermes lane a product-facing run view before any
runtime or write gate is enabled.

## Codex/Hermes Run Detail Timeline

`codex_hermes_run_detail_timeline` is a read-only command that binds the run
view dashboard to the active task run and shows one per-run evidence timeline.
It groups:

- active task-run record
- approvals linked to the run
- runner readiness linked to the run
- joint Codex/Hermes plan linked to the run
- stored artifact preview
- typed event log preview
- transcript bundles linked to the run
- transcript export and protection policies linked to the run

The timeline derives counts and summaries from existing records only. It does
not create task runs, approvals, runner invocations, joint plans, artifacts,
transcripts, export policies, protection policies, or events. It also does not
spawn processes, control terminals, call live MCP tools, read live config,
write files, apply patches, control the desktop, capture media, export data,
write memory, or execute anything. This gives the operator a single-run
inspection surface before live Codex/Hermes runners or write gates are enabled.

## Codex/Hermes Run Selection Comparison

`codex_hermes_run_selection_comparison` is a read-only command that builds on
the active run detail timeline. It lists run-selection options and compares the
active run across three runtime lanes:

- Codex
- Hermes
- Gravity Omega reconciliation

The comparison derives counts from existing task-run, approval, runner,
joint-plan, process-plan, typed-event, transcript-bundle, transcript export, and
transcript protection ledgers. It does not select, mutate, reorder, create, or
delete task runs or evidence records. It also does not spawn processes, control
terminals, call live MCP tools, read live config, write files, apply patches,
control the desktop, capture media, export data, write memory, or execute
anything. This gives the operator one place to see whether Codex, Hermes, and
Gravity Omega evidence are balanced before any live execution or mutation gate
is opened.

## Codex/Hermes Evidence Diff Board

`codex_hermes_run_evidence_diff_board` is a read-only command that derives
direct Codex-vs-Hermes gap records from the run selection comparison. It
compares:

- planned phases
- runner readiness
- process plans
- typed events
- transcript bundles
- export policies
- protection policies
- total ready evidence

The diff board is advisory only. It does not select, mutate, reorder, create,
delete, export, or execute task runs or evidence records. It also does not spawn
processes, control terminals, call live MCP tools, read live config, write
files, apply patches, control the desktop, capture media, export data, write
memory, or execute anything. This gives the operator a parity checklist for
closing Codex/Hermes evidence gaps before any live runtime or mutation gate is
opened.

## Codex/Hermes Reconciliation Checklist

`codex_hermes_run_reconciliation_checklist` is a read-only command that consumes
the evidence diff board and turns each Codex-vs-Hermes metric into an operator
check. It also adds a Gravity Omega reconciliation check so the operator can see
whether the app has its own reconciliation evidence before live runtime work
starts.

The checklist marks balanced diff records as ready and visible gaps as
action-required, but it does not resolve, mutate, reorder, create, delete,
export, or execute task runs or evidence records. It also does not spawn
processes, control terminals, call live MCP tools, read live config, write
files, apply patches, control the desktop, capture media, export data, write
memory, or execute anything. This gives the operator a close-gap checklist that
can guide later Codex/Hermes orchestration without opening any live gate.

## Codex/Hermes Reconciliation Action Plan

`codex_hermes_run_reconciliation_action_plan` is a read-only command that
consumes the reconciliation checklist and ranks action-required gaps into a
close-gap action plan. It carries each action's source check, source diff,
metric, priority, missing evidence count, current Codex/Hermes counts, blocked
state, and recommended operator next step.

The action plan is advisory only. It does not assign, approve, resolve, mutate,
reorder, create, delete, export, or execute task runs, checklist items, actions,
or evidence records. It also does not spawn processes, control terminals, call
live MCP tools, read live config, write files, apply patches, control the
desktop, capture media, export data, write memory, or execute anything. This
lets the operator see which close-gap items matter first while every live
runtime, write, export, memory, desktop, capture, and execution gate remains
sealed.

## Codex/Hermes Evidence Attachment Preview

`codex_hermes_run_evidence_attachment_preview` is a read-only command that
consumes the reconciliation action plan and previews the blocked Hermes-side
evidence attachments needed for each close-gap action. Each preview carries the
source action, source diff, target runtime, evidence metric, attachment kind,
priority, missing evidence count, blocked state, and recommended operator next
step.

The attachment preview is advisory only. It does not attach, upload, persist,
assign, approve, resolve, mutate, reorder, create, delete, export, or execute
task runs, actions, or evidence records. It also does not spawn processes,
control terminals, call live MCP tools, read live config, open sockets, write
files, apply patches, control the desktop, capture media, export data, write
memory, or execute anything. This lets the operator see what proof will be
needed before any evidence intake or runtime gate opens.

## Codex/Hermes Evidence Attachment Approval Packet

`codex_hermes_run_evidence_attachment_approval_packet` is a read-only command
that consumes the evidence attachment preview and maps every blocked
Hermes-side proof need to an explicit operator approval packet. Each packet
carries its source preview, source action, source diff, target runtime, evidence
metric, attachment kind, required approval kind, approval status, missing
evidence count, blocked state, and operator question.

The approval packet is advisory only. It does not create approvals, resolve
approvals, attach evidence, upload, persist, assign, mutate, reorder, create,
delete, export, or execute task runs, actions, approvals, or evidence records.
It also does not spawn processes, control terminals, call live MCP tools, read
live config, open sockets, write files, apply patches, control the desktop,
capture media, export data, write memory, or execute anything. This lets the
operator see the approval shape required before any evidence intake can happen.

## Codex/Hermes Evidence Intake Workbench

`codex_hermes_run_evidence_intake_workbench` is a read-only command that
consumes the evidence attachment approval packet and previews disabled intake
forms for Hermes-side proof gaps. Each form carries its source approval packet,
source preview, target runtime, evidence metric, attachment kind, required
fields, missing evidence count, approval state, blocked submit state, and next
operator step.

The intake workbench is advisory only. It does not submit forms, create
approvals, resolve approvals, attach evidence, upload, persist, assign, mutate,
reorder, create, delete, export, or execute task runs, actions, approvals,
forms, or evidence records. It also does not spawn processes, control
terminals, call live MCP tools, read live config, open sockets, write files,
apply patches, control the desktop, capture media, export data, write memory,
or execute anything. This lets the operator see the future intake shape without
opening approval mutation or evidence intake gates.

## Codex/Hermes Evidence Validation Summary

`codex_hermes_run_evidence_validation_summary` is a read-only command that
consumes the evidence intake workbench and previews validation readiness for
each disabled Hermes-side proof gap. Each summary carries its source intake
form, source packet, target runtime, evidence metric, attachment kind, required
field count, missing field-value count, missing evidence count, approval state,
evidence presence, blocked validation state, and validation message.

The validation summary is advisory only. It does not validate live evidence,
submit forms, create approvals, resolve approvals, attach evidence, upload,
persist, assign, mutate, reorder, create, delete, export, or execute task runs,
actions, approvals, forms, summaries, or evidence records. It also does not
spawn processes, control terminals, call live MCP tools, read live config, open
sockets, write files, apply patches, control the desktop, capture media, export
data, write memory, or execute anything. This lets the operator see why every
future intake remains blocked before any operator confirmation or validation
submission gate is opened.

## Codex/Hermes Evidence Operator Confirmation Dry-Runs

`codex_hermes_run_evidence_operator_confirmation_dry_runs` is a read-only
command that consumes the evidence validation summary and previews the operator
acknowledgements required before evidence intake can proceed. Each dry-run
carries its source validation summary, source form, source packet, target
runtime, evidence metric, attachment kind, required acknowledgements, missing
acknowledgement count, missing field-value count, missing evidence count,
validation readiness, confirmation state, blocked submit state, and dry-run
message.

The operator confirmation dry-runs are advisory only. They do not record
confirmations, validate live evidence, submit forms, create approvals, resolve
approvals, attach evidence, upload, persist, assign, mutate, reorder, create,
delete, export, or execute task runs, actions, approvals, forms, confirmations,
or evidence records. They also do not spawn processes, control terminals, call
live MCP tools, read live config, open sockets, write files, apply patches,
control the desktop, capture media, export data, write memory, or execute
anything. This lets the operator see the future confirmation gate shape without
opening confirmation submission, evidence intake, or runtime gates.

## First-Class MCP Dashboard

`first_class_mcp_dashboard` is a read-only command that turns existing local MCP
evidence ledgers into one operator surface for the three first-class local MCP
lanes:

- Omega Brain
- SSWP
- Omega Stenographer

The dashboard summarizes each lane's expected command ids, evidence depth, ready
evidence count, and current read-only status across local MCP contracts, health
preflights, health records, discovery policies, gated-call policies,
call-approval/audit requests, consent/approval decisions, audit outcomes,
recovery/pre-call guards, final approvals, live-call dry-runs, typed command
contracts, status probe preflights, and config lookup preflights.

The command reads existing records only. It does not create local MCP records,
call MCP servers, probe processes, read config, open sockets, capture Steno
data, export transcripts, write memory, write files, apply patches, spawn
processes, control terminals or the desktop, or execute anything. It exists so
Omega Brain, SSWP, and Steno appear as native replacement-app lanes rather than
anonymous plugin rows while every live gate remains disabled.

## Steno Pet Companion Dashboard

`steno_pet_companion_dashboard` is a read-only command that turns existing
transcript evidence, Omega Stenographer MCP evidence, and Codex pet readiness
records into one operator surface.

The dashboard groups five sections:

- Steno transcript evidence
- Steno export policy
- Steno protection policy
- Omega Stenographer MCP lane
- Codex pet companion readiness

The command derives its counts from existing run transcript bundles, transcript
export policies, transcript protection policies, the first-class MCP dashboard,
agent capability inventories, and first-class integration readiness records. It
does not create transcript, export, protection, MCP, inventory, readiness, pet,
asset, config, capture, or memory records.

The dashboard explicitly keeps capture, export, pet asset inspection, live MCP
calls, config reads, sockets, writes, patches, desktop control, terminal
control, process spawning, memory writes, and execution disabled. It exists so
Steno and the Codex pet have a visible first-class product surface before any
capture/export or asset-loading path is enabled.

## Terminal Process Lane Dashboard

`terminal_process_lane_dashboard` is a read-only command that turns existing
runner and process ledgers into one terminal/process operator surface. It
groups:

- runner invocation gate evidence
- runner adapter readiness
- process command plans
- process stream initialization
- process lifecycles
- process control policies
- supervisor preflights
- supervisor heartbeats
- supervisor exit summaries
- output-tail summaries

The command derives its counts from existing records only. It does not create
runner, adapter, command-plan, stream, lifecycle, policy, supervisor, output,
terminal, process, config, capture, export, or memory records.

The dashboard explicitly keeps terminal writes, process spawning, stream reads,
live tailing, process control, file writes, patches, desktop control, live MCP
calls, config reads, capture, export, memory writes, and execution disabled. It
exists so Gravity Omega can show the terminal/process lane as a coherent product
surface before any PTY, process runner, supervisor loop, PID model, stream
reader, or control gate is enabled.

## Approval Evidence Spine Dashboard

`approval_evidence_spine_dashboard` is a read-only command that unifies existing
safety evidence into one native operator surface. It groups:

- approval records
- persisted runner gate decisions
- task-run artifact previews
- typed agent event logs
- local MCP call approval/audit requests
- local MCP consent and approval decisions
- local MCP audit outcomes
- transcript export policies
- transcript protection policies
- terminal/process lane evidence

The command derives its counts from existing ledgers only. It does not create
approval, gate, artifact, event, MCP audit, consent, transcript, terminal,
process, config, capture, export, memory, file, patch, or execution records, and
it does not evaluate a new live command.

The dashboard explicitly keeps mutation, file writes, patch application, process
spawning, terminal control, desktop control, live MCP calls, sockets, config
reads, capture, export, memory writes, workspace writes, and execution disabled.
It exists so approvals, audits, transcripts, and terminal/process evidence read
as one product spine before any live control or mutation gate is enabled.

## Linux Desktop Control Readiness Dashboard

`linux_desktop_control_readiness_dashboard` is a read-only command that groups
existing Linux desktop computer-use readiness evidence into one native operator
surface. It summarizes:

- replacement-app foundation desktop lane
- replacement-app work queue desktop lane
- agent capability inventory desktop items
- first-class integration desktop readiness items
- approval/evidence spine prerequisite sections
- browser and Linux computer-use command surface

The command derives its counts from existing ledgers only. It does not create
desktop, capture, OCR, target-window, element-action, socket, process, terminal,
config, approval, MCP, export, memory, file, patch, or execution records. It also
does not call computer-use tools, inspect the live desktop, capture screenshots,
perform OCR, focus windows, click/type/scroll/drag, open sockets, spawn
processes, control terminals, call MCP servers, read local config, write files,
apply patches, export data, write memory, or execute anything.

The dashboard explicitly keeps desktop control, capture, sockets, process
spawn, terminal control, file writes, patches, live MCP calls, config reads,
exports, memory writes, workspace writes, and execution disabled. It exists so
Linux desktop control has a visible product-facing readiness surface before any
screenshot, OCR, target-window, element-action, socket, process, terminal, or
execution gate is opened.

## Desktop Capture Action Approval Policy Dashboard

`desktop_capture_action_approval_policy_dashboard` is a read-only command that
turns the next Linux desktop-control policy layer into one operator surface. It
groups:

- Linux desktop readiness prerequisites
- approval/evidence spine prerequisites
- sandbox restricted-policy evidence
- browser and Linux computer-use command surface
- screenshot, OCR, target-window, and element-action policy areas
- operator confirmation gates

The command derives readiness counts from existing ledgers and uses static
policy-area metadata only. It does not create desktop, screenshot, OCR,
target-window, element-action, socket, process, terminal, config, approval,
sandbox, export, memory, file, patch, or execution records. It also does not
call computer-use tools, inspect the live desktop, capture screenshots, perform
OCR, enumerate or focus windows, click/type/scroll/drag, open sockets, spawn
processes, control terminals, call MCP servers, read local config, write files,
apply patches, export data, write memory, or execute anything.

The dashboard explicitly keeps screenshot capture, OCR, target-window control,
element actions, desktop control, sockets, process spawn, terminal control,
file writes, patches, live MCP calls, config reads, exports, memory writes,
workspace writes, and execution disabled. It exists so desktop capture/action
approval policy is visible before any live desktop control or capture gate is
opened.

## Desktop Capture Action Approval Records

`desktop_capture_action_approval_records` is a read-only command that turns the
sealed desktop capture/action approval policy into four explicit operator
records:

- screenshot capture approval policy
- OCR extraction approval policy
- target-window resolution approval policy
- element action approval policy

Each record carries the capability id, required approval, required evidence,
required operator confirmation, redaction profile, and retention tier. The
records derive from the desktop capture/action approval policy dashboard and do
not create live approvals, screenshots, OCR output, target-window focus,
element actions, socket/process/terminal activity, config reads, exports, file
writes, patches, memory writes, or execution.

The records explicitly keep screenshot capture, OCR, target-window control,
element actions, desktop control, sockets, process spawn, terminal control,
file writes, patches, live MCP calls, config reads, exports, memory writes,
workspace writes, and execution disabled. They exist so the per-capability
approval model is visible before operator confirmation dry-runs or live desktop
capabilities are considered.

## Desktop Operator Confirmation Dry Runs

`desktop_capture_action_operator_confirmation_dry_runs` is a read-only command
that derives four explicit confirmation dry-runs from the desktop capture/action
approval records:

- screenshot operator confirmation dry-run
- OCR operator confirmation dry-run
- target-window operator confirmation dry-run
- element action operator confirmation dry-run

Each dry-run record keeps the source approval record id, capability, policy
area, required confirmation text, confirmation prompt, dry-run summary, required
evidence, redaction profile, and retention tier. It does not record a real
operator approval, inspect the desktop, capture screenshots, run OCR, focus a
window, perform element actions, open sockets, spawn processes, control
terminals, call MCP servers, read local config, write files, apply patches,
export data, write memory, or execute anything.

The dry-runs explicitly keep screenshot capture, OCR, target-window control,
element actions, desktop control, sockets, process spawn, terminal control,
file writes, patches, live MCP calls, config reads, exports, memory writes,
workspace writes, and execution disabled. They exist so the human confirmation
step is visible before final pre-action dry-runs or live desktop capabilities
are considered.

## Desktop Final Pre-Action Dry Runs

`desktop_capture_action_final_preaction_dry_runs` is a read-only command that
derives four final pre-action dry-runs from the operator-confirmation dry-runs:

- screenshot final pre-action dry-run
- OCR final pre-action dry-run
- target-window final pre-action dry-run
- element action final pre-action dry-run

Each final dry-run keeps the source confirmation dry-run id, source approval
record id, capability, policy area, pre-action checklist, pre-action summary,
required confirmation, required evidence, redaction profile, retention tier, and
the explicit requirement for confirmed operator evidence. It does not record
confirmed operator evidence, inspect the desktop, capture screenshots, run OCR,
focus a window, perform element actions, open sockets, spawn processes, control
terminals, call MCP servers, read local config, write files, apply patches,
export data, write memory, or execute anything.

The final dry-runs explicitly keep screenshot capture, OCR, target-window
control, element actions, desktop control, sockets, process spawn, terminal
control, file writes, patches, live MCP calls, config reads, exports, memory
writes, workspace writes, and execution disabled. They exist so confirmed
operator evidence remains a visible blocker before any live desktop capability
can be considered.

## Desktop Action Safety Summary

`desktop_action_safety_summary` is a read-only command that aggregates the
sealed desktop action safety stack into one compact operator view:

- desktop capture/action policy dashboard
- screenshot, OCR, target-window, and element-action approval records
- operator-confirmation dry-runs
- final pre-action dry-runs
- per-capability safety matrix

The summary derives counts from the existing read-only desktop policy,
approval, confirmation, and final pre-action surfaces. It does not record
confirmed operator evidence, inspect the desktop, capture screenshots, run OCR,
focus a window, perform element actions, open sockets, spawn processes, control
terminals, call MCP servers, read local config, write files, apply patches,
export data, write memory, or execute anything.

The summary explicitly keeps screenshot capture, OCR, target-window control,
element actions, desktop control, sockets, process spawn, terminal control,
file writes, patches, live MCP calls, config reads, exports, memory writes,
workspace writes, and execution disabled. It exists so the full desktop safety
posture is visible before any release checklist or live desktop capability gate
is considered.

## Linux Desktop Readiness Release Checklist

`linux_desktop_readiness_release_checklist` is a read-only command that
aggregates the Linux desktop release posture into one operator checklist before
any live desktop capability gate can be considered:

- Linux desktop readiness dashboard
- desktop action safety summary
- approval/evidence spine
- sandbox restricted policy
- confirmed operator evidence requirement
- final release decision gate

The checklist derives counts from existing sealed read-only desktop safety
surfaces. It does not record confirmed operator evidence, inspect the desktop,
capture screenshots, run OCR, focus a window, perform element actions, open
sockets, spawn processes, control terminals, call MCP servers, read local
config, write files, apply patches, export data, write memory, or execute
anything.

The checklist explicitly keeps screenshot capture, OCR, target-window control,
element actions, desktop control, sockets, process spawn, terminal control,
file writes, patches, live MCP calls, config reads, exports, memory writes,
workspace writes, and execution disabled. It exists so evidence readiness and
release readiness are separated: readiness evidence can be visible while the
actual release decision remains blocked.

## Workspace Editor Navigation Lane

`workspace_editor_navigation_lane` is a read-only command that aggregates
existing persisted workspace/editor records into one compact navigation lane:

- workspace inspection
- workspace preview
- tree metadata
- file preview
- editor tab state
- edit/save preflight
- write policy
- write approval
- buffer draft
- dirty-state preflight

The command only lists existing records and counts them. It does not create
records, read live file contents, read config files, call MCP servers, spawn
terminal or process sessions, control the desktop, capture media, export data,
write memory, write workspace files, apply patches, or execute anything. It is
the bridge from record ledgers toward a real read-only editor shell while every
mutation gate remains disabled.

## Workspace Editor Shell Layout

`workspace_editor_shell_layout` is a read-only command that derives a product
layout from the workspace editor navigation lane. It exposes four panels:

- workspace tree
- file preview
- tab buffer
- mutation gates

Each panel is built from existing persisted record counts only. The command does
not create records, read live file contents, open config files, call MCP
servers, connect sockets, spawn terminal or process sessions, control the
desktop, capture media, export data, write memory, write workspace files, apply
patches, or execute anything. This is the first editor-shell shape for the
rebuild: useful enough to drive UI composition, but still sealed away from every
mutation path.

## Workspace Editor Shell Bindings

`workspace_editor_shell_bindings` is a read-only command that binds each editor
shell panel to existing UI targets:

- `workspace-tree` binds to workspace inspection, preview, and tree metadata
  summaries/ledgers.
- `file-preview` binds to file preview summary, preview text, and file preview
  ledger.
- `tab-buffer` binds to editor tab summary, buffer preview, and tab ledger.
- `mutation-gates` binds to edit/save, write policy, write approval, buffer
  draft, and dirty-state summaries/ledgers.

The command also records panel dependencies so the frontend can explain why a
panel is waiting without creating records or performing live reads. It does not
open files, read config, call MCP servers, connect sockets, spawn processes,
control terminals or the desktop, capture media, export data, write memory,
write workspace files, apply patches, or execute anything.

## Workspace Editor Shell Focus Model

`workspace_editor_shell_focus_model` is a read-only command that chooses the
current editor-shell navigation target from existing shell bindings. The focus
preference is:

1. tab buffer, when read-only editor tab state is ready
2. file preview, when bounded preview evidence is ready but no tab is ready
3. workspace tree, when only workspace/tree evidence is ready
4. mutation gates, only to explain blocked edit/save/write/dirty evidence

The command returns focus metadata only: active panel id, active target id,
ranked focus items, readiness, and reasons. It does not move a cursor, open a
file, read config, call MCP servers, connect sockets, spawn processes, control
terminals or the desktop, capture media, export data, write memory, write
workspace files, apply patches, or execute anything.

## First-Class Integration Launchpad

`first_class_integration_launchpad` is a live read-only command that makes the
remaining core integration toolbar rows product-visible without enabling their
underlying actions.

The launchpad covers:

- `agent.hermes_companion`
- `agent.joint_ci`
- `mcp.sswp_call`
- `steno.capture`

Each toolbar row now opens the launchpad through
`first_class_integration_launchpad` while preserving the underlying target name
as readiness metadata. Hermes process start, Joint CI execution, SSWP MCP
calls, Omega Stenographer capture, transcript reads, terminal/process control,
config reads, sockets, file reads, writes, patches, desktop control, capture,
export, memory writes, workspace writes, and execution remain disabled.

## Gated Action Release Board

`gated_action_release_board` is a live read-only command that derives the
remaining gated toolbar rows from `toolbar.v0.json` and groups them by release
lane:

- workspace mutation: save, save as, replace
- terminal/process: new terminal
- developer surface: devtools
- security shield: Gravity Shield, Void, and Basilisk start/stop actions
- mobile pairing: pairing QR generation

The board records the required approval, dry-run, rollback, and evidence lane
for each gated action. It does not create approvals, write audit records, save
files, replace text, create terminals, toggle devtools, start security actions,
generate pairing QR codes, read config, call MCP servers, connect sockets,
control the desktop, capture media, export data, write memory, write workspace
files, apply patches, or execute anything.

## Gated Adapter Release Queue

`gated_adapter_release_queue` is the product-facing release pipeline for the
remaining gated toolbar actions. It aggregates the workspace mutation,
terminal/process, security shield, and native shell/pairing workbenches into one
ranked queue, assigns an adapter kind to each gated command, and shows the exact
blocked stages that must be proven before a live adapter can exist.

`create_gated_adapter_release_packet_stub` records a sealed release packet in
XDG app state for all 12 gated adapter candidates, and
`list_gated_adapter_release_packets` returns the latest packet evidence. Packet
recording is intentionally evidence-only: it does not enable adapters, write
workspace files, allocate PTYs, spawn processes, control the desktop, call MCP
servers, connect sockets, read config, capture media, export data, write memory,
apply patches, or execute anything.

## Workspace Mutation Workbench

`workspace_mutation_workbench` is a live read-only command for the gated
workspace mutation lane. It turns `file.save`, `file.save_as`, and
`search.replace` into one operator workflow covering:

- toolbar command mapping
- operator preview
- write approval policy
- approval evidence
- writable-buffer draft
- dirty-transition preflight
- mutable-buffer transaction
- diff preview and rollback
- final confirmation

The workbench is intentionally not a save adapter. It does not read workspace
files, create approvals, write audit records, save files, replace text, apply
patches, open dialogs, spawn terminals/processes, call MCP servers, connect
sockets, control the desktop, capture media, export data, write memory, write
workspace files, or execute anything.

## Terminal Process Workbench

`terminal_process_workbench` is a live read-only command for the gated terminal
creation lane. It turns `terminal.new` into one operator workflow covering:

- toolbar command mapping
- process command plan
- sandbox policy match
- operator approval evidence
- PTY allocation policy
- stream initialization
- process lifecycle record
- control policy
- supervisor heartbeat
- output evidence
- exit summary and rollback

The workbench is intentionally not a PTY adapter. It does not allocate a
terminal, write terminal input, spawn processes, read streams, tail output,
control processes, kill or resize terminals, write files, apply patches, call
MCP servers, connect sockets, control the desktop, capture media, export data,
write memory, write workspace files, or execute anything.

## Security Shield Workbench

`security_shield_workbench` is a live read-only command for the restricted
Gravity Shield, Infinite Void, and Basilisk toolbar rows. It covers:

- toolbar command mapping
- host impact report
- operator/YubiKey confirmation
- privilege boundary
- rollback plan
- audit evidence
- post-action verification
- final release

The workbench is intentionally not a host-control adapter. It does not start or
stop shields, change containment, alter firewall or process state, prompt sudo
or YubiKey authentication, spawn processes, control terminals or the desktop,
read config, write files, apply patches, call MCP servers, connect sockets,
capture media, export data, write memory, write workspace files, or execute
anything.

## Native Shell Pairing Workbench

`native_shell_pairing_workbench` is a live read-only command for the final
gated native-surface rows:

- `developer.devtools`
- `mobile.qr`

It covers operator intent, release policy, visible session indicators,
token/scope policy, audit evidence, revocation/cleanup, and final release.
The workbench does not toggle devtools, expose debug shells, generate pairing
QR codes or tokens, connect sockets, pair devices, read config, spawn
processes, control terminals or the desktop, write files, apply patches, call
MCP servers, capture media, export data, write memory, write workspace files,
or execute anything.

## VERITAS Modules Dashboard

`veritas_modules_dashboard` is a read-only command that makes the Phase 5
VERITAS module migration lane visible in the native shell without turning on
module execution.

The dashboard classifies eight legacy/current surfaces:

- module registry
- module describe endpoint
- module run route
- document analyzer and report generator
- VERITAS Vault context
- security and Sentinel panels
- provenance and evolution proposals
- media and tool modules

Each row is tagged as a Rust-port candidate, sandboxed-sidecar candidate, or
archive-review candidate. The dashboard also records the known route mismatch:
the MCP bridge expected `/api/modules/<module_id>/execute` while the backend
surface exposed `/api/modules/<module_id>/run`.

This command creates no records and does not call the old Flask backend. Module
run, sidecar spawn, Python bridge, MCP execute, terminal/process control, file
writes, patch application, config reads, sockets, desktop control, capture,
export, memory writes, workspace writes, and execution all remain disabled.

## Toolbar Missing Command Closure

The toolbar registry now treats `security.refresh` and `mobile.qr` as explicit
native command targets instead of unknown/missing controls:

- `security.refresh` maps to `security_scan`; its live read-only intent surface
  is now handled by the Toolbar Action Readiness center while native scanning
  remains disabled.
- `mobile.qr` maps to `mobile_pairing_qr` and remains `gated` until
  Tailscale-first pairing policy, token expiry, revocation, and approval
  evidence exist.

This closes the "visible control with no known handler" class in the toolbar
registry. It does not enable security scanning, shield actions, pairing-token
generation, socket access, external tunnels, process spawning, terminal control,
file writes, patch application, capture, export, memory writes, workspace
writes, or execution.

## Toolbar Dry-Run Actions

Every toolbar registry row renders a dry-run button in the native scaffold UI.
The button calls `resolveCommandStub(command.id)`, which uses the Rust
`execute_command_stub` bridge in Tauri and the static browser-preview fallback
outside Tauri.

The dry-run action updates the Command Dry Run panel with the resolved command
id, status, target command, and blocked/gated reason. This makes toolbar
functions clickable and inspectable without enabling the underlying live
operation. Disabled and gated commands still do not run security scans, generate
pairing QR codes, create files, save files, spawn processes, open terminals,
call MCP servers, control the desktop, capture, export, write memory, mutate the
workspace, or execute anything.

## Bundled Docs And About Panels

`docs_open` and `about_open` are the first toolbar functions promoted to `live`
in the Rust/Tauri scaffold. They are intentionally narrow: both render bundled
in-app metadata and do not use an external opener, browser launch, network
request, filesystem read, config read, MCP call, socket, capture, export,
workspace write, memory write, process spawn, terminal control, desktop control,
or execution path.

`help.docs` opens the bundled docs panel, which lists the operator doctrine,
command contract, rebuild audit, toolbar registry, and feature contract as
static sections. `help.about` opens the About panel, which reports compiled
runtime identity, scaffold scope, integration lanes, and disabled safety gates.
The dry-run resolver returns `live` for these two commands while still returning
`blocked` for disabled/gated toolbar rows.

## Live Command Palette Surface

`command_palette_open` promotes the `command.palette` toolbar function to a
live in-app registry browser. The panel lists command groups and all toolbar
commands with their target command, safety tier, state, surface, and blocked or
live reason.

The palette is read-only in this slice. It does not bind global hotkeys, change
selection state, execute commands, mutate editor buffers, open or read files,
run searches, call MCP servers, connect sockets, spawn processes, control
terminals or the desktop, capture media, export data, write memory, write
workspace files, apply patches, or execute anything.

## Live Terminal Panel Toggle

`terminal_toggle` promotes the `terminal.toggle` toolbar function to a live
in-app panel operation. The command opens the existing terminal/process lane as
a read-only evidence surface and returns the same terminal/process dashboard
metadata behind a small visibility wrapper.

This does not create a PTY, write terminal input, read live streams, tail
output, send signals, spawn processes, resize or kill terminals, read config,
call MCP servers, connect sockets, control the desktop, capture media, export
data, write memory, write workspace files, apply patches, or execute anything.

## Live Find Panel

`editor_find` promotes the `search.find` toolbar function to a live in-app Find
panel. The panel lists the intended search scopes: current buffer, open tabs,
workspace preview, and command registry.

The Find panel is metadata-only in this slice. It does not bind query input,
move focus, read editor buffers, scan workspace files, search live content,
replace text, read config, call MCP servers, connect sockets, control the
desktop, capture media, export data, write memory, write workspace files, apply
patches, or execute anything.

## Live SSWP Status Panel

`sswp_status` promotes the `mcp.sswp_status` toolbar function to a live SSWP
status panel. The panel narrows the existing first-class MCP dashboard to the
SSWP lane and shows evidence counts, expected command ids, readiness status,
and disabled gates.

The SSWP panel is read-only in this slice. It reads existing MCP evidence
ledgers only and creates no new records. It does not probe live MCP servers,
call SSWP, discover live capabilities, read local MCP config, connect sockets,
capture media, export data, write memory, control the desktop, control
terminal/process lanes, write workspace files, apply patches, or execute
anything.

## Live Steno Search Panel

`steno_search` promotes the `steno.search` toolbar function to a live Steno
Search panel. The panel reuses the existing Steno/pet companion dashboard and
shows transcript-bundle readiness, transcript-protection readiness,
Omega Stenographer evidence, and disabled gate posture.

The Steno Search panel is readiness-only in this slice. It does not read
transcript contents, build a live transcript index, bind query input, call Omega
Stenographer, capture audio, export transcript data, read local MCP config,
connect sockets, write memory, control the desktop, control terminal/process
lanes, write workspace files, apply patches, or execute anything.

## Toolbar Action Readiness Center

`toolbar_action_readiness` makes every non-live gated toolbar row meaningfully
clickable without enabling its target action. The command reads the
toolbar registry, classifies the action family, and returns a read-only
checklist covering target mapping, verification text, approval needs, evidence
logging, and gate-release requirements.

The readiness center is intentionally non-executing. It does not create
approvals, write audit records, invoke target commands, open file pickers,
spawn terminals/processes, read workspace files, read local MCP config, call MCP
servers, connect sockets, capture media, export data, write memory, control the
desktop, write workspace files, apply patches, or execute anything.

## Safe Toolbar Intent Promotion

The formerly disabled safe toolbar rows now use the Toolbar Action Readiness center as
their live in-app intent surface. This includes new file/window/file-open/folder
open, exit, undo, redo, fullscreen, security refresh, and Codex review intent
buttons.

These rows are live only as readiness/intent panels. They do not create files,
open file or folder pickers, create windows, toggle fullscreen, exit the app,
mutate editor history, run security scans, start Codex, write files, read
workspace content, spawn processes, call MCP servers, connect sockets, write
memory, control the desktop, or execute anything.

## Workspace Files Dashboard

`workspace_files_dashboard` is a read-only command that turns the contracted
workspace file/search lane into a product-facing operator surface. It consumes
existing workspace records only:

- workspace inspections
- workspace previews
- scoped tree metadata
- bounded file-content previews
- editor tab state
- edit/save preflights
- write policies and approval evidence
- writable-buffer drafts
- dirty-state preflights
- mutable-buffer transaction evidence

The dashboard summarizes six operation areas: scoped workspace boundary, file
tree listing, file content read preview, search contract readiness, watcher
gate, and write/patch gate. List, read, and search-contract readiness are shown
from existing read-only evidence; live search, watchers, file writes, patch
application, terminal/process control, desktop control, live MCP calls, sockets,
config reads, capture, export, memory writes, workspace writes, and execution
remain disabled.

The command creates no records and does not read live file contents. It is the
first native replacement-app surface for workspace files: useful enough to
drive the UI, still sealed away from mutation.

## Core Feature Status Reconciliation

The feature migration contract now marks these previously contracted lanes as
`scaffolded` because each one has a verified product-facing read-only surface in
the Rust/Tauri scaffold:

- `terminal`: covered by `terminal_process_lane_dashboard`
- `codex-operating-loop`: covered by the Codex/Hermes run-view, detail,
  selection, diff, reconciliation, evidence attachment, intake, validation, and
  operator-confirmation surfaces
- `mcp-and-plugins`: covered by `first_class_mcp_dashboard` and the local MCP
  contract, health, discovery, gated-call, audit, consent, recovery, final
  approval, live-call dry-run, typed command, status-probe, and sealed config
  readiness records
- `sswp`: covered as a named first-class MCP subsystem in
  `first_class_mcp_dashboard`
- `omega-stenographer`: covered by `first_class_mcp_dashboard` and
  `steno_pet_companion_dashboard`
- `security-and-approvals`: covered by approval/evidence spine, sandbox policy,
  execution gate decisions, desktop approval policy, approval records,
  operator-confirmation dry-runs, final pre-action dry-runs, desktop action
  safety summary, and Linux desktop readiness release checklist

This is status reconciliation, not live-capability enablement. The scaffolded
state means the native app has read-only product surfaces, contracts, and tests;
it does not mean terminal writes, process spawning, live MCP calls, SSWP calls,
Steno capture, file writes, patch application, desktop control, config reads,
sockets, capture, export, memory writes, workspace writes, or execution are
enabled.

## Workspace Editor Keyboard Navigation Map

`workspace_editor_keyboard_navigation_map` is a read-only command that derives
keyboard traversal metadata from `workspace_editor_shell_focus_model`.

The traversal order is the focus-rank order:

1. tab buffer
2. file preview
3. workspace tree
4. mutation gates

The map records previous and next panel ids, previous and next target ids, and
reserved key hints for `Alt+Up`, `Alt+Down`, `Home`, and `End`. These keys are
documentation only in this slice: the frontend renders them but does not install
listeners, move focus, open a file, read config, call MCP servers, connect
sockets, spawn processes, control terminals or the desktop, capture media,
export data, write memory, write workspace files, apply patches, or execute
anything.

## Workspace Editor Command Palette Map

`workspace_editor_command_palette_map` is a read-only command that derives
panel-scoped command intent from `workspace_editor_keyboard_navigation_map`.

The palette lists disabled commands for:

- tab buffer focus summary
- bounded file preview review
- workspace tree summary review
- mutation gate explanation

Every command returns an id, source panel, source target id, shortcut hint,
disabled reason, and binding status. The command palette does not bind hotkeys,
install click actions, move focus, open a file, read config, call MCP servers,
connect sockets, spawn processes, control terminals or the desktop, capture
media, export data, write memory, write workspace files, apply patches, or
execute anything.

## Workspace Editor Command Search Map

`workspace_editor_command_search_map` is a read-only command that derives
grouped command discovery metadata from `workspace_editor_command_palette_map`.

The search map groups editor commands into:

- editor buffer commands
- preview commands
- workspace tree commands
- safety gate commands

Each group returns command ids, panel ids, static search tokens, disabled command
counts, and active-group state. The search index is metadata only: it does not
bind query inputs, install hotkeys, install click actions, move focus, open a
file, read config, call MCP servers, connect sockets, spawn processes, control
terminals or the desktop, capture media, export data, write memory, write
workspace files, apply patches, or execute anything.

## Agent Composer Draft Run

The right-rail agent composer is now an operator draft surface instead of a
dead placeholder. In Tauri it calls `create_task_run_stub` with `mode=joint_ci`,
the rebuild scaffold repo path, and the user's prompt, then refreshes the
OmegaTaskRun ledger, artifact preview, Codex/Hermes run view, and command
resolution panel.

This is durable evidence capture only. It creates a blocked task-run record and
does not start Codex, Hermes, shells, terminals, sidecars, MCP calls, file reads,
file writes, patches, desktop control, sockets, capture, export, memory writes,
workspace writes, or execution.

## Resizable Bottom Evidence Dock

The scaffold now includes a sticky bottom evidence dock using the Worker D
layout range of 100-400px. The dock has a keyboard and pointer accessible
resizer, persists height in local storage, mirrors the latest OmegaTaskRun
records, and shows the selected task-run artifact tail when available.

The dock is a read-only evidence mirror. It does not allocate PTYs, stream
terminal output, spawn processes, tail live files, call MCP servers, read config,
write files, apply patches, control the desktop, open sockets, capture media,
export data, write memory, write workspace files, or execute anything.

## Activity Rail Icon System

The primary activity rail now uses local line-icon controls with screen-reader
labels instead of temporary text-letter buttons. Each rail button keeps its
existing `data-panel` target and `aria-pressed` state, adds an explicit
`aria-label`, and uses a reusable `.rail-icon` pattern for the Command,
Workspace, Vault, Security, Plugins, and Codex/Hermes CI areas.

This is a navigation polish and accessibility pass only. It does not change the
rail routing model, execute commands, read files, write files, apply patches,
call MCP servers, spawn terminals or processes, control the desktop, capture
media, export data, write memory, write workspace files, or execute anything.

## Toolbar Registry Search

The toolbar registry panel now includes a local search input. It filters the
already-loaded toolbar command array by id, label, current action, target
command, state, capability tier, unavailable reason, and verification text, then
re-renders the same safe dry-run/open buttons for the matching rows.

The filter is client-side only. It does not perform workspace search, read
files, read config, call MCP servers, fetch network data, execute commands,
spawn terminals or processes, control the desktop, capture media, export data,
write memory, write workspace files, apply patches, or execute anything.

## Global Command Search Shortcut

`Ctrl+K` and `Cmd+K` now switch the activity rail to the Command area and focus
the toolbar registry search input. The shortcut is an ergonomic navigation path
only: it selects local command metadata that is already loaded in the page.

The shortcut does not dispatch commands, run toolbar actions, perform workspace
search, read files, read config, call MCP servers, fetch network data, spawn
terminals or processes, control the desktop, capture media, export data, write
memory, write workspace files, apply patches, or execute anything.

## Finish Pass 1 Runtime Probe Substrate

`runtime_probe_board` is the first live bounded process substrate in the
rebuild. It runs only hard-coded version probes for the local runtimes needed by
the replacement app: Python, Node, ffmpeg, ffprobe, Cargo, Codex, Hermes, and
Chrome. The UI exposes this as a manual Runtime Probes panel so startup does not
spawn anything implicitly.

The command captures short stdout/stderr evidence, exit codes, required-runtime
blockers, and the target sidecar/family each probe supports. It intentionally
keeps sidecar launch, PTY allocation, terminal input, arbitrary shell execution,
workspace reads/writes, config reads, MCP calls, sockets, desktop control,
capture, export, memory writes, patches, and task execution disabled.

## Finish Pass 2 Runtime Launch Packet Pipeline

`create_runtime_launch_packet_stub` reruns the same bounded runtime probes and
records XDG app-state launch-packet evidence only for probes that pass.
`list_runtime_launch_packets` reads the latest recorded packets back into the
Runtime Launch Packets panel.

Each packet records the runtime target, binary, args, sidecar id, command
family, probe output, approval requirement, record path, and next gate. Packets
are prerequisites for future launch approvals only: they do not start Codex,
Hermes, Python, browser, media, terminal, MCP, SSWP, Steno, desktop, or pet
sidecars, and they keep PTYs, terminal input, arbitrary shell execution,
workspace reads/writes, config reads, MCP calls, sockets, desktop control,
capture, export, memory writes, patches, and task execution disabled.

## Finish Pass 3 Joint Run Packet Bridge

`create_joint_runtime_run_packet_stub` records a persisted joint run envelope
that links the latest or requested OmegaTaskRun to Codex and Hermes runtime
launch packets. If either runtime packet is missing, the record is still written
as blocked evidence with explicit blockers. `list_joint_runtime_run_packets`
feeds those records back into the Joint Run Packet Ledger.

This is the bridge between the composer and real Codex/Hermes orchestration. It
does not start Codex or Hermes, allocate a PTY, run shell commands, call MCP
servers, read or write workspace files, apply patches, control the desktop,
open sockets, capture media, export data, write memory, or execute anything.

## Finish Pass 4 Runner Evidence Spine

`create_runner_evidence_spine_stub` records the full disabled Codex/Hermes
runner evidence chain in one product action. It creates or reuses an
OmegaTaskRun, records approval evidence, prepares a runner, writes a joint
Codex/Hermes plan, appends typed runtime events, creates a read-only workspace
lease and runner adapter, then records Codex and Hermes process plans, stream
files, lifecycle, cancel/retry policies, supervisor queued/running/exited
heartbeats, exit summaries, output-tail summaries, transcript bundles, export
policies, and protection policies. `list_runner_evidence_spines` feeds those
summary records back into the Runner Spine Ledger.

This replaces the slow ten-button prerequisite path with one auditable run
spine. It still does not start Codex or Hermes, allocate a PTY, attach a PID,
stream live output, read workspace files, write workspace files, apply patches,
call MCP servers, control the desktop, open sockets, export transcripts, write
memory, or execute anything.

## Finish Pass 5 Supervised Runtime Runner

`run_supervised_runtime_smoke` is the first bounded native process supervisor
inside the rebuild. It can spawn only the existing hard-coded runtime probe
targets, clamps the timeout to 500-10000ms, runs with stdin closed, captures
PID, exit code, timeout, duration, stdout, and stderr, and writes stdout/stderr
transcripts plus JSON/JSONL evidence under XDG app state.
`list_supervised_runtime_smokes` feeds those records back into the Runtime Smoke
Ledger.

This intentionally promotes process spawn only for fixed runtime-version smoke
commands. It still does not run arbitrary shell commands, start Codex or Hermes
tasks, allocate PTYs, launch sidecars, read workspace files, write workspace
files, apply patches, call MCP servers, control the desktop, open sockets,
export transcripts, write memory, or perform user-task execution.

## Finish Pass 6 Live Workspace Explorer

`workspace_explorer_snapshot` is the first live workspace read surface in the
rebuild. It scopes reads to the rebuild workspace, validates that requested
roots remain inside that scope, lists a bounded tree, skips `node_modules`,
`target`, `.git`, and `.sswp` files, and reads one UTF-8 text preview with a
byte cap. The UI exposes this as the Workspace Explorer panel with a live tree
and preview.

This intentionally promotes file listing and bounded text preview only. It does
not save files, apply patches, run search/replace, start watchers, spawn
processes, allocate PTYs, run Codex or Hermes tasks, call MCP servers, control
the desktop, open sockets, read config files, export data, write memory, or
execute user tasks.

## Finish Pass 7 Codex/Hermes Transcript Sessions

`run_agent_transcript_session` is the first supervised agent-runtime transcript
surface. It runs only four fixed allowlisted sessions: `codex --version`,
`codex --help`, `hermes --version`, and `hermes --help`. Each session runs with
stdin closed, a clamped timeout, PID/exit/timeout/duration capture, and
stdout/stderr transcript files plus JSON/JSONL evidence under XDG app state.
`list_agent_transcript_sessions` feeds those records into the Agent Session
Ledger.

This intentionally promotes transcript capture for Codex/Hermes runtime
discovery only. It does not accept arbitrary prompts, run `codex exec`, run
`codex apply`, start `hermes chat`, allocate PTYs, launch sidecars, read or
write workspace files, apply patches, call MCP servers, control the desktop,
open sockets, read config files, capture media, export data, write memory, or
execute user tasks.

## Finish Pass 8 Release Candidate Self-Audit

`replacement_app_ship_readiness` now includes a read-only release artifact
audit for the native binary at `target/release/gravity-omega-native`. The
finish-line view reports the artifact path, whether it exists, whether it is a
file, its byte size, modified timestamp, and whether that is enough to treat the
binary as a release candidate artifact.

This is packaging visibility only. It does not create package bundles, install
desktop entries, open the app, control the desktop, write files, apply patches,
spawn terminals or processes, open sockets, export artifacts, write memory, or
execute user tasks.

## Finish Pass 9 Linux Launcher Package Template

The rebuild scaffold now includes `packaging/gravity-omega-native.desktop` and
`packaging/install-local-desktop-entry.sh`. The desktop entry points at the
verified release binary and bundled icon. The install script is deliberately
separate from validation and build: it can copy the template into the local
applications directory later, but it is not run automatically.

This is launcher packaging only. It does not install the app, write a desktop
entry during validation, launch the GUI, create deb/rpm/AppImage bundles, touch
the current Electron app, modify `.sswp` files, or execute user tasks.

## Finish Pass 10 Live Launch Smoke

The release binary was launched under a bounded timeout and verified through
the Linux desktop window list. The smoke produced a visible
`Gravity Omega Native` window with `app_id="Gravity-omega-native"` and closed
when the timeout expired. No controls were clicked and the launcher was not
installed.

## Finish Pass 11 Operator-Unlocked Agent Prompt Runner

`run_unlocked_agent_prompt_session` and
`list_unlocked_agent_prompt_sessions` are now the first real arbitrary prompt
execution bridge in the native app. The runner accepts prompt text from the
operator composer and can invoke:

- `codex exec --json --sandbox workspace-write --ask-for-approval never --skip-git-repo-check --ephemeral -C <rebuild-root> <prompt>`
- `codex exec --json --sandbox read-only --ask-for-approval never --skip-git-repo-check --ephemeral -C <rebuild-root> <prompt>`
- `hermes chat -Q --max-turns 1 --source gravity-omega-native --query <prompt>`

Every run uses `Command::new` with fixed argv construction, stdin closed,
bounded timeout, PID/exit/timeout/duration capture, stdout/stderr transcript
files, JSON/JSONL evidence, task-run association when available, and an
in-app Unlocked Agent Ledger. The Codex Write button intentionally enables
workspace-write mode inside the rebuild workspace; Hermes is exposed as a real
quiet chat lane. The runner still does not use shell interpolation,
`danger-full-access`, `codex apply`, desktop control, live MCP calls, config
reads, transcript export, or memory writes.

## Finish Pass 12 App Control Unlock And Launch

Release artifact readiness now treats the existing release binary as
operator-launchable. When `target/release/gravity-omega-native` exists and is a
non-empty file, `replacement_app_ship_readiness` reports the desktop launcher
template ready, `launch_enabled=true`, `process_spawn_enabled=true`,
`desktop_control_enabled=true`, and `execution_enabled=true` for the release
artifact lane. Installation remains separate: the local desktop menu entry is
not installed automatically.

This is a deliberate launch-control unlock for the native rebuild binary. It
does not enable `danger-full-access`, `codex apply`, live MCP calls, config
reads, transcript export, memory writes, or mutation of the current Electron
app.
