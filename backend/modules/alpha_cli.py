"""
Alpha Predator CLI Wrapper — Omega Module Adapter
===================================================
Headless CLI entry point for alpha_scanner_god.py.
Patches Streamlit with a no-op mock so the scanner's
pure-logic functions (decide_action, kernel_score,
hazard_model, entropy_signal) can run without a web server.

Usage:
    python alpha_cli.py <chain_id>          # Scan top pairs on chain
    python alpha_cli.py <token_address>     # Scan specific token
    python alpha_cli.py --all               # Scan all default chains
"""

import sys
import os
import json
import types
from datetime import datetime

# ── Streamlit Mock ────────────────────────────────────────────
# Alpha imports streamlit at module level and calls st.set_page_config()
# on load. We inject a no-op mock so the import succeeds headlessly.

_mock_st = types.ModuleType("streamlit")

class _NoOp:
    """Callable that returns itself for any attribute access or call.
    Special handling for st.columns/st.tabs which need tuple unpacking.
    Supports int/float/str conversion for st.slider/st.number_input wrapping."""
    def __call__(self, *a, **kw):
        # st.columns([1, 10]) or st.tabs(["Tab1", "Tab2"]) — list/tuple arg
        if a and isinstance(a[0], (list, tuple)):
            return [_NoOp() for _ in a[0]]
        # st.columns(2) — int arg
        if a and isinstance(a[0], int) and a[0] > 0:
            return [_NoOp() for _ in range(a[0])]
        # For widgets with a default value (3rd positional or 'value' kwarg),
        # return that default so int(st.slider("label", 10, 180, 30)) returns 30
        if 'value' in kw:
            return kw['value']
        if len(a) >= 3:
            return a[2]  # slider(label, min, max, default)
        return self
    def __getattr__(self, _): return self
    def __bool__(self): return False
    def __iter__(self): return iter([])
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def __contains__(self, _): return False
    def __len__(self): return 0
    def __int__(self): return 0
    def __float__(self): return 0.0
    def __str__(self): return ""
    def __index__(self): return 0
    def __eq__(self, other): return False
    def __hash__(self): return 0

_noop = _NoOp()
for attr in [
    "set_page_config", "markdown", "title", "header", "subheader",
    "write", "text", "code", "json", "dataframe", "table",
    "button", "checkbox", "radio", "selectbox", "multiselect",
    "slider", "text_input", "text_area", "number_input",
    "columns", "sidebar", "expander", "tabs", "container",
    "form", "form_submit_button", "spinner", "progress",
    "success", "error", "warning", "info", "toast",
    "empty", "metric", "plotly_chart", "altair_chart",
    "session_state", "rerun", "stop", "cache_data",
    "cache_resource", "experimental_rerun", "divider",
    "toggle", "color_picker", "date_input", "time_input",
    "file_uploader", "download_button", "link_button",
    "page_link", "caption", "latex", "echo",
]:
    setattr(_mock_st, attr, _noop)

# session_state needs to be a dict-like
_mock_st.session_state = {}

sys.modules["streamlit"] = _mock_st

# Now safe to import alpha's functions
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Import will execute the module top-level (st.set_page_config, st.markdown, etc.)
# which are now no-ops
import alpha_scanner_god as alpha


# ── CLI Scanner ───────────────────────────────────────────────

def scan_chain(chain_id: str, n: int = 20):
    """Scan top N pairs on a chain and return decisions."""
    settings = alpha.default_settings()
    pairs = alpha.resolve_pairs_from_search(chain_id, n)
    results = []
    for p in pairs:
        fields = alpha.pair_to_fields(p)
        decision = alpha.decide_action(fields, settings)
        result = {
            "chain": chain_id,
            "pair": fields["pairId"][:10],
            "base": fields["baseSymbol"],
            "quote": fields["quoteSymbol"],
            "price": fields["priceUsd"],
            "liq": fields["liquidityUsd"],
            "vol24h": fields["volumeH24"],
            "action": decision["action"],
            "confidence": round(decision["confidence"], 3),
            "priority": round(decision["priority"], 3),
            "strategy": decision["strategy"],
            "sizing": decision["sizing"],
            "hazard_score": decision["hazard"]["hazard_score"],
            "hazard_window": decision["hazard"]["hazard_window"],
            "entropy_verdict": decision["entropy"]["verdict"],
            "entropy_bias": decision["entropy"]["bias"],
            "reasons": decision["reasons"],
        }
        results.append(result)
    return results


def scan_token(token_addr: str):
    """Scan a specific token across all chains."""
    settings = alpha.default_settings()
    pair = alpha.resolve_best_pair_any_chain(token_addr, settings.chains)
    if not pair:
        return {"error": f"No pair found for {token_addr}"}
    fields = alpha.pair_to_fields(pair)
    decision = alpha.decide_action(fields, settings)
    return {
        "chain": fields["chainId"],
        "pair": fields["pairId"],
        "base": fields["baseSymbol"],
        "quote": fields["quoteSymbol"],
        "price": fields["priceUsd"],
        "liq": fields["liquidityUsd"],
        "vol24h": fields["volumeH24"],
        "action": decision["action"],
        "confidence": round(decision["confidence"], 3),
        "priority": round(decision["priority"], 3),
        "strategy": decision["strategy"],
        "sizing": decision["sizing"],
        "stop_hint": decision["stop_hint"],
        "tp_hint": decision["tp_hint"],
        "hazard": decision["hazard"],
        "entropy": decision["entropy"],
        "reasons": decision["reasons"],
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "scanner": "Alpha Predator CLI",
            "version": alpha.APP_VERSION,
            "usage": "alpha_cli.py <chain_id|token_address|--all>",
            "chains": alpha.DEFAULT_CHAINS,
        }, indent=2))
        sys.exit(0)

    target = sys.argv[1]
    ts = datetime.utcnow().isoformat() + "Z"

    if target == "--all":
        settings = alpha.default_settings()
        all_results = {}
        for chain in settings.chains:
            print(f"[Alpha] Scanning {chain}...", file=sys.stderr)
            all_results[chain] = scan_chain(chain, n=10)
        report = {"scanner": "Alpha Predator CLI", "timestamp": ts, "results": all_results}
        print(json.dumps(report, indent=2))

    elif target.startswith("0x") or len(target) > 30:
        # Token address
        print(f"[Alpha] Scanning token {target}...", file=sys.stderr)
        result = scan_token(target)
        report = {"scanner": "Alpha Predator CLI", "timestamp": ts, "result": result}
        print(json.dumps(report, indent=2))

    else:
        # Chain ID
        print(f"[Alpha] Scanning chain {target}...", file=sys.stderr)
        results = scan_chain(target, n=20)
        report = {"scanner": "Alpha Predator CLI", "timestamp": ts, "chain": target, "results": results}
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

