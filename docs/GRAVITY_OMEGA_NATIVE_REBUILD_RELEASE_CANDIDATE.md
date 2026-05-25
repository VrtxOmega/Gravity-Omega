# Gravity Omega Native Rebuild Release Candidate

Status: publish-ready Rust/Tauri rebuild branch.

This document is the GitHub-facing manifest for the native Gravity Omega rebuild. It explains what belongs in the branch, what intentionally stays local, how to verify the app, and what is still guarded.

## Included Tree

```text
docs/
├── GRAVITY_OMEGA_NATIVE_REBUILD_RELEASE_CANDIDATE.md
├── GRAVITY_OMEGA_RUST_REBUILD_AUDIT.md
├── GRAVITY_OMEGA_UI_UX_TEST_MATRIX.md
├── GRAVITY_OMEGA_UNIFIED_ACTION_PLAN.md
└── RUST_TAURI_COMMAND_CONTRACT.md

rebuild/
├── FIRST_CLASS_SPECS.md
└── gravity-omega-tauri/
    ├── packaging/
    │   ├── gravity-omega-native.desktop
    │   ├── install-local-desktop-entry.sh
    │   └── launch-gravity-omega-native.sh
    ├── scripts/
    │   ├── qa-workbench-interactions.mjs
    │   └── validate-scaffold.mjs
    ├── src-tauri/
    │   ├── Cargo.toml
    │   ├── Cargo.lock
    │   ├── build.rs
    │   ├── capabilities/default.json
    │   ├── icons/icon.png
    │   └── src/
    │       ├── commands.rs
    │       └── main.rs
    └── web/
        ├── contracts/
        ├── src/
        ├── vendor/
        ├── gravity-omega-home-test.html
        ├── gravity-omega-long-prompt-stress-test.html
        ├── index.html
        └── veritas-hand.html
```

## Excluded Local State

These files are intentionally not part of the publish set:

- `.sswp.json` local witness state
- `rebuild/gravity-omega-tauri/Omega Agent Work.md` run scratchpad
- `rebuild/gravity-omega-tauri/src-tauri/target/` release/debug binaries
- `rebuild/gravity-omega-tauri/node_modules/`
- logs, local transcripts, app state, secrets, and temporary screenshots

Release binaries should be produced locally with `npm run build`; they are not committed.

## Product Surface In This Candidate

- Native Rust/Tauri application shell.
- Monaco-style editor lane with Gravity Omega home surface and generated artifact previews.
- Omega Agent chat rail with Codex Lead + Hermes/Kimi modes.
- Omega Computer center surface with 10 worker lanes and visible handoff controls.
- Left activity rail and sidebar cards wired to visible main work surfaces.
- Terminal, Output, Artifact, Problems, and Evidence bottom lanes.
- Sovereign Docs / Veritas-branded preview direction preserved in the web surface.
- Runtime, sidecar, MCP, SSWP, Steno, pet, evidence, and approval readiness surfaces.
- Safe launcher and local desktop-entry templates.
- Repeatable browser/CDP QA harness for workbench interactions.

## Verification Commands

Run from `rebuild/gravity-omega-tauri`:

```bash
npm run validate
node --check web/src/main.js
node --check scripts/validate-scaffold.mjs
node --check scripts/qa-workbench-interactions.mjs
cargo check --manifest-path src-tauri/Cargo.toml
npm run build
```

Interactive browser QA:

```bash
python3 -m http.server 4174 --bind 127.0.0.1
node scripts/qa-workbench-interactions.mjs
```

The QA harness checks activity rail buttons, sidebar cards, bottom tabs, menu/toolbar/settings commands, long prompt input, Codex/Hermes mode controls, run buttons, and artifact preview controls.

## Latest Local Evidence

Last verified locally on 2026-05-25:

- `npm run validate` passed with 19 files, 11 command groups, 41 feature lanes, and 34 toolbar commands.
- `node --check web/src/main.js` passed.
- `node --check scripts/validate-scaffold.mjs` passed.
- `node --check scripts/qa-workbench-interactions.mjs` passed.
- `cargo check --manifest-path src-tauri/Cargo.toml` passed.
- `npm run build` passed and produced `src-tauri/target/release/gravity-omega-native`.
- `node scripts/qa-workbench-interactions.mjs` passed with no browser events or failures.
- The rebuilt native app launched successfully through `packaging/launch-gravity-omega-native.sh`.
- Linux Computer Use input readiness was restored locally by repairing the user `ydotoold` service; no system service files are committed in this branch.

## Guarded / Not Yet Unlocked

This branch keeps dangerous actions explicit and gated:

- destructive desktop control
- arbitrary terminal execution
- unrestricted file writes
- patch application
- live MCP calls
- memory writes
- exports/captures
- old Electron app mutation
- `.sswp` mutation

The rebuild exposes the product surfaces and evidence flows needed to keep unlocking those areas deliberately.

## GitHub Review Notes

This is a large replacement-app branch. The important review points are:

- `rebuild/gravity-omega-tauri/` is the native app lane.
- `docs/` records the parity audit, command contract, test matrix, unified action plan, and this release-candidate manifest.
- `web/vendor/` is committed because the Tauri webview serves Monaco and xterm assets locally.
- The generated release binary and local runtime artifacts are excluded.
