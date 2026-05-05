<div align="center">
  <img src="https://raw.githubusercontent.com/VrtxOmega/Gravity-Omega/master/omega_icon.png" width="100" alt="VERITAS" />
  <h1>SOVEREIGN CAPTURE</h1>
  <p><strong>High-Assurance Screen Recording & Conversion Platform</strong></p>
  <p><em>Capture. Convert. Control.</em></p>
</div>

![Status](https://img.shields.io/badge/Status-ACTIVE-success?style=for-the-badge&labelColor=000000&color=d4af37)
![Platform](https://img.shields.io/badge/Platform-Windows-blue?style=for-the-badge&labelColor=000000)
![Stack](https://img.shields.io/badge/Stack-Electron%20%2B%20FFmpeg-informational?style=for-the-badge&labelColor=000000)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge&labelColor=000000)

---

SovereignCapture is a desktop screen recorder built with Electron and FFmpeg. Three-tab interface for recording, library management, and format conversion — all processed locally with zero cloud dependency.

> **Everything stays on your machine. No uploads, no telemetry, no accounts.**

## Features

- **Live Preview** - Real-time camera/screen preview before recording starts
- **Quality Presets** - Low (2Mbps), Medium (4Mbps), High (8Mbps), Max (16Mbps)
- **Cinematic Countdown** - Animated 3-2-1 overlay with sound cues
- **Webcam PiP** - Picture-in-picture webcam overlay during recording
- **System Audio** - Capture desktop audio alongside screen content
- **Auto-Save** - Recordings saved automatically to your library on stop
- **Format Conversion** - FFmpeg-powered conversion between MP4, MOV, GIF, and AVI
- **Trim Editor** - Cut recordings to exact start/end points before export
- **HTTP API** - Programmatic recording control on port 5060
- **Global Hotkey** - `Ctrl+Shift+R` to toggle recording from anywhere

## Architecture

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Shell** | Electron | Window management, system tray, IPC |
| **Renderer** | HTML/CSS/JS | 3-tab UI (Record / Library / Convert) |
| **Capture** | desktopCapturer + FFmpeg | Screen/audio/webcam capture pipeline |
| **Converter** | FFmpeg CLI | Format transcoding and trim operations |
| **API** | Express (port 5060) | Remote toggle for automation workflows |

## Quick Start

### Requirements
- Node.js 20+
- FFmpeg installed and on PATH

### Install

`ash
npm install
npm start
`

### Global Hotkey
Press `Ctrl+Shift+R` at any time to start/stop recording.

### API Control
`ash
# Toggle recording
curl http://localhost:5060/toggle
`

## UI

Three-tab interface with VERITAS gold-and-obsidian design:

| Tab | Function |
|-----|----------|
| **Record** | Live preview, quality selection, start/stop controls |
| **Library** | Browse, playback, and manage saved recordings |
| **Convert** | Format conversion with trim and quality controls |

## License

MIT

---

<div align="center">
  <sub>Built by <a href="https://github.com/VrtxOmega">RJ Lopez</a> | VERITAS Framework</sub>
</div>