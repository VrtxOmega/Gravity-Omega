# Gravity Omega Native Workbench

Status: release-candidate native workbench with operator-unlocked agent prompt runner.

This directory is the clean Rust/Tauri rebuild lane for Gravity Omega. The first viewport is now the native Gravity Omega workbench shell: activity bar, explorer, editor lane, bottom terminal/evidence panel, and Omega chat with Codex/Hermes prompt controls. The current Electron app remains a read-only parity reference while the native runtime absorbs each feature.

## Layout

```text
rebuild/gravity-omega-tauri/
├── scripts/
│   ├── qa-workbench-interactions.mjs
│   └── validate-scaffold.mjs
├── packaging/
│   ├── gravity-omega-native.desktop
│   ├── launch-gravity-omega-native.sh
│   └── install-local-desktop-entry.sh
├── src-tauri/
│   ├── Cargo.toml
│   ├── build.rs
│   ├── capabilities/default.json
│   ├── icons/icon.png
│   ├── src/commands.rs
│   ├── src/main.rs
│   └── tauri.conf.json
├── web/
│   ├── contracts/
│   │   ├── commands.v0.json
│   │   ├── features.v0.json
│   │   ├── sandbox.v0.json
│   │   └── toolbar.v0.json
│   ├── src/
│   │   ├── main.js
│   │   └── styles.css
│   ├── vendor/
│   │   ├── monaco/
│   │   └── xterm/
│   └── index.html
└── package.json
```

## Rules For This Lane

- The current Electron app remains a reference implementation.
- Native commands start as explicit bounded records until each feature has tests.
- No destructive command executes without an approval/audit path.
- No Windows, WSL, `/mnt/c`, or AppData paths are allowed in native defaults.
- Runtime data should use XDG paths on Linux.
- Codex-style planning, diff inspection, approvals, tests, logs, and final evidence are product features, not just developer habits.

## Local Checks

These checks do not download dependencies:

```bash
npm run validate --prefix rebuild/gravity-omega-tauri
node --check rebuild/gravity-omega-tauri/web/src/main.js
cargo test --manifest-path rebuild/gravity-omega-tauri/src-tauri/Cargo.toml
cargo check --manifest-path rebuild/gravity-omega-tauri/src-tauri/Cargo.toml
```

`cargo fmt` is not listed because this local toolchain does not currently include `cargo-fmt`.

## Interaction QA

The rebuild includes a focused browser/CDP QA harness:

```bash
python3 -m http.server 4174 --bind 127.0.0.1
node scripts/qa-workbench-interactions.mjs
```

It verifies that the visible workbench controls are real product controls: activity rail panels, sidebar cards, bottom tabs, toolbar/menu/settings commands, Codex/Hermes mode buttons, run buttons, long prompt intake, and artifact preview controls.

## Linux Launcher Template

`packaging/gravity-omega-native.desktop` points at the verified release binary
under `src-tauri/target/release/gravity-omega-native` and the bundled app icon.
It is a template only; it is not installed into the desktop menu by validation
or build commands.

When the release binary exists and you deliberately want a local menu entry,
`packaging/install-local-desktop-entry.sh` copies the template into
`${XDG_DATA_HOME:-$HOME/.local/share}/applications` and refreshes the desktop
database when that tool is available.

## Operator-Unlocked Agent Runs

The Command area includes an Unlocked Agent Run panel. `Codex Write` runs a
real bounded `codex exec` prompt in workspace-write mode against this rebuild
workspace. `Hermes` runs a real bounded `hermes chat -Q` prompt from the same
composer text. Both commands capture stdout/stderr transcripts and JSON/JSONL
evidence under XDG app state.
