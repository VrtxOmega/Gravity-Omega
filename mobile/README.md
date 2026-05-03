<div align="center">
  <img src="https://raw.githubusercontent.com/VrtxOmega/Gravity-Omega/master/omega_icon.png" width="100" alt="OMEGA MOBILE" />
  <h1>GRAVITY OMEGA MOBILE</h1>
  <p><strong>Android Client for the Gravity Omega AI Platform — React Native Operator Terminal</strong></p>
</div>

<div align="center">

![Status](https://img.shields.io/badge/Status-ARCHIVED-8B0000?style=for-the-badge&labelColor=000000&color=d4af37)
![Version](https://img.shields.io/badge/Version-v1.1.0--FINAL-informational?style=for-the-badge&labelColor=000000)
![Platform](https://img.shields.io/badge/Platform-Android-brightgreen?style=for-the-badge&labelColor=000000)
![Stack](https://img.shields.io/badge/Stack-React%20Native-informational?style=for-the-badge&labelColor=000000)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge&labelColor=000000)

</div>

---

> **NOTICE: OmegaMobile has been merged into [Gravity-Omega](https://github.com/VrtxOmega/Gravity-Omega/tree/master/mobile) as the official mobile extension.**
> This repository is archived. Future development continues in the parent Gravity-Omega repo under the `mobile/` directory.

---

## Ecosystem Canon

Gravity Omega Mobile was the Android terminal of the VERITAS & Sovereign Ecosystem — a React Native client connecting to the desktop Gravity Omega AI platform via WebSocket bridge with localtunnel NAT traversal. It allowed operators to issue commands, receive intelligence summaries, and monitor their sovereign stack from a mobile device. The mobile extension has been absorbed into the parent project to unify the deployment surface and reduce maintenance overhead.

---

## What It Was

An Android companion app providing:

- Real-time chat interface to Gravity Omega's LLM backend
- Push notifications for critical alerts and pipeline completions
- Voice input for hands-free command entry
- Bridge to the desktop agent loop via WebSocket
- localtunnel NAT traversal for remote access to the desktop instance

---

## Migration Path

The full source code, build logs, and architectural documentation are now maintained as a `mobile/` subdirectory in [Gravity-Omega](https://github.com/VrtxOmega/Gravity-Omega/tree/master/mobile).

```bash
git clone https://github.com/VrtxOmega/Gravity-Omega.git
cd Gravity-Omega/mobile
# See README.md in that directory for build instructions
```

---

## History

- v1.0.0 — Initial Android client with WebSocket bridge
- v1.1.0 — Push notifications, voice input, localtunnel integration
- v1.2.0-ARCHIVED — Merged into Gravity-Omega `mobile/` subdirectory

---

## License

Released under the [MIT License](LICENSE).

---

<div align="center">
  <sub>Archived and maintained by <a href="https://github.com/VrtxOmega">RJ Lopez</a> &nbsp;|&nbsp; VERITAS &amp; Sovereign Ecosystem &mdash; Omega Universe</sub>
</div>
