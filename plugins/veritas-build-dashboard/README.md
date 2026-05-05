<div align="center">

# Ω Sovereign Docs & VERITAS Intelligence Server

[![Status](https://img.shields.io/badge/Status-Active-gold?style=for-the-badge&labelColor=1a1a1a&color=d4af37)](#)
[![Python](https://img.shields.io/badge/Python-3.14+-gold?style=for-the-badge&labelColor=1a1a1a&color=d4af37)](#)
[![Electron](https://img.shields.io/badge/Electron-v41.2.0-gold?style=for-the-badge&labelColor=1a1a1a&color=d4af37)](#)
[![Flask](https://img.shields.io/badge/Flask-API_Port_5070-gold?style=for-the-badge&labelColor=1a1a1a&color=d4af37)](#)
[![VERITAS](https://img.shields.io/badge/Standard-VERITAS-gold?style=for-the-badge&labelColor=1a1a1a&color=d4af37)](#)

*The unified, offline-first document generation and intelligence platform for the VERITAS ecosystem.*

</div>

---

## 🏛️ Ecosystem Architecture

Sovereign Docs is a robust Electron + Flask hybrid application that consolidates the legacy VERITAS PDF Generator, VERITAS Reporter, and Morning Brief mechanisms into an isolated, sovereign desktop module. 

| Layer | Component | Description |
|-------|-----------|-------------|
| **Compute Core** | `format_router.py` | Orchestrates the multi-format Document Object Model, handles file hashing, and generates unified trace IDs. |
| **Doc Engines** | `engines/` | 7 discrete compilation pipelines (PDF, DOCX, HTML, MD, TXT, Slides, Auto-Receipt). Utilizes PyPDF and Jinja2 templating. |
| **Intelligence** | `analyze_engine.py` | Built-in AI analysis interceptor that can seamlessly refine, rewrite, or structure text before compilation. |
| **Brief Engine** | `brief_engine.py` | Autonomous vault synthesis engine extracting intelligence strictly from local Moltbook data. |
| **REST Bridge** | `app.py` | Local Flask API serving endpoints on port `5070` for headless integration. |
| **Interface** | `main.js` | Native Electron v41 desktop client featuring a 4-tab dashboard (Create, Analyze, Brief, Library) and verified system tray IPC. |

---

## ✨ Core Features & Pipelines

### 7-Format Export Engine
A single input string or uploaded document is routed through `format_router.export_all()` to instantly produce seven immutable assets in parallel:
- **PDF**: Featuring cryptographic QR provenance stamping and active confidentiality watermarks.
- **DOCX & HTML**: Retaining strict hierarchical markdown formatting.
- **Slides**: Auto-paged presentation format.
- **Auto-Receipt**: Unforgeable cryptographic receipt containing output hashes, a custom Trace ID, and the operation manifest.

### Sovereign Briefing Dashboard
Direct integration with the local Vault to synthesize daily operations. Driven by the `/api/generate_brief` endpoint, it extracts actionable intelligence and Moltbook posts into an executive rollup.

### AI Integration & Document Parsing
Includes REST ingestion endpoints (`/api/upload`, `/api/scrape_url`) that extract raw text from files or URLs. Optional AI intercept flags trigger `analyze_engine.py` to route text through local LLM containers for grammatical refinement or structural analysis *before* finalizing the document export.

### VERITAS Aesthetics
Native dark-mode gold-and-obsidian (`#d4af37` and `#1a1a1a`) CSS layout built directly into the client. Designed to look and feel exactly like a premium intel terminal, completely isolated from cloud trackers or external CDN dependencies.

---

## 📡 API Reference & Interception

The core engine is entirely decoupled from the Electron shell and operates exposed via REST on `127.0.0.1:5070`:

- `POST /api/export` - Compiles raw content into specified output formats.
- `POST /api/upload` - Advanced multipart form ingestion supporting file uploading, format selection, and `model` attachment for AI rewriting.
- `POST /api/scrape_url` - Ingests a raw URL and parses strict markdown.
- `POST /api/generate_brief` - Synthesizes Vault memory into a Moltbook timeline.
- `GET /api/library` - Discovers output files across `output/documents` and `output/receipts`.
- `POST /api/refine` - Native target for text refinement across `qwen2.5` language structures.

---

## 🚀 Quick Start / Runbook

### 1. Initialize API Bridge (Terminal 1)
```powershell
# Navigate to the backend directory
cd backend

# Install PyPDF, Flask, Jinja2 environment (If not globally resolved)
pip install -r requirements.txt

# Launch the Flask bridging server on Port 5070
python app.py
```

### 2. Launch Interface Shell (Terminal 2)
```powershell
# In the project root, install Node dependencies (Requires Electron v41)
npm install

# Boot the VERITAS UI Shell
npm start
```
*Tip: On Windows, you can double-click the `SovereignDocs.vbs` launcher for a silent boot that suppresses active terminal windows.*

---

<div align="center">
  <br>
  <b>Built by RJ Lopez | VERITAS Framework</b>
</div>
