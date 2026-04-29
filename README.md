<div align="center">
  <img src="https://raw.githubusercontent.com/VrtxOmega/Gravity-Omega/master/omega_icon.png" width="120" alt="GRAVITY OMEGA" />
  <h1>GRAVITY OMEGA</h1>
  <p><strong>Sovereign AI Operator Platform — Electron Desktop Terminal with Multi-Model Intelligence Stack</strong></p>
</div>

<div align="center">

![Status](https://img.shields.io/badge/Status-ACTIVE-success?style=for-the-badge&labelColor=000000&color=d4af37)
![Version](https://img.shields.io/badge/Version-v2.0.0--SEALED-informational?style=for-the-badge&labelColor=000000&color=d4af37)
![Stack](https://img.shields.io/badge/Stack-Electron%20%2B%20Python%20%2B%20Node.js-informational?style=for-the-badge&labelColor=000000)
![Models](https://img.shields.io/badge/Models-Ollama%20%7C%20Mistral%20%7C%20Gemini-blue?style=for-the-badge&labelColor=000000)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge&labelColor=000000)

</div>

---

Gravity Omega is the sovereign operator's terminal — a desktop AI platform that unifies local model inference, agent orchestration, browser automation, and multi-channel communication under one VERITAS-governed interface. It does not depend on cloud APIs by default; every inference runs locally through Ollama, every action is logged, and every decision passes through the Omega agent loop before execution.

---

## Ecosystem Canon

Gravity Omega is the command surface of the VERITAS & Sovereign Ecosystem — the place where operator intent becomes deterministic action. It hosts the Edge Gallery (skill launcher), the Hermes bridge (external agent tool-call protocol), the Ollama inference router, and the browser automation engine inside a single Electron shell. Other ecosystem nodes — veritas-vault (memory), omega-brain-mcp (governance), Aegis (security), Ollama-Omega (inference transport) — are all accessible from within the Gravity Omega operator interface. The platform enforces a single invariant: no action executes before the operator approves or the agent loop validates it.

---

## Overview

Gravity Omega v2 is an Electron desktop application combining three operational layers:

| Layer | Technology | Role |
|---|---|---|
| **Main Process** | Electron + Node.js | Window management, IPC hub, system tray, auto-updater |
| **Renderer** | HTML/CSS/JS + Electron APIs | UI surface: chat, settings, gallery, browser view |
| **Backend** | Python (Flask/FastAPI) | Model orchestration, agent loop, tool execution |
| **Bridge** | Hermes ACP Adapter | External agent tool-call protocol (67-tool arsenal when unleashed) |

The operator interacts through a chat-style interface that routes to the Omega agent loop. The loop determines whether to use local Ollama models, cloud inference (optional), browser automation, or filesystem tools — with every execution logged and every tool call passing through the `omega-brain-mcp` governance layer when integrated.

---

## Features

| Capability | Detail |
|---|---|
| Multi-Model Chat | Switch between Ollama local models, Mistral API, and Gemini without restart |
| Agent Loop | Omega agent evaluates context, selects tools, and executes with operator confirmation |
| Browser Automation | Puppeteer-driven browser control for research, scraping, and UI interaction |
| Edge Gallery | Launch ecosystem skills as standalone windows within the platform |
| Hermes Bridge | Connect external Hermes agents with full 67-tool access when `OMEGA_UNLEASH` is set |
| File System Tools | Read, write, search, and analyze files across the operator's machine |
| Vault Integration | Session persistence through the Veritas Vault capture server |
| Omega Brain Gate | Optional governance layer — every tool call validated by omega-brain-mcp |
| System Tray | Minimize to tray; hotkey-activate for instant access |
| Dark Theme | VERITAS gold-and-obsidian aesthetic; no light mode |

---

## Architecture

```
+---------------------------------------------------------------+
|                    ELECTRON SHELL                             |
|  main.js       - Window/tray lifecycle, IPC hub               |
|  preload.js    - Secure contextBridge API surface             |
|  renderer/     - Chat UI, Settings, Gallery, Browser View     |
+-----------------------+----------------------+----------------+
                        |                      |
                        v                      v
+---------------------------------------------------------------+
|                   OMEGA AGENT LOOP                            |
|  omega/omega_agent.js - Intent evaluation, tool selection     |
|  backend/web_server.py - Model routing, inference dispatch    |
|  main.js _ollamaChat() - Electron main fallback layer         |
+-----------------------+----------------------+----------------+
                        |                      |
           +------------+----------+ +-------+---------------+
           |                       | |                         |
           v                       v v                         v
+-------------------+     +------------------+     +----------------+
|  LOCAL INFERENCE  |     |  CLOUD BRIDGE    |     |  TOOL EXECUTOR |
|  Ollama daemon    |     |  Mistral, Gemini |     |  Filesystem    |
|  (port 11434)     |     |  (optional)      |     |  Browser       |
+-------------------+     +------------------+     |  Shell         |
                                                   +----------------+
                                                   |  Hermes ACP    |
                                                   +----------------+
```

### Three-Layer Inference Stack

Gravity Omega has **three distinct inference layers** — all must be aligned for correct routing:

1. **Python Backend** (`backend/web_server.py`): REST API for model listing, chat completion, and tool execution
2. **JS Agent Loop** (`omega/omega_agent.js`): Frontend-side agent orchestration with tool-call dispatch
3. **Electron Main Fallback** (`main.js _ollamaChat()`): Direct Ollama Cloud API fallback when local daemon is unavailable

> **Critical**: When modifying Ollama Cloud routing, all three layers must be updated simultaneously. Updating only the Python backend while leaving `main.js` on local Ollama will produce silent failures.

---

## Quickstart

### Prerequisites

- **Node.js** 20+
- **Python** 3.11+
- **Ollama** running locally (for local inference)
- **Windows** (primary target with WSL support)

### Install and Run

```bash
# 1. Clone the repository
git clone https://github.com/VrtxOmega/Gravity-Omega.git
cd Gravity-Omega

# 2. Install Node dependencies
npm install

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Start the application
npm start
```

### Development Mode

```bash
# Electron dev mode with live reload
npm run dev

# Python backend standalone
python backend/web_server.py
```

### Build Windows Installer

```bash
npm run dist
# Output: dist/Gravity-Omega-Setup.exe
```

---

## Configuration

| Path | Content |
|---|---|
| `backend/.env` | OLLAMA_API_KEY, model defaults, inference timeout |
| `omega/config.js` | Agent loop parameters, tool timeout, retry policy |
| `renderer/app.js` | UI preferences, theme, keyboard shortcuts |
| `~/.omega-brain/` | Session logs, RAG store, vault artifacts |

**Ollama**: The local inference expects `http://localhost:11434`. Pull models before use:

```bash
ollama pull qwen2.5:7b
ollama pull mistral:7b
```

**Environment Variables**:
- `OMEGA_UNLEASH=1` — Enables full 67-tool Hermes bridge arsenal (use with discretion)
- `OLLAMA_API_KEY` — Required for Ollama Cloud routing on main.js fallback layer

---

## Data Model / Storage

| Layer | Technology | Path | Description |
|---|---|---|---|
| Session Logs | SQLite | `~/.omega-brain/logs.db` | Chat history, tool calls, agent decisions |
| RAG Store | SQLite+FTS5 | `~/.omega-brain/omega_brain.db` | Knowledge fragments, semantic search |
| Vault Artifacts | Filesystem | `~/.gemini/antigravity/` | Session captures, clipboard snapshots |
| Settings | JSON | `~/.omega/settings.json` | UI preferences, model selection, API keys |

---

## Security & Sovereignty

- **Local-first**: All inference defaults to local Ollama. Cloud APIs are opt-in.
- **No telemetry**: No analytics, no crash reporting, no update checks.
- **Hermes bridge isolation**: When `OMEGA_UNLEASH` is not set, the bridge is restricted to 30 safe tools.
- **IPC sanitization**: All renderer->main process messages pass through contextBridge with type validation.
- **WAL journaling**: SQLite databases use Write-Ahead Logging for crash resilience.

---

## Mobile Extension

The Android companion is maintained as a `mobile/` subdirectory within this repository:

```bash
cd mobile
# See mobile/README.md for React Native build instructions
```

The original standalone [OmegaMobile](https://github.com/VrtxOmega/OmegaMobile) repository is archived and superseded by this integrated location.

---

## Omega Universe

| Repository | Role |
|---|---|
| [veritas-vault](https://github.com/VrtxOmega/veritas-vault) | Session capture, knowledge retention, RAG chat |
| [omega-brain-mcp](https://github.com/VrtxOmega/omega-brain-mcp) | Governance, audit ledger, 10-gate pipeline |
| [Ollama-Omega](https://github.com/VrtxOmega/Ollama-Omega) | Local Ollama inference bridge for IDEs |
| [Aegis](https://github.com/VrtxOmega/Aegis) | Security posture and threat hunting |
| [aegis-rewrite](https://github.com/VrtxOmega/aegis-rewrite) | Next-gen security scanner with AI remediation |
| [hermes-sentinel](https://github.com/VrtxOmega/hermes-sentinel) | Secret execution without exposing credentials |
| [drift](https://github.com/VrtxOmega/drift) | 3D visualization of GitHub development universe |

---


## 🌐 VERITAS Omega Ecosystem

This project is part of the [VERITAS Omega Universe](https://github.com/VrtxOmega/veritas-portfolio) — a sovereign AI infrastructure stack.

- [VERITAS-Omega-CODE](https://github.com/VrtxOmega/VERITAS-Omega-CODE) — Deterministic verification spec (10-gate pipeline)
- [omega-brain-mcp](https://github.com/VrtxOmega/omega-brain-mcp) — Governance MCP server (Triple-A rated on Glama)
- [Gravity-Omega](https://github.com/VrtxOmega/Gravity-Omega) — Desktop AI operator platform
- [Ollama-Omega](https://github.com/VrtxOmega/Ollama-Omega) — Ollama MCP bridge for any IDE
- [OmegaWallet](https://github.com/VrtxOmega/OmegaWallet) — Desktop Ethereum wallet (renderer-cannot-sign)
- [veritas-vault](https://github.com/VrtxOmega/veritas-vault) — Local-first AI knowledge engine
- [sovereign-arcade](https://github.com/VrtxOmega/sovereign-arcade) — 8-game arcade with VERITAS design system
- [SSWP](https://github.com/VrtxOmega/sswp-mcp) — Deterministic build attestation protocol
## License

Released under the [MIT License](LICENSE).

---

<div align="center">
  <sub>Built by <a href="https://github.com/VrtxOmega">RJ Lopez</a> &nbsp;|&nbsp; VERITAS &amp; Sovereign Ecosystem &mdash; Omega Universe</sub>
</div>
