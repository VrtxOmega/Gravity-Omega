"""
omega_model_router.py — Multi-model routing for Omega Brain
============================================================
Called by both web_server.py (/api/brain/route) and directly
from omega_brain_mcp.py (standalone fallback).

Routing table:
  FLASH  — gemini-2.0-flash  (summarize, lookup, classify, search)
  PRO    — gemini-1.5-pro    (analyze, generate, architecture, review)
  OLLAMA — local qwen/llama  (no-internet fallback)
  AUTO   — this module decides based on task_type

All calls are pure urllib — zero new dependencies.
GOOGLE_API_KEY env var required for Gemini calls.
OLLAMA_URL env var for Ollama (default: http://localhost:11434).
"""
import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ── Model IDs ────────────────────────────────────────────────────────────────
MODELS = {
    "flash":   "gemini-2.0-flash",
    "flash15": "gemini-1.5-flash",
    "pro":     "gemini-1.5-pro",
    "pro2":    "gemini-2.0-pro-exp",
}

OLLAMA_URL  = os.environ.get("OLLAMA_URL",  "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")

# ── Task → model mapping ──────────────────────────────────────────────────────
# Keep Flash for anything cheap. Pro only for heavy reasoning.
TASK_ROUTES = {
    # Lightweight → Flash
    "summarize":   "flash",
    "classify":    "flash",
    "lookup":      "flash",
    "translate":   "flash",
    "paraphrase":  "flash",
    "search":      "flash",
    "extract":     "flash",
    "format":      "flash",
    "validate":    "flash",
    # Medium → Flash (still fast enough)
    "explain":     "flash",
    "review":      "flash",
    "compare":     "flash",
    "diff":        "flash",
    # Heavy → Pro
    "analyze":     "pro",
    "generate":    "pro",
    "architect":   "pro",
    "debug":       "pro",
    "plan":        "pro",
    "reason":      "pro",
    "synthesize":  "pro",
    # Default
    "auto":        "flash",  # start cheap, escalate if needed
}

# Token limits per tier (approximate — keeps responses tight)
MAX_OUTPUT_TOKENS = {
    "flash": 2048,
    "pro":   4096,
    "ollama": 2048,
}


def _classify_task(prompt: str, task_type: str = "auto") -> str:
    """Determine model tier from task_type or prompt keywords."""
    t = task_type.lower().strip()
    if t in TASK_ROUTES:
        return TASK_ROUTES[t]

    # Keyword-based fallback if task_type is unrecognized or "auto"
    prompt_lower = prompt.lower()
    heavy_keywords = {"architect", "design", "optimize", "implement", "debug",
                      "refactor", "analyze", "complex", "entire", "system",
                      "production", "security", "audit", "reason"}
    if any(k in prompt_lower for k in heavy_keywords):
        return "pro"
    return "flash"


def _call_gemini(prompt: str, model_key: str, system: str = "") -> dict:
    """Call Google Gemini REST API. Returns {text, model, tokens, error?}."""
    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return {"error": "GOOGLE_API_KEY not set", "provider": "gemini"}

    model_id = MODELS.get(model_key, MODELS["flash"])
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model_id}:generateContent?key={api_key}")

    contents = []
    if system:
        contents.append({
            "role": "user",
            "parts": [{"text": f"[System instruction: {system}]"}]
        })
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    body = json.dumps({
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": MAX_OUTPUT_TOKENS.get(model_key, 2048),
            "temperature": 0.3,
        }
    }).encode()

    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        candidate = data.get("candidates", [{}])[0]
        text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
        usage = data.get("usageMetadata", {})
        return {
            "text": text,
            "model": model_id,
            "provider": "gemini",
            "input_tokens":  usage.get("promptTokenCount", 0),
            "output_tokens": usage.get("candidatesTokenCount", 0),
        }
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:200]
        return {"error": f"Gemini HTTP {e.code}: {err}", "provider": "gemini"}
    except Exception as e:
        return {"error": str(e), "provider": "gemini"}


def _call_ollama(prompt: str, system: str = "") -> dict:
    """Call local Ollama. Returns {text, model, error?}."""
    url = f"{OLLAMA_URL}/api/generate"
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    body = json.dumps({
        "model":  OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {"num_predict": MAX_OUTPUT_TOKENS["ollama"]},
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        return {
            "text":     data.get("response", ""),
            "model":    data.get("model", OLLAMA_MODEL),
            "provider": "ollama",
        }
    except Exception as e:
        return {"error": str(e), "provider": "ollama"}


def route_call(prompt: str, task_type: str = "auto",
               system: str = "", model_override: str = "") -> dict:
    """
    Main routing entry point.

    Args:
        prompt:         The input text/question/task.
        task_type:      SUMMARIZE | CLASSIFY | ANALYZE | GENERATE | AUTO etc.
        system:         Optional system instruction.
        model_override: Force a specific tier: flash | pro | ollama

    Returns:
        {text, model, provider, tier, task_type, routed_to,
         input_tokens?, output_tokens?, error?, ts}
    """
    tier = model_override.lower() if model_override else _classify_task(prompt, task_type)

    ts = datetime.now(timezone.utc).isoformat()

    # Try Gemini first, fall back to Ollama
    if tier in ("flash", "pro", "flash15", "pro2"):
        result = _call_gemini(prompt, tier, system)
    elif tier == "ollama":
        result = _call_ollama(prompt, system)
    else:
        result = _call_gemini(prompt, "flash", system)
        tier = "flash"

    # Fallback to Ollama if Gemini fails
    if "error" in result and tier != "ollama":
        fallback = _call_ollama(prompt, system)
        if "error" not in fallback:
            result = fallback
            result["fallback_from"] = tier
            tier = "ollama"

    result.update({
        "tier":      tier,
        "task_type": task_type,
        "routed_to": result.get("model", f"ollama/{OLLAMA_MODEL}"),
        "ts":        ts,
    })
    return result
