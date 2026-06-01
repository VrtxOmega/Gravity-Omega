import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = path.resolve(import.meta.dirname, "..");
const repoRoot = path.resolve(root, "../..");

const requiredFiles = [
  "README.md",
  "package.json",
  "web/index.html",
  "web/src/main.js",
  "web/src/styles.css",
  "web/contracts/commands.v0.json",
  "web/contracts/features.v0.json",
  "web/contracts/sandbox.v0.json",
  "web/contracts/toolbar.v0.json",
  "packaging/gravity-omega-native.desktop",
  "packaging/launch-gravity-omega-native.sh",
  "packaging/install-local-desktop-entry.sh",
  "src-tauri/Cargo.toml",
  "src-tauri/build.rs",
  "src-tauri/tauri.conf.json",
  "src-tauri/icons/icon.png",
  "src-tauri/capabilities/default.json",
  "src-tauri/src/main.rs",
  "src-tauri/src/commands.rs",
];

function readJson(rel) {
  const full = path.join(root, rel);
  return JSON.parse(fs.readFileSync(full, "utf8"));
}

const missing = requiredFiles.filter((rel) => !fs.existsSync(path.join(root, rel)));
if (missing.length > 0) {
  console.error(`Missing workbench files:\n${missing.map((m) => `- ${m}`).join("\n")}`);
  process.exit(1);
}

const commands = readJson("web/contracts/commands.v0.json");
const features = readJson("web/contracts/features.v0.json");
const sandbox = readJson("web/contracts/sandbox.v0.json");
const toolbar = readJson("web/contracts/toolbar.v0.json");
const packageJson = readJson("package.json");
const tauriConfig = readJson("src-tauri/tauri.conf.json");
const frontendSource = fs.readFileSync(path.join(root, "web/src/main.js"), "utf8");
const styleSource = fs.readFileSync(path.join(root, "web/src/styles.css"), "utf8");
const htmlSource = fs.readFileSync(path.join(root, "web/index.html"), "utf8");
const rustCommandsSource = fs.readFileSync(path.join(root, "src-tauri/src/commands.rs"), "utf8");
const desktopEntrySource = fs.readFileSync(path.join(root, "packaging/gravity-omega-native.desktop"), "utf8");
const desktopLauncherScriptSource = fs.readFileSync(path.join(root, "packaging/launch-gravity-omega-native.sh"), "utf8");
const desktopInstallScriptSource = fs.readFileSync(path.join(root, "packaging/install-local-desktop-entry.sh"), "utf8");
const visibleProductShell = htmlSource.split('<div id="app-shell">')[0] ?? htmlSource;

if (/\bscaffold\b/i.test(visibleProductShell)) {
  throw new Error("Visible Gravity Omega product shell must not describe itself as a scaffold.");
}

if (/<details[^>]+id="omega-agent-run-center-details"[^>]*\sopen(?:\s|=|>)/.test(visibleProductShell)) {
  throw new Error("Codex/Hermes run center must be collapsed by default so the chat rail owns the vertical space.");
}

const visibleInitialExplorer = visibleProductShell.split('<section class="omega-sidebar-card"')[0] ?? visibleProductShell;
for (const sourceTreeNeedle of ["web/src/main.js", "src-tauri/src/commands.rs", "rebuild/gravity-omega-tauri"]) {
  if (visibleInitialExplorer.includes(sourceTreeNeedle)) {
    throw new Error(`Initial explorer must not expose rebuild source-tree internals: ${sourceTreeNeedle}.`);
  }
}

for (const deadVisibleNeedle of [
  "omega-release-gate-strip",
  "Gravity Omega is open.",
  "VERITAS Command Center",
  "Editor + Monaco",
  "Omega chat + Codex/Hermes",
  "Terminal + transcripts",
  "MCP / SSWP / Steno",
  "Evidence spine",
]) {
  if (visibleProductShell.includes(deadVisibleNeedle)) {
    throw new Error(`Visible product shell must not expose non-clickable release strip content: ${deadVisibleNeedle}.`);
  }
}

for (const runtimeEvidenceSpineNeedle of [
  "omega-runtime-evidence-spine",
  "omega-runtime-evidence-spine-status",
  "omega-runtime-evidence-spine-gates",
  "omega-runtime-evidence-spine-list",
  "Runtime Evidence Spine",
]) {
  if (!visibleProductShell.includes(runtimeEvidenceSpineNeedle)) {
    throw new Error(`Visible product shell missing runtime evidence spine element: ${runtimeEvidenceSpineNeedle}.`);
  }
}

for (const runtimeEvidenceStyleNeedle of [
  ".omega-runtime-evidence-spine",
  ".omega-runtime-evidence-spine-list",
  ".omega-runtime-evidence-card",
]) {
  if (!styleSource.includes(runtimeEvidenceStyleNeedle)) {
    throw new Error(`Runtime evidence spine missing style hook: ${runtimeEvidenceStyleNeedle}.`);
  }
}

if (frontendSource.includes("/home/rage/apps/gravity-omega-v2")) {
  throw new Error("Visible workbench runtime must target the Rust/Tauri rebuild, not the old Electron app.");
}

if (!Array.isArray(commands.groups) || commands.groups.length < 8) {
  throw new Error("Command contract must contain the major migrated IPC groups.");
}

for (const desktopNeedle of [
  "Type=Application",
  "Name=Gravity Omega",
  "Exec=/usr/bin/env bash /home/rage/apps/gravity-omega-rust-rebuild/rebuild/gravity-omega-tauri/packaging/launch-gravity-omega-native.sh",
  "Icon=/home/rage/apps/gravity-omega-rust-rebuild/rebuild/gravity-omega-tauri/src-tauri/icons/icon.png",
  "Terminal=false",
  "Categories=Development;",
  "StartupWMClass=gravity-omega-native",
]) {
  if (!desktopEntrySource.includes(desktopNeedle)) {
    throw new Error(`Desktop launcher template missing ${desktopNeedle}.`);
  }
}

for (const launcherNeedle of [
  "set -euo pipefail",
  "gravity-omega-native",
  "launcher.log",
  "cd \"$app_root\"",
  "set +e",
  "/usr/bin/setsid -f \"$binary\" >>\"$log_file\" 2>&1",
  "set -e",
  "launch requested",
  "launch spawn status",
]) {
  if (!desktopLauncherScriptSource.includes(launcherNeedle)) {
    throw new Error(`Desktop launcher script missing ${launcherNeedle}.`);
  }
}

for (const scriptNeedle of [
  "set -euo pipefail",
  "gravity-omega-native.desktop",
  "launch-gravity-omega-native.sh",
  "chmod 0755 \"$launcher_script\"",
  "update-desktop-database",
  "Release binary is missing or not executable",
]) {
  if (!desktopInstallScriptSource.includes(scriptNeedle)) {
    throw new Error(`Desktop launcher installer missing ${scriptNeedle}.`);
  }
}

for (const unlockedNeedle of [
  "run_unlocked_agent_prompt_session",
  "run_unlocked_agent_prompt_session_stream",
  "unlocked-agent-prompt-stream",
  "UnlockedAgentPromptSessionRecord",
  "prompt_stdin: Option<String>",
  "unlocked_agent_prompt_stdin_mode",
  "write_unlocked_agent_prompt_stdin",
  "hermes_log_write_preflight",
  "Hermes/Kimi log path is not writable for this Gravity Omega process",
  "<prompt:stdin>",
  ".stdin(unlocked_agent_prompt_stdin_mode",
  "codex-workspace-write",
  "hermes-chat",
  "unlocked-agent-prompt-sessions",
  "record_hermes_kimi_assist_brief",
  "HermesKimiAssistBriefRecord",
  "hermes-kimi-assist-briefs",
  "<compact-assist-query>",
  "spawn_hermes_kimi_pipe_reader",
  "run_hermes_kimi_assist_process_with_binary",
  "query_transport",
  "argv_char_count",
  "stdout_pipe_reader_enabled",
  "stderr_pipe_reader_enabled",
  "timeout_kill_sent",
  "wait_after_kill_ms",
  "partial_output_captured",
  "Do not edit files.",
  "Do not run shell commands or call tools.",
  "bounded_execution_performed",
  "launch_enabled: artifact_ready",
  "desktop_control_enabled: artifact_ready",
  "900_000",
]) {
  if (!rustCommandsSource.includes(unlockedNeedle) && !frontendSource.includes(unlockedNeedle)) {
    throw new Error(`Unlocked agent prompt lane missing ${unlockedNeedle}.`);
  }
}

if (/workspace_arg\.clone\(\),\s*prompt\.to_string\(\),/.test(rustCommandsSource)) {
  throw new Error("Codex unlocked prompt targets must not pass full prompt text as argv after -C; use stdin transport.");
}

const hermesAssistProcessStart = rustCommandsSource.indexOf("fn run_hermes_kimi_assist_process_with_binary");
const hermesAssistProcessEnd = rustCommandsSource.indexOf("#[tauri::command]\npub fn record_hermes_kimi_assist_brief", hermesAssistProcessStart);
if (hermesAssistProcessStart < 0 || hermesAssistProcessEnd < hermesAssistProcessStart) {
  throw new Error("Hermes/Kimi assist process runner body is missing.");
}
const hermesAssistProcessBody = rustCommandsSource.slice(hermesAssistProcessStart, hermesAssistProcessEnd);
if (hermesAssistProcessBody.includes("wait_with_output")) {
  throw new Error("Hermes/Kimi assist runner must drain stdout/stderr pipes while the process runs, not wait_with_output afterward.");
}

const productTerminalProcessStart = rustCommandsSource.indexOf("fn run_product_terminal_command_process");
const productTerminalProcessEnd = rustCommandsSource.indexOf("#[tauri::command]\npub fn run_product_terminal_command", productTerminalProcessStart);
if (productTerminalProcessStart < 0 || productTerminalProcessEnd < productTerminalProcessStart) {
  throw new Error("Product terminal command process runner body is missing.");
}
const productTerminalProcessBody = rustCommandsSource.slice(productTerminalProcessStart, productTerminalProcessEnd);
if (productTerminalProcessBody.includes("wait_with_output")) {
  throw new Error("Product terminal command runner must drain stdout/stderr pipes while the process runs, not wait_with_output afterward.");
}

const productTerminalStreamStart = rustCommandsSource.indexOf("pub fn run_product_terminal_command_stream");
const productTerminalStreamEnd = rustCommandsSource.indexOf("fn write_product_terminal_command_result", productTerminalStreamStart);
if (productTerminalStreamStart < 0 || productTerminalStreamEnd < productTerminalStreamStart) {
  throw new Error("Product terminal stream runner body is missing.");
}
const productTerminalStreamBody = rustCommandsSource.slice(productTerminalStreamStart, productTerminalStreamEnd);
for (const terminalStreamNeedle of [
  "stdout_pipe_reader_enabled",
  "stderr_pipe_reader_enabled",
  "timeout_kill_sent",
  "wait_after_kill_ms",
  "partial_output_captured",
  "timeout_ms",
]) {
  if (!productTerminalStreamBody.includes(terminalStreamNeedle)) {
    throw new Error(`Product terminal stream runner must persist lifecycle evidence field ${terminalStreamNeedle}.`);
  }
}

const sswpRegistryCommandStart = rustCommandsSource.indexOf("fn run_sswp_registry_command");
const sswpRegistryCommandEnd = rustCommandsSource.indexOf("fn parse_sswp_registry_nodes", sswpRegistryCommandStart);
if (sswpRegistryCommandStart < 0 || sswpRegistryCommandEnd < sswpRegistryCommandStart) {
  throw new Error("SSWP registry command runner body is missing.");
}
const sswpRegistryCommandBody = rustCommandsSource.slice(sswpRegistryCommandStart, sswpRegistryCommandEnd);
if (sswpRegistryCommandBody.includes("wait_with_output")) {
  throw new Error("SSWP registry runner must drain stdout/stderr pipes while the process runs, not wait_with_output afterward.");
}
for (const sswpProbeNeedle of [
  "spawn_sswp_registry_pipe_reader",
  "stdout_pipe_reader_enabled",
  "stderr_pipe_reader_enabled",
  "timeout_kill_sent",
  "wait_after_kill_ms",
  "partial_output_captured",
]) {
  if (!sswpRegistryCommandBody.includes(sswpProbeNeedle)) {
    throw new Error(`SSWP registry runner missing pipe-drain evidence field ${sswpProbeNeedle}.`);
  }
}

const agentTranscriptRunnerStart = rustCommandsSource.indexOf("fn run_agent_transcript_target_with_binary");
const agentTranscriptRunnerEnd = rustCommandsSource.indexOf("#[allow(clippy::too_many_arguments)]", agentTranscriptRunnerStart);
if (agentTranscriptRunnerStart < 0 || agentTranscriptRunnerEnd < agentTranscriptRunnerStart) {
  throw new Error("Agent transcript runner body is missing.");
}
const agentTranscriptRunnerBody = rustCommandsSource.slice(agentTranscriptRunnerStart, agentTranscriptRunnerEnd);
if (agentTranscriptRunnerBody.includes("wait_with_output")) {
  throw new Error("Agent transcript runner must drain stdout/stderr pipes while the process runs, not wait_with_output afterward.");
}
for (const agentTranscriptNeedle of [
  "spawn_agent_transcript_pipe_reader",
  "stdout_pipe_reader_enabled",
  "stderr_pipe_reader_enabled",
  "timeout_kill_sent",
  "wait_after_kill_ms",
  "partial_output_captured",
]) {
  if (!agentTranscriptRunnerBody.includes(agentTranscriptNeedle)) {
    throw new Error(`Agent transcript runner missing pipe-drain evidence field ${agentTranscriptNeedle}.`);
  }
}

const runtimeSidecarSnapshotStart = rustCommandsSource.indexOf("pub fn record_runtime_sidecar_process_snapshot");
const runtimeSidecarSnapshotEnd = rustCommandsSource.indexOf("#[tauri::command]\npub fn list_runtime_sidecar_process_snapshots", runtimeSidecarSnapshotStart);
if (runtimeSidecarSnapshotStart < 0 || runtimeSidecarSnapshotEnd < runtimeSidecarSnapshotStart) {
  throw new Error("Runtime sidecar process snapshot runner body is missing.");
}
const runtimeSidecarSnapshotBody = rustCommandsSource.slice(runtimeSidecarSnapshotStart, runtimeSidecarSnapshotEnd);
if (runtimeSidecarSnapshotBody.includes(".output()")) {
  throw new Error("Runtime sidecar process snapshot must drain stdout/stderr pipes with a timeout, not Command::output.");
}
for (const runtimeSnapshotNeedle of [
  "run_runtime_sidecar_process_list_command",
  "spawn_runtime_sidecar_process_pipe_reader",
  "process_list_timeout_ms",
  "process_list_timed_out",
  "stdout_pipe_reader_enabled",
  "stderr_pipe_reader_enabled",
  "process_list_timeout_kill_sent",
  "process_list_wait_after_kill_ms",
  "process_list_partial_output_captured",
]) {
  if (!rustCommandsSource.includes(runtimeSnapshotNeedle)) {
    throw new Error(`Runtime sidecar process snapshot missing bounded pipe-drain evidence field ${runtimeSnapshotNeedle}.`);
  }
}

for (const unlockedUiNeedle of [
  "run-unlocked-codex-agent-btn",
  "run-unlocked-hermes-agent-btn",
  "unlocked-agent-prompt-ledger",
]) {
  if (!htmlSource.includes(unlockedUiNeedle) || !frontendSource.includes(unlockedUiNeedle)) {
    throw new Error(`Unlocked agent prompt UI missing ${unlockedUiNeedle}.`);
  }
}

