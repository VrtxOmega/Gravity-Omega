"""
Omega Claw — MCP Server
=========================
MCP server that registers Omega Claw as a native tool inside Antigravity.

Uses the MCP Python SDK (JSON-RPC 2.0, stdio transport).

Registered Tools:
  - omega_assess  — Run gate pipeline on a file, return envelope
  - omega_status  — Show daemon state and recent assessments
  - omega_promote — Trigger forge pipeline on a specific file
  - omega_audit   — Return last N audit ledger entries

Registered Resources:
  - omega://index     — Current file index state
  - omega://envelopes — All classified files and their envelopes

IMPORTANT: Inside Antigravity, Omega is UNBOUND.
The MCP server provides assessment tools, not restrictions.
"""

import json
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from gate_pipeline import run_gate_pipeline
from risk_calibrator import calibrate
from audit_ledger import AuditLedger
from omega_claw_daemon import OmegaClawDaemon

log = logging.getLogger("OmegaClaw.MCP")

# ══════════════════════════════════════════════════════════════
# MCP SERVER SETUP
# ══════════════════════════════════════════════════════════════

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, Resource
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    log.warning("MCP SDK not installed. Run: pip install mcp")


# ══════════════════════════════════════════════════════════════
# GLOBAL STATE
# ══════════════════════════════════════════════════════════════

_ledger = AuditLedger()
_daemon = OmegaClawDaemon(ledger=_ledger)


def _assess_file(path: str) -> dict:
    """Run the full gate pipeline on a file."""
    try:
        content = Path(path).read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError) as e:
        return {"error": str(e)}

    gate_results, file_hash = run_gate_pipeline(content, path)
    report = calibrate(gate_results)

    # Also log to audit ledger
    _ledger.append(
        filename=os.path.basename(path),
        file_hash=file_hash,
        gate_verdicts=[g.to_dict() for g in gate_results],
        envelope=report.envelope,
        risk_score=report.risk_score,
        metadata={"full_path": path, "source": "mcp"},
    )

    return report.to_dict()


# ══════════════════════════════════════════════════════════════
# MCP SERVER DEFINITION
# ══════════════════════════════════════════════════════════════

if HAS_MCP:
    app = Server("omega-claw")

    # ── Tool: omega_assess ────────────────────────────────────

    @app.list_tools()
    async def list_tools():
        return [
            Tool(
                name="omega_assess",
                description="Run the 5-gate VERITAS pipeline on a Python file. "
                            "Returns envelope (SOVEREIGN/SHIELDED/CONTAINED), "
                            "risk score, and gate-by-gate verdicts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute path to the Python file to assess",
                        }
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="omega_status",
                description="Show Omega Claw daemon status and last 5 assessments.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="omega_promote",
                description="Run forge assessment on a file and promote if SOVEREIGN.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source_path": {
                            "type": "string",
                            "description": "Path to the file to promote",
                        },
                        "dest_path": {
                            "type": "string",
                            "description": "Destination path for the promoted file",
                        },
                    },
                    "required": ["source_path", "dest_path"],
                },
            ),
            Tool(
                name="omega_audit",
                description="Return the last N entries from the audit ledger.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of records to return (default 10)",
                            "default": 10,
                        }
                    },
                },
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        if name == "omega_assess":
            path = arguments.get("path", "")
            if not path:
                return [TextContent(type="text", text="Error: 'path' is required")]
            result = _assess_file(path)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "omega_status":
            index = _daemon.get_index()
            recent = _ledger.read_last_n(5)
            status = {
                "daemon_running": _daemon.is_running,
                "indexed_files": len(index),
                "total_assessments": _ledger.count,
                "recent": [r.to_dict() for r in recent],
            }
            return [TextContent(type="text", text=json.dumps(status, indent=2))]

        elif name == "omega_promote":
            src = arguments.get("source_path", "")
            dst = arguments.get("dest_path", "")
            if not src or not dst:
                return [TextContent(type="text", text="Error: source_path and dest_path required")]

            # Assess first
            result = _assess_file(src)
            if result.get("error"):
                return [TextContent(type="text", text=f"Assessment error: {result['error']}")]

            if result.get("envelope") != "SOVEREIGN":
                return [TextContent(
                    type="text",
                    text=f"PROMOTION BLOCKED: File is {result['envelope']}, "
                         f"not SOVEREIGN.\nReason: {result.get('escalation_reason', 'unknown')}"
                )]

            # Promote
            import shutil
            try:
                Path(dst).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                return [TextContent(
                    type="text",
                    text=f"PROMOTED: {src} → {dst}\nEnvelope: SOVEREIGN"
                )]
            except OSError as e:
                return [TextContent(type="text", text=f"Promotion failed: {e}")]

        elif name == "omega_audit":
            count = arguments.get("count", 10)
            records = _ledger.read_last_n(count)
            chain_ok, checked, fail_idx = _ledger.verify_chain()
            audit = {
                "chain_verified": chain_ok,
                "records_checked": checked,
                "failure_index": fail_idx,
                "records": [r.to_dict() for r in records],
            }
            return [TextContent(type="text", text=json.dumps(audit, indent=2))]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    # ── Resources ─────────────────────────────────────────────

    @app.list_resources()
    async def list_resources():
        return [
            Resource(
                uri="omega://index",
                name="Omega File Index",
                description="Current file index state — all tracked files and their metadata",
                mimeType="application/json",
            ),
            Resource(
                uri="omega://envelopes",
                name="Omega Envelopes",
                description="All classified files and their operational envelopes",
                mimeType="application/json",
            ),
        ]

    @app.read_resource()
    async def read_resource(uri: str) -> str:
        if uri == "omega://index":
            index = _daemon.get_index()
            data = {}
            for path, entry in index.items():
                data[path] = {
                    "file_hash": entry.file_hash,
                    "last_modified": entry.last_modified,
                    "envelope": entry.envelope,
                    "assessed": entry.assessed,
                }
            return json.dumps(data, indent=2)

        elif uri == "omega://envelopes":
            index = _daemon.get_index()
            envelopes = {}
            for path, entry in index.items():
                if entry.assessed and entry.envelope:
                    envelopes[path] = entry.envelope
            return json.dumps(envelopes, indent=2)

        return json.dumps({"error": f"Unknown resource: {uri}"})


# ══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════

async def main():
    """Run the MCP server via stdio transport."""
    if not HAS_MCP:
        print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    log.info("Omega Claw MCP server starting...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
