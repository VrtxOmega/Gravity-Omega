# The Coder Bible — VS Code Extension

## Install (Developer / Sideload)

### Requirements
- VS Code 1.80+
- Python 3.9+ with `requests` installed
- `coders_bible.db` at `C:\Veritas_Lab\coders-bible\coders_bible.db`

### Steps

1. **Open VS Code** and go to `Extensions` (Ctrl+Shift+X)
2. Click **...** (top-right) → **Install from VSIX...**  
   — OR use the Developer Install method below

#### Developer Install (recommended while in dev)

```bash
# Option A — Symlink the folder (no packaging needed)
code --install-extension c:\Veritas_Lab\coders-bible\vscode-extension

# Option B — Open the extension folder directly as a dev extension
code --extensionDevelopmentPath=c:\Veritas_Lab\coders-bible\vscode-extension
```

> The simplest method: press `F5` inside VS Code with the extension folder open — it launches an **Extension Development Host** window with the sidebar live.

---

## Usage

| Action | How |
|---|---|
| Open sidebar | Click **Ω** in activity bar |
| Search | Type query → Enter or click **Go** |
| Quick search | `Ctrl+Shift+B` anywhere in VS Code |
| Search selection | Select text in editor → `Ctrl+Shift+B` |
| Filter domain | Dropdown: Python / JS / Rust / Go / etc. |
| Filter type | `!! Gotchas`, `>> Recipes`, `-- Docs` |
| Insert at cursor | Click **INS** on any result card |
| Copy to clipboard | Click **CPY** on any result card |

---

## Configuration

In VS Code Settings (`Ctrl+,`) search **"The Coder Bible"**:

| Setting | Default | Description |
|---|---|---|
| `codersBible.dbPath` | *(auto)* | Path to `coders_bible.db` |
| `codersBible.pythonPath` | `python` | Python executable |
| `codersBible.defaultDomain` | *(none)* | Auto-filter domain |

---

## Architecture

```
VS Code Sidebar WebView
    ↓  postMessage
extension.js (Node.js)
    ↓  execFile
cb.py --json (Python FTS5 subprocess)
    ↓
coders_bible.db (SQLite)
```

- **Zero network** — all search is local FTS5
- **Zero AI** — deterministic BM25-style full-text search
- **Subprocess isolation** — crash-safe, timeout-protected (15s)
- **JSON protocol** — `cb.py search "q" --json` / `cb.py stats --json`

---

## Packaging (VSIX for distribution)

```bash
npm install -g vsce
cd vscode-extension
vsce package
# Produces: coders-bible-1.0.0.vsix
```