for (const productShellNeedle of [
  "omega-product-shell",
  "data-tauri-drag-region",
  "data-window-command=\"minimize\"",
  "Gravity Omega Workbench",
  "Omega Scratch.md",
  "Omega Workspace",
  "Open or refresh a workspace",
  "omega-activity-bar",
  "data-activity-label=\"Explorer\"",
  "data-activity-label=\"Tools\"",
  "data-product-command=\"menu-file\"",
  "data-product-command=\"menu-terminal\"",
  "data-panel-action=\"desktop\"",
  "data-panel-action=\"omega-computer\"",
  "data-panel-action=\"shield\"",
  "data-action-glyph=\"&Omega;\"",
  "data-panel-action=\"evidence\"",
  "data-panel-action=\"sswp\"",
  "data-panel-action=\"providers\"",
  "omega-sidebar",
  "omega-monaco-container",
  "omega-home-surface",
  "omega-home-mark",
  "omega-home-title",
  "omega-computer-main-surface",
  "rel=\"icon\" href=\"data:,\"",
  "omega-editor-input",
  "omega-product-save-btn",
  "id=\"omega-product-save-btn\" type=\"button\" title=\"Save draft\" aria-label=\"Save draft\" data-product-command=\"save\"",
  "omega-product-search-btn",
  "omega-product-split-btn",
  "omega-command-palette-product",
  "omega-editor-search-input",
  "omega-editor-replace-input",
  "omega-editor-search-results",
  "omega-workspace-search-run",
  "omega-workspace-search-status",
  "omega-mcp-dashboard-product",
  "omega-mcp-dashboard-status",
  "omega-mcp-dashboard-list",
  "omega-sswp-dashboard-product",
  "omega-sswp-dashboard-status",
  "omega-sswp-dashboard-list",
  "omega-steno-pet-dashboard-product",
  "omega-steno-pet-dashboard-status",
  "omega-steno-pet-dashboard-list",
  "data-search-mode=\"workspace\"",
  "omega-terminal-command-input",
  "omega-terminal-session-bar",
  "omega-terminal-session-status",
  "omega-terminal-session-id",
  "omega-terminal-session-cwd",
  "omega-terminal-session-exit",
  "omega-terminal-session-duration",
  "omega-terminal-session-record",
  "omega-terminal-clear",
  "omega-terminal-show-evidence",
  "omega-xterm-surface",
  "omega-output-view",
  "omega-problems-view",
  "omega-evidence-view",
  "omega-browser-status-line",
  "omega-media-status-line",
  "omega-ocr-status-line",
  "omega-modules-status-line",
  "omega-sidecar-packet-status",
  "omega-sidecar-packet-list",
  "data-sidecar-packet-target=\"all\"",
  "omega-sidecar-lifecycle-status",
  "omega-sidecar-lifecycle-list",
  "omega-sidecar-lifecycle-probe",
  "omega-provider-status-line",
  "omega-ship-status-line",
  "omega-toolbar-parity-status",
  "omega-toolbar-parity-list",
  "omega-toolbar-proof-run",
  "omega-toolbar-proof-status",
  "omega-toolbar-proof-list",
  "omega-product-agent-run-summary",
  "omega-product-agent-run-list",
  "omega-agent-run-center-details",
  "omega-product-agent-run-compact",
  "omega-agent-run-center-summary",
  "omega-product-agent-run-refresh",
  "omega-product-joint-packet",
  "omega-chat-resizer-product",
  "omega-bottom-resizer-product",
  "omega-layout-reset-product",
  "omega-product-new-btn",
  "omega-product-open-btn",
  "omega-product-save-as-btn",
  "omega-product-undo-btn",
  "omega-product-redo-btn",
  "omega-product-artifact-preview-btn",
  "omega-product-sovereign-docs-btn",
  "omega-product-computer-btn",
  "omega-computer-status-line",
  "omega-artifact-preview-fit-product",
  "omega-artifact-preview-tall-product",
  "omega-artifact-preview-expand-product",
  "omega-artifact-preview-overlay",
  "omega-artifact-preview-overlay-frame",
  "omega-artifact-preview-overlay-text",
  "omega-product-terminal-btn",
  "data-bottom-view=\"artifact\"",
  "omega-artifact-preview-frame-product",
  "omega-artifact-preview-text-product",
  "omega-terminal-quickbar",
  "omega-command-palette-list",
  "omega-context-toggle",
  "omega-evidence-history-status",
  "omega-evidence-history-list",
  "omega-evidence-history-refresh",
  "data-product-command=\"replace-current\"",
  "data-product-command=\"replace-all\"",
  "data-product-command=\"workspace-search\"",
  "data-product-command=\"artifact-preview\"",
  "data-product-command=\"artifact-preview-expand\"",
  "data-product-command=\"sovereign-docs-preview\"",
  "data-product-command=\"omega-computer\"",
  "data-product-command=\"layout-reset\"",
  "data-product-command=\"workbench-smoke\"",
  "data-product-command=\"ui-smoke\"",
  "data-product-panel=\"omega\"",
  "data-product-panel=\"media\"",
  "omega-chat-input-parity",
  "omega-parity-codex-write",
  "omega-parity-hermes",
  "omega-parity-compare",
  "omega-parity-recover",
  "omega-agent-mode-row",
  "data-agent-run-mode=\"codex-lead\"",
  "data-agent-run-mode=\"evidence-compare\"",
  "Codex Lead + Hermes/Kimi",
  "Describe the work. Ctrl+Enter runs Codex Lead + Hermes/Kimi.",
  "Run Main",
  "Codex Only",
  "Hermes Only",
  "Run Dual",
  "Recover",
  "Workbench ready. Ask Omega, Codex, or Hermes from the right rail.",
  "omega-bottom-panel",
]) {
  if (!htmlSource.includes(productShellNeedle)) {
    throw new Error(`Visible Gravity Omega workbench shell missing ${productShellNeedle}.`);
  }
}

for (const productBridgeNeedle of [
  "initOmegaProductShell",
  "product_workspace_file_open",
  "product_workspace_file_save",
  "product_workspace_search",
  "run_product_terminal_command",
  "run_product_terminal_command_stream",
  "record_product_terminal_transcript_replay",
  "list_product_terminal_transcript_replays",
  "record_sovereign_docs_preview",
  "list_sovereign_docs_previews",
  "product-terminal-stream",
  "tauriListen",
  "bindProductTerminalStreamEvents",
  "loadMonacoEditor",
  "monacoVsUrl",
  "monacoWorkerUrl",
  "getWorkerUrl",
  "./vendor/monaco/vs/base/worker/workerMain.js",
  "runTerminalCommand",
  "runProductCommand",
  "runToolbarParityAction",
  "replaceEditorText",
  "createUntitledFile",
  "startProductResize",
  "resizeProductLayoutFromKeyboard",
  "setProductLayoutSize",
  "restoreProductLayoutSettings",
  "resetProductLayoutSettings",
  "productCommandRegistry",
  "renderCommandPalette",
  "runSelectedCommandPaletteItem",
  "previewActiveArtifact",
  "renderArtifactPreviewTab",
  "buildSovereignDocsPreviewHtml",
  "renderSovereignDocsMarkdownBlocks",
  "renderSovereignDocsPreview",
  "recordSovereignDocsPreview",
  "loadSovereignDocsPreviews",
  "scheduleSovereignDocsPreviewUpdate",
  "toggleSovereignDocsPreview",
  "frontendOmegaComputerSessionRecord",
  "recordOmegaComputerSession",
  "loadOmegaComputerSessions",
  "omegaComputerWorkersFromRecord",
  "renderOmegaComputerSwarmTerminal",
  "showOmegaComputerMainSurface",
  "omegaPanelMainSurface",
  "setPanelMainSurfaceVisible",
  "showPanelActionMainSurface",
  "panelSurfaceGateKeys",
  "panelSurfaceMetric",
  "panelSurfaceCard",
  "panelSurfaceRecordCards",
  "panelSurfaceSectionCards",
  "panelActionRunActions",
  "copyOmegaComputerPromptToComposer",
  "runOmegaComputerComposerAction",
  "formatOmegaComputerWorkPacket",
  "openOmegaComputerWorkPacket",
  "Omega Computer Session Packet",
  "Evidence Required",
  "Blocked Actions",
  "omega-computer-stage-rail",
  "omega-computer-detail-grid",
  "renderOmegaComputerSession",
  "openOmegaComputerSurface",
  "Omega Computer",
  "Sovereign Docs Live Preview",
  "VERITAS Sovereign Docs",
  "Veritas-branded Markdown to PDF live preview",
  "PDF export disabled until renderer sidecar",
  "agent-generated",
  "artifactPreviewFrameProduct",
  "artifactPreviewTextProduct",
  "artifact rendered in sandboxed preview",
  "Preview Active Artifact",
  "restoreEditorSession",
  "persistEditorSession",
  "gravity-omega.product-layout.v5",
  "gravity-omega.editor-session.v5",
  "gravity-omega.editor-session-recovery.v1",
  "isGeneratedStartupEditorSession",
  "Previous generated agent/editor session parked for recovery.",
  "defaultScratchPath",
  "isOmegaHomeContent",
  "syncOmegaHomeSurface",
  "restorePromptContextState",
  "buildAgentPrompt",
  "agentWorkArtifactPath",
  "Omega Agent Work.md",
  "agentWorkDoctrinePaths",
  "/home/rage/AGENTS.md",
  "/home/rage/tasks/todo.md",
  "/home/rage/tasks/lessons.md",
  "Output Separation Contract",
  "startAgentWorkArtifact",
  "appendAgentWorkArtifact",
  "queueAgentWorkArtifactLine",
  "collectAgentWorkFileCandidates",
  "normalizeAgentWorkFileCandidate",
  "hydrateAgentWorkFileCandidates",
  "Generated/Changed File Tabs",
  "fileCandidates: new Set()",
  "flushAgentWorkArtifact",
  "extractCodexWorkArtifactLine",
  "agentStreamIssueSummary",
  "waitForProductPaint",
  "agentRunStartingText",
  "agentRunAcceptedText",
  "agentRunFinalSummaryText",
  "codexLeadAssistTimeoutMs",
  "updateCodexLeadPreparationStatus",
  "is starting now.",
  "Run accepted. Watching stream for readable output.",
  "Agent work artifact opens in Monaco",
  "timeout_ms: 900000",
  "runAgentComparison",
  "runPrimaryAgentWork",
  "recoverAgentRunUi",
  "ignoredAgentStreamIds",
  "Run Recovery Requested",
  "backend_process_cancellation=not_exposed",
  "Backend process cancellation is not exposed",
  "Late events from this recovered session will be ignored by the UI.",
  "createComparisonSummary",
  "compareExistingAgentEvidence",
  "isAgentRunStatusFollowup",
  "runLatestAgentRunStatusRecap",
  "Latest Omega Computer recap",
  "mode=local-evidence-recap",
  "Compare reads existing Codex/Hermes evidence only; it does not launch live agents.",
  "codex-hermes-compare-preview",
  "compare does not launch live agents",
  "restoreTerminalHistory",
  "rememberTerminalCommand",
  "updateTerminalSessionHud",
  "terminalStateFromStatus",
  "clearProductTerminal",
  "showTerminalEvidence",
  "recordTerminalTranscriptReplay",
  "captureTerminalTranscriptReplay",
  "loadTerminalTranscriptReplays",
  "formatTerminalReplay",
  "terminal-stream-completion",
  "terminal-sync-completion",
  "replayRecordPath",
  "[terminal_replay]",
  "lastTerminalSession",
  "terminal-session-hud",
  "refreshProductExplorer",
  "renderWorkspaceExplorerSnapshot",
  "loadWorkspaceExplorerSnapshot",
  "loadProductWorkspaceSearch",
  "runWorkspaceSearch",
  "renderWorkspaceSearchResults",
  "setSearchMode",
  "renderProductFirstClassMcpDashboard",
  "renderProductSswpDashboard",
  "recordSswpRegistrySnapshot",
  "registry_node_count",
  "risky_node_count",
  "latest_registry_snapshot_path",
  "renderProductStenoPetDashboard",
  "refreshProductAgentRunCenter",
  "renderProductAgentRunCenter",
  "productAgentRunCompact",
  "data-has-runs",
  "recordProductJointRuntimePacket",
  "runUnlockedAgentPromptSessionStream",
  "bindUnlockedAgentPromptStreamEvents",
  "unlocked-agent-prompt-stream",
  "bindNativeWindowControls",
  "native_window_command",
  "getCurrentWindow",
  "extractCodexAssistantText",
  "isIgnorableAgentStderr",
  "refreshProductEvidenceHistory",
  "renderProductEvidenceHistory",
  "product_evidence_history",
  "refreshVisibleSidecarLaunchPackets",
  "renderVisibleSidecarLaunchPackets",
  "refreshVisibleSidecarLifecycle",
  "renderVisibleSidecarLifecycle",
  "recordVisibleSidecarLaunchPacket",
  "createRuntimeLaunchPacket",
  "loadRuntimeLaunchPackets",
  "loadUnlockedAgentPromptSessions",
  "loadJointRuntimeRunPackets",
  "switchProductPanel",
  "renderEditorSearch",
  "refreshFirstClassStatusPanels",
  "provider_settings_dashboard",
  "loadSidecarReadinessBoard",
  "loadVeritasModulesDashboard",
  "loadReplacementAppShipReadiness",
  "run_product_workbench_smoke",
  "list_product_workbench_smokes",
  "runProductWorkbenchSmoke",
  "runProductUiSmoke",
  "product_ui_smoke_",
  "event.key === \"F9\"",
  "event.key === \"F10\"",
  "Validator shortcut failed",
  "UI smoke shortcut failed",
  "focusProductTerminalCommandInput",
  "clampNumber(value, cssPixelValue(\"--chat-min-width\", 240), cssPixelValue(\"--chat-max-width\", 480))",
  "viewportBottomPanelMaxHeight",
  "productBottomPanelMaxHeight()",
  "activeArtifactPreview",
  "openArtifactPreviewOverlay",
  "closeArtifactPreviewOverlay",
  "layout reset to 320px chat rail and 180px bottom dock",
  "productSidebarStorageKey",
  "omega-sidebar-collapsed",
  "setProductSidebarCollapsed",
  "restoreProductSidebarCollapsed",
  "setActivityRailFeedback",
  "panelActionButtons",
  "setPanelActionFeedback",
  "openProductWorkSurface",
  "openPanelActionWorkSurface",
  "runPanelAction",
  "panel card started",
  "opened as a central surface",
  "data-action-selected",
  "Omega Computer control surface ready",
  "Desktop Control opened as a central surface",
  "record_desktop_environment_snapshot",
  "record_desktop_read_only_capability_snapshot",
  "record_evidence_durability_manifest",
  "evidence-durability",
  "latest_desktop_environment_ydotool_socket_is_socket",
  "latest_desktop_read_only_capability_window_inventory_ready",
  "manifest_hash",
  "Security Shield opened as a central surface",
  "Ship Readiness opened as a central surface",
  "MCP lanes=${mcp.lane_count",
  "Approval Evidence Spine",
  "SSWP Registry",
  "probePipes=",
  "registry_list_pipe_reader_enabled",
  "registry_risky_pipe_reader_enabled",
  "Sidecar Launch + Probe",
  "providers.providers",
  "ship.items",
  "loadSecurityShieldWorkbench(\"security.gravity_shield\")",
  "loadLinuxDesktopControlReadinessDashboard()",
  "openOmegaComputerSurface(\"sidebar-card\")",
  "runActivityPanelAction",
  "handleActivityPanelClick",
  "activity rail opened",
  "dataset.panelState",
  "dataset.activityState",
  "toggleSidebar",
  "aria-expanded",
  "explorer starts in neutral Omega Workspace",
  "refreshVisibleToolbarParity",
  "runVisibleToolbarProof",
  "toolbarParityActionIds",
  "resolveCommandStub",
  "loadToolbarRegistry",
  "recordUnlockedAgentPromptSession(runtime)",
  "codex-workspace-write",
  "hermes-chat",
  "omega-runtime-evidence-spine-status",
  "renderRuntimeEvidenceSpine",
  "refreshRuntimeEvidenceSpine",
  "loadProductEvidenceHistory",
  "loadTerminalTranscriptReplays",
  "loadAgentTranscriptSessions",
  "loadUnlockedAgentPromptSessions",
  "bounded_process_capture",
  "agentRunModeStorageKey",
  "restoreAgentRunMode",
  "activeAgentRun",
  "beginAgentRunGate",
  "updateAgentRunGate",
  "clearAgentRunGate",
  "describeActiveAgentRun",
  "data-agent-run-gate",
  "runAgentEvidenceComparison",
  "runCodexLeadDualExecution",
  "productCommandFeedback",
  "syncProductCommandActiveStates",
  "completeProductCommandFeedback",
  "codexLeadStreamingPrompt",
  "codexLeadStagePrompt",
  "runBlockingAgentStage",
  "hermesKimiSkillInventory",
  "groupHermesKimiSkills",
  "formatHermesKimiSkillInventory",
  "formatLongPromptPreview",
  "appendPromptMessage",
  "formatPromptForAgentWorkHeader",
  "hermesKimiCapabilityBrief",
  "formatHermesKimiRuntimeInventory",
  "recordHermesKimiCapabilityInventory",
  "recordHermesKimiAssistBrief",
  "formatHermesKimiAssistBrief",
  "describeCodexHermesRunViewEvidence",
  "agent-run-postmortem",
  "agent_session_failure_count",
  "latest_agent_postmortem_status",
  "assist_postmortems=",
  "assist_timeouts=",
  "postmortems=",
  "postmortem-failures",
  "failure_postmortem_count",
  "postmortem-timeouts",
  "timeout_postmortem_count",
  "unlocked-agent-prompt-sessions",
  "transcript_evidence_ready",
  "stdout_transcript_found",
  "stderr_transcript_line_count",
  "stdout_preview_source",
  "transcripts ready=",
  "evidence_summaries",
  "codex_orchestration_count",
  "hermes_inventory_count",
  "hermes_assist_count",
  "hermes_assist_failure_count",
  "hermes_assist_timeout_count",
  "latest_hermes_assist_status",
  "latest_hermes_assist_postmortem_status",
  "record_process_spawn_enabled",
  'source_id: "hermes-kimi-assist"',
  "stderr_preview_source",
  "Hermes/Kimi Live Capability Inventory",
  "Hermes/Kimi Assist Brief",
  "runtimeInventory",
  "hermesAssist",
  "includeFullInventory = false",
  "compact category summary",
  "Run this as one responsive Codex-owned work session",
  "mode=responsive-codex-lead-stream",
  "autonomous-ai-agents/hermes-agent",
  "github/github-code-review",
  "frontend/frontend-visual-polish",
  "software-development/test-driven-development",
  "veritas/veritas-omega-code",
  "Kimi 2.6",
  "Kimi/Moonshot",
  "omega-stenographer",
  "sswp",
  "recent_pet_runtime_signals",
  "Pet signal:",
  "recent_pet_attention_items",
  "Pet attention:",
  "attention=",
  "recent_terminal_sessions",
  "recent_terminal_replays",
  "recent_blocked_terminal_commands",
  "blocked_terminal_command_count",
  "recent_process_control_policies",
  "recent_process_exit_summaries",
  "stdout_pipe_reader_enabled",
  "stderr_pipe_reader_enabled",
  "timeout_kill_sent",
  "wait_after_kill_ms",
  "partial_output_captured",
  "pipeReaders=",
  "activeTerminalStreamRun",
  "recordTerminalStreamLifecycleEvent",
  "tickTerminalStreamWatchdog",
  "data-terminal-stream-session",
  "terminal stream stale warning",
  "Terminal session:",
  "Terminal replay:",
  "Blocked terminal command:",
  "Process control:",
  "Process exit:",
]) {
  if (!frontendSource.includes(productBridgeNeedle)) {
    throw new Error(`Visible workbench prompt bridge missing ${productBridgeNeedle}.`);
  }
}

