"""
Omega Brain MCP v2 — Bidirectional Antigravity ↔ Omega Brain Bridge
=====================================================================
Exposes Omega's provenance stack, Vault, Cortex, and S.E.A.L. to Antigravity
as first-class MCP tools. Pure HTTP bridge — connects to the Flask backend
at OMEGA_BRAIN_URL (default: http://127.0.0.1:5000).

8 Tools:
  - omega_preload_context  — Episodic task briefing (call at task start)
  - omega_rag_query        — Semantic RAG search of Vault knowledge
  - omega_vault_search     — FTS keyword search
  - omega_cortex_check     — Tri-Node approval gate
  - omega_cortex_steer     — Correction mode (steer drifting args, not just block)
  - omega_seal_run         — Cryptographic S.E.A.L. trace for an agentic run
  - omega_log_session      — Write Antigravity session back to Omega's Vault
  - omega_brain_status     — Unified brain health: provenance + vault + sentinel

3 Resources:
  - omega://brain/status   — Provenance stack health
  - omega://vault/recent   — Last 10 context fragments
  - omega://session/current — Current MCP session ID + call counter

SHIELDED INVARIANTS:
  - All writes go to Omega's local VAULT_DB — REAL_VAULT_DB is never written
  - All tool calls include X-Omega-Session-ID for ledger grouping
  - Every HTTP call has 10s timeout; timeout returns structured TOOL_TIMEOUT code
  - Auth token read from OMEGA_AUTH_TOKEN env var at startup
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError

log = logging.getLogger("OmegaBrain.MCP")

# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════

BRAIN_URL   = os.environ.get("OMEGA_BRAIN_URL", "http://127.0.0.1:5000")
AUTH_TOKEN  = os.environ.get("OMEGA_AUTH_TOKEN", "sentinel")
TIMEOUT_S   = 10   # all HTTP calls

# Session ID — unique per MCP server startup (chains all tool calls in this session)
_SESSION_ID   = str(uuid.uuid4())
_CALL_COUNTER = 0

# ★ Handoff file — persists across Antigravity restarts for cross-session continuity
# Written at session end via omega_write_handoff tool.
# Auto-read at startup and injected into omega://session/preload resource.
HANDOFF_FILE = Path(os.environ.get(
    "OMEGA_HANDOFF_PATH",
    str(Path.home() / ".gemini" / "antigravity" / "omega_handoff.json")
))

# ★ Auto-preload: fires at startup, cached here for resource injection.
# Antigravity reads all resources on MCP connection — this injects context automatically.
_STARTUP_PRELOAD: dict = {}
_STARTUP_PRELOAD_TS: str = ""

# ══════════════════════════════════════════════════════════════
# MCP SDK
# ══════════════════════════════════════════════════════════════

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, Resource, Prompt, PromptMessage, PromptArgument
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    log.warning("MCP SDK not installed. Run: pip install mcp")


# ══════════════════════════════════════════════════════════════
# HTTP HELPERS
# ══════════════════════════════════════════════════════════════

def _headers() -> dict:
    """Auth + session headers for every call."""
    return {
        "Content-Type": "application/json",
        "X-Omega-Token": AUTH_TOKEN,
        "X-Omega-Session-ID": _SESSION_ID,
    }


def _get(path: str, params: dict | None = None) -> dict:
    """HTTP GET to Flask backend. Returns dict or error envelope."""
    global _CALL_COUNTER
    _CALL_COUNTER += 1
    url = f"{BRAIN_URL}{path}"
    if params:
        from urllib.parse import urlencode
        url += "?" + urlencode(params)
    req = urllib_request.Request(url, headers=_headers(), method="GET")
    try:
        with urllib_request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        return {"error": e.reason, "status": e.code, "veritas_code": "HTTP_ERROR"}
    except URLError as e:
        if "timed out" in str(e.reason).lower():
            return {"error": "Backend timeout", "veritas_code": "TOOL_TIMEOUT"}
        return {"error": str(e.reason), "veritas_code": "BACKEND_UNREACHABLE"}
    except Exception as e:
        return {"error": str(e), "veritas_code": "TOOL_ERROR"}


def _post(path: str, body: dict) -> dict:
    """HTTP POST to Flask backend. Returns dict or error envelope."""
    global _CALL_COUNTER
    _CALL_COUNTER += 1
    url = f"{BRAIN_URL}{path}"
    data = json.dumps(body).encode()
    req = urllib_request.Request(url, data=data, headers=_headers(), method="POST")
    try:
        with urllib_request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        body_err = ""
        try:
            body_err = e.read().decode()[:200]
        except Exception:
            pass
        return {"error": f"{e.reason}: {body_err}", "status": e.code, "veritas_code": "HTTP_ERROR"}
    except URLError as e:
        if "timed out" in str(e.reason).lower():
            return {"error": "Backend timeout", "veritas_code": "TOOL_TIMEOUT"}
        return {"error": str(e.reason), "veritas_code": "BACKEND_UNREACHABLE"}
    except Exception as e:
        return {"error": str(e), "veritas_code": "TOOL_ERROR"}


def _veritas_score(result: dict) -> float:
    """
    Inline VERITAS scoring for RAG/preload results.
    score = clamp01(agreement * quality * independence_factor)
    agreement         = fragment similarity spread (1.0 if single source, less if spread)
    quality           = provenance tier average  (A=1.0, B=0.85, C=0.70, else 0.5)
    independence_factor = 1.0 if distinct sources >= 2, else 0.7
    """
    fragments = result.get("rag_fragments", result.get("fragments", []))
    if not fragments:
        return 0.0

    tier_map = {"A": 1.0, "B": 0.85, "C": 0.70, "D": 0.55}
    quality = sum(tier_map.get(str(f.get("tier", "C")).upper(), 0.5) for f in fragments) / len(fragments)

    sources = set(str(f.get("source", i)) for i, f in enumerate(fragments))
    independence_factor = 1.0 if len(sources) >= 2 else 0.7

    scores = [float(f.get("score", 0.8)) for f in fragments if "score" in f]
    agreement = (max(scores) - min(scores)) if len(scores) >= 2 else 0.0
    agreement_score = max(0.0, 1.0 - agreement)  # tighter spread = higher agreement

    raw = agreement_score * quality * independence_factor
    return round(min(1.0, max(0.0, raw)), 4)


def _write_handoff(task: str, summary: str, decisions: list, files: list,
                   next_steps: list, conversation_id: str) -> dict:
    """
    Write a sealed session handoff file to HANDOFF_FILE.
    SHA-256 seal over the content (minus the seal field itself).
    Overwrites any previous handoff — only the most recent session matters.
    Returns the written record.
    """
    import hashlib as _hashlib
    record = {
        "conversation_id": conversation_id or _SESSION_ID,
        "task": task[:500],
        "summary": summary[:2000],
        "decisions": decisions[:50],
        "files_modified": files[:100],
        "next_steps": next_steps[:20],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mcp_session_id": _SESSION_ID,
    }
    # Seal: SHA-256 over canonical JSON (excl. seal field)
    content = json.dumps(record, sort_keys=True)
    record["seal"] = _hashlib.sha256(content.encode()).hexdigest()
    HANDOFF_FILE.parent.mkdir(parents=True, exist_ok=True)
    HANDOFF_FILE.write_text(json.dumps(record, indent=2), encoding="utf-8")
    log.info(f"[omega-brain] Handoff written: {HANDOFF_FILE}")
    return record


def _read_handoff() -> dict | None:
    """
    Read and verify the handoff file. Returns the record if seal is valid.
    Returns None if absent, unreadable, or seal mismatch (tamper guard).
    """
    import hashlib as _hashlib
    if not HANDOFF_FILE.exists():
        return None
    try:
        raw = json.loads(HANDOFF_FILE.read_text(encoding="utf-8"))
        seal = raw.pop("seal", None)
        expected = _hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
        if seal != expected:
            log.warning(f"[omega-brain] Handoff seal mismatch — ignoring (possible tampering)")
            return None
        raw["seal"] = seal   # restore for display
        raw["seal_verified"] = True
        return raw
    except Exception as e:
        log.warning(f"[omega-brain] Handoff read error: {e}")
        return None


def _run_startup_preload():
    """
    ★ Auto-preload: Called once at MCP server startup.
    Fetches a general workspace briefing and caches it.
    Also reads the handoff file if present — makes it the lead context
    so Antigravity immediately knows what was happening last session.
    Non-fatal: if the backend isn't running yet, returns a graceful stub.
    """
    global _STARTUP_PRELOAD, _STARTUP_PRELOAD_TS
    _STARTUP_PRELOAD_TS = datetime.now(timezone.utc).isoformat()

    # 1. Read handoff file first — this is the most important context
    handoff = _read_handoff()

    # 2. Fetch live preload from backend
    result = _get("/api/brain/preload", {"task": "general workspace context and recent decisions"})
    if "error" in result:
        bundle = {
            "auto_preload": True,
            "status": "BACKEND_OFFLINE",
            "message": "Omega backend not running. Start Gravity Omega to enable brain context.",
            "session_id": _SESSION_ID,
            "timestamp": _STARTUP_PRELOAD_TS,
        }
    else:
        result["auto_preload"] = True
        result["veritas_score"] = _veritas_score(result)
        result["session_id"] = _SESSION_ID
        bundle = result

    # 3. Merge handoff as lead context (takes priority)
    if handoff:
        bundle["last_session_handoff"] = handoff
        bundle["handoff_present"] = True
        log.info(f"[omega-brain] Handoff loaded: task='{handoff.get('task', '')[:60]}' from {handoff.get('timestamp', '?')}")
    else:
        bundle["handoff_present"] = False

    _STARTUP_PRELOAD = bundle
    log.info(f"[omega-brain] Startup preload: status={bundle.get('status', 'OK')} handoff={bundle['handoff_present']}")


# Run immediately at import time (non-blocking — backend may not be up yet, that's fine)
try:
    _run_startup_preload()
except Exception as _e:
    _STARTUP_PRELOAD = {"auto_preload": True, "status": "PRELOAD_ERROR", "error": str(_e)}
    log.warning(f"[omega-brain] Startup preload failed (non-fatal): {_e}")


# ══════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════

def _tool_preload_context(task: str) -> str:
    result = _get("/api/brain/preload", {"task": task})
    result["veritas_score"] = _veritas_score(result)
    result["session_id"] = _SESSION_ID
    return json.dumps(result, indent=2)


def _tool_rag_query(query: str, top_k: int = 5) -> str:
    result = _post("/api/provenance/search", {"query": query, "top_k": top_k})
    result["veritas_score"] = _veritas_score(result)
    result["session_id"] = _SESSION_ID
    return json.dumps(result, indent=2)


def _tool_vault_search(query: str) -> str:
    result = _post("/api/vault/search", {"query": query})
    result["session_id"] = _SESSION_ID
    return json.dumps(result, indent=2)


def _tool_cortex_check(tool: str, args: dict, baseline_prompt: str) -> str:
    result = _post("/api/cortex/intercept", {
        "tool": tool,
        "args": args,
        "baseline_prompt": baseline_prompt,
    })
    result["session_id"] = _SESSION_ID
    return json.dumps(result, indent=2)


def _tool_cortex_steer(tool: str, args: dict, baseline_prompt: str) -> str:
    result = _post("/api/cortex/steer", {
        "tool": tool,
        "args": args,
        "baseline_prompt": baseline_prompt,
    })
    result["session_id"] = _SESSION_ID
    return json.dumps(result, indent=2)


def _tool_seal_run(context: dict, response: str) -> str:
    result = _post("/api/provenance/seal", {
        "context": context,
        "response": response,
    })
    result["session_id"] = _SESSION_ID
    return json.dumps(result, indent=2)


def _tool_log_session(session_id: str, task: str, decisions: list, files_modified: list) -> str:
    result = _post("/api/vault/log-session", {
        "session_id": session_id or _SESSION_ID,
        "task": task,
        "decisions": decisions,
        "files_modified": files_modified,
    })
    return json.dumps(result, indent=2)


def _tool_brain_status() -> str:
    prov   = _get("/api/provenance/status")
    vault  = _get("/api/vault/context")

    # ── Session age + break recommendation ───────────────────────────────────
    session_age_minutes = 0
    break_recommended   = False
    break_reason        = ""
    if _STARTUP_PRELOAD_TS:
        try:
            started = datetime.fromisoformat(_STARTUP_PRELOAD_TS.replace("Z", "+00:00"))
            session_age_minutes = int(
                (datetime.now(timezone.utc) - started).total_seconds() / 60
            )
        except Exception:
            pass
    if session_age_minutes >= 90:
        break_recommended = True
        break_reason = f"Session is {session_age_minutes} min old — quota pressure likely. Call omega_seal_task now then start a new conversation."
    elif _CALL_COUNTER >= 60:
        break_recommended = True
        break_reason = f"{_CALL_COUNTER} tool calls this session — context window growing. Call omega_seal_task now then start a new conversation."

    status = {
        "session_id":            _SESSION_ID,
        "call_counter":          _CALL_COUNTER,
        "session_age_minutes":   session_age_minutes,
        "break_recommended":     break_recommended,
        "break_reason":          break_reason,
        "break_action":          "Call omega_seal_task (one tap) then open a new conversation" if break_recommended else "",
        "backend_url":           BRAIN_URL,
        "timestamp":             datetime.now(timezone.utc).isoformat(),
        "provenance":            prov,
        "vault_stats":           vault.get("stats", {}),
        "vault_error":           vault.get("error"),
        "overall_health":        "OK" if "error" not in prov and "error" not in vault else "DEGRADED",
    }
    return json.dumps(status, indent=2)



# ★ NEW: omega_execute — Cortex-wrapped meta-tool (matches standalone v2.0)
# Replaces raw tool calls with: Cortex check → dispatch → auto-seal.
# Hard-blocks below similarity 0.45 (NAEF invariant).
_TOOL_ENDPOINTS: dict[str, tuple[str, str]] = {
    "omega_rag_query":       ("/api/provenance/search",  "POST"),
    "omega_vault_search":    ("/api/vault/search",        "POST"),
    "omega_preload_context": ("/api/brain/preload",       "GET"),
    "omega_cortex_check":    ("/api/cortex/intercept",   "POST"),
    "omega_cortex_steer":    ("/api/cortex/steer",        "POST"),
    "omega_seal_run":        ("/api/provenance/seal",     "POST"),
    "omega_log_session":     ("/api/vault/log-session",  "POST"),
    "omega_brain_status":    ("/api/provenance/status",  "GET"),
}

def _tool_execute(tool: str, args: dict, baseline_prompt: str) -> str:
    """
    Cortex-wrapped meta-execution (omega_execute).
    1. Run Cortex similarity check.
    2. Hard-block if similarity < 0.45 (NAEF invariant).
    3. Steer args if 0.45 <= similarity < 0.65.
    4. Dispatch to underlying tool.
    5. Auto-seal result in SEAL ledger.
    Returns structured envelope with cortex_verdict, similarity, and tool result.
    """
    # Step 1 — Cortex check
    cortex = _post("/api/cortex/intercept", {
        "tool": tool,
        "args": args,
        "baseline_prompt": baseline_prompt,
    })
    similarity = float(cortex.get("similarity", 1.0))
    approved   = cortex.get("approved", True)

    # Step 2 — Hard block
    if similarity < 0.45:
        return json.dumps({
            "omega_execute": True,
            "cortex_verdict": "NAEF_BLOCK",
            "similarity": similarity,
            "approved": False,
            "reason": "Similarity below 0.45 — unconditional NAEF block. Action not executed.",
            "session_id": _SESSION_ID,
        }, indent=2)

    # Step 3 — Steer if drifting
    if 0.45 <= similarity < 0.65:
        steer = _post("/api/cortex/steer", {
            "tool": tool, "args": args, "baseline_prompt": baseline_prompt,
        })
        args = steer.get("steered_args", args)
        cortex_verdict = "STEERED"
    else:
        cortex_verdict = "APPROVED" if approved else "SOFT_BLOCK"

    if not approved and cortex_verdict != "STEERED":
        return json.dumps({
            "omega_execute": True,
            "cortex_verdict": cortex_verdict,
            "similarity": similarity,
            "approved": False,
            "cortex_result": cortex,
            "session_id": _SESSION_ID,
        }, indent=2)

    # Step 4 — Dispatch to underlying tool
    try:
        if tool == "omega_rag_query":
            result_str = _tool_rag_query(args.get("query", ""), int(args.get("top_k", 5)))
        elif tool == "omega_vault_search":
            result_str = _tool_vault_search(args.get("query", ""))
        elif tool == "omega_preload_context":
            result_str = _tool_preload_context(args.get("task", ""))
        elif tool == "omega_cortex_check":
            result_str = _tool_cortex_check(args.get("tool", ""), args.get("args", {}), args.get("baseline_prompt", ""))
        elif tool == "omega_cortex_steer":
            result_str = _tool_cortex_steer(args.get("tool", ""), args.get("args", {}), args.get("baseline_prompt", ""))
        elif tool == "omega_seal_run":
            result_str = _tool_seal_run(args.get("context", {}), args.get("response", ""))
        elif tool == "omega_log_session":
            result_str = _tool_log_session(args.get("session_id", ""), args.get("task", ""),
                                           args.get("decisions", []), args.get("files_modified", []))
        elif tool == "omega_brain_status":
            result_str = _tool_brain_status()
        else:
            # Unknown tool — pass through to backend as generic action
            result = _post("/api/brain/execute", {"tool": tool, "args": args})
            result_str = json.dumps(result)
    except Exception as exc:
        result_str = json.dumps({"error": str(exc), "veritas_code": "DISPATCH_ERROR"})

    # Step 5 — Auto-seal
    _post("/api/provenance/seal", {
        "context": {"tool": tool, "args": args, "cortex_verdict": cortex_verdict,
                    "similarity": similarity, "session_id": _SESSION_ID},
        "response": result_str[:500],
    })

    return json.dumps({
        "omega_execute": True,
        "cortex_verdict": cortex_verdict,
        "similarity": round(similarity, 4),
        "tool": tool,
        "result": json.loads(result_str) if result_str.startswith("{") else result_str,
        "session_id": _SESSION_ID,
    }, indent=2)


# ★ NEW: omega_brain_report — human-readable audit report (matches standalone v2.0)
def _tool_brain_report(last_n: int = 20) -> str:
    """
    Generate a human-readable audit report: SEAL chain, Cortex history,
    VERITAS score summary, and session stats. Aggregates from backend endpoints.
    """
    # Fetch SEAL chain tail
    seal_chain = _get("/api/provenance/seal/chain", {"limit": last_n})
    # Fetch Cortex verdict history
    cortex_hist = _get("/api/cortex/history", {"limit": last_n})
    # Fetch overall brain status
    status = json.loads(_tool_brain_status())

    seal_entries = seal_chain.get("entries", seal_chain.get("chain", []))
    cortex_entries = cortex_hist.get("verdicts", cortex_hist.get("history", []))

    lines = [
        "═══ OMEGA BRAIN AUDIT REPORT ═══",
        f"Session   : {_SESSION_ID}",
        f"Generated : {datetime.now(timezone.utc).isoformat()}",
        f"Backend   : {BRAIN_URL}",
        f"Health    : {status.get('overall_health', 'UNKNOWN')}",
        f"Calls     : {_CALL_COUNTER}",
        "",
        f"── S.E.A.L. Chain (last {last_n}) ─────────────────────────",
    ]

    if seal_entries:
        for i, e in enumerate(seal_entries[-last_n:]):
            h = e.get("hash", e.get("seal", "?"))[:16]
            ts = e.get("timestamp", e.get("created_at", "?"))[:19]
            task = e.get("task", e.get("context", {}).get("task", "?") if isinstance(e.get("context"), dict) else "?")[:50]
            lines.append(f"  [{i+1:02d}] {ts} | {h}... | {task}")
    else:
        lines.append("  No SEAL entries found (backend may not support chain endpoint)")

    lines += [
        "",
        f"── Cortex Verdict History (last {last_n}) ──────────────────",
    ]

    if cortex_entries:
        naef_blocks = sum(1 for e in cortex_entries if e.get("similarity", 1.0) < 0.45)
        steered     = sum(1 for e in cortex_entries if 0.45 <= e.get("similarity", 1.0) < 0.65)
        approved    = len(cortex_entries) - naef_blocks - steered
        lines += [
            f"  APPROVED   : {approved}",
            f"  STEERED    : {steered}",
            f"  NAEF_BLOCK : {naef_blocks}",
        ]
        for e in cortex_entries[-5:]:
            sim = e.get("similarity", "?")
            verdict = "BLOCK" if (isinstance(sim, float) and sim < 0.45) else ("STEER" if (isinstance(sim, float) and sim < 0.65) else "OK")
            lines.append(f"  [{verdict:5}] sim={sim:.3f if isinstance(sim, float) else '?'} tool={e.get('tool','?')[:30]}")
    else:
        lines.append("  No Cortex history found")

    # VERITAS score from last preload
    veritas = _STARTUP_PRELOAD.get("veritas_score", "N/A")
    vault_stats = status.get("vault_stats", {})
    lines += [
        "",
        "── VERITAS Score ───────────────────────────────────────────",
        f"  Last preload score : {veritas}",
        f"  Vault documents    : {vault_stats.get('document_count', vault_stats.get('count', 'N/A'))}",
        f"  Vault sessions     : {vault_stats.get('session_count', 'N/A')}",
        "",
        "═══ END REPORT ═══",
    ]

    return json.dumps({
        "report": "\n".join(lines),
        "session_id": _SESSION_ID,
        "seal_count": len(seal_entries),
        "cortex_checks": len(cortex_entries),
        "overall_health": status.get("overall_health", "UNKNOWN"),
        "veritas_score": veritas,
    }, indent=2)


# ══════════════════════════════════════════════════════════════
# MCP SERVER
# ══════════════════════════════════════════════════════════════

if HAS_MCP:
    app = Server("omega-brain")

    # ── Tool Registry ─────────────────────────────────────────

    @app.list_tools()
    async def list_tools():
        return [
            Tool(
                name="omega_preload_context",
                description=(
                    "Episodic task briefing — call at the START of every task. "
                    "Returns RAG fragments, recent vault sessions, KI matches, and "
                    "Sentinel state in a single bundle with an integrity hash. "
                    "Also returns a veritas_score (0.0–1.0) on the knowledge quality."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "Natural-language description of the current task",
                        }
                    },
                    "required": ["task"],
                },
            ),
            Tool(
                name="omega_rag_query",
                description=(
                    "Semantic RAG search of the Omega provenance/knowledge stack. "
                    "Returns top-k matching fragments with source provenance and a veritas_score."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "top_k": {"type": "integer", "description": "Max results (default 5)", "default": 5},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="omega_vault_search",
                description=(
                    "Full-text keyword search across the Veritas Vault. "
                    "Searches real Vault's documents table (READ-ONLY) and local entries."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keyword search query"},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="omega_cortex_check",
                description=(
                    "Tri-Node Cortex approval gate. Returns approved: true/false + similarity score. "
                    "Use before high-impact operations (file deletes, deploys, schema changes)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string", "description": "Name of the tool being invoked"},
                        "args": {"type": "object", "description": "Tool arguments"},
                        "baseline_prompt": {"type": "string", "description": "System prompt or baseline context"},
                    },
                    "required": ["tool", "args", "baseline_prompt"],
                },
            ),
            Tool(
                name="omega_cortex_steer",
                description=(
                    "Cortex correction mode. If action drifts from baseline (similarity 0.45–0.65), "
                    "returns steered_args with corrections applied instead of hard-blocking. "
                    "Below 0.45: unconditional NAEF block. Above 0.65: passes as-is."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string", "description": "Name of the tool being invoked"},
                        "args": {"type": "object", "description": "Tool arguments"},
                        "baseline_prompt": {"type": "string", "description": "Baseline system prompt"},
                    },
                    "required": ["tool", "args", "baseline_prompt"],
                },
            ),
            Tool(
                name="omega_seal_run",
                description=(
                    "Cryptographic S.E.A.L. trace. Logs the context and response of an agentic run "
                    "to the Omega audit ledger with a tamper-proof hash chain. "
                    "Call at the END of every significant agentic task for full provenance."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context": {"type": "object", "description": "Run context (task, files, tool calls)"},
                        "response": {"type": "string", "description": "Final output or summary"},
                    },
                    "required": ["context", "response"],
                },
            ),
            Tool(
                name="omega_log_session",
                description=(
                    "Write an Antigravity session to Omega's local Vault (VAULT_DB). "
                    "NEVER writes to the real Veritas Vault (REAL_VAULT_DB — always read-only). "
                    "Use to create persistent memory of decisions and file changes."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Antigravity conversation ID"},
                        "task": {"type": "string", "description": "High-level task description"},
                        "decisions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of key decisions made during the session",
                        },
                        "files_modified": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Absolute file paths modified during the session",
                        },
                    },
                    "required": ["task"],
                },
            ),
            Tool(
                name="omega_brain_status",
                description=(
                    "Unified Omega brain health check: provenance stack, vault stats, "
                    "current session ID, and total MCP call count."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
            # ★ NEW: omega_execute — Cortex-wrapped meta-tool
            Tool(
                name="omega_execute",
                description=(
                    "Cortex-wrapped meta-tool. The DEFAULT way to call any Omega tool. "
                    "Runs: Cortex similarity check → NAEF hard-block if <0.45 → steer if <0.65 → "
                    "dispatch → auto-seal in SEAL ledger. Use instead of calling tools directly "
                    "for full provenance and NAEF compliance."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string", "description": "Omega tool name to execute"},
                        "args": {"type": "object", "description": "Arguments for the tool"},
                        "baseline_prompt": {"type": "string", "description": "System prompt or baseline context for Cortex check"},
                    },
                    "required": ["tool", "args", "baseline_prompt"],
                },
            ),
            # ★ NEW: omega_brain_report — human-readable audit
            Tool(
                name="omega_brain_report",
                description=(
                    "Generate a human-readable audit report: SEAL chain, Cortex verdict history, "
                    "VERITAS score summary, and session stats. Use to inspect provenance health "
                    "or share audit evidence."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "last_n": {"type": "integer", "description": "Number of recent entries to include (default 20)", "default": 20},
                    },
                },
            ),
            # ★ Session handoff tool: write sealed cross-session context file
            Tool(
                name="omega_write_handoff",
                description=(
                    "Write a sealed session handoff file so the NEXT Antigravity session "
                    "automatically has full context about what was happening. "
                    "Call this at the END of any significant task. The handoff is SHA-256 sealed, "
                    "auto-read on next MCP startup, and injected into omega://session/preload."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "What was being worked on"},
                        "summary": {"type": "string", "description": "Detailed summary of what was accomplished"},
                        "decisions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Key decisions made this session",
                        },
                        "files_modified": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Files that were changed",
                        },
                        "next_steps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "What should happen next session",
                        },
                        "conversation_id": {
                            "type": "string",
                            "description": "Current Antigravity conversation ID",
                        },
                    },
                    "required": ["task", "summary"],
                },
            ),
        ]

    # ── Tool Dispatch ─────────────────────────────────────────

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        try:
            if name == "omega_preload_context":
                task = arguments.get("task", "")
                if not task:
                    return [TextContent(type="text", text='{"error": "task is required", "veritas_code": "MISSING_PARAM"}')]
                return [TextContent(type="text", text=_tool_preload_context(task))]

            elif name == "omega_rag_query":
                query = arguments.get("query", "")
                top_k = int(arguments.get("top_k", 5))
                if not query:
                    return [TextContent(type="text", text='{"error": "query is required", "veritas_code": "MISSING_PARAM"}')]
                return [TextContent(type="text", text=_tool_rag_query(query, top_k))]

            elif name == "omega_vault_search":
                query = arguments.get("query", "")
                if not query:
                    return [TextContent(type="text", text='{"error": "query is required", "veritas_code": "MISSING_PARAM"}')]
                return [TextContent(type="text", text=_tool_vault_search(query))]

            elif name == "omega_cortex_check":
                return [TextContent(type="text", text=_tool_cortex_check(
                    arguments.get("tool", ""),
                    arguments.get("args", {}),
                    arguments.get("baseline_prompt", ""),
                ))]

            elif name == "omega_cortex_steer":
                return [TextContent(type="text", text=_tool_cortex_steer(
                    arguments.get("tool", ""),
                    arguments.get("args", {}),
                    arguments.get("baseline_prompt", ""),
                ))]

            elif name == "omega_seal_run":
                return [TextContent(type="text", text=_tool_seal_run(
                    arguments.get("context", {}),
                    arguments.get("response", ""),
                ))]

            elif name == "omega_log_session":
                return [TextContent(type="text", text=_tool_log_session(
                    arguments.get("session_id", ""),
                    arguments.get("task", ""),
                    arguments.get("decisions", []),
                    arguments.get("files_modified", []),
                ))]

            elif name == "omega_brain_status":
                return [TextContent(type="text", text=_tool_brain_status())]

            elif name == "omega_write_handoff":
                record = _write_handoff(
                    task=arguments.get("task", ""),
                    summary=arguments.get("summary", ""),
                    decisions=arguments.get("decisions", []),
                    files=arguments.get("files_modified", []),
                    next_steps=arguments.get("next_steps", []),
                    conversation_id=arguments.get("conversation_id", ""),
                )
                # Also update the in-memory preload so current session sees it too
                _STARTUP_PRELOAD["last_session_handoff"] = record
                _STARTUP_PRELOAD["handoff_present"] = True
                return [TextContent(type="text", text=json.dumps({
                    "written": True,
                    "path": str(HANDOFF_FILE),
                    "seal": record["seal"][:16] + "...",
                    "task": record["task"][:80],
                    "timestamp": record["timestamp"],
                    "message": "Handoff sealed. Next Antigravity session will auto-load this context.",
                }, indent=2))]

            # ★ NEW: omega_execute dispatch
            elif name == "omega_execute":
                return [TextContent(type="text", text=_tool_execute(
                    arguments.get("tool", ""),
                    arguments.get("args", {}),
                    arguments.get("baseline_prompt", ""),
                ))]

            # ★ NEW: omega_brain_report dispatch
            elif name == "omega_brain_report":
                return [TextContent(type="text", text=_tool_brain_report(
                    int(arguments.get("last_n", 20))
                ))]

            return [TextContent(type="text", text=f'{{"error": "Unknown tool: {name}", "veritas_code": "UNKNOWN_TOOL"}}')]


        except Exception as e:
            log.error(f"Tool {name} failed: {e}")
            return [TextContent(type="text", text=json.dumps({
                "error": str(e),
                "tool": name,
                "veritas_code": "TOOL_ERROR",
                "session_id": _SESSION_ID,
            }))]

    # ── Resources ─────────────────────────────────────────────

    @app.list_resources()
    async def list_resources():
        return [
            Resource(
                uri="omega://brain/status",
                name="Omega Brain Status",
                description="Provenance stack health, indexed chunks, seal count",
                mimeType="application/json",
            ),
            Resource(
                uri="omega://vault/recent",
                name="Vault Recent Context",
                description="Last 10 context fragments from Veritas Vault (read-only)",
                mimeType="application/json",
            ),
            Resource(
                uri="omega://session/current",
                name="Current MCP Session",
                description="Current session ID and tool call counter",
                mimeType="application/json",
            ),
            # ★ Auto-preload resource: Antigravity reads this on connection, injecting context automatically
            Resource(
                uri="omega://session/preload",
                name="Omega Startup Brain Preload",
                description=(
                    "Auto-fetched at server startup: RAG fragments, recent vault sessions, "
                    "KI matches, Sentinel state. Read automatically by Antigravity on MCP "
                    "connection — provides brain context with zero manual tool calls."
                ),
                mimeType="application/json",
            ),
            # ★ Handoff resource: shows last session's sealed handoff (cross-session continuity)
            Resource(
                uri="omega://session/handoff",
                name="Last Session Handoff",
                description=(
                    "Sealed cross-session handoff written by omega_write_handoff at end of "
                    "previous session. Contains task, summary, decisions, files changed, "
                    "and next steps. SHA-256 verified on read. Auto-loaded at MCP startup."
                ),
                mimeType="application/json",
            ),
        ]

    @app.read_resource()
    async def read_resource(uri: str) -> str:
        if uri == "omega://brain/status":
            return json.dumps(_get("/api/provenance/status"))

        elif uri == "omega://vault/recent":
            ctx = _get("/api/vault/context")
            return json.dumps(ctx.get("recent", []))

        elif uri == "omega://session/current":
            return json.dumps({
                "session_id": _SESSION_ID,
                "call_counter": _CALL_COUNTER,
                "backend_url": BRAIN_URL,
                "started_at": _STARTUP_PRELOAD_TS,
            })

        elif uri == "omega://session/preload":
            # Return cached startup preload — auto-injected on MCP connection
            return json.dumps(_STARTUP_PRELOAD, indent=2)

        elif uri == "omega://session/handoff":
            handoff = _read_handoff()
            if handoff:
                return json.dumps(handoff, indent=2)
            return json.dumps({
                "handoff_present": False,
                "message": "No handoff file found. Call omega_write_handoff at end of a session to enable cross-session continuity.",
            })

        return json.dumps({"error": f"Unknown resource: {uri}", "veritas_code": "UNKNOWN_RESOURCE"})

    # ★ MCP Prompts — Antigravity can invoke these automatically
    # omega_task_start: call at the beginning of every task for auto context injection
    # omega_seal_task:  call at the end to SEAL and log the session

    @app.list_prompts()
    async def list_prompts():
        return [
            Prompt(
                name="omega_task_start",
                description=(
                    "Brief Antigravity at task start. Pulls Omega brain context "
                    "(RAG + Vault + last session handoff) automatically."
                ),
                arguments=[
                    PromptArgument(
                        name="task",
                        description="One line: what are you working on?",
                        required=False,  # if blank, uses general workspace context
                    )
                ],
            ),
            Prompt(
                name="omega_seal_task",
                description=(
                    "ONE TAP to close a session: auto-reads what was done, "
                    "logs to Vault, creates S.E.A.L. trace, writes sealed handoff. "
                    "No typing required. Next Antigravity restart has full context."
                ),
                arguments=[
                    # ALL optional — autoseal generates everything from vault tape
                    PromptArgument(name="note", description="Optional one-line note (leave blank for full auto)", required=False),
                ],
            ),
            Prompt(
                name="omega_write_handoff",
                description=(
                    "Seal session context for next restart. Auto-generated from "
                    "vault history — no paragraphs needed. One tap, done."
                ),
                arguments=[
                    PromptArgument(name="note", description="Optional one-line note (leave blank for full auto)", required=False),
                ],
            ),
        ]

    @app.get_prompt()
    async def get_prompt(name: str, arguments: dict) -> dict:
        arguments = arguments or {}

        # ── omega_task_start ─────────────────────────────────────────
        # Smart context detection: figures out if this is a continuation,
        # a context-switch, or a fresh start — and surfaces info accordingly.
        if name == "omega_task_start":
            task = arguments.get("task", "").strip() or "general workspace context"

            # Fetch preload (RAG + handoff already merged in)
            try:
                preload = json.loads(_tool_preload_context(task))
            except Exception:
                preload = {}

            handoff = preload.get("last_session_handoff", {})
            handoff_task = handoff.get("task", "")
            rag_count = len(preload.get("rag_fragments", []))
            veritas = preload.get("veritas_score", 0.0)

            # ── Context mode detection ──────────────────────────────
            # Simple keyword overlap: how many words from current task appear in last session?
            def _keyword_overlap(a: str, b: str) -> float:
                a_words = set(w.lower() for w in a.split() if len(w) > 3)
                b_words = set(w.lower() for w in b.split() if len(w) > 3)
                if not a_words or not b_words:
                    return 0.0
                return len(a_words & b_words) / max(len(a_words), len(b_words))

            overlap = _keyword_overlap(task, handoff_task) if handoff_task else 0.0

            if overlap >= 0.35:
                mode = "CONTINUATION"
            elif handoff_task and overlap > 0.0:
                mode = "CONTEXT_SWITCH"
            else:
                mode = "FRESH_START"

            # ── Build briefing based on mode ────────────────────────
            if mode == "CONTINUATION":
                # Lead with last session — this is what they care about
                decisions_preview = "\n  ".join(
                    (handoff.get("decisions") or [])[:3]
                ) or "none logged"
                files_preview = ", ".join(
                    (handoff.get("files_modified") or [])[:4]
                ) or "none"
                next_preview = ", ".join(
                    (handoff.get("next_steps") or [])[:3]
                ) or "not specified"
                briefing = (
                    f"▶ CONTINUING: {handoff_task}\n\n"
                    f"Last session summary: {handoff.get('summary', '')[:400]}\n\n"
                    f"Files touched: {files_preview}\n"
                    f"Key decisions:\n  {decisions_preview}\n"
                    f"Next steps from last session: {next_preview}\n\n"
                    f"RAG context: {rag_count} fragments | VERITAS {veritas:.2f}"
                )

            elif mode == "CONTEXT_SWITCH":
                # Surface last session lightly as background
                briefing = (
                    f"◀ CONTEXT SWITCH → {task}\n\n"
                    f"Previous session was on: {handoff_task}\n"
                    f"Summary: {handoff.get('summary', '')[:200]}\n\n"
                    f"Starting fresh context for: {task}\n"
                    f"RAG context: {rag_count} fragments | VERITAS {veritas:.2f}"
                )

            else:
                # Fresh start — RAG + sentinel only, don't push stale handoff
                sentinel = preload.get("sentinel_state", {})
                sentinel_status = sentinel.get("status", "unknown") if isinstance(sentinel, dict) else "unknown"
                briefing = (
                    f"★ NEW: {task}\n\n"
                    f"No prior session detected for this context.\n"
                    f"RAG context: {rag_count} fragments | VERITAS {veritas:.2f}\n"
                    f"Sentinel: {sentinel_status}"
                )

            return {
                "messages": [
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=briefing),
                    )
                ]
            }

        # ── omega_seal_task / omega_write_handoff ────────────────────
        # ONE TAP — no typing. Autoseal reads vault tape and generates
        # task/summary/files automatically. Optional note appended if provided.
        elif name in ("omega_seal_task", "omega_write_handoff"):
            note = arguments.get("note", "").strip()

            # Hit autoseal — reads recent tape entries, auto-composes everything
            auto = _post("/api/brain/autoseal", {
                "task": note or "",
                "session_id": _SESSION_ID,
            })

            task    = auto.get("task", note or "session")
            summary = auto.get("summary", task)
            decisions = auto.get("decisions", [])
            files   = auto.get("files_modified", [])

            # Vault log
            _tool_log_session(_SESSION_ID, task, decisions, files)

            # S.E.A.L. trace
            _tool_seal_run({"task": task, "session_id": _SESSION_ID, "auto": True}, summary)

            # Sealed handoff file
            record = _write_handoff(task, summary, decisions, files, [], _SESSION_ID)
            _STARTUP_PRELOAD["last_session_handoff"] = record
            _STARTUP_PRELOAD["handoff_present"] = True

            files_short = (
                ", ".join(files[:4]) + (" ..." if len(files) > 4 else "")
            ) if files else "none logged"

            return {
                "messages": [
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=(
                                f"OMEGA SEALED ✓\n"
                                f"Task: {task[:80]}\n"
                                f"Files: {files_short}\n"
                                f"Seal: {record['seal'][:16]}...\n\n"
                                f"Next session auto-loads this context. "
                                f"It will detect CONTINUATION, CONTEXT_SWITCH, or FRESH_START automatically."
                            ),
                        ),
                    )
                ]
            }

        return {"messages": [{"role": "user", "content": {"type": "text", "text": f"Unknown prompt: {name}"}}]}



# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

async def main():
    if not HAS_MCP:
        print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    log.info(f"Omega Brain MCP v2 starting — session {_SESSION_ID}")
    log.info(f"Backend: {BRAIN_URL}")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
