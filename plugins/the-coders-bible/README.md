<div align="center">
  <img src="https://raw.githubusercontent.com/VrtxOmega/Gravity-Omega/master/omega_icon.png" width="100" alt="CODERS BIBLE" />
  <h1>CODER'S BIBLE</h1>
  <p><strong>Sovereign Documentation Harvest & Retrieval Engine — VERITAS & Omega Ecosystem</strong></p>
</div>

<div align="center">

![Status](https://img.shields.io/badge/Status-ACTIVE-success?style=for-the-badge&labelColor=000000&color=d4af37)
![Version](https://img.shields.io/badge/Version-v1.2.0-informational?style=for-the-badge&labelColor=000000&color=d4af37)
![Stack](https://img.shields.io/badge/Stack-Python%20%2B%20SQLite-informational?style=for-the-badge&labelColor=000000)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge&labelColor=000000)

</div>

---

Coder's Bible is the documentation intelligence layer of the Omega Universe — an autonomous harvester that ingests deterministic facts from official sources (man pages, SDK references, CLI docs) and persists them into a local SQLite corpus with 256-dimensional SHA-derived embeddings and FTS5 full-text search. Every assertion is tagged by provenance tier, source, and evidence quality. No cloud relay, no ephemeral cache.

---

## Ecosystem Canon

Within the VERITAS & Sovereign Ecosystem, intelligence without provenance is narrative without evidence. Coder's Bible enforces the opposite: every harvested fragment carries a source identifier, a confidence tier (A-D), and a SHA-256 digest derived embedding. The ingestion pipeline runs on a governed cadence — scraping SDK references, man pages, and language documentation — then depositing the results into the omega-brain RAG store where they feed the vault's retrieval-augmented query engine. Operators do not google for syntax; they query their own provenance-tagged corpus.

---

## Overview

Coder's Bible is a deterministic documentation harvesting and retrieval engine written in Python. It connects to official sources (pkg.go.dev, ruby-doc.org, git-scm.com docs, python stdlib, man7.org, and more), extracts deterministic facts — commands, syntax, flags, types — and stores them in a structured SQLite database with 256-dimensional embeddings for semantic retrieval. Every fragment is tagged with its provenance tier, source URL, and confidence level.

The system is designed to run autonomously on a scheduled cadence (cron), harvesting documentation at configurable intervals and maintaining a living, queryable knowledge corpus that powers the Omega intelligence layer.

---

## Features

| Capability | Detail |
|---|---|
| Multi-Territory Harvest | Scrapes Go, Ruby, Rust, Python, Git, Docker, Kubernetes, PowerShell, TypeScript, and more |
| SHA-256 Derived Embeddings | 256-dim vectors generated from secure digest repetition for semantic similarity |
| Provenance Tiering | Every fragment tagged A (verified), B (reliable), C (single source), or D (unverified) |
| FTS5 Full-Text Search | Fast exact-match queries via SQLite FTS5 virtual tables |
| RAG Integration | Feeds omega-brain-mcp for contextual retrieval inside agent pipelines |
| Batch Ingestion | Bulk import from JSON files; 500+ fragments per session |
| Autonomous Scheduling | Cron-driven nightly harvest runs; self-monitoring and retry logic |
| Two-Way Vault Bridge | Syncs harvested knowledge items into the Veritas Vault for permanent retention |

---

## Architecture

```
+---------------------------------------------------------------+
|                      HARVEST SOURCES                          |
|  pkg.go.dev  ruby-doc.org  doc.rust-lang.org  git-scm.com    |
|  docs.docker.com  kubernetes.io  man7.org  python docs       |
+----------------------+-----------------------+----------------+
                       |                       |
                       v                       v
+---------------------------------------------------------------+
|                     INGESTION PIPELINE                        |
|  scraper.py -> parser -> tier_classifier -> embedder           |
|  (HTML/MD parsing | regex extraction | source attribution)   |
+----------------------+-----------------------+----------------+
                       |                       |
                       v                       v
+---------------------------------------------------------------+
|                     STORAGE LAYER                             |
|  SQLite (better-sqlite3, WAL mode, FTS5)                      |
|  fragments (text, source, tier, embedding)                     |
|  ~/.omega-brain/omega_brain.db                                |
+------------------+---------------------+----------------------+
                 |                       |
                 v                       v
+---------------------------+   +-------------------------------+
|      RAG ENGINE           |   |       VAULT BRIDGE            |
|  Semantic similarity      |   |  hermes_vault_bridge.py       |
|  query via omega_rag_     |   |  Two-way artifact + knowledge |
|  query (MCP)              |   |  Item sync to Veritas Vault   |
+---------------------------+   +-------------------------------+
```

---

## Quickstart

### Prerequisites

- **Python** 3.10+
- **SQLite** with FTS5 support
- **Node.js** 20+ (for vault bridge components)

### Install and Run

```bash
# 1. Clone the repository
git clone https://github.com/VrtxOmega/coders-bible.git
cd coders-bible

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run a single-territory harvest (e.g., Go stdlib)
python harvest_go.py

# 4. Or run the full ecosystem scan
python ecosystem_scan.py --all-territories
```

### Database Inspection

```bash
# Check fragment count
python check_db.py
# Output: Total fragments: 53,623 | Sources: 12 | Tiers: A=22,041 B=18,902
```

### Scheduled Harvest

```bash
# Add to crontab for nightly ecosystem scan
crontab -e
# 0 3 * * * cd /path/to/coders-bible && python ecosystem_scan.py --all-territories >> /tmp/harvest.log 2>&1
```

---

## Configuration

| Path | Content |
|---|---|
| `harvest_config.yaml` | Territory definitions, source URLs, parsing rules |
| `tiers.json` | Tier assignment logic (A-D) by source domain |
| `embed_config.yaml` | SHA-256 repetition factor and dimension settings |
| `~/.omega-brain/omega_brain.db` | Primary SQLite corpus for all harvested fragments |

---

## Data Model / Storage

### Primary Tables

| Table | Description |
|---|---|
| `fragments` | Harvested text, source URL, tier, timestamp, embedding blob |
| `fragments_fts` | FTS5 virtual table for full-text search |
| `sources` | Source metadata (domain, territory, reliability score) |
| `harvest_runs` | Audit log of each ingestion session |

### Knowledge Item Health States

```
hot  ->  active  ->  good  ->  stale  ->  dormant
```

Health computed from last-harvest timestamp and cross-source verification status. Stale fragments are re-harvested on the next sweep.

---

## Security & Sovereignty

- **Local-first storage**: All harvested fragments reside in the local SQLite database. No harvested data is transmitted to external services.
- **Source integrity**: Fragments are validated against checksums and source freshness markers before ingestion.
- **No credential leakage**: The ingestion pipeline does not require API keys for public documentation sources.
- **Provenance chain**: Every fragment carries its source URL and ingestion timestamp for deterministic audit.

---

## Omega Universe

Related nodes in the VERITAS & Sovereign Ecosystem:

| Repository | Role |
|---|---|
| [omega-brain-mcp](https://github.com/VrtxOmega/omega-brain-mcp) | Governance and RAG query server |
| [veritas-vault](https://github.com/VrtxOmega/veritas-vault) | Knowledge retention and session capture |
| [Gravity-Omega](https://github.com/VrtxOmega/Gravity-Omega) | Desktop AI platform and agent orchestration |
| [Ollama-Omega](https://github.com/VrtxOmega/Ollama-Omega) | Local inference bridge for agents |

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