const sovereignDocsStart = frontendSource.indexOf("const buildSovereignDocsPreviewHtml");
const sovereignDocsEnd = frontendSource.indexOf("const isRenderableArtifactPath", sovereignDocsStart);
if (sovereignDocsStart < 0 || sovereignDocsEnd < sovereignDocsStart) {
  throw new Error("Sovereign Docs preview renderer must be isolated before artifact path rendering.");
}

const sovereignDocsRendererSource = frontendSource.slice(sovereignDocsStart, sovereignDocsEnd);
for (const forbidden of ["http://", "https://", "fetch(", "XMLHttpRequest", "sendBeacon", "<script", "<link", "@import", "url("]) {
  if (sovereignDocsRendererSource.includes(forbidden)) {
    throw new Error(`Sovereign Docs preview renderer must stay self-contained; found ${forbidden}.`);
  }
}

const evidenceCompareFunctionMatch = frontendSource.match(/const runAgentEvidenceComparison = async \(\) => \{[\s\S]*?\n  \};\n\n  const hermesKimiSkillInventory/);
if (!evidenceCompareFunctionMatch) {
  throw new Error("Evidence Compare handler body could not be found for freeze-guard validation.");
}

const evidenceCompareFunctionBody = evidenceCompareFunctionMatch[0];
if (evidenceCompareFunctionBody.includes("runUnlockedAgentPromptSession(") || evidenceCompareFunctionBody.includes("runUnlockedAgentPromptSessionStream(")) {
  throw new Error("Evidence Compare must not launch live Codex/Hermes agent sessions; it must read existing evidence only.");
}

if (!evidenceCompareFunctionBody.includes("compareExistingAgentEvidence")) {
  throw new Error("Evidence Compare handler must route through compareExistingAgentEvidence.");
}

const compareFunctionMatch = frontendSource.match(/const runAgentComparison = async \(\) => \{[\s\S]*?\n  \};\n\n  sendBtn\?\.addEventListener/);
if (!compareFunctionMatch) {
  throw new Error("Agent comparison dispatcher body could not be found for mode validation.");
}

const compareFunctionBody = compareFunctionMatch[0];
if (!compareFunctionBody.includes("agentRunMode === \"evidence-compare\"")) {
  throw new Error("Agent comparison dispatcher must require explicit Evidence Compare mode before read-only reconciliation.");
}

if (!compareFunctionBody.includes("runAgentEvidenceComparison") || !compareFunctionBody.includes("runCodexLeadDualExecution")) {
  throw new Error("Agent comparison dispatcher must preserve both Evidence Compare and Codex Lead dual execution modes.");
}

const primaryFunctionMatch = frontendSource.match(/const runPrimaryAgentWork = async \(\) => \{[\s\S]*?\n  \};\n\n  sendBtn\?\.addEventListener/);
if (!primaryFunctionMatch) {
  throw new Error("Primary agent work function could not be found.");
}

const primaryFunctionBody = primaryFunctionMatch[0];
if (!primaryFunctionBody.includes("isAgentRunStatusFollowup(prompt)") || !primaryFunctionBody.includes("runLatestAgentRunStatusRecap(prompt)")) {
  throw new Error("Primary agent work must answer status/recap follow-ups from existing evidence instead of launching a new run.");
}

const sendHandlerMatch = frontendSource.match(/sendBtn\?\.addEventListener\("click", \(\) => \{[\s\S]*?\n  \}\);\n\n  const runVisibleAgent/);
if (!sendHandlerMatch || !sendHandlerMatch[0].includes("runPrimaryAgentWork")) {
  throw new Error("Primary composer Send button must run the Codex Lead + Hermes/Kimi main work path.");
}

if (sendHandlerMatch[0].includes("runVisibleAgent(\"codex-readonly\"")) {
  throw new Error("Primary composer Send button must not fall back to Codex Read as the main work path.");
}

const codexLeadFunctionMatch = frontendSource.match(/const runCodexLeadDualExecution = async \(\) => \{[\s\S]*?\n  \};\n\n  const runAgentComparison/);
if (!codexLeadFunctionMatch) {
  throw new Error("Codex Lead dual execution handler could not be found.");
}

const codexLeadFunctionBody = codexLeadFunctionMatch[0];
if (!codexLeadFunctionBody.includes("runUnlockedAgentPromptSessionStream(\"codex-workspace-write\"")) {
  throw new Error("Run Dual must start a responsive codex-workspace-write stream.");
}

if (!codexLeadFunctionBody.includes("beginAgentRunGate({")) {
  throw new Error("Run Dual must acquire the shared agent run gate before runtime preflight/stream work.");
}

if (!frontendSource.includes("const recordAgentRunLifecycleEvent = (eventName") || !frontendSource.includes("const tickAgentRunWatchdog = () => {")) {
  throw new Error("Agent runs must record lifecycle telemetry and include a stale-stream watchdog.");
}

if (!frontendSource.includes("agentRunStaleEventThresholdMs") || !frontendSource.includes("stale-stream-warning")) {
  throw new Error("Agent run watchdog must emit explicit stale-stream warnings without clearing the run gate.");
}

if (!frontendSource.includes("Omega Agent Work is still being updated in Monaco.")) {
  throw new Error("Agent run watchdog must update the visible chat answer when a stream goes quiet.");
}

if (!frontendSource.includes("const recoverAgentRunUi = () => {") || !frontendSource.includes("recoverBtn?.addEventListener(\"click\"")) {
  throw new Error("Agent runs must expose an operator recovery control for wedged visible run state.");
}

if (!frontendSource.includes("ignoredAgentStreamIds.has(payload.session_id)") || !frontendSource.includes("rememberIgnoredAgentStreamId(snapshot.sessionId)")) {
  throw new Error("Recovered agent streams must be ignored so stale lifecycle events cannot resurrect old run state.");
}

if (!frontendSource.includes("backend_process_cancellation=not_exposed") || !frontendSource.includes("This is not a backend kill")) {
  throw new Error("Agent run recovery must be honest that it resets the UI gate without claiming backend process cancellation.");
}

if (!frontendSource.includes("agentRunFinalSummaryText({ label, runtime, payload, readback, loaded })")) {
  throw new Error("Agent stream completion must replace the running chat bubble with a final evidence summary.");
}

if (!codexLeadFunctionBody.includes("updateAgentRunGate({")) {
  throw new Error("Run Dual must update the shared agent run gate after the stream is accepted.");
}

if (!codexLeadFunctionBody.includes("promptChars: prompt.length") || !codexLeadFunctionBody.includes("recordAgentRunLifecycleEvent(\"stream-accepted\"")) {
  throw new Error("Run Dual must track prompt size and accepted-stream lifecycle evidence.");
}

if (codexLeadFunctionBody.includes("runBlockingAgentStage(") || codexLeadFunctionBody.includes("runUnlockedAgentPromptSession(")) {
  throw new Error("Run Dual must not await blocking renderer-side agent stages.");
}

if (!frontendSource.includes("const createAgentAnswerMessage = (label, initialText = \"Waiting for agent output...\")")) {
  throw new Error("Agent answer bubbles must accept immediate starting text.");
}

if (!frontendSource.includes("body.textContent = initialText")) {
  throw new Error("Agent answer bubbles must render immediate starting text instead of a stale waiting placeholder.");
}

if (!codexLeadFunctionBody.includes("await waitForProductPaint();")) {
  throw new Error("Run Dual must yield a browser paint before starting long agent work so the chat preamble is visible.");
}

if (codexLeadFunctionBody.indexOf("await waitForProductPaint();") > codexLeadFunctionBody.indexOf("runUnlockedAgentPromptSessionStream(\"codex-workspace-write\"")) {
  throw new Error("Run Dual paint yield must happen before the long streaming invoke starts.");
}

if (codexLeadFunctionBody.includes("Waiting for readable stream output")) {
  throw new Error("Run Dual must not overwrite the immediate chat preamble with a generic waiting message after stream acceptance.");
}

for (const prepNeedle of [
  "await updateCodexLeadPreparationStatus(\"Codex Lead recording orchestration\"",
  "await updateCodexLeadPreparationStatus(\"Codex Lead orchestration recorded\"",
  "await updateCodexLeadPreparationStatus(\"Hermes/Kimi inventory running\"",
  "await updateCodexLeadPreparationStatus(\"Hermes/Kimi inventory recorded\"",
  "await updateCodexLeadPreparationStatus(\"Hermes/Kimi assist running\"",
  "timeoutMs: codexLeadAssistTimeoutMs",
  "await updateCodexLeadPreparationStatus(\"Codex Lead stream handoff\"",
]) {
  if (!codexLeadFunctionBody.includes(prepNeedle)) {
    throw new Error(`Run Dual missing visible preparation status step: ${prepNeedle}`);
  }
}

if (!frontendSource.includes("const codexLeadAssistTimeoutMs = 15000")) {
  throw new Error("Run Dual must use an explicit shorter renderer-side Hermes/Kimi assist timeout.");
}

