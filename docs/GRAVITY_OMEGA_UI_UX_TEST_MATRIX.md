# Gravity Omega UI/UX Test Matrix

Status: consolidated from Worker D and wired into the Rust/Tauri scaffold as `ui_ux_test_matrix`.
Coverage: Worker D's 20 feature families are mapped to the same 20 command families as the command-surface collapse board.

## Worker D Findings

Current Electron app problems:

- Chat rail is cramped at a fixed width.
- Bottom panel needs stronger resize behavior.
- Sidebar is too narrow for media and VERITAS panels.
- File tree uses emoji icons.
- Toolbar buttons are tiny and text-only.
- Chat header is crowded.
- Focus rings are missing.
- Loading skeletons are missing.
- Hover previews are missing.
- Drag/drop feedback is too weak.

Rust/Tauri scaffold problems:

- Missing warning, info, memory, and review semantic colors.
- No animation/motion system.
- No shadow depth system.
- No focus states.
- No icon system beyond rail letters.

## Design Direction

Use custom CSS variables and a small internal component layer rather than Tailwind.

Layout targets:

- Activity rail: 48px.
- Sidebar: 260px, collapsible later.
- Chat rail: 320px default, resizable target range 240-480px.
- Bottom panel: 180px default, resizable target range 100-400px.
- Panel transitions: 150ms base, spring easing for panel motion.

Design tokens now required by validation:

- `--warning`
- `--info`
- `--memory`
- `--review`
- `--shadow-sm`
- `--shadow-md`
- `--transition-base`
- `--spring-panel`

Interaction gates:

All interactive families must expose visible focus rings before product-ready status.

- Every interactive control must have `:focus-visible`.
- Long-running panels need loading skeletons.
- File/workspace rows need hover preview strategy.
- Resize-sensitive panels need visible drag affordances before release.
- Mutation/execution panels must show warning, danger, approval, rollback, and blocked states.

## 20 Feature Families

The UI/UX matrix covers the same 20 command families as the command-surface collapse board:

1. Runtime and shell identity.
2. Command registry and toolbar.
3. Task run timeline.
4. Approval and evidence spine.
5. Workspace read and search.
6. Workspace edit and diff.
7. Terminal and process supervisor.
8. Codex runtime.
9. Hermes runtime.
10. Joint Codex/Hermes CI.
11. MCP dashboard.
12. SSWP fleet.
13. Omega Stenographer.
14. Pet companion.
15. Linux desktop control.
16. Media and audiobook.
17. Browser automation.
18. Python module sidecar.
19. Security and restricted controls.
20. Settings and providers.

## Hard Blocker Rules

- No feature family can be marked product-ready without visible keyboard focus.
- No long-running family can be product-ready without loading and failure states.
- No mutation or execution family can be product-ready without warning, danger, approval, and rollback states.
- No cramped panel can be product-ready without responsive or resizable layout acceptance checks.
- No icon-dependent navigation can be product-ready with only unlabeled letters or emoji placeholders.

## Current Scaffold Slice

This slice adds:

- `ui_ux_test_matrix` Rust command.
- UI/UX Test Matrix scaffold panel.
- Static CSS design token pass for semantic warning/info/memory/review colors.
- Focus-visible rings for buttons, textareas, rail buttons, panel buttons, and list items.
- Motion tokens and 150ms transitions.
- Shadow depth tokens.
- Skeleton loading utility.

It does not install packages, fetch icons, enable live resizing, or touch the current Electron app.