const assistBriefFunctionMatch = frontendSource.match(/async function recordHermesKimiAssistBrief\(\{[\s\S]*?\n\}/);
if (!assistBriefFunctionMatch?.[0]?.includes("timeoutMs = 15000") || !assistBriefFunctionMatch[0].includes("timeout_ms: timeoutMs")) {
  throw new Error("Hermes/Kimi assist helper must accept and forward an explicit timeoutMs value.");
}

if (!codexLeadFunctionBody.includes("createCodexLeadOrchestrationRecord(prompt)")) {
  throw new Error("Run Dual must record a Codex Lead orchestration packet before starting the stream.");
}

if (codexLeadFunctionBody.indexOf("createCodexLeadOrchestrationRecord(prompt)") > codexLeadFunctionBody.indexOf("runUnlockedAgentPromptSessionStream(\"codex-workspace-write\"")) {
  throw new Error("Codex Lead orchestration evidence must be created before the responsive stream starts.");
}

if (!codexLeadFunctionBody.includes("recordHermesKimiCapabilityInventory(prompt)")) {
  throw new Error("Run Dual must record a current Hermes/Kimi capability inventory before starting the stream.");
}

if (codexLeadFunctionBody.indexOf("recordHermesKimiCapabilityInventory(prompt)") > codexLeadFunctionBody.indexOf("runUnlockedAgentPromptSessionStream(\"codex-workspace-write\"")) {
  throw new Error("Hermes/Kimi capability inventory evidence must be created before the responsive stream starts.");
}

if (!codexLeadFunctionBody.includes("recordHermesKimiAssistBrief({") || !codexLeadFunctionBody.includes("timeoutMs: codexLeadAssistTimeoutMs")) {
  throw new Error("Run Dual must run a bounded Hermes/Kimi assist brief before starting the stream.");
}

if (codexLeadFunctionBody.indexOf("recordHermesKimiAssistBrief({") > codexLeadFunctionBody.indexOf("runUnlockedAgentPromptSessionStream(\"codex-workspace-write\"")) {
  throw new Error("Hermes/Kimi assist evidence must be created before the responsive Codex stream starts.");
}

if (!codexLeadFunctionBody.includes("codexLeadStreamingPrompt({ prompt, orchestration, hermesInventory, hermesAssist })")) {
  throw new Error("Codex Lead stream prompt must include orchestration, Hermes/Kimi inventory, and Hermes/Kimi assist summaries.");
}

const visibleAgentFunctionMatch = frontendSource.match(/const runVisibleAgent = async \(runtime, label\) => \{[\s\S]*?\n  \};\n\n  codexBtn/);
if (!visibleAgentFunctionMatch) {
  throw new Error("Visible single-agent handler could not be found.");
}

const visibleAgentFunctionBody = visibleAgentFunctionMatch[0];
if (!visibleAgentFunctionBody.includes("await waitForProductPaint();")) {
  throw new Error("Single-agent runs must yield a browser paint before starting long agent work.");
}

if (visibleAgentFunctionBody.indexOf("await waitForProductPaint();") > visibleAgentFunctionBody.indexOf("runUnlockedAgentPromptSessionStream(runtime, promptWithContext)")) {
  throw new Error("Single-agent paint yield must happen before the long streaming invoke starts.");
}

if (!visibleAgentFunctionBody.includes("beginAgentRunGate({")) {
  throw new Error("Single-agent runs must acquire the shared agent run gate before starting.");
}

if (!visibleAgentFunctionBody.includes("updateAgentRunGate({")) {
  throw new Error("Single-agent runs must update the shared agent run gate after stream acceptance.");
}

if (!visibleAgentFunctionBody.includes("promptChars: prompt.length") || !visibleAgentFunctionBody.includes("recordAgentRunLifecycleEvent(\"stream-accepted\"")) {
  throw new Error("Single-agent runs must track prompt size and accepted-stream lifecycle evidence.");
}

if (!visibleAgentFunctionBody.includes("activeAgentRun?.phase !== \"streaming\"")) {
  throw new Error("Single-agent runs must keep controls locked while an accepted stream is still running.");
}

for (const streamLifecycleNeedle of [
  "recordAgentRunLifecycleEvent(`stream-${payload.kind}`",
  "recordAgentRunLifecycleEvent(\"stream-error\"",
  "recordAgentRunLifecycleEvent(\"stream-started\"",
  "recordAgentRunLifecycleEvent(\"stream-finished\"",
]) {
  if (!frontendSource.includes(streamLifecycleNeedle)) {
    throw new Error(`Agent stream listener missing lifecycle telemetry: ${streamLifecycleNeedle}`);
  }
}

if (visibleAgentFunctionBody.includes("finally {\n      sendBtn?.removeAttribute(\"disabled\")")) {
  throw new Error("Single-agent runs must not unconditionally re-enable buttons in finally after stream acceptance.");
}

for (const productStyleNeedle of [
  "#omega-product-shell + #app-shell",
  "#omega-monaco-frame",
  "#omega-monaco-container",
  "#omega-home-surface",
  "#omega-computer-main-surface",
  "#omega-monaco-frame.omega-main-surface-active #omega-monaco-container",
  ".omega-computer-main-shell",
  ".omega-computer-main-controls",
  ".omega-computer-main-actions button[data-omega-computer-action=\"main\"]",
  ".omega-home-mark",
  ".omega-home-title",
  "omega-home-pulse",
  "#omega-xterm-surface",
  "#omega-terminal-command-input",
  ".omega-terminal-session-bar",
  "#omega-terminal-session-status[data-state=\"running\"]",
  ".omega-terminal-quickbar",
  "#omega-command-palette-product",
  ".omega-command-palette-title",
  ".omega-context-toggle",
  ".omega-agent-mode-row",
  ".omega-activity-btn::after",
  ".omega-activity-btn[data-panel-state=\"collapsed\"].active",
  ".omega-activity-btn[data-activity-state=\"running\"]",
  ".omega-activity-btn[data-activity-state=\"done\"]",
  ".omega-integration-grid button[data-panel-action]",
  ".omega-integration-grid button[data-panel-action]::before",
  ".omega-integration-grid button[data-panel-action]:hover",
  ".omega-integration-grid button[data-panel-action]:hover::before",
  ".omega-integration-grid button[data-panel-action][data-action-selected]",
  ".omega-integration-grid button[data-panel-action][data-action-state=\"running\"]",
  ".omega-integration-grid button[data-panel-action][data-action-state=\"done\"]",
  "#omega-panel-main-surface",
  ".omega-panel-main-shell",
  ".omega-panel-main-card-grid",
  ".omega-panel-main-chip-row",
  ".omega-panel-main-chip",
  ".omega-panel-main-shell[data-panel-action-surface=\"mcp\"] .omega-panel-main-card",
  ".omega-panel-main-actions button[data-panel-primary-action]",
  "grid-template-areas:",
  "text-overflow: ellipsis",
  ".omega-first-class-dashboard-card .item-title",
  ".omega-first-class-dashboard-card .item-badge",
  ".omega-first-class-dashboard-card p",
  ".omega-first-class-dashboard-list",
  ".omega-icon-vault::after",
  ".omega-icon-shield::after",
  ".omega-icon-tools::after",
  ".omega-icon-media::after",
  "#omega-parity-send",
  ".omega-side-panel",
  ".omega-bottom-view",
  ".omega-artifact-preview-product",
  ".omega-artifact-preview-actions",
  "#omega-artifact-preview-overlay",
  "#omega-artifact-preview-frame-product",
  "#omega-artifact-preview-text-product",
  ".omega-tool-docs::before",
  ".omega-tool-docs::after",
  ".omega-tool-computer::before",
  ".omega-tool-computer::after",
  ".omega-computer-terminal-surface",
  ".omega-computer-screen",
  ".omega-computer-worker-card",
  ".omega-computer-worker-progress",
  "#omega-editor-toolbar button.active",
  ".omega-integration-grid",
  ".omega-toolbar-parity-item",
  ".omega-toolbar-parity-actions",
  ".omega-replace-row",
  ".omega-search-mode-row",
  ".omega-workspace-search-status",
  "#omega-parity-recover",
  ".omega-first-class-dashboard",
  ".omega-dashboard-header",
  ".omega-first-class-dashboard-list",
  ".omega-first-class-dashboard-card",
  ".omega-agent-run-center",
  ".omega-agent-run-center-summary",
  ".omega-agent-run-center-body",
  ".omega-agent-run-center-chevron",
  ".omega-agent-run-item",
  ".omega-evidence-history-list",
  ".omega-evidence-history-item",
  ".omega-sidecar-packet-list",
  ".omega-sidecar-packet-item",
  ".omega-sidecar-lifecycle",
  ".omega-tree-row.directory",
  ".omega-product-resizer",
  "#omega-chat-panel-product",
  "#omega-bottom-panel",
  "--product-chat-width: var(--chat-width)",
  "--product-bottom-height: var(--bottom-panel-height)",
  "grid-template-columns: var(--activity-width) var(--sidebar-width) minmax(560px, 1fr) minmax(var(--chat-min-width), var(--product-chat-width))",
  "grid-template-rows: 38px 34px minmax(260px, 1fr) var(--product-bottom-height)",
  "#omega-product-shell.omega-calm-mode #omega-product-main",
  "#omega-product-shell.omega-calm-mode #omega-sidebar",
  "#omega-product-shell.omega-sidebar-collapsed #omega-product-main",
  "#omega-product-shell.omega-sidebar-collapsed #omega-sidebar",
]) {
  if (!styleSource.includes(productStyleNeedle)) {
    throw new Error(`Visible workbench styling missing ${productStyleNeedle}.`);
  }
}

for (const vendorPath of [
  "web/vendor/monaco/vs/loader.js",
  "web/vendor/xterm/xterm.js",
  "web/vendor/xterm/xterm.css",
  "web/vendor/xterm/xterm-addon-fit.js",
]) {
  if (!fs.existsSync(path.join(root, vendorPath))) {
    throw new Error(`Product workbench vendor asset missing ${vendorPath}.`);
  }
}

if (!commands.source?.audit_doc || !fs.existsSync(path.join(repoRoot, commands.source.audit_doc))) {
  throw new Error("Command contract must reference an audit document included in this branch.");
}

const unifiedActionPlanPath = path.join(repoRoot, "docs/GRAVITY_OMEGA_UNIFIED_ACTION_PLAN.md");
if (!fs.existsSync(unifiedActionPlanPath)) {
  throw new Error("Unified Kimi action plan must be included in docs/GRAVITY_OMEGA_UNIFIED_ACTION_PLAN.md.");
}

const unifiedActionPlan = fs.readFileSync(unifiedActionPlanPath, "utf8");
for (const requiredPhrase of ["20 command families", "OmegaTaskRun", "Worker C", "workspace_edit"]) {
  if (!unifiedActionPlan.includes(requiredPhrase)) {
    throw new Error(`Unified action plan missing ${requiredPhrase}.`);
  }
}

const uiUxMatrixPath = path.join(repoRoot, "docs/GRAVITY_OMEGA_UI_UX_TEST_MATRIX.md");
if (!fs.existsSync(uiUxMatrixPath)) {
  throw new Error("UI/UX test matrix must be included in docs/GRAVITY_OMEGA_UI_UX_TEST_MATRIX.md.");
}

const uiUxMatrixDoc = fs.readFileSync(uiUxMatrixPath, "utf8");
for (const requiredPhrase of ["Worker D", "20 feature families", "focus rings", "loading skeletons"]) {
  if (!uiUxMatrixDoc.includes(requiredPhrase)) {
    throw new Error(`UI/UX test matrix missing ${requiredPhrase}.`);
  }
}

for (const styleNeedle of [
  "--warning",
  "--info",
  "--memory",
  "--review",
  "--activity-width",
  "--sidebar-width",
  "--chat-min-width",
  "--chat-max-width",
  "--bottom-panel-min-height",
  "--bottom-panel-max-height",
  "--bottom-panel-max-height: 760px",
  "--transition-base",
  "--spring-panel",
  "--shadow-sm",
  "--shadow-focus",
  ":focus-visible",
  ".skeleton",
  "skeleton-shimmer",
  ".surface-hidden",
  "data-active-area",
  ".sr-only",
  ".rail-icon",
  ".icon-command",
  ".icon-workspace",
  ".toolbar-search-row",
  ".toolbar-search-input",
  ".agent-rail-resizer",
  ".is-resizing-agent-rail",
  ".composer-status",
  ".bottom-evidence-dock",
  ".bottom-dock-resizer",
  ".is-resizing-bottom-dock",
]) {
  if (!styleSource.includes(styleNeedle)) {
    throw new Error(`UI/UX design token pass missing ${styleNeedle}.`);
  }
}

for (const group of commands.groups) {
  if (!group.id || !group.title || !Array.isArray(group.current_ipc) || !Array.isArray(group.target_commands)) {
    throw new Error(`Invalid command group: ${JSON.stringify(group)}`);
  }
  if (group.current_ipc.length === 0 || group.target_commands.length === 0) {
    throw new Error(`Command group ${group.id} needs current and target commands.`);
  }
}

if (!Array.isArray(features.features) || features.features.length < 5) {
  throw new Error("Feature migration contract is too small.");
}

if (sandbox.execution_enabled !== false) {
  throw new Error("Sandbox contract must keep live execution disabled.");
}

if (!Array.isArray(sandbox.policies) || sandbox.policies.length < 3) {
  throw new Error("Sandbox contract must define read/write/restricted policies.");
}

if (!Array.isArray(sandbox.allowed_prefixes) || sandbox.allowed_prefixes.length < 8) {
  throw new Error("Sandbox contract must include command allowlist prefixes.");
}

for (const requiredPrefix of ["codex-review", "codex-exec-json", "codex-exec-readonly-json", "codex-exec-workspace-write-json", "hermes-companion", "cargo-check"]) {
  if (!sandbox.allowed_prefixes.some((prefix) => prefix.id === requiredPrefix)) {
    throw new Error(`Sandbox allowlist missing ${requiredPrefix}.`);
  }
}

if (!Array.isArray(toolbar.titlebar_actions) || toolbar.titlebar_actions.length < 18) {
  throw new Error("Toolbar contract must include the current titlebar action inventory.");
}

if (!Array.isArray(toolbar.commands) || toolbar.commands.length < toolbar.titlebar_actions.length) {
  throw new Error("Toolbar contract must map visible actions to target commands.");
}

const toolbarActions = new Set(
  toolbar.commands
    .map((command) => command.current_action)
    .filter((action) => typeof action === "string" && action.length > 0),
);

for (const action of toolbar.titlebar_actions) {
  if (!toolbarActions.has(action)) {
    throw new Error(`Toolbar action ${action} is not mapped in the command registry.`);
  }
}

for (const requiredId of ["security.refresh", "mobile.qr", "agent.codex_review", "agent.hermes_companion", "agent.joint_ci", "agent.omega_computer"]) {
  if (!toolbar.commands.some((command) => command.id === requiredId)) {
    throw new Error(`Toolbar contract missing required command ${requiredId}.`);
  }
}

if (!packageJson.scripts?.validate) {
  throw new Error("package.json must expose a validate script.");
}

if (tauriConfig.identifier !== "com.veritas.gravityomega.native") {
  throw new Error("Unexpected Tauri application identifier.");
}

if (tauriConfig.build?.devUrl) {
  throw new Error("Static scaffold should use frontendDist instead of a devUrl.");
}

if (tauriConfig.build?.frontendDist !== "../web") {
  throw new Error("Static scaffold frontendDist must point at the isolated web asset directory.");
}

if (tauriConfig.app?.withGlobalTauri !== true) {
  throw new Error("Live command smoke requires app.withGlobalTauri.");
}

if (tauriConfig.app?.windows?.[0]?.decorations !== false) {
  throw new Error("Gravity Omega native shell must own the chrome; Tauri decorations must be disabled.");
}

if (htmlSource.includes('<header id="omega-titlebar" data-tauri-drag-region>')) {
  throw new Error("Window controls must not sit inside a full-width data-tauri-drag-region titlebar.");
}

for (const nativeWindowNeedle of [
  "native_window_command",
  "get_webview_window(\"main\")",
  ".minimize()",
  ".is_maximized()",
  ".unmaximize()",
  ".maximize()",
  ".close()",
]) {
  if (!rustCommandsSource.includes(nativeWindowNeedle) && !frontendSource.includes(nativeWindowNeedle)) {
    throw new Error(`Native window command bridge missing ${nativeWindowNeedle}.`);
  }
}

for (const forbiddenFrontendNeedle of [
  "gravity-omega.product-layout.v2",
  "gravity-omega.editor-session.v2",
  "gravity-omega.product-layout.v3",
  "gravity-omega.editor-session.v3",
  "gravity-omega.product-layout.v4",
  "gravity-omega.editor-session.v4",
  "--ask-for-approval",
]) {
  if (frontendSource.includes(forbiddenFrontendNeedle) || rustCommandsSource.includes(forbiddenFrontendNeedle)) {
    throw new Error(`Stale native rescue artifact still present: ${forbiddenFrontendNeedle}`);
  }
}

for (const command of [
  "runtime_health",
  "command_manifest",
  "replacement_app_foundation_scorecard",
  "replacement_app_work_queue",
  "command_surface_collapse_board",
  "replacement_app_ship_readiness",
  "sidecar_readiness_board",
  "sidecar_launch_policy_manifest",
  "sidecar_health_packet_console",
  "record_runtime_sidecar_process_snapshot",
  "list_runtime_sidecar_process_snapshots",
  "runtime_probe_board",
  "run_runtime_depth_probe",
  "record_hermes_kimi_capability_inventory",
  "list_hermes_kimi_capability_inventories",
  "record_hermes_kimi_assist_brief",
  "list_hermes_kimi_assist_briefs",
  "create_runtime_launch_packet_stub",
  "list_runtime_launch_packets",
  "create_joint_runtime_run_packet_stub",
  "list_joint_runtime_run_packets",
  "create_runner_evidence_spine_stub",
  "list_runner_evidence_spines",
  "run_supervised_runtime_smoke",
  "list_supervised_runtime_smokes",
  "run_agent_transcript_session",
  "list_agent_transcript_sessions",
  "record_pet_runtime_signal",
  "list_pet_runtime_signals",
  "record_pet_runtime_snapshot_signal",
  "run_unlocked_agent_prompt_session",
  "run_unlocked_agent_prompt_session_stream",
  "list_unlocked_agent_prompt_sessions",
  "ui_ux_test_matrix",
  "codex_hermes_run_view_dashboard",
  "codex_hermes_run_detail_timeline",
  "codex_hermes_run_selection_comparison",
  "codex_hermes_run_evidence_diff_board",
  "codex_hermes_run_reconciliation_checklist",
  "codex_hermes_run_reconciliation_action_plan",
  "codex_hermes_run_evidence_attachment_preview",
  "codex_hermes_run_evidence_attachment_approval_packet",
  "codex_hermes_run_evidence_intake_workbench",
  "codex_hermes_run_evidence_validation_summary",
  "codex_hermes_run_evidence_operator_confirmation_dry_runs",
  "steno_pet_companion_dashboard",
  "steno_search",
  "terminal_process_lane_dashboard",
  "terminal_toggle",
  "approval_evidence_spine_dashboard",
  "record_desktop_environment_snapshot",
  "list_desktop_environment_snapshots",
  "record_desktop_read_only_capability_snapshot",
  "list_desktop_read_only_capability_snapshots",
  "record_evidence_durability_manifest",
  "list_evidence_durability_manifests",
  "linux_desktop_control_readiness_dashboard",
  "desktop_capture_action_approval_policy_dashboard",
  "desktop_capture_action_approval_records",
  "desktop_capture_action_operator_confirmation_dry_runs",
  "desktop_capture_action_final_preaction_dry_runs",
  "desktop_action_safety_summary",
  "linux_desktop_readiness_release_checklist",
  "workspace_editor_navigation_lane",
  "workspace_editor_shell_layout",
  "workspace_editor_shell_bindings",
  "workspace_editor_shell_focus_model",
  "workspace_editor_keyboard_navigation_map",
  "workspace_editor_command_palette_map",
  "workspace_editor_command_search_map",
  "editor_find",
  "workspace_edit",
  "workspace_mutation_workbench",
  "workspace_files_dashboard",
  "workspace_explorer_snapshot",
  "product_workspace_file_open",
  "product_workspace_file_save",
  "product_workspace_search",
  "run_product_terminal_command",
  "run_product_terminal_command_stream",
  "record_product_terminal_transcript_replay",
  "list_product_terminal_transcript_replays",
  "record_sovereign_docs_preview",
  "list_sovereign_docs_previews",
  "record_omega_computer_session",
  "list_omega_computer_sessions",
  "run_product_workbench_smoke",
  "list_product_workbench_smokes",
  "product_evidence_history",
  "terminal_process_workbench",
  "security_shield_workbench",
  "native_shell_pairing_workbench",
  "veritas_modules_dashboard",
  "agent_runtime_status",
  "provider_settings_dashboard",
  "task_run_templates",
  "command_registry",
  "docs_open",
  "about_open",
  "command_palette_open",
  "toolbar_action_readiness",
  "first_class_integration_launchpad",
  "gated_action_release_board",
  "gated_adapter_release_queue",
  "create_gated_adapter_release_packet_stub",
  "list_gated_adapter_release_packets",
  "execute_command_stub",
  "create_task_run_stub",
  "list_task_runs",
  "create_approval_record_stub",
  "list_approval_records",
  "resolve_approval_record_stub",
  "task_run_artifact_preview",
  "sandbox_policy_manifest",
  "evaluate_execution_gate",
  "prepare_runner_invocation_stub",
  "list_runner_invocations",
  "create_joint_agent_plan_stub",
  "list_joint_agent_plans",
  "create_agent_capability_inventory_stub",
  "list_agent_capability_inventories",
  "create_first_class_integration_readiness_stub",
  "list_first_class_integration_readiness",
  "append_agent_event_stub",
  "agent_event_log_preview",
  "create_workspace_lease_stub",
  "list_workspace_leases",
  "create_workspace_inspection_record_stub",
  "list_workspace_inspection_records",
  "create_workspace_preview_record_stub",
  "list_workspace_preview_records",
  "create_workspace_tree_metadata_record_stub",
  "list_workspace_tree_metadata_records",
  "create_workspace_file_content_preview_record_stub",
  "list_workspace_file_content_preview_records",
  "create_workspace_editor_tab_state_stub",
  "list_workspace_editor_tab_states",
  "create_workspace_edit_preflight_stub",
  "list_workspace_edit_preflights",
  "create_workspace_write_approval_policy_stub",
  "list_workspace_write_approval_policies",
  "create_workspace_write_approval_stub",
  "list_workspace_write_approvals",
  "create_workspace_writable_buffer_draft_stub",
  "list_workspace_writable_buffer_drafts",
  "create_workspace_dirty_transition_preflight_stub",
  "list_workspace_dirty_transition_preflights",
  "create_workspace_mutable_buffer_transaction_stub",
  "list_workspace_mutable_buffer_transactions",
  "create_workspace_editor_buffer_materialization_policy_stub",
  "list_workspace_editor_buffer_materialization_policies",
  "create_workspace_editor_buffer_attachment_stub",
  "list_workspace_editor_buffer_attachments",
  "create_workspace_editor_buffer_editable_state_preflight_stub",
  "list_workspace_editor_buffer_editable_state_preflights",
  "create_workspace_editable_buffer_view_binding_stub",
  "list_workspace_editable_buffer_view_bindings",
  "create_workspace_editable_text_viewport_materialization_stub",
  "list_workspace_editable_text_viewport_materializations",
  "create_workspace_editable_text_attachment_verification_stub",
  "list_workspace_editable_text_attachment_verifications",
  "create_workspace_editable_text_model_handle_stub",
  "list_workspace_editable_text_model_handles",
  "create_workspace_editable_text_model_storage_preflight_stub",
  "list_workspace_editable_text_model_storage_preflights",
  "create_workspace_editable_text_model_text_snapshot_stub",
  "list_workspace_editable_text_model_text_snapshots",
  "prepare_runner_adapter_stub",
  "list_runner_adapters",
  "build_process_command_plan_stub",
  "list_process_command_plans",
  "initialize_process_streams_stub",
  "list_process_stream_inits",
  "create_process_lifecycle_stub",
  "list_process_lifecycles",
  "create_process_control_policy_stub",
  "list_process_control_policies",
  "create_process_supervisor_preflight_stub",
  "list_process_supervisor_preflights",
  "create_process_supervisor_heartbeat_stub",
  "list_process_supervisor_heartbeats",
  "create_process_supervisor_exit_summary_stub",
  "list_process_supervisor_exit_summaries",
  "create_process_output_tail_summary_stub",
  "list_process_output_tail_summaries",
  "create_run_transcript_bundle_stub",
  "list_run_transcript_bundles",
  "create_transcript_export_policy_stub",
  "list_transcript_export_policies",
  "create_transcript_protection_policy_stub",
  "list_transcript_protection_policies",
  "create_local_mcp_lane_capability_contract_stub",
  "list_local_mcp_lane_capability_contracts",
  "first_class_mcp_dashboard",
  "sswp_status",
  "record_sswp_registry_snapshot",
  "list_sswp_registry_snapshots",
  "create_local_mcp_health_preflight_stub",
  "list_local_mcp_health_preflights",
  "create_local_mcp_health_record_stub",
  "list_local_mcp_health_records",
  "create_local_mcp_capability_discovery_policy_stub",
  "list_local_mcp_capability_discovery_policies",
  "create_local_mcp_gated_call_policy_stub",
  "list_local_mcp_gated_call_policies",
  "create_local_mcp_call_approval_audit_stub",
  "list_local_mcp_call_approval_audits",
  "create_local_mcp_consent_approval_decision_stub",
  "list_local_mcp_consent_approval_decisions",
  "create_local_mcp_audit_outcome_stub",
  "list_local_mcp_audit_outcomes",
  "create_local_mcp_recovery_precall_guard_stub",
  "list_local_mcp_recovery_precall_guards",
  "create_local_mcp_final_call_approval_stub",
  "list_local_mcp_final_call_approvals",
  "create_local_mcp_live_call_dry_run_stub",
  "list_local_mcp_live_call_dry_runs",
  "create_local_mcp_typed_command_contract_stub",
  "list_local_mcp_typed_command_contracts",
  "create_local_mcp_status_probe_preflight_stub",
  "list_local_mcp_status_probe_preflights",
  "create_local_mcp_config_lookup_preflight_stub",
  "list_local_mcp_config_lookup_preflights",
  "create_local_mcp_config_read_policy_stub",
  "list_local_mcp_config_read_policies",
  "create_local_mcp_config_path_allowlist_stub",
  "list_local_mcp_config_path_allowlists",
  "create_local_mcp_config_path_resolution_request_stub",
  "list_local_mcp_config_path_resolution_requests",
  "create_local_mcp_config_path_resolution_approval_stub",
  "list_local_mcp_config_path_resolution_approvals",
  "create_local_mcp_config_path_resolution_dry_run_stub",
  "list_local_mcp_config_path_resolution_dry_runs",
  "create_local_mcp_config_path_materialization_request_stub",
  "list_local_mcp_config_path_materialization_requests",
  "create_local_mcp_config_path_materialization_approval_stub",
  "list_local_mcp_config_path_materialization_approvals",
  "create_local_mcp_config_path_materialization_final_dry_run_stub",
  "list_local_mcp_config_path_materialization_final_dry_runs",
  "create_local_mcp_config_path_read_preflight_request_stub",
  "list_local_mcp_config_path_read_preflight_requests",
  "create_local_mcp_config_path_read_preflight_approval_stub",
  "list_local_mcp_config_path_read_preflight_approvals",
  "create_local_mcp_config_path_read_preflight_final_dry_run_stub",
  "list_local_mcp_config_path_read_preflight_final_dry_runs",
  "create_local_mcp_config_path_controlled_read_request_stub",
  "list_local_mcp_config_path_controlled_read_requests",
  "create_local_mcp_config_path_controlled_read_approval_stub",
  "list_local_mcp_config_path_controlled_read_approvals",
  "create_local_mcp_config_path_controlled_read_final_dry_run_stub",
  "list_local_mcp_config_path_controlled_read_final_dry_runs",
  "create_local_mcp_config_path_sealed_read_request_stub",
  "list_local_mcp_config_path_sealed_read_requests",
  "create_local_mcp_config_path_sealed_read_approval_stub",
  "list_local_mcp_config_path_sealed_read_approvals",
  "create_local_mcp_config_path_sealed_read_final_dry_run_stub",
  "list_local_mcp_config_path_sealed_read_final_dry_runs",
  "create_local_mcp_config_path_sealed_content_preflight_stub",
  "list_local_mcp_config_path_sealed_content_preflights",
  "create_local_mcp_config_path_sealed_content_final_dry_run_stub",
  "list_local_mcp_config_path_sealed_content_final_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_approval_stub",
  "list_local_mcp_config_path_sealed_config_content_read_approvals",
  "create_local_mcp_config_path_sealed_config_content_read_final_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_final_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_execution_preflight_stub",
  "list_local_mcp_config_path_sealed_config_content_read_execution_preflights",
  "create_local_mcp_config_path_sealed_config_content_read_audit_recovery_preexecution_stub",
  "list_local_mcp_config_path_sealed_config_content_read_audit_recovery_preexecutions",
  "create_local_mcp_config_path_sealed_config_content_read_final_approval_stub",
  "list_local_mcp_config_path_sealed_config_content_read_final_approvals",
  "create_local_mcp_config_path_sealed_config_content_read_final_execution_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_final_execution_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_redaction_schema_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_redaction_schema_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_parse_hash_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_parse_hash_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_content_shape_policy_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_content_shape_policy_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_structural_intent_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_structural_intent_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_field_inventory_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_field_inventory_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_key_presence_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_key_presence_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_key_requirement_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_key_requirement_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_key_value_shape_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_key_value_shape_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_value_contract_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_value_contract_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_value_redaction_map_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_value_redaction_map_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_schema_key_map_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_schema_key_map_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_schema_binding_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_schema_binding_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_schema_validation_plan_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_schema_validation_plan_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_coverage_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_coverage_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_coverage_report_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_coverage_report_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_report_archive_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_report_archive_dry_runs",
  "create_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_archive_retention_dry_run_stub",
  "list_local_mcp_config_path_sealed_config_content_read_schema_validation_fixture_archive_retention_dry_runs",
]) {
  if (!frontendSource.includes(command)) {
    throw new Error(`Frontend must attempt live Tauri command ${command}.`);
  }
  if (!rustCommandsSource.includes(`fn ${command}`)) {
    throw new Error(`Rust command ${command} is not implemented.`);
  }
}

for (const stateNeedle of [
  "XDG_STATE_HOME",
  "OmegaTaskRunRecord",
  "ApprovalRecord",
  "ArtifactPreview",
  "task-runs",
  "approvals",
  "SandboxContract",
  "ExecutionGateDecision",
  "RunnerInvocationRecord",
  "runner-invocations",
  "JointAgentPlanRecord",
  "joint-agent-plans",
  "AgentCapabilityInventoryRecord",
  "agent-capability-inventories",
  "FirstClassIntegrationReadinessRecord",
  "first-class-integration-readiness",
  "OmegaComputerSessionRecord",
  "omega-computer-sessions",
  "AgentEventRecord",
  "agent-events",
  "WorkspaceLeaseRecord",
  "workspace-leases",
  "WorkspaceInspectionRecord",
  "workspace-inspections",
  "WorkspacePreviewRecord",
  "workspace-previews",
  "WorkspaceTreeMetadataRecord",
  "workspace-tree-metadata",
  "WorkspaceFileContentPreviewRecord",
  "workspace-file-previews",
  "ReleaseArtifactStatus",
  "release_binary_path",
  "WorkspaceEditorTabStateRecord",
  "workspace-editor-tabs",
  "WorkspaceEditPreflightRecord",
  "workspace-edit-preflights",
  "WorkspaceWriteApprovalPolicyRecord",
  "workspace-write-approval-policies",
  "WorkspaceWriteApprovalRecord",
  "workspace-write-approvals",
  "WorkspaceWritableBufferDraftRecord",
  "workspace-writable-buffer-drafts",
  "WorkspaceDirtyTransitionPreflightRecord",
  "workspace-dirty-transition-preflights",
  "WorkspaceMutableBufferTransactionRecord",
  "workspace-mutable-buffer-transactions",
  "WorkspaceEditorBufferMaterializationPolicyRecord",
  "workspace-editor-buffer-materialization-policies",
  "WorkspaceEditorBufferAttachmentRecord",
  "workspace-editor-buffer-attachments",
  "WorkspaceEditorBufferEditableStatePreflightRecord",
  "workspace-editor-buffer-editable-state-preflights",
  "WorkspaceEditorBufferViewBindingRecord",
  "workspace-editor-buffer-view-bindings",
  "WorkspaceEditableTextViewportMaterializationRecord",
  "workspace-editable-text-viewport-materializations",
  "WorkspaceEditableTextAttachmentVerificationRecord",
  "workspace-editable-text-attachment-verifications",
  "WorkspaceEditableTextModelHandleRecord",
  "workspace-editable-text-model-handles",
  "WorkspaceEditableTextModelStoragePreflightRecord",
  "workspace-editable-text-model-storage-preflights",
  "WorkspaceEditableTextModelTextSnapshotRecord",
  "workspace-editable-text-model-text-snapshots",
  "RunnerAdapterRecord",
  "runner-adapters",
  "ProcessCommandPlanRecord",
  "process-command-plans",
  "ProcessStreamInitRecord",
  "process-stream-inits",
  "ProcessLifecycleRecord",
  "process-lifecycles",
  "ProcessControlPolicyRecord",
  "process-control-policies",
  "ProcessSupervisorPreflightRecord",
  "process-supervisor-preflights",
  "ProcessSupervisorHeartbeatRecord",
  "process-supervisor-heartbeats",
  "ProcessSupervisorExitSummaryRecord",
  "process-supervisor-exit-summaries",
  "ProcessOutputTailSummaryRecord",
  "process-output-tail-summaries",
  "RunTranscriptBundleRecord",
  "run-transcript-bundles",
  "TranscriptExportPolicyRecord",
  "transcript-export-policies",
  "TranscriptProtectionPolicyRecord",
  "transcript-protection-policies",
  "AgentTranscriptSessionRecord",
  "agent-transcript-sessions",
  "PetRuntimeAttentionItem",
  "recent_pet_runtime_signals",
  "recent_pet_attention_items",
  "ProductTerminalSessionSummary",
  "ProductTerminalBlockedCommandRecord",
  "recent_terminal_sessions",
  "recent_terminal_replays",
  "recent_blocked_terminal_commands",
  "recent_process_control_policies",
  "recent_process_exit_summaries",
  "LocalMcpLaneCapabilityContractRecord",
  "local-mcp-lane-capability-contracts",
  "LocalMcpHealthPreflightRecord",
  "local-mcp-health-preflights",
  "LocalMcpHealthRecord",
  "local-mcp-health",
  "LocalMcpCapabilityDiscoveryPolicyRecord",
  "local-mcp-capability-discovery-policies",
  "LocalMcpGatedCallPolicyRecord",
  "local-mcp-gated-call-policies",
  "LocalMcpCallApprovalAuditRecord",
  "local-mcp-call-approval-audits",
  "LocalMcpConsentApprovalDecisionRecord",
  "local-mcp-consent-approval-decisions",
  "LocalMcpAuditOutcomeRecord",
  "local-mcp-audit-outcomes",
  "LocalMcpRecoveryPrecallGuardRecord",
  "local-mcp-recovery-precall-guards",
  "LocalMcpFinalCallApprovalRecord",
  "local-mcp-final-call-approvals",
  "LocalMcpLiveCallDryRunRecord",
  "local-mcp-live-call-dry-runs",
  "LocalMcpTypedCommandContractRecord",
  "local-mcp-typed-command-contracts",
  "LocalMcpStatusProbePreflightRecord",
  "local-mcp-status-probe-preflights",
  "LocalMcpConfigLookupPreflightRecord",
  "local-mcp-config-lookup-preflights",
  "LocalMcpConfigReadPolicyRecord",
  "local-mcp-config-read-policies",
  "LocalMcpConfigPathAllowlistRecord",
  "local-mcp-config-path-allowlists",
  "LocalMcpConfigPathResolutionRequestRecord",
  "local-mcp-config-path-resolution-requests",
  "LocalMcpConfigPathResolutionApprovalRecord",
  "local-mcp-config-path-resolution-approvals",
  "LocalMcpConfigPathResolutionDryRunRecord",
  "local-mcp-config-path-resolution-dry-runs",
  "LocalMcpConfigPathMaterializationRequestRecord",
  "local-mcp-config-path-materialization-requests",
  "LocalMcpConfigPathMaterializationApprovalRecord",
  "local-mcp-config-path-materialization-approvals",
  "LocalMcpConfigPathMaterializationFinalDryRunRecord",
  "local-mcp-config-path-materialization-final-dry-runs",
  "LocalMcpConfigPathReadPreflightRequestRecord",
  "local-mcp-config-path-read-preflight-requests",
  "LocalMcpConfigPathReadPreflightApprovalRecord",
  "local-mcp-config-path-read-preflight-approvals",
  "LocalMcpConfigPathReadPreflightFinalDryRunRecord",
  "local-mcp-config-path-read-preflight-final-dry-runs",
  "LocalMcpConfigPathControlledReadRequestRecord",
  "local-mcp-config-path-controlled-read-requests",
  "LocalMcpConfigPathControlledReadApprovalRecord",
  "local-mcp-config-path-controlled-read-approvals",
  "LocalMcpConfigPathControlledReadFinalDryRunRecord",
  "local-mcp-config-path-controlled-read-final-dry-runs",
  "LocalMcpConfigPathSealedReadRequestRecord",
  "local-mcp-config-path-sealed-read-requests",
  "LocalMcpConfigPathSealedReadApprovalRecord",
  "local-mcp-config-path-sealed-read-approvals",
  "LocalMcpConfigPathSealedReadFinalDryRunRecord",
  "local-mcp-config-path-sealed-read-final-dry-runs",
  "LocalMcpConfigPathSealedContentPreflightRecord",
  "local-mcp-config-path-sealed-content-preflights",
  "LocalMcpConfigPathSealedContentFinalDryRunRecord",
  "local-mcp-config-path-sealed-content-final-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadApprovalRecord",
  "local-mcp-config-path-sealed-config-content-read-approvals",
  "LocalMcpConfigPathSealedConfigContentReadFinalDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-final-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadExecutionPreflightRecord",
  "local-mcp-config-path-sealed-config-content-read-execution-preflights",
  "LocalMcpConfigPathSealedConfigContentReadAuditRecoveryPreexecutionRecord",
  "local-mcp-config-path-sealed-config-content-read-audit-recovery-preexecutions",
  "LocalMcpConfigPathSealedConfigContentReadFinalApprovalRecord",
  "local-mcp-config-path-sealed-config-content-read-final-approvals",
  "LocalMcpConfigPathSealedConfigContentReadFinalExecutionDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-final-execution-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadRedactionSchemaDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-redaction-schema-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadParseHashDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-parse-hash-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadContentShapePolicyDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-content-shape-policy-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadStructuralIntentDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-structural-intent-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadFieldInventoryDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-field-inventory-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadKeyPresenceDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-key-presence-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadKeyRequirementDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-key-requirement-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadKeyValueShapeDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-key-value-shape-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadValueContractDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-value-contract-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadValueRedactionMapDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-value-redaction-map-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadSchemaKeyMapDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-schema-key-map-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadSchemaBindingDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-schema-binding-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationPlanDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-plan-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureCoverageDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-coverage-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureCoverageReportDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-coverage-report-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureReportArchiveDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-report-archive-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureArchiveRetentionDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-archive-retention-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReviewDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-review-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionSignoffDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-signoff-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionSignoffFinalizationDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-signoff-finalization-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleaseGateDryRunRecord",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-gate-dry-runs",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleaseApprovalDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationGateDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationApprovalDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationFinalizationDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseGateDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseApprovalDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseFinalizationDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseCompletionReviewDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseClosureReviewDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseClosureApprovalDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseClosureFinalizationDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseClosureCompletionReviewDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseClosureReleaseReadinessDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseClosureReleaseApprovalDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseClosureReleaseFinalizationDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseClosureReleaseCompletionReviewDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseClosureReleaseReleaseReadinessDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseClosureReleaseReleaseApprovalDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseClosureReleaseReleaseFinalizationDryRunRecord",
  "LocalMcpConfigPathSealedConfigContentReadSchemaValidationFixtureRetentionReleasePublicationReleaseClosureReleaseReleaseCompletionReviewDryRunRecord",
  "ReplacementAppFoundationScorecard",
  "replacement_app_foundation_scorecard_read_only",
  "ReplacementAppWorkQueue",
  "replacement_app_work_queue_read_only",
  "ReplacementAppShipReadiness",
  "replacement_app_ship_readiness_read_only",
  "SidecarReadinessBoard",
  "sidecar_readiness_board_read_only",
  "SidecarLaunchPolicyManifest",
  "sidecar_launch_policy_manifest_read_only",
  "SidecarHealthPacketConsole",
  "sidecar_health_packet_console_read_only",
  "RuntimeSidecarProcessSnapshotRecord",
  "RuntimeSidecarProcessTargetSnapshot",
  "runtime_sidecar_process_snapshot_recorded",
  "UiUxTestMatrix",
  "ui_ux_test_matrix_read_only",
  "CodexHermesRunViewDashboard",
  "codex_hermes_run_view_dashboard_read_only",
  "postmortem-failures",
  "failure_postmortem_count",
  "postmortem-timeouts",
  "timeout_postmortem_count",
  "CodexHermesRunViewEvidenceSummary",
  "list_codex_lead_orchestration_records",
  "codex_orchestration_count",
  "hermes_inventory_count",
  "hermes_assist_count",
  "hermes_assist_failure_count",
  "hermes_assist_timeout_count",
  "latest_hermes_assist_status",
  "latest_hermes_assist_postmortem_status",
  "agent_session_failure_count",
  "latest_agent_postmortem_status",
  "unlocked_agent_session_run_view_summary",
  "unlocked_agent_session_is_postmortem",
  "hermes_assist_is_postmortem",
  "transcript_evidence_preview",
  "stdout_transcript_found",
  "stderr_transcript_line_count",
  "transcript_evidence_ready",
  "stdout_preview_source",
  "stderr_preview_source",
  "agent_run_postmortem_waiting",
  "evidence_summary_count",
  "evidence_summaries",
  "codex_orchestration_run_view_summary",
  "hermes_inventory_run_view_summary",
  "hermes_assist_run_view_summary",
  "record_process_spawn_enabled",
  "CodexHermesRunDetailTimeline",
  "codex_hermes_run_detail_timeline_read_only",
  "CodexHermesRunSelectionComparison",
  "codex_hermes_run_selection_comparison_read_only",
  "CodexHermesRunEvidenceDiffBoard",
  "codex_hermes_run_evidence_diff_board_read_only",
  "CodexHermesRunReconciliationChecklist",
  "codex_hermes_run_reconciliation_checklist_read_only",
  "CodexHermesRunReconciliationActionPlan",
  "codex_hermes_run_reconciliation_action_plan_read_only",
  "CodexHermesRunEvidenceAttachmentPreview",
  "codex_hermes_run_evidence_attachment_preview_read_only",
  "CodexHermesRunEvidenceAttachmentApprovalPacket",
  "codex_hermes_run_evidence_attachment_approval_packet_read_only",
  "CodexHermesRunEvidenceIntakeWorkbench",
  "codex_hermes_run_evidence_intake_workbench_read_only",
  "CodexHermesRunEvidenceValidationSummary",
  "codex_hermes_run_evidence_validation_summary_read_only",
  "CodexHermesRunEvidenceOperatorConfirmationDryRuns",
  "codex_hermes_run_evidence_operator_confirmation_dry_runs_read_only",
  "StenoPetCompanionDashboard",
  "steno_pet_companion_dashboard_read_only",
  "TerminalProcessLaneDashboard",
  "terminal_process_lane_dashboard_read_only",
  "ApprovalEvidenceSpineDashboard",
  "approval_evidence_spine_dashboard_read_only",
  "DesktopEnvironmentSnapshotRecord",
  "desktop_environment_snapshot_recorded",
  "desktop_environment_snapshots_dir",
  "DesktopReadOnlyCapabilitySnapshotRecord",
  "desktop_read_only_capability_snapshot_recorded",
  "desktop_read_only_capability_snapshots_dir",
  "EvidenceDurabilityManifestRecord",
  "evidence_durability_manifest_recorded",
  "evidence_durability_manifests_dir",
  "stable_local_evidence_hash",
  "path_probe_enabled: true",
  "latest_desktop_environment_snapshot_fresh",
  "latest_desktop_environment_ydotool_socket_is_socket",
  "latest_desktop_read_only_capability_window_inventory_ready",
  "LinuxDesktopControlReadinessDashboard",
  "linux_desktop_control_readiness_dashboard_read_only",
  "DesktopCaptureActionApprovalPolicyDashboard",
  "desktop_capture_action_approval_policy_dashboard_read_only",
  "DesktopCaptureActionApprovalRecord",
  "desktop_capture_action_approval_records_read_only",
  "DesktopCaptureActionOperatorConfirmationDryRun",
  "desktop_capture_action_operator_confirmation_dry_runs_read_only",
  "DesktopCaptureActionFinalPreActionDryRun",
  "desktop_capture_action_final_preaction_dry_runs_read_only",
  "DesktopActionSafetySummary",
  "desktop_action_safety_summary_read_only",
  "LinuxDesktopReadinessReleaseChecklist",
  "linux_desktop_readiness_release_checklist_read_only",
  "FirstClassMcpDashboard",
  "first_class_mcp_dashboard_read_only",
  "WorkspaceEditorNavigationLane",
  "workspace_editor_navigation_lane_read_only",
  "WorkspaceEditorShellLayout",
  "workspace_editor_shell_layout_read_only",
  "WorkspaceEditorShellBindings",
  "workspace_editor_shell_bindings_read_only",
  "WorkspaceEditorShellFocusModel",
  "workspace_editor_shell_focus_model_read_only",
  "WorkspaceEditorKeyboardNavigationMap",
  "workspace_editor_keyboard_navigation_map_read_only",
  "WorkspaceEditorCommandPaletteMap",
  "workspace_editor_command_palette_map_read_only",
  "WorkspaceEditorCommandSearchMap",
  "workspace_editor_command_search_map_read_only",
  "WorkspaceFilesDashboard",
  "workspace_files_dashboard_read_only",
  "WorkspaceExplorerSnapshot",
  "workspace_explorer_snapshot_read_only",
  "WorkspaceEditPlan",
  "workspace_edit_save_preview_read_only",
  "VeritasModulesDashboard",
  "veritas_modules_dashboard_read_only",
  "SswpStatusPanel",
  "sswp_status_panel_read_only",
  "BundledDocsPanel",
  "docs_open_bundled_in_app",
  "AboutPanel",
  "about_open_bundled_in_app",
  "CommandPalettePanel",
  "command_palette_open_read_only",
  "TerminalPanelToggle",
  "terminal_toggle_panel_visible_read_only",
  "EditorFindPanel",
  "editor_find_panel_read_only",
  "StenoSearchRequest",
  "StenoSearchResult",
  "StenoSearchPanel",
  "steno_search_panel_read_only",
  "steno_search_dirs",
  "steno_search_file_allowed",
  "steno_search_snippet",
  "steno_recent_postmortem_results",
  "steno_recent_postmortem_read_only",
  "agent-postmortem",
  "hermes-assist-postmortem",
  "steno_search_reads_approved_evidence_records_without_live_mcp",
  "ToolbarActionReadinessPanel",
  "toolbar_action_blocked_readiness",
  "FirstClassIntegrationLaunchpad",
  "first_class_integration_launchpad_read_only",
  "GatedActionReleaseBoard",
  "gated_action_release_board_read_only",
  "GatedAdapterReleaseQueue",
  "gated_adapter_release_queue_ready_for_packet",
  "create_gated_adapter_release_packet_stub",
  "gated-adapter-release-queue",
  "WorkspaceMutationWorkbench",
  "workspace_mutation_workbench_read_only",
  "TerminalProcessWorkbench",
  "terminal_process_workbench_read_only",
  "SecurityShieldWorkbench",
  "security_shield_workbench_read_only",
  "NativeShellPairingWorkbench",
  "native_shell_pairing_workbench_read_only",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-approval-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-gate-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-approval-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-finalization-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-gate-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-approval-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-finalization-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-completion-review-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-review-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-approval-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-finalization-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-completion-review-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-readiness-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-approval-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-finalization-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-completion-review-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-readiness-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-approval-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization-dry-runs",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-completion-review-dry-runs",
  "agent_transcript_session_recorded",
  "execution_enabled: false",
]) {
  if (!rustCommandsSource.includes(stateNeedle)) {
    throw new Error(`Rust evidence persistence missing ${stateNeedle}.`);
  }
}

for (const elementId of [
  "command-resolution",
  "task-run-ledger",
  "create-task-run-btn",
  "approval-ledger",
  "create-approval-btn",
  "resolve-approval-btn",
  "artifact-preview",
  "sandbox-policy-list",
  "sandbox-gate-decision",
  "prepare-runner-btn",
  "runner-readiness",
  "runner-ledger",
  "record-runner-evidence-spine-btn",
  "runner-evidence-spine-summary",
  "runner-evidence-spine-count",
  "runner-evidence-spine-ledger",
  "run-supervised-runtime-smoke-btn",
  "supervised-runtime-smoke-summary",
  "supervised-runtime-smoke-count",
  "supervised-runtime-smoke-ledger",
  "create-joint-plan-btn",
  "joint-plan-summary",
  "joint-plan-ledger",
  "create-joint-runtime-run-packet-btn",
  "joint-runtime-run-packet-summary",
  "joint-runtime-run-packet-count",
  "joint-runtime-run-packet-ledger",
  "create-agent-inventory-btn",
  "agent-inventory-summary",
  "agent-inventory-count",
  "agent-inventory-ledger",
  "create-integration-readiness-btn",
  "integration-readiness-summary",
  "integration-readiness-count",
  "integration-readiness-ledger",
  "refresh-foundation-scorecard-btn",
  "foundation-scorecard-summary",
  "foundation-scorecard-count",
  "foundation-scorecard-list",
  "refresh-foundation-work-queue-btn",
  "foundation-work-queue-summary",
  "foundation-work-queue-count",
  "foundation-work-queue-list",
  "refresh-command-surface-collapse-board-btn",
  "command-surface-collapse-board-summary",
  "command-surface-collapse-board-count",
  "command-surface-collapse-board-list",
  "refresh-ui-ux-test-matrix-btn",
  "ui-ux-test-matrix-summary",
  "ui-ux-test-matrix-count",
  "ui-ux-test-matrix-list",
  "refresh-ship-readiness-btn",
  "ship-readiness-summary",
  "ship-readiness-count",
  "ship-readiness-list",
  "refresh-sidecar-readiness-btn",
  "sidecar-readiness-summary",
  "sidecar-readiness-count",
  "sidecar-readiness-list",
  "refresh-sidecar-launch-policy-btn",
  "sidecar-launch-policy-summary",
  "sidecar-launch-policy-count",
  "sidecar-launch-policy-list",
  "refresh-sidecar-health-packet-btn",
  "sidecar-health-packet-summary",
  "sidecar-health-packet-count",
  "sidecar-health-packet-list",
  "run-runtime-probes-btn",
  "record-runtime-launch-packets-btn",
  "runtime-probe-summary",
  "runtime-probe-count",
  "runtime-probe-list",
  "runtime-launch-packet-count",
  "runtime-launch-packet-list",
  "refresh-workspace-edit-family-btn",
  "workspace-edit-family-summary",
  "workspace-edit-family-count",
  "workspace-edit-family-list",
  "refresh-workspace-files-dashboard-btn",
  "workspace-files-dashboard-summary",
  "workspace-files-dashboard-count",
  "workspace-files-dashboard-list",
  "refresh-workspace-explorer-btn",
  "workspace-explorer-summary",
  "workspace-explorer-count",
  "workspace-explorer-tree",
  "workspace-explorer-preview",
  "refresh-veritas-modules-dashboard-btn",
  "veritas-modules-dashboard-summary",
  "veritas-modules-dashboard-count",
  "veritas-modules-dashboard-list",
  "refresh-codex-hermes-run-view-btn",
  "codex-hermes-run-view-summary",
  "codex-hermes-run-view-count",
  "codex-hermes-run-view-list",
  "refresh-codex-hermes-run-detail-timeline-btn",
  "codex-hermes-run-detail-timeline-summary",
  "codex-hermes-run-detail-timeline-count",
  "codex-hermes-run-detail-timeline-list",
  "refresh-codex-hermes-run-selection-comparison-btn",
  "codex-hermes-run-selection-comparison-summary",
  "codex-hermes-run-selection-comparison-count",
  "codex-hermes-run-selection-comparison-list",
  "refresh-codex-hermes-run-evidence-diff-board-btn",
  "codex-hermes-run-evidence-diff-board-summary",
  "codex-hermes-run-evidence-diff-board-count",
  "codex-hermes-run-evidence-diff-board-list",
  "refresh-codex-hermes-run-reconciliation-checklist-btn",
  "codex-hermes-run-reconciliation-checklist-summary",
  "codex-hermes-run-reconciliation-checklist-count",
  "codex-hermes-run-reconciliation-checklist-list",
  "refresh-codex-hermes-run-reconciliation-action-plan-btn",
  "codex-hermes-run-reconciliation-action-plan-summary",
  "codex-hermes-run-reconciliation-action-plan-count",
  "codex-hermes-run-reconciliation-action-plan-list",
  "refresh-codex-hermes-run-evidence-attachment-preview-btn",
  "codex-hermes-run-evidence-attachment-preview-summary",
  "codex-hermes-run-evidence-attachment-preview-count",
  "codex-hermes-run-evidence-attachment-preview-list",
  "refresh-codex-hermes-run-evidence-attachment-approval-packet-btn",
  "codex-hermes-run-evidence-attachment-approval-packet-summary",
  "codex-hermes-run-evidence-attachment-approval-packet-count",
  "codex-hermes-run-evidence-attachment-approval-packet-list",
  "refresh-codex-hermes-run-evidence-intake-workbench-btn",
  "codex-hermes-run-evidence-intake-workbench-summary",
  "codex-hermes-run-evidence-intake-workbench-count",
  "codex-hermes-run-evidence-intake-workbench-list",
  "refresh-codex-hermes-run-evidence-validation-summary-btn",
  "codex-hermes-run-evidence-validation-summary-summary",
  "codex-hermes-run-evidence-validation-summary-count",
  "codex-hermes-run-evidence-validation-summary-list",
  "refresh-codex-hermes-run-evidence-operator-confirmation-dry-runs-btn",
  "codex-hermes-run-evidence-operator-confirmation-dry-runs-summary",
  "codex-hermes-run-evidence-operator-confirmation-dry-runs-count",
  "codex-hermes-run-evidence-operator-confirmation-dry-runs-list",
  "refresh-workspace-editor-navigation-btn",
  "workspace-editor-navigation-summary",
  "workspace-editor-navigation-count",
  "workspace-editor-navigation-list",
  "refresh-workspace-editor-shell-btn",
  "workspace-editor-shell-summary",
  "workspace-editor-shell-count",
  "workspace-editor-shell-list",
  "refresh-workspace-editor-bindings-btn",
  "workspace-editor-bindings-summary",
  "workspace-editor-bindings-count",
  "workspace-editor-bindings-list",
  "refresh-workspace-editor-focus-btn",
  "workspace-editor-focus-summary",
  "workspace-editor-focus-count",
  "workspace-editor-focus-list",
  "refresh-workspace-editor-keys-btn",
  "workspace-editor-keys-summary",
  "workspace-editor-keys-count",
  "workspace-editor-keys-list",
  "refresh-workspace-editor-palette-btn",
  "workspace-editor-palette-summary",
  "workspace-editor-palette-count",
  "workspace-editor-palette-list",
  "refresh-workspace-editor-search-btn",
  "workspace-editor-search-summary",
  "workspace-editor-search-count",
  "workspace-editor-search-list",
  "create-local-mcp-contract-btn",
  "local-mcp-contract-summary",
  "local-mcp-contract-count",
  "local-mcp-contract-ledger",
  "refresh-first-class-mcp-dashboard-btn",
  "first-class-mcp-dashboard-summary",
  "first-class-mcp-dashboard-count",
  "first-class-mcp-dashboard-list",
  "refresh-steno-pet-companion-dashboard-btn",
  "steno-pet-companion-dashboard-summary",
  "steno-pet-companion-dashboard-count",
  "steno-pet-companion-dashboard-list",
  "refresh-terminal-process-lane-dashboard-btn",
  "terminal-process-lane-dashboard-summary",
  "terminal-process-lane-dashboard-count",
  "terminal-process-lane-dashboard-list",
  "refresh-approval-evidence-spine-dashboard-btn",
  "approval-evidence-spine-dashboard-summary",
  "approval-evidence-spine-dashboard-count",
  "approval-evidence-spine-dashboard-list",
  "refresh-linux-desktop-control-readiness-dashboard-btn",
  "linux-desktop-control-readiness-dashboard-summary",
  "linux-desktop-control-readiness-dashboard-count",
  "linux-desktop-control-readiness-dashboard-list",
  "refresh-desktop-capture-action-approval-policy-dashboard-btn",
  "desktop-capture-action-approval-policy-dashboard-summary",
  "desktop-capture-action-approval-policy-dashboard-count",
  "desktop-capture-action-approval-policy-dashboard-list",
  "refresh-desktop-capture-action-approval-records-btn",
  "desktop-capture-action-approval-records-summary",
  "desktop-capture-action-approval-records-count",
  "desktop-capture-action-approval-records-list",
  "refresh-desktop-capture-action-operator-confirmation-dry-runs-btn",
  "desktop-capture-action-operator-confirmation-dry-runs-summary",
  "desktop-capture-action-operator-confirmation-dry-runs-count",
  "desktop-capture-action-operator-confirmation-dry-runs-list",
  "refresh-desktop-capture-action-final-preaction-dry-runs-btn",
  "desktop-capture-action-final-preaction-dry-runs-summary",
  "desktop-capture-action-final-preaction-dry-runs-count",
  "desktop-capture-action-final-preaction-dry-runs-list",
  "refresh-desktop-action-safety-summary-btn",
  "desktop-action-safety-summary-summary",
  "desktop-action-safety-summary-count",
  "desktop-action-safety-summary-list",
  "refresh-linux-desktop-readiness-release-checklist-btn",
  "linux-desktop-readiness-release-checklist-summary",
  "linux-desktop-readiness-release-checklist-count",
  "linux-desktop-readiness-release-checklist-list",
  "create-local-mcp-preflight-btn",
  "local-mcp-preflight-summary",
  "local-mcp-preflight-count",
  "local-mcp-preflight-ledger",
  "record-agent-event-btn",
  "agent-event-count",
  "agent-event-preview",
  "create-workspace-lease-btn",
  "workspace-lease-summary",
  "workspace-lease-ledger",
  "create-workspace-inspection-btn",
  "workspace-inspection-summary",
  "workspace-inspection-ledger",
  "create-workspace-preview-btn",
  "workspace-preview-summary",
  "workspace-preview-ledger",
  "create-tree-metadata-btn",
  "tree-metadata-summary",
  "tree-metadata-ledger",
  "create-file-preview-btn",
  "file-preview-summary",
  "file-preview-ledger",
  "file-preview-text",
  "create-editor-tab-btn",
  "editor-tab-summary",
  "editor-tab-ledger",
  "editor-tab-buffer",
  "create-edit-intent-btn",
  "create-save-gate-btn",
  "edit-preflight-summary",
  "edit-preflight-count",
  "edit-preflight-ledger",
  "create-buffer-policy-btn",
  "create-save-policy-btn",
  "write-policy-summary",
  "write-policy-count",
  "write-policy-ledger",
  "create-write-approval-btn",
  "write-approval-summary",
  "write-approval-count",
  "write-approval-ledger",
  "create-buffer-draft-btn",
  "buffer-draft-summary",
  "buffer-draft-count",
  "buffer-draft-ledger",
  "create-dirty-preflight-btn",
  "dirty-preflight-summary",
  "dirty-preflight-count",
  "dirty-preflight-ledger",
  "create-mutable-transaction-btn",
  "mutable-transaction-summary",
  "mutable-transaction-count",
  "mutable-transaction-ledger",
  "create-materialization-policy-btn",
  "materialization-policy-summary",
  "materialization-policy-count",
  "materialization-policy-ledger",
  "create-buffer-attachment-btn",
  "buffer-attachment-summary",
  "buffer-attachment-count",
  "buffer-attachment-ledger",
  "create-editable-state-preflight-btn",
  "editable-state-preflight-summary",
  "editable-state-preflight-count",
  "editable-state-preflight-ledger",
  "create-view-binding-btn",
  "view-binding-summary",
  "view-binding-count",
  "view-binding-ledger",
  "create-text-viewport-btn",
  "text-viewport-summary",
  "text-viewport-count",
  "text-viewport-ledger",
  "create-text-attachment-btn",
  "text-attachment-summary",
  "text-attachment-count",
  "text-attachment-ledger",
  "create-text-model-handle-btn",
  "text-model-handle-summary",
  "text-model-handle-count",
  "text-model-handle-ledger",
  "create-text-model-storage-btn",
  "text-model-storage-summary",
  "text-model-storage-count",
  "text-model-storage-ledger",
  "create-text-model-snapshot-btn",
  "text-model-snapshot-summary",
  "text-model-snapshot-count",
  "text-model-snapshot-ledger",
  "prepare-runner-adapter-btn",
  "runner-adapter-summary",
  "runner-adapter-ledger",
  "build-process-plan-btn",
  "process-plan-summary",
  "process-plan-ledger",
  "init-streams-btn",
  "stream-init-summary",
  "stream-init-ledger",
  "create-lifecycle-btn",
  "lifecycle-summary",
  "lifecycle-ledger",
  "create-control-policy-btn",
  "control-policy-summary",
  "control-policy-ledger",
  "create-supervisor-preflight-btn",
  "supervisor-preflight-summary",
  "supervisor-preflight-ledger",
  "create-supervisor-heartbeat-btn",
  "supervisor-heartbeat-summary",
  "supervisor-heartbeat-ledger",
  "create-supervisor-exit-summary-btn",
  "supervisor-exit-summary",
  "supervisor-exit-summary-ledger",
  "create-output-tail-summary-btn",
  "output-tail-summary",
  "output-tail-summary-ledger",
  "create-transcript-bundle-btn",
  "transcript-bundle-summary",
  "transcript-bundle-ledger",
  "create-export-policy-btn",
  "export-policy-summary",
  "export-policy-ledger",
  "create-protection-policy-btn",
  "protection-policy-summary",
  "protection-policy-ledger",
  "create-local-mcp-health-btn",
  "local-mcp-health-summary",
  "local-mcp-health-ledger",
  "create-local-mcp-contract-btn",
  "local-mcp-contract-summary",
  "local-mcp-contract-ledger",
  "create-local-mcp-preflight-btn",
  "local-mcp-preflight-summary",
  "local-mcp-preflight-ledger",
  "create-local-mcp-discovery-policy-btn",
  "local-mcp-discovery-policy-summary",
  "local-mcp-discovery-policy-ledger",
  "create-local-mcp-gated-call-policy-btn",
  "local-mcp-gated-call-policy-summary",
  "local-mcp-gated-call-policy-ledger",
  "create-local-mcp-call-approval-audit-btn",
  "local-mcp-call-approval-audit-summary",
  "local-mcp-call-approval-audit-ledger",
  "create-local-mcp-consent-approval-btn",
  "local-mcp-consent-approval-summary",
  "local-mcp-consent-approval-ledger",
  "create-local-mcp-audit-outcome-btn",
  "local-mcp-audit-outcome-summary",
  "local-mcp-audit-outcome-ledger",
  "create-local-mcp-recovery-precall-guard-btn",
  "local-mcp-recovery-precall-guard-summary",
  "local-mcp-recovery-precall-guard-ledger",
  "create-local-mcp-final-call-approval-btn",
  "local-mcp-final-call-approval-summary",
  "local-mcp-final-call-approval-ledger",
  "create-local-mcp-live-call-dry-run-btn",
  "local-mcp-live-call-dry-run-summary",
  "local-mcp-live-call-dry-run-ledger",
  "create-local-mcp-typed-command-contract-btn",
  "local-mcp-typed-command-contract-summary",
  "local-mcp-typed-command-contract-ledger",
  "create-local-mcp-status-probe-preflight-btn",
  "local-mcp-status-probe-preflight-summary",
  "local-mcp-status-probe-preflight-ledger",
  "create-local-mcp-config-lookup-preflight-btn",
  "local-mcp-config-lookup-preflight-summary",
  "local-mcp-config-lookup-preflight-ledger",
  "create-local-mcp-config-read-policy-btn",
  "local-mcp-config-read-policy-summary",
  "local-mcp-config-read-policy-ledger",
  "create-local-mcp-config-path-allowlist-btn",
  "local-mcp-config-path-allowlist-summary",
  "local-mcp-config-path-allowlist-ledger",
  "create-local-mcp-config-path-resolution-request-btn",
  "local-mcp-config-path-resolution-request-summary",
  "local-mcp-config-path-resolution-request-ledger",
  "create-local-mcp-config-path-resolution-approval-btn",
  "local-mcp-config-path-resolution-approval-summary",
  "local-mcp-config-path-resolution-approval-ledger",
  "create-local-mcp-config-path-resolution-dry-run-btn",
  "local-mcp-config-path-resolution-dry-run-summary",
  "local-mcp-config-path-resolution-dry-run-ledger",
  "create-local-mcp-config-path-materialization-request-btn",
  "local-mcp-config-path-materialization-request-summary",
  "local-mcp-config-path-materialization-request-ledger",
  "create-local-mcp-config-path-materialization-approval-btn",
  "local-mcp-config-path-materialization-approval-summary",
  "local-mcp-config-path-materialization-approval-ledger",
  "create-local-mcp-config-path-materialization-final-dry-run-btn",
  "local-mcp-config-path-materialization-final-dry-run-summary",
  "local-mcp-config-path-materialization-final-dry-run-ledger",
  "create-local-mcp-config-path-read-preflight-request-btn",
  "local-mcp-config-path-read-preflight-request-summary",
  "local-mcp-config-path-read-preflight-request-ledger",
  "create-local-mcp-config-path-read-preflight-approval-btn",
  "local-mcp-config-path-read-preflight-approval-summary",
  "local-mcp-config-path-read-preflight-approval-ledger",
  "create-local-mcp-config-path-read-preflight-final-dry-run-btn",
  "local-mcp-config-path-read-preflight-final-dry-run-summary",
  "local-mcp-config-path-read-preflight-final-dry-run-ledger",
  "create-local-mcp-config-path-controlled-read-request-btn",
  "local-mcp-config-path-controlled-read-request-summary",
  "local-mcp-config-path-controlled-read-request-ledger",
  "create-local-mcp-config-path-controlled-read-approval-btn",
  "local-mcp-config-path-controlled-read-approval-summary",
  "local-mcp-config-path-controlled-read-approval-ledger",
  "create-local-mcp-config-path-controlled-read-final-dry-run-btn",
  "local-mcp-config-path-controlled-read-final-dry-run-summary",
  "local-mcp-config-path-controlled-read-final-dry-run-ledger",
  "create-local-mcp-config-path-sealed-read-request-btn",
  "local-mcp-config-path-sealed-read-request-summary",
  "local-mcp-config-path-sealed-read-request-ledger",
  "create-local-mcp-config-path-sealed-read-approval-btn",
  "local-mcp-config-path-sealed-read-approval-summary",
  "local-mcp-config-path-sealed-read-approval-ledger",
  "create-local-mcp-config-path-sealed-read-final-dry-run-btn",
  "local-mcp-config-path-sealed-read-final-dry-run-summary",
  "local-mcp-config-path-sealed-read-final-dry-run-ledger",
  "create-local-mcp-config-path-sealed-content-preflight-btn",
  "local-mcp-config-path-sealed-content-preflight-summary",
  "local-mcp-config-path-sealed-content-preflight-ledger",
  "create-local-mcp-config-path-sealed-content-final-dry-run-btn",
  "local-mcp-config-path-sealed-content-final-dry-run-summary",
  "local-mcp-config-path-sealed-content-final-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-approval-btn",
  "local-mcp-config-path-sealed-config-content-read-approval-summary",
  "local-mcp-config-path-sealed-config-content-read-approval-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-final-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-final-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-final-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-execution-preflight-btn",
  "local-mcp-config-path-sealed-config-content-read-execution-preflight-summary",
  "local-mcp-config-path-sealed-config-content-read-execution-preflight-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-audit-recovery-preexecution-btn",
  "local-mcp-config-path-sealed-config-content-read-audit-recovery-preexecution-summary",
  "local-mcp-config-path-sealed-config-content-read-audit-recovery-preexecution-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-final-approval-btn",
  "local-mcp-config-path-sealed-config-content-read-final-approval-summary",
  "local-mcp-config-path-sealed-config-content-read-final-approval-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-final-execution-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-final-execution-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-final-execution-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-redaction-schema-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-redaction-schema-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-redaction-schema-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-parse-hash-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-parse-hash-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-parse-hash-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-content-shape-policy-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-content-shape-policy-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-content-shape-policy-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-structural-intent-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-structural-intent-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-structural-intent-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-field-inventory-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-field-inventory-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-field-inventory-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-key-presence-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-key-presence-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-key-presence-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-key-requirement-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-key-requirement-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-key-requirement-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-key-value-shape-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-key-value-shape-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-key-value-shape-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-value-contract-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-value-contract-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-value-contract-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-value-redaction-map-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-value-redaction-map-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-value-redaction-map-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-schema-key-map-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-schema-key-map-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-key-map-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-schema-binding-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-schema-binding-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-binding-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-plan-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-plan-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-plan-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-coverage-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-coverage-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-coverage-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-coverage-report-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-coverage-report-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-coverage-report-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-report-archive-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-report-archive-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-report-archive-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-archive-retention-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-archive-retention-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-archive-retention-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-review-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-review-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-review-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-signoff-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-signoff-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-signoff-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-signoff-finalization-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-signoff-finalization-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-signoff-finalization-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-gate-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-gate-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-gate-dry-run-ledger",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-approval-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-gate-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-approval-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-finalization-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-gate-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-approval-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-finalization-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-completion-review-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-review-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-approval-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-finalization-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-completion-review-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-readiness-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-approval-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-finalization-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-completion-review-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-readiness-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-approval-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization-dry-run-btn",
  "create-local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-completion-review-dry-run-btn",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-approval-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-gate-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-approval-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-finalization-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-gate-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-approval-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-finalization-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-completion-review-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-review-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-approval-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-finalization-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-completion-review-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-readiness-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-approval-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-finalization-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-completion-review-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-readiness-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-approval-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-completion-review-dry-run-summary",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-approval-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-gate-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-approval-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-finalization-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-gate-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-approval-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-finalization-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-completion-review-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-review-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-approval-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-finalization-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-completion-review-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-readiness-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-approval-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-finalization-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-completion-review-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-readiness-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-approval-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-finalization-dry-run-ledger",
  "local-mcp-config-path-sealed-config-content-read-schema-validation-fixture-retention-release-publication-release-closure-release-release-completion-review-dry-run-ledger",
  "refresh-bundled-docs-panel-btn",
  "bundled-docs-panel-summary",
  "bundled-docs-panel-count",
  "bundled-docs-panel-list",
  "refresh-about-panel-btn",
  "about-panel-summary",
  "about-panel-count",
  "about-panel-list",
  "refresh-command-palette-panel-btn",
  "command-palette-panel-summary",
  "command-palette-panel-count",
  "command-palette-panel-list",
  "refresh-terminal-toggle-panel-btn",
  "terminal-toggle-panel-summary",
  "terminal-toggle-panel-count",
  "terminal-toggle-panel-list",
  "refresh-find-panel-btn",
  "find-panel-summary",
  "find-panel-count",
  "find-panel-list",
  "refresh-sswp-status-panel-btn",
  "sswp-status-panel-summary",
  "sswp-status-panel-count",
  "sswp-status-panel-list",
  "refresh-steno-search-panel-btn",
  "steno-search-panel-summary",
  "steno-search-panel-count",
  "steno-search-query",
  "steno-search-run-btn",
  "steno-search-panel-list",
  "run-agent-transcript-session-btn",
  "agent-transcript-session-summary",
  "agent-transcript-session-ledger",
  "agent-transcript-session-count",
  "toolbar-action-readiness-summary",
  "toolbar-action-readiness-count",
  "toolbar-action-readiness-list",
]) {
  if (!frontendSource.includes(elementId)) {
    throw new Error(`Frontend missing evidence UI element ${elementId}.`);
  }
}

for (const frontendNeedle of [
  "toolbarDryRunButton",
  "resolveCommandStub(command.id)",
  "loadBundledDocsPanel",
  "loadAboutPanel",
  "loadCommandPalettePanel",
  "loadTerminalTogglePanel",
  "loadFindPanel",
  "loadSswpStatusPanel",
  "loadStenoSearchPanel",
  "invoke(\"steno_search\", {",
  "results = panel.results ?? []",
  "postmortems = panel.recent_postmortem_results ?? []",
  "Recent Codex/Hermes postmortems",
  "postmortems=",
  "stenoSearchQueryInput",
  "stenoSearchRunBtn",
  "loadToolbarActionReadiness",
  "loadFirstClassIntegrationLaunchpad",
  "loadGatedActionReleaseBoard",
  "renderToolbarActionReadiness",
  "renderFirstClassIntegrationLaunchpad",
  "renderGatedActionReleaseBoard",
  "loadCommandSurfaceCollapseBoard",
  "renderCommandSurfaceCollapseBoard",
  "loadUiUxTestMatrix",
  "renderUiUxTestMatrix",
  "loadReplacementAppShipReadiness",
  "renderReplacementAppShipReadiness",
  "loadSidecarReadinessBoard",
  "renderSidecarReadinessBoard",
  "loadSidecarLaunchPolicyManifest",
  "renderSidecarLaunchPolicyManifest",
  "loadSidecarHealthPacketConsole",
  "recordRuntimeSidecarProcessSnapshot",
  "recordRuntimeSidecarProcessSnapshot(\"gravity-omega-first-class-mcp-dashboard\")",
  "Runtime process:",
  "runtime_target_id",
  "runtime_process_snapshot_count",
  "running_runtime_lane_count",
  "mcp_runtime_process_count",
  "loadRuntimeSidecarProcessSnapshots",
  "renderSidecarHealthPacketConsole",
  "loadRuntimeProbeBoard",
  "runRuntimeDepthProbe",
  "renderRuntimeProbeBoard",
  "runRuntimeProbes",
  "runtime_probe_board",
  "run_runtime_depth_probe",
  "SSWP witness runtime",
  "sswp-cli",
  "createRuntimeLaunchPacket",
  "loadRuntimeLaunchPackets",
  "renderRuntimeLaunchPackets",
  "recordRuntimeLaunchPackets",
  "create_runtime_launch_packet_stub",
  "list_runtime_launch_packets",
  "createCodexLeadOrchestrationRecord",
  "codexLeadOrchestrationBrief",
  "create_codex_lead_orchestration_record",
  "recordPetRuntimeSignal",
  "recordPetRuntimeSnapshotSignal",
  "setPetCompanionRuntimeState",
  "data-pet-state",
  "release_artifact_ready",
  "release_binary_size_bytes",
  "createJointRuntimeRunPacket",
  "loadJointRuntimeRunPackets",
  "renderJointRuntimeRunPacketLedger",
  "recordJointRuntimeRunPacket",
  "create_joint_runtime_run_packet_stub",
  "list_joint_runtime_run_packets",
  "createRunnerEvidenceSpine",
  "loadRunnerEvidenceSpines",
  "renderRunnerEvidenceSpineLedger",
  "recordRunnerEvidenceSpine",
  "create_runner_evidence_spine_stub",
  "list_runner_evidence_spines",
  "runSupervisedRuntimeSmoke",
  "loadSupervisedRuntimeSmokes",
  "renderSupervisedRuntimeSmokeLedger",
  "recordSupervisedRuntimeSmoke",
  "run_supervised_runtime_smoke",
  "list_supervised_runtime_smokes",
  "runAgentTranscriptSession",
  "loadAgentTranscriptSessions",
  "renderAgentTranscriptSessionLedger",
  "recordAgentTranscriptSession",
  "Agent transcript:",
  "agent_transcript_pipe_reader_ready_count",
  "recent_agent_transcript_sessions",
  "run_agent_transcript_session",
  "list_agent_transcript_sessions",
  "loadWorkspaceExplorerSnapshot",
  "renderWorkspaceExplorerSnapshot",
  "workspace_explorer_snapshot",
  "loadWorkspaceEditFamily",
  "renderWorkspaceEditFamily",
  "recordTerminalTranscriptReplay",
  "captureTerminalTranscriptReplay",
  "terminal-stream-completion",
  "terminal-sync-completion",
  "inferSurfaceArea",
  "applyRailArea",
  "aria-pressed",
  "setAgentRailWidth",
  "restoreAgentRailWidth",
  "agent-rail-resizer",
  "aria-valuenow",
  "agent-composer-input",
  "agent-composer-draft-btn",
  "agent-composer-status",
  "setComposerDraftStatus",
  "createComposerTaskRun",
  "agent.composer_draft",
  "bottom-evidence-dock",
  "bottom-dock-resizer",
  "setBottomDockHeight",
  "restoreBottomDockHeight",
  "renderBottomEvidenceDock",
  "refreshBottomEvidenceDock",
  "omega-runtime-evidence-spine-list",
  "omega-runtime-evidence-card",
  "toolbar-search-input",
  "toolbar-search-summary",
  "filterToolbarCommands",
  "renderToolbarRegistry",
  "focusToolbarSearch",
  "Command search focused",
  "event.key.toLowerCase() === \"k\"",
  "command.target_command === \"docs_open\"",
  "command.target_command === \"about_open\"",
  "command.target_command === \"command_palette_open\"",
  "command.target_command === \"terminal_toggle\"",
  "command.target_command === \"editor_find\"",
  "command.target_command === \"sswp_status\"",
  "command.target_command === \"steno_search\"",
  "command.target_command === \"first_class_integration_launchpad\"",
  "command.target_command === \"omega_computer_session\"",
  "command.target_command === \"file_write\"",
  "command.target_command === \"file_save_as\"",
  "command.target_command === \"editor_replace\"",
  "command.target_command === \"terminal_create\"",
  "command.target_command === \"security_shield_action\"",
  "command.target_command === \"devtools_toggle\"",
  "command.target_command === \"mobile_pairing_qr\"",
  "command.state !== \"live\"",
  "Toolbar dry-run failed",
]) {
  if (!frontendSource.includes(frontendNeedle)) {
    throw new Error(`Frontend missing toolbar dry-run wiring ${frontendNeedle}.`);
  }
}

for (const runtimeDepthNeedle of [
  "RuntimeDepthProbeRecord",
  "runtime-depth-probes",
  "runtime_depth_probe_recorded",
  "runtime_depth_hermes_log_preflight",
  "runtime_depth_hermes_capability_probes",
  "RuntimeDepthHermesCapabilityProbe",
  "hermes_skill_count",
  "hermes_mcp_server_count",
  "hermes_hook_count",
  "push_product_evidence_history_dir(&mut items, \"runtime-depth\"",
  "RuntimeSidecarProcessSnapshotRecord",
  "RuntimeSidecarProcessTargetSnapshot",
  "record_runtime_sidecar_process_snapshot",
  "list_runtime_sidecar_process_snapshots",
  "runtime-sidecar-process-snapshots",
  "runtime_sidecar_process_snapshot_recorded",
  "runtime_sidecar_process_targets",
  "first_class_mcp_runtime_target",
  "runtime_target_id",
  "runtime_process_snapshot_count",
  "runtime_process_snapshot_freshness_threshold_ms",
  "latest_runtime_process_snapshot_freshness_status",
  "latest_runtime_process_snapshot_pipe_reader_ready",
  "runtime_snapshot_freshness_status",
  "runtime_snapshot_pipe_reader_ready",
  "runtime_snapshot_partial_output_captured",
  "runtime_snapshot_timed_out",
  "runtime_process_snapshot_waiting",
  "running_runtime_lane_count",
  "mcp_runtime_process_count",
  "pid=,args=",
  "process_control_enabled: false",
  "sidecar_launch_enabled: false",
  "terminal_execution_enabled: false",
  "push_product_evidence_history_dir(&mut items, \"runtime-sidecar-process\"",
  "ProductTerminalTranscriptReplayRecord",
  "product_terminal_blocked_commands_dir",
  "record_product_terminal_blocked_command",
  "list_product_terminal_blocked_commands",
  "product_terminal_command_blocked",
  "record_product_terminal_transcript_replay",
  "list_product_terminal_transcript_replays",
  "product-terminal-transcript-replays",
  "product_terminal_transcript_replay_recorded",
  "ProductTerminalCommandProcessOutput",
  "spawn_product_terminal_pipe_reader",
  "run_product_terminal_command_process",
  "stdout_pipe_reader_enabled",
  "stderr_pipe_reader_enabled",
  "timeout_kill_sent",
  "wait_after_kill_ms",
  "partial_output_captured",
  "recent_process_control_policies",
  "recent_process_exit_summaries",
  "\"terminal-blocked\"",
  "process_spawn_enabled: false",
  "terminal_write_enabled: false",
  "live_tail_enabled: false",
  "process_control_enabled: false",
  "push_product_evidence_history_dir(&mut items, \"terminal-replay\"",
  "SovereignDocsPreviewRecord",
  "record_sovereign_docs_preview",
  "list_sovereign_docs_previews",
  "sovereign-docs-previews",
  "sovereign_docs_preview_recorded",
  "build_sovereign_docs_preview_html",
  "VERITAS Sovereign Docs",
  "pdf_export_enabled: false",
  "network_access_enabled: false",
  "push_product_evidence_history_dir(&mut items, \"sovereign-docs\"",
  "OmegaComputerSessionRecord",
  "OmegaComputerRole",
  "OmegaComputerStage",
  "OmegaComputerWorker",
  "record_omega_computer_session",
  "list_omega_computer_sessions",
  "omega-computer-sessions",
  "omega_computer_session_recorded",
  "omega_computer_roles",
  "omega_computer_stages",
  "omega_computer_workers",
  "specialist_worker_count",
  "active_worker_id",
  "progress_rail_enabled: true",
  "clickable_worker_views: true",
  "DR-01",
  "Deep Research",
  "QA-07",
  "codex_lead_enabled: true",
  "hermes_kimi_assist_enabled: true",
  "pointer_injection_enabled: false",
  "keyboard_injection_enabled: false",
  "target_window_control_enabled: false",
  "terminal_execution_enabled: false",
  "push_product_evidence_history_dir(&mut items, \"omega-computer\"",
  "HermesKimiCapabilityInventoryRecord",
  "record_hermes_kimi_capability_inventory",
  "hermes-kimi-capability-inventories",
  "hermes_kimi_capability_inventory_recorded",
  "hermes_kimi_focus_skills",
  "push_product_evidence_history_dir(&mut items, \"hermes-inventory\"",
  "HermesKimiAssistBriefRecord",
  "record_hermes_kimi_assist_brief",
  "hermes-kimi-assist-briefs",
  "hermes_kimi_assist_brief_recorded",
  "hermes_assist_is_postmortem",
  "hermes-kimi-assist-postmortem",
  "Latest failed/timed-out Hermes/Kimi assist brief",
  "compact_hermes_kimi_assist_query",
  "run_hermes_kimi_assist_process",
  "push_product_evidence_history_dir(&mut items, \"hermes-assist\"",
  "SswpRegistrySnapshotRecord",
  "record_sswp_registry_snapshot",
  "list_sswp_registry_snapshots",
  "sswp-registry-snapshots",
  "run_sswp_registry_command(&[\"registry\", \"list\"]",
  "run_sswp_registry_command(&[\"registry\", \"risky\"",
  "parse_sswp_registry_nodes",
  "witness_enabled: false",
  "verify_enabled: false",
  "push_product_evidence_history_dir(&mut items, \"sswp-registry\"",
  "CodexLeadOrchestrationRecord",
  "CodexLeadDelegationLane",
  "codex_lead_orchestrations_dir",
  "create_codex_lead_orchestration_record",
  "codex_lead_orchestration_recorded",
  "build_codex_lead_delegations",
  "push_product_evidence_history_dir(&mut items, \"codex-orchestration\"",
  "PetRuntimeSignalRecord",
  "PetRuntimeAttentionItem",
  "pet_attention_item_count",
  "latest_pet_attention_state",
  "pet_runtime_attention_items",
  "codex-agent-postmortem",
  "hermes-kimi-postmortem",
  "terminal-blocked",
  "process-control-policy",
  "process-exit-summary",
  "record_pet_runtime_signal",
  "record_pet_runtime_snapshot_signal",
  "pet_runtime_signal_recorded",
  "Runtime sidecar process snapshot is green",
  "Runtime sidecar process snapshot has gaps",
  "runtime-snapshot:",
  "pet_runtime_signals_dir",
  "latest_pet_state",
  "push_product_evidence_history_dir(&mut items, \"pet-signal\"",
]) {
  if (!rustCommandsSource.includes(runtimeDepthNeedle)) {
    throw new Error(`Runtime depth probe evidence missing ${runtimeDepthNeedle}.`);
  }
}

for (const petStyleNeedle of [
  ".omega-first-class-dashboard-card[data-state=\"working\"]",
  ".omega-first-class-dashboard-card[data-state=\"success\"]",
  ".omega-first-class-dashboard-card[data-state=\"error\"]",
]) {
  if (!styleSource.includes(petStyleNeedle)) {
    throw new Error(`Pet runtime state styling missing ${petStyleNeedle}.`);
  }
}

console.log(`Validated ${requiredFiles.length} files, ${commands.groups.length} command groups, ${features.features.length} feature lanes, ${toolbar.commands.length} toolbar commands.`);
