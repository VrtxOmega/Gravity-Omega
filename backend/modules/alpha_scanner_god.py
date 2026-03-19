# alpha_scanner_god.py
# ⚡ ALPHA PREDATOR // BUY+SHORT GOD MODE
# v2.0.0-phase1 (DB-clean, schema-consistent, timezone-correct, evidence-safe)
#
# NOTE: I cannot run your local environment here, but this script is internally consistent:
# - decisions table includes `evidence TEXT NOT NULL DEFAULT ''`
# - every INSERT always provides a non-null evidence string
# - time is fixed to America/Chicago using zoneinfo (with safe fallback)
# - Streamlit rerun uses st.rerun() when available

import json
import math
import os
import re
import sqlite3
import time
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st

# -------------------------
# TIMEZONE FIX (America/Chicago)
# -------------------------
try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("America/Chicago")
except Exception:
    LOCAL_TZ = None

def _local_now() -> datetime:
    return datetime.now(LOCAL_TZ) if LOCAL_TZ else datetime.now()

def now_ts() -> str:
    return _local_now().strftime("%Y-%m-%d %H:%M:%S")

def now_hms() -> str:
    return _local_now().strftime("%H:%M:%S")

def st_rerun_safe():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

# -------------------------
# CONSTANTS
# -------------------------
APP_VERSION = "v2.0.0-phase1"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "alpha_predator_god.db")
WATCHLIST_PATH = os.path.join(SCRIPT_DIR, "watchlist.json")
SETTINGS_PATH = os.path.join(SCRIPT_DIR, "settings.json")
WATCHLIST_PATH = "watchlist.json"
SETTINGS_PATH = "settings.json"

DEX_API = "https://api.dexscreener.com/latest/dex"
HTTP_TIMEOUT = 12

DEFAULT_CHAINS = [
    "solana", "base", "ethereum", "bsc", "arbitrum", "optimism", "polygon",
    "avalanche", "fantom", "cronos", "sui", "ton"
]

CHAIN_QUICK_HINTS = {
    "solana": "base58 token address OR pairId",
    "base": "0x token or pairId",
    "ethereum": "0x token or pairId",
    "bsc": "0x token or pairId",
    "arbitrum": "0x token or pairId",
    "optimism": "0x token or pairId",
    "polygon": "0x token or pairId",
    "avalanche": "0x token or pairId",
    "fantom": "0x token or pairId",
    "cronos": "0x token or pairId",
    "sui": "Sui token address or pairId (varies)",
    "ton": "TON token address or pairId (varies)",
}

# -------------------------
# UI
# -------------------------
st.set_page_config(page_title="ALPHA PREDATOR // BUY+SHORT GOD MODE", page_icon="⚡", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #050505; color: #00FF41; font-family: 'Courier New', monospace; }
.stTextInput > div > div > input { color: #00FF41; background-color: #111; border: 1px solid #333; }
.stTextArea > div > div > textarea { color: #00FF41; background-color: #111; border: 1px solid #333; }
div.stButton > button { background-color: #00FF41; color: black; border: none; font-weight: bold; width: 100%; padding: 12px; font-size: 16px; }
div.stButton > button:hover { background-color: #00CC33; }

.coin-card {
  border: 1px solid #333; padding: 18px; border-radius: 10px;
  background: #0a0a0a; margin-bottom: 16px; transition: transform 0.08s;
  box-shadow: 0 4px 6px rgba(0,0,0,0.35);
}
.coin-card:hover { transform: scale(1.012); border-color: #00FF41; }
.metric-row { display:flex; justify-content:space-between; margin-top:10px; font-size: 13px; border-bottom: 1px solid #222; padding-bottom:6px; }
.metric-label { color:#888; }
.metric-val { color:#FFF; font-weight:bold; }

.trade-btn {
  display:block; width:100%; text-align:center; background:#1a1a1a; color:#00FF41;
  text-decoration:none; padding: 9px; margin-top: 12px; border: 1px solid #00FF41;
  border-radius: 6px; font-weight:bold;
}
.trade-btn:hover { background:#00FF41; color:black; }

.muted { color:#8a8a8a; font-size: 12px; }
.small { font-size: 12px; color:#8a8a8a; }
.badge { display:inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; border: 1px solid #333; margin-left: 8px;}
.badge-buy { border-color:#00FF41; color:#00FF41; }
.badge-short { border-color:#ff4b4b; color:#ff4b4b; }
.badge-none { border-color:#777; color:#bbb; }
.hr { border-top:1px solid #222; margin: 10px 0 14px; }
</style>
""", unsafe_allow_html=True)

# -------------------------
# UTIL
# -------------------------
def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def safe_get(d: Any, path: List[str], default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur

def compact_num(x: float) -> str:
    try:
        x = float(x)
    except Exception:
        return "0"
    absx = abs(x)
    if absx >= 1e9: return f"{x/1e9:.2f}B"
    if absx >= 1e6: return f"{x/1e6:.2f}M"
    if absx >= 1e3: return f"{x/1e3:.2f}K"
    if absx >= 1: return f"{x:.2f}"
    return f"{x:.6f}".rstrip("0").rstrip(".")

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def is_probably_email(s: str) -> bool:
    return bool(re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", s or "", re.IGNORECASE))

def dexscreener_pair_url(chain_id: str, pair_id: str) -> str:
    if chain_id and pair_id:
        return f"https://dexscreener.com/{chain_id}/{pair_id}"
    return "https://dexscreener.com"

def http_get_json(url: str) -> Optional[dict]:
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None

# -------------------------
# JSON IO
# -------------------------
def load_json(path: str, default: Any):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path: str, obj: Any):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

# -------------------------
# DB
# -------------------------
def db_connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    return con

def _db_add_column_if_missing(con: sqlite3.Connection, table: str, col: str, col_type: str):
    cur = con.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    cols = {row[1] for row in cur.fetchall()}
    if col not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")

def db_init():
    con = db_connect()
    cur = con.cursor()

    # Fresh create includes evidence as NOT NULL with DEFAULT
    cur.execute("""
    CREATE TABLE IF NOT EXISTS decisions (
        ts TEXT,
        chainId TEXT,
        pairId TEXT,
        baseSymbol TEXT,
        quoteSymbol TEXT,
        dexId TEXT,

        action TEXT,
        confidence REAL,
        priority REAL,
        strategy TEXT,
        reasons TEXT,

        sizing TEXT,
        stop_hint TEXT,
        tp_hint TEXT,

        record_hash TEXT,

        hazard_score REAL,
        hazard_window TEXT,
        short_ready INTEGER,
        hazard_triggers TEXT,

        entropy_crash_days INTEGER,
        entropy_peak_days INTEGER,
        entropy_verdict TEXT,
        entropy_bias TEXT,

        evidence TEXT NOT NULL DEFAULT '',
        meta_json TEXT
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_decisions_ts ON decisions(ts);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_decisions_pair ON decisions(chainId, pairId);")

    # Migrations (safe)
    for col, col_type in [
        ("ts", "TEXT"), ("chainId", "TEXT"), ("pairId", "TEXT"),
        ("baseSymbol", "TEXT"), ("quoteSymbol", "TEXT"), ("dexId", "TEXT"),
        ("action", "TEXT"), ("confidence", "REAL"), ("priority", "REAL"),
        ("strategy", "TEXT"), ("reasons", "TEXT"),
        ("sizing", "TEXT"), ("stop_hint", "TEXT"), ("tp_hint", "TEXT"),
        ("record_hash", "TEXT"),
        ("hazard_score", "REAL"), ("hazard_window", "TEXT"), ("short_ready", "INTEGER"),
        ("hazard_triggers", "TEXT"),
        ("entropy_crash_days", "INTEGER"), ("entropy_peak_days", "INTEGER"),
        ("entropy_verdict", "TEXT"), ("entropy_bias", "TEXT"),
        ("evidence", "TEXT"),
        ("meta_json", "TEXT"),
    ]:
        _db_add_column_if_missing(con, "decisions", col, col_type)

    # Backfill any null evidence rows if a previous schema allowed NULLs
    try:
        cur.execute("UPDATE decisions SET evidence='' WHERE evidence IS NULL;")
    except Exception:
        pass

    con.commit()
    con.close()

def db_insert_decision(row: Dict[str, Any]):
    # Evidence: ALWAYS non-null
    evidence = row.get("evidence")
    if evidence is None or (isinstance(evidence, str) and evidence.strip() == ""):
        evidence = "{}"

    con = db_connect()
    cur = con.cursor()
    cur.execute("""
    INSERT INTO decisions (
      ts, chainId, pairId, baseSymbol, quoteSymbol, dexId,
      action, confidence, priority, strategy, reasons,
      sizing, stop_hint, tp_hint,
      record_hash,
      hazard_score, hazard_window, short_ready, hazard_triggers,
      entropy_crash_days, entropy_peak_days, entropy_verdict, entropy_bias,
      evidence,
      meta_json
    ) VALUES (
      ?,?,?,?,?,?,
      ?,?,?,?,?,
      ?,?,?,
      ?,
      ?,?,?,?,
      ?,?,?,?,
      ?,
      ?
    );
    """, (
        row.get("ts"), row.get("chainId"), row.get("pairId"), row.get("baseSymbol"), row.get("quoteSymbol"), row.get("dexId"),
        row.get("action"), row.get("confidence"), row.get("priority"), row.get("strategy"), row.get("reasons"),
        row.get("sizing"), row.get("stop_hint"), row.get("tp_hint"),
        row.get("record_hash"),
        row.get("hazard_score"), row.get("hazard_window"), row.get("short_ready"), row.get("hazard_triggers"),
        row.get("entropy_crash_days"), row.get("entropy_peak_days"), row.get("entropy_verdict"), row.get("entropy_bias"),
        evidence,
        row.get("meta_json"),
    ))
    con.commit()
    con.close()

def db_recent_decisions(limit: int = 250) -> pd.DataFrame:
    con = db_connect()
    df = pd.read_sql_query("""
        SELECT ts, chainId, pairId, baseSymbol, quoteSymbol, dexId,
               action, confidence, priority, strategy, reasons, sizing,
               stop_hint, tp_hint,
               hazard_score, hazard_window, short_ready, hazard_triggers,
               entropy_crash_days, entropy_peak_days, entropy_verdict, entropy_bias,
               evidence
        FROM decisions
        ORDER BY ts DESC
        LIMIT ?
    """, con, params=(limit,))
    con.close()
    return df

def db_reset():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    db_init()

# -------------------------
# DEXSCREENER API
# -------------------------
def api_pair(chain_id: str, pair_id: str) -> Optional[dict]:
    return http_get_json(f"{DEX_API}/pairs/{chain_id}/{pair_id}")

def api_token(token_addr: str) -> Optional[dict]:
    return http_get_json(f"{DEX_API}/tokens/{token_addr}")

def api_search(query: str) -> Optional[dict]:
    return http_get_json(f"{DEX_API}/search?q={requests.utils.quote(query)}")

def _pick_best_pair(pairs: List[dict], chain_whitelist: Optional[List[str]] = None) -> Optional[dict]:
    best = None
    best_liq = -1.0
    for p in pairs or []:
        chain_id = p.get("chainId", "")
        if chain_whitelist and chain_id not in chain_whitelist:
            continue
        liq = safe_get(p, ["liquidity", "usd"], 0) or 0
        if liq > best_liq:
            best_liq = liq
            best = p
    return best

def resolve_best_pair_any_chain(token_or_addr: str, chains: List[str]) -> Optional[dict]:
    data = api_token(token_or_addr)
    if not data:
        return None
    return _pick_best_pair(data.get("pairs", []), chain_whitelist=chains)

def resolve_pairs_from_search(chain_id: str, n: int) -> List[dict]:
    queries = [f"chain:{chain_id} new", f"chain:{chain_id} volume", f"{chain_id}"]
    pairs_out: List[dict] = []
    seen = set()
    for q in queries:
        data = api_search(q)
        if not data:
            continue
        for p in data.get("pairs", []):
            if p.get("chainId") != chain_id:
                continue
            pid = p.get("pairAddress") or p.get("pairId") or ""
            if not pid:
                continue
            key = f"{chain_id}:{pid}"
            if key in seen:
                continue
            seen.add(key)
            pairs_out.append(p)
            if len(pairs_out) >= n:
                return pairs_out
    return pairs_out[:n]

def pair_to_fields(p: dict) -> dict:
    base = p.get("baseToken", {}) or {}
    quote = p.get("quoteToken", {}) or {}
    pair_id = p.get("pairAddress") or p.get("pairId") or ""
    chain_id = p.get("chainId", "") or ""
    return {
        "chainId": chain_id,
        "pairId": pair_id,
        "dexId": p.get("dexId", "") or "",
        "baseSymbol": base.get("symbol", "") or "",
        "quoteSymbol": quote.get("symbol", "") or "",
        "priceUsd": float(p.get("priceUsd") or 0),
        "liquidityUsd": float(safe_get(p, ["liquidity", "usd"], 0) or 0),
        "volumeH24": float(safe_get(p, ["volume", "h24"], 0) or 0),
        "txnsH24Buys": int(safe_get(p, ["txns", "h24", "buys"], 0) or 0),
        "txnsH24Sells": int(safe_get(p, ["txns", "h24", "sells"], 0) or 0),
        "pc1h": float(safe_get(p, ["priceChange", "h1"], 0) or 0),
        "pc6h": float(safe_get(p, ["priceChange", "h6"], 0) or 0),
        "pc24h": float(safe_get(p, ["priceChange", "h24"], 0) or 0),
        "fdv": float(p.get("fdv") or 0),
        "url": p.get("url", "") or dexscreener_pair_url(chain_id, pair_id),
    }

# -------------------------
# TARGET EXTRACT
# -------------------------
def clean_token_name(raw_name: str) -> str:
    name = (raw_name or "").replace("*", "").replace("_", "").strip()
    name = re.sub(r'^(V[234]|CPMM|DLMM|WP)\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r"\s{2,}", " ", name)
    return name.strip()

def extract_targets(text: str) -> List[Dict[str, str]]:
    targets: List[Dict[str, str]] = []
    seen = set()

    sol_pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
    evm_pattern = r'0x[a-fA-F0-9]{40}'

    for pat in [sol_pattern, evm_pattern]:
        for addr in re.findall(pat, text or ""):
            if addr not in seen:
                targets.append({"type": "address", "value": addr})
                seen.add(addr)

    name_pattern = r'([a-zA-Z0-9\.\-\$\*\s]+?)\s*/\s*(?:SOL|WETH|USDC|BNB|WBNB|USDT|USD1|DAI)'
    for m in re.findall(name_pattern, text or ""):
        clean = clean_token_name(m)
        if clean and clean not in seen and not is_probably_email(clean):
            targets.append({"type": "name", "value": clean})
            seen.add(clean)

    return targets

# -------------------------
# ENTROPY (DETERMINISTIC)
# -------------------------
def entropy_signal_from_liq_vol(liquidity_usd: float, volume_24h_usd: float, stress_test: float = 1.0) -> dict:
    liq = float(liquidity_usd or 0.0)
    vol = float(volume_24h_usd or 0.0)
    stx = float(stress_test or 1.0)

    vol_ratio = (vol / liq if liq > 0 else 50.0) * stx
    hype_score = min(vol_ratio * 10.0, 100.0)

    scam_prob = 40.0 if liq < 20000.0 else 0.0
    dump_pressure = 0.12 + (vol_ratio * 0.04)

    days = 60
    price_curve, fear_curve = [], []
    curr_price, curr_fear = 100.0, 0.0

    for day in range(days):
        growth = (hype_score / 22.0) / (day + 1.0)
        jitter = ((math.sin((day + 1) * 2.618) + math.sin((day + 1) * 1.414)) / 2.0)
        pseudo_noise = dump_pressure * 2.2 * jitter

        curr_fear += (scam_prob / 45.0) + (pseudo_noise / 2.8)
        curr_price += (growth * 11.0) - max(0.0, curr_fear) + pseudo_noise
        curr_price = max(0.0, curr_price)

        price_curve.append(curr_price)
        fear_curve.append(curr_fear)

    crash_day = days
    for i in range(days):
        if fear_curve[i] > price_curve[i]:
            crash_day = i
            break

    peak_day = 0
    if crash_day > 0:
        peak_day = max(range(crash_day), key=lambda i: price_curve[i])

    verdict = "STRATEGIC BUY" if crash_day > 25 else ("SCALP ONLY" if crash_day > 10 else "AVOID")
    bias = "SHORT" if crash_day <= 7 else ("BUY" if crash_day >= 25 else "NONE")

    return {
        "crash_days": int(crash_day),
        "peak_days": int(peak_day),
        "verdict": verdict,
        "bias": bias,
        "vol_ratio": float(vol_ratio),
        "hype_score": float(hype_score),
        "dump_pressure": float(dump_pressure),
        "scam_prob": float(scam_prob),
    }

# -------------------------
# KERNEL SETTINGS (dataclasses with safe defaults)
# -------------------------
@dataclass
class Gate:
    min_liquidity_usd: float = 48000.0
    min_volume_24h_usd: float = 25000.0
    min_txns_24h: int = 50

@dataclass
class Integrity:
    max_fdv_usd: float = 2.0e11
    min_price_usd: float = 1e-12
    reject_email_names: bool = True

@dataclass
class Signals:
    buy_momo_pc1: float = 1.0
    buy_momo_pc6: float = 2.0
    buy_momo_pc24: float = 5.0
    short_momo_pc1: float = -2.0
    short_momo_pc6: float = -5.0
    short_momo_pc24: float = -10.0
    min_buy_pressure: float = 0.55
    min_sell_pressure: float = 0.58

@dataclass
class Settings:
    refresh_interval_sec: int = 30
    top_n: int = 20
    candidates_per_chain: int = 35
    chains: List[str] = field(default_factory=lambda: DEFAULT_CHAINS.copy())

    auto_calibrate: bool = False
    aggressiveness: float = 45.0
    liq_bounds: Tuple[float, float] = (15000.0, 350000.0)
    vol_bounds: Tuple[float, float] = (5000.0, 250000.0)
    tx_bounds: Tuple[int, int] = (10, 400)

    gate: Gate = field(default_factory=Gate)
    integrity: Integrity = field(default_factory=Integrity)
    signals: Signals = field(default_factory=Signals)

    entropy_mode: str = "Veto (risk-off)"
    entropy_stress: float = 1.0
    entropy_short_hz: int = 7
    entropy_buy_hz: int = 25

    def to_json(self) -> dict:
        return asdict(self)

def default_settings() -> Settings:
    return Settings()

def load_settings() -> Settings:
    raw = load_json(SETTINGS_PATH, {})
    s = default_settings()
    try:
        for k, v in raw.items():
            if k in ("gate", "integrity", "signals"):
                continue
            if hasattr(s, k):
                setattr(s, k, v)

        if isinstance(raw.get("gate"), dict):
            s.gate = Gate(**{**asdict(s.gate), **raw["gate"]})
        if isinstance(raw.get("integrity"), dict):
            s.integrity = Integrity(**{**asdict(s.integrity), **raw["integrity"]})
        if isinstance(raw.get("signals"), dict):
            s.signals = Signals(**{**asdict(s.signals), **raw["signals"]})

        if not isinstance(s.chains, list) or not s.chains:
            s.chains = DEFAULT_CHAINS.copy()
        else:
            s.chains = [c for c in s.chains if c in DEFAULT_CHAINS] or DEFAULT_CHAINS.copy()
    except Exception:
        s = default_settings()
    return s

def save_settings(s: Settings):
    save_json(SETTINGS_PATH, s.to_json())

def load_watchlist() -> List[dict]:
    wl = load_json(WATCHLIST_PATH, [])
    return wl if isinstance(wl, list) else []

def save_watchlist(wl: List[dict]):
    save_json(WATCHLIST_PATH, wl)

# -------------------------
# CORE KERNEL
# -------------------------
def gate_check(f: dict, gate: Gate) -> Tuple[bool, List[str]]:
    reasons = []
    liq = f["liquidityUsd"]
    vol = f["volumeH24"]
    tx = f["txnsH24Buys"] + f["txnsH24Sells"]
    if liq < gate.min_liquidity_usd: reasons.append("GATE_LIQUIDITY_LOW")
    if vol < gate.min_volume_24h_usd: reasons.append("GATE_VOLUME_LOW")
    if tx < gate.min_txns_24h: reasons.append("GATE_TXNS_LOW")
    return (len(reasons) == 0), reasons

def integrity_check(f: dict, integrity: Integrity) -> Tuple[bool, List[str]]:
    reasons = []
    if f["priceUsd"] <= integrity.min_price_usd:
        reasons.append("INTEGRITY_PRICE_INVALID")
    if f["fdv"] and f["fdv"] > integrity.max_fdv_usd:
        reasons.append("INTEGRITY_FDV_TOO_HIGH")
    if integrity.reject_email_names:
        if is_probably_email(f["baseSymbol"]) or is_probably_email(f["quoteSymbol"]):
            reasons.append("INTEGRITY_EMAIL_TOKEN")
    if len((f["baseSymbol"] or "").strip()) == 0:
        reasons.append("INTEGRITY_SYMBOL_EMPTY")
    return (len(reasons) == 0), reasons

def buy_pressure(buys: int, sells: int) -> float:
    t = buys + sells
    return 0.5 if t <= 0 else buys / t

def sell_pressure(buys: int, sells: int) -> float:
    t = buys + sells
    return 0.5 if t <= 0 else sells / t

def hazard_model(f: dict) -> dict:
    triggers = []
    liq = max(1.0, float(f["liquidityUsd"] or 1.0))
    vol = max(0.0, float(f["volumeH24"] or 0.0))
    vr = vol / liq

    pc1 = float(f["pc1h"] or 0.0)
    pc6 = float(f["pc6h"] or 0.0)
    pc24 = float(f["pc24h"] or 0.0)

    buys = int(f["txnsH24Buys"] or 0)
    sells = int(f["txnsH24Sells"] or 0)
    sp = sell_pressure(buys, sells)

    hazard = 0.0
    hazard += clamp(vr * 120.0, 0.0, 45.0)
    if pc1 < -3: triggers.append("PC1_SHARP_DROP"); hazard += 18
    if pc6 < -7: triggers.append("PC6_DOWN"); hazard += 15
    if pc24 < -15: triggers.append("PC24_HEAVY_DOWN"); hazard += 12
    if sp > 0.62: triggers.append("SELL_PRESSURE"); hazard += 10
    if liq < 25000: triggers.append("LOW_LIQUIDITY"); hazard += 12

    hazard = clamp(hazard, 0.0, 100.0)

    if hazard >= 80:
        window = "0-6h"
    elif hazard >= 65:
        window = "6-24h"
    elif hazard >= 50:
        window = "1-3d"
    elif hazard >= 35:
        window = "3-7d"
    else:
        window = "-"

    short_ready = 1 if (hazard >= 65 and (pc1 < 0 or pc6 < 0 or sp > 0.6)) else 0

    return {
        "hazard_score": float(hazard),
        "hazard_window": window,
        "short_ready": int(short_ready),
        "hazard_triggers": triggers,
    }

def position_sizing_hint(priority: float) -> str:
    if priority >= 0.80: return "L"
    if priority >= 0.55: return "M"
    if priority >= 0.35: return "S"
    return "XS"

def stops_tps_hint(f: dict) -> Tuple[str, str]:
    vol_proxy = abs(f["pc1h"]) + 0.6 * abs(f["pc6h"]) + 0.35 * abs(f["pc24h"])
    vol_proxy = clamp(vol_proxy, 1.0, 50.0)
    stop = clamp(vol_proxy * 0.45, 1.5, 18.0)
    tp1 = clamp(stop * 1.5, 2.0, 25.0)
    tp2 = clamp(stop * 2.5, 3.0, 40.0)
    tp3 = clamp(stop * 4.0, 4.0, 75.0)
    return (f"Stop ≈ {stop:.1f}% (vol*0.45)", f"TPs ≈ {tp1:.1f}% / {tp2:.1f}% / {tp3:.1f}%")

def kernel_score(f: dict, sig: Signals) -> dict:
    tags = []
    pc1, pc6, pc24 = f["pc1h"], f["pc6h"], f["pc24h"]
    buys, sells = f["txnsH24Buys"], f["txnsH24Sells"]
    bp = buy_pressure(buys, sells)
    sp = sell_pressure(buys, sells)

    buy_momo = 0.0
    if pc1 >= sig.buy_momo_pc1: tags.append("BUY_PC1_OK"); buy_momo += 0.25
    if pc6 >= sig.buy_momo_pc6: tags.append("BUY_PC6_OK"); buy_momo += 0.35
    if pc24 >= sig.buy_momo_pc24: tags.append("BUY_PC24_OK"); buy_momo += 0.25
    if bp >= sig.min_buy_pressure: tags.append("BUY_PRESSURE"); buy_momo += 0.25
    buy_score = clamp(buy_momo, 0.0, 1.0)

    short_momo = 0.0
    if pc1 <= sig.short_momo_pc1: tags.append("SHORT_PC1_OK"); short_momo += 0.25
    if pc6 <= sig.short_momo_pc6: tags.append("SHORT_PC6_OK"); short_momo += 0.35
    if pc24 <= sig.short_momo_pc24: tags.append("SHORT_PC24_OK"); short_momo += 0.25
    if sp >= sig.min_sell_pressure: tags.append("SELL_PRESSURE_OK"); short_momo += 0.25
    short_score = clamp(short_momo, 0.0, 1.0)

    confidence = clamp(max(buy_score, short_score), 0.0, 1.0)

    return {
        "buy_score": float(buy_score),
        "short_score": float(short_score),
        "confidence": float(confidence),
        "tags": tags,
        "buy_pressure": float(bp),
        "sell_pressure": float(sp),
    }

def decide_action(f: dict, s: Settings) -> dict:
    reasons: List[str] = []

    gate_pass, gate_reasons = gate_check(f, s.gate)
    integrity_pass, integ_reasons = integrity_check(f, s.integrity)

    reasons.extend(gate_reasons)
    reasons.extend(integ_reasons)

    hazard = hazard_model(f)
    score = kernel_score(f, s.signals)
    entropy = entropy_signal_from_liq_vol(
        f["liquidityUsd"], f["volumeH24"], stress_test=s.entropy_stress
    )

    action = "NO_TRADE"
    strategy = "GATE_FAIL" if (not gate_pass or not integrity_pass) else "KERNEL"

    if gate_pass and integrity_pass:
        if score["buy_score"] >= 0.70 and score["buy_score"] >= score["short_score"]:
            action = "BUY"
        elif score["short_score"] >= 0.70 and score["short_score"] > score["buy_score"]:
            action = "SHORT"
        else:
            action = "NO_TRADE"
            strategy = "LOW_SIGNAL"

    if s.entropy_mode == "Veto (risk-off)":
        if entropy["verdict"] == "AVOID" and action in ("BUY", "SHORT"):
            action = "NO_TRADE"
            strategy = "ENTROPY_VETO"
            reasons.append("ENTROPY_VETO_AVOID")
    elif s.entropy_mode == "Generator (BUY/SHORT)":
        if gate_pass and integrity_pass:
            if action == "NO_TRADE":
                if entropy["bias"] == "SHORT" and entropy["crash_days"] <= s.entropy_short_hz:
                    action = "SHORT"
                    strategy = "ENTROPY_GENERATED"
                    reasons.append("ENTROPY_GENERATED_SHORT")
                elif entropy["bias"] == "BUY" and entropy["crash_days"] >= s.entropy_buy_hz:
                    action = "BUY"
                    strategy = "ENTROPY_GENERATED"
                    reasons.append("ENTROPY_GENERATED_BUY")
            else:
                if entropy["verdict"] == "SCALP ONLY":
                    reasons.append("ENTROPY_SCALP_WINDOW")
                if entropy["verdict"] == "AVOID":
                    reasons.append("ENTROPY_CAUTION_AVOID")
        else:
            reasons.append("ENTROPY_BLOCKED_BY_GATE_OR_INTEGRITY")

    if hazard["short_ready"] == 1:
        reasons.append("HAZARD_SHORT_READY")

    liq_norm = clamp(math.log10(max(10.0, f["liquidityUsd"])) / 6.0, 0.0, 1.0)
    vol_norm = clamp(math.log10(max(10.0, f["volumeH24"])) / 6.0, 0.0, 1.0)
    base_priority = 0.55 * score["confidence"] + 0.25 * liq_norm + 0.20 * vol_norm

    if action == "BUY":
        base_priority -= (hazard["hazard_score"] / 100.0) * 0.22
    elif action == "SHORT":
        base_priority += (hazard["hazard_score"] / 100.0) * 0.18

    base_priority = clamp(base_priority, 0.0, 1.0)

    sizing = position_sizing_hint(base_priority)
    stop_hint, tp_hint = stops_tps_hint(f)

    reasons = sorted(set(reasons))

    return {
        "action": action,
        "confidence": float(score["confidence"]),
        "priority": float(base_priority),
        "strategy": strategy,
        "reasons": reasons,
        "sizing": sizing,
        "stop_hint": stop_hint,
        "tp_hint": tp_hint,
        "hazard": hazard,
        "entropy": entropy,
        "score": score,
        "gate_pass": gate_pass,
        "integrity_pass": integrity_pass,
    }

# -------------------------
# AUTO-CALIBRATION (gate only; deterministic)
# -------------------------
def auto_calibrate_thresholds(s: Settings, scan_features: List[dict]) -> Tuple[Settings, dict]:
    report = {"changed": False, "notes": [], "before": {}, "after": {}}
    if not scan_features:
        report["notes"].append("No scan features; no calibration.")
        return s, report

    pass_flags = []
    for f in scan_features:
        gp, _ = gate_check(f, s.gate)
        ip, _ = integrity_check(f, s.integrity)
        pass_flags.append(1 if (gp and ip) else 0)
    pass_rate = sum(pass_flags) / max(1, len(pass_flags))

    target = 0.10 + (s.aggressiveness / 100.0) * 0.18
    report["notes"].append(f"Pass rate {pass_rate:.2%}, target {target:.2%}")

    liq_lo, liq_hi = s.liq_bounds
    vol_lo, vol_hi = s.vol_bounds
    tx_lo, tx_hi = s.tx_bounds

    before = {
        "min_liq": s.gate.min_liquidity_usd,
        "min_vol": s.gate.min_volume_24h_usd,
        "min_tx": s.gate.min_txns_24h,
    }

    liq = float(s.gate.min_liquidity_usd)
    vol = float(s.gate.min_volume_24h_usd)
    tx = int(s.gate.min_txns_24h)

    if pass_rate < target:
        strength = 0.05 + (s.aggressiveness / 100.0) * 0.18
        liq *= (1.0 - strength)
        vol *= (1.0 - strength)
        tx = int(round(tx * (1.0 - (strength * 0.8))))
        report["notes"].append(f"Loosened thresholds by ~{strength:.0%}.")
    elif pass_rate > target * 1.6:
        strength = 0.03 + (1.0 - (s.aggressiveness / 100.0)) * 0.07
        liq *= (1.0 + strength)
        vol *= (1.0 + strength)
        tx = int(round(tx * (1.0 + (strength * 0.7))))
        report["notes"].append(f"Tightened thresholds by ~{strength:.0%}.")
    else:
        report["notes"].append("Within tolerance; no calibration.")
        return s, report

    liq = clamp(liq, liq_lo, liq_hi)
    vol = clamp(vol, vol_lo, vol_hi)
    tx = int(clamp(tx, tx_lo, tx_hi))

    s.gate.min_liquidity_usd = float(liq)
    s.gate.min_volume_24h_usd = float(vol)
    s.gate.min_txns_24h = int(tx)

    after = {
        "min_liq": s.gate.min_liquidity_usd,
        "min_vol": s.gate.min_volume_24h_usd,
        "min_tx": s.gate.min_txns_24h,
    }

    report["changed"] = True
    report["before"] = before
    report["after"] = after
    return s, report

# -------------------------
# CANDIDATES + SCAN
# -------------------------
def build_candidates(s: Settings, watchlist: List[dict], pasted_text: str = "") -> List[dict]:
    pairs: List[dict] = []
    seen = set()

    # Discover per chain
    for cid in s.chains:
        discovered = resolve_pairs_from_search(cid, s.candidates_per_chain)
        for p in discovered:
            chain_id = p.get("chainId", "")
            pair_id = p.get("pairAddress") or p.get("pairId") or ""
            if not chain_id or not pair_id:
                continue
            key = f"{chain_id}:{pair_id}"
            if key in seen:
                continue
            seen.add(key)
            pairs.append(p)

    # Include pinned watchlist
    for item in watchlist:
        if not isinstance(item, dict):
            continue
        chain_id = item.get("chainId", "")
        pair_id = item.get("pairId", "")
        if chain_id and pair_id:
            key = f"{chain_id}:{pair_id}"
            if key in seen:
                continue
            data = api_pair(chain_id, pair_id)
            if data and data.get("pair"):
                p = data["pair"]
                seen.add(key)
                pairs.append(p)

    # Paste targets
    targets = extract_targets(pasted_text or "")
    for t in targets:
        if t["type"] == "address":
            best = resolve_best_pair_any_chain(t["value"], s.chains)
            if best:
                chain_id = best.get("chainId", "")
                pair_id = best.get("pairAddress") or best.get("pairId") or ""
                if chain_id and pair_id:
                    key = f"{chain_id}:{pair_id}"
                    if key not in seen:
                        seen.add(key)
                        pairs.append(best)
        elif t["type"] == "name":
            data = api_search(t["value"])
            if not data:
                continue
            best = _pick_best_pair(data.get("pairs", []), chain_whitelist=s.chains)
            if best:
                chain_id = best.get("chainId", "")
                pair_id = best.get("pairAddress") or best.get("pairId") or ""
                if chain_id and pair_id:
                    key = f"{chain_id}:{pair_id}"
                    if key not in seen:
                        seen.add(key)
                        pairs.append(best)

    return pairs

def scan_radar(s: Settings, watchlist: List[dict], pasted_text: str = "") -> Tuple[List[dict], List[dict]]:
    raw_pairs = build_candidates(s, watchlist, pasted_text=pasted_text)

    features: List[dict] = []
    for p in raw_pairs:
        f = pair_to_fields(p)
        if not f["chainId"] or not f["pairId"]:
            continue
        features.append(f)

    # Auto-calibrate (optional)
    if s.auto_calibrate:
        s2, report = auto_calibrate_thresholds(s, features)
        if report.get("changed"):
            save_settings(s2)
            st.session_state["settings"] = s2
            st.session_state["last_calibration_report"] = report
            s = s2

    decisions: List[dict] = []
    for f in features:
        d = decide_action(f, s)
        decisions.append({
            "ts": now_ts(),
            "chainId": f["chainId"],
            "pairId": f["pairId"],
            "dexId": f["dexId"],
            "baseSymbol": f["baseSymbol"],
            "quoteSymbol": f["quoteSymbol"],
            "url": f["url"],
            "features": f,
            "decision": d,
        })

    # Persist decisions
    for r in decisions:
        f = r["features"]
        d = r["decision"]
        record_hash = sha1(f"{r['chainId']}|{r['pairId']}|{d['action']}|{d['priority']:.6f}|{d['confidence']:.6f}")

        evidence = json.dumps({
            "reasons": d["reasons"],
            "tags": d["score"]["tags"],
            "hazard_triggers": d["hazard"]["hazard_triggers"],
            "buy_pressure": d["score"]["buy_pressure"],
            "sell_pressure": d["score"]["sell_pressure"],
            "pc": {"h1": f["pc1h"], "h6": f["pc6h"], "h24": f["pc24h"]},
            "liqUsd": f["liquidityUsd"],
            "vol24h": f["volumeH24"],
            "entropy": d["entropy"],
            "gate_pass": d["gate_pass"],
            "integrity_pass": d["integrity_pass"],
        }, ensure_ascii=False)

        db_row = {
            "ts": r["ts"],
            "chainId": r["chainId"],
            "pairId": r["pairId"],
            "baseSymbol": r["baseSymbol"],
            "quoteSymbol": r["quoteSymbol"],
            "dexId": r["dexId"],

            "action": d["action"],
            "confidence": d["confidence"],
            "priority": d["priority"],
            "strategy": d["strategy"],
            "reasons": ", ".join(d["reasons"]),

            "sizing": d["sizing"],
            "stop_hint": d["stop_hint"],
            "tp_hint": d["tp_hint"],

            "record_hash": record_hash,

            "hazard_score": d["hazard"]["hazard_score"],
            "hazard_window": d["hazard"]["hazard_window"],
            "short_ready": d["hazard"]["short_ready"],
            "hazard_triggers": ", ".join(d["hazard"]["hazard_triggers"]),

            "entropy_crash_days": d["entropy"]["crash_days"],
            "entropy_peak_days": d["entropy"]["peak_days"],
            "entropy_verdict": d["entropy"]["verdict"],
            "entropy_bias": d["entropy"]["bias"],

            "evidence": evidence,
            "meta_json": json.dumps({
                "score": d["score"],
                "entropy_mode": s.entropy_mode
            }, ensure_ascii=False),
        }
        db_insert_decision(db_row)

    return decisions, features

# -------------------------
# SESSION INIT
# -------------------------
db_init()

if "settings" not in st.session_state:
    st.session_state["settings"] = load_settings()
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = load_watchlist()
if "last_scan" not in st.session_state:
    st.session_state["last_scan"] = None
if "last_scan_time" not in st.session_state:
    st.session_state["last_scan_time"] = None
if "auto_refresh" not in st.session_state:
    st.session_state["auto_refresh"] = True
if "last_refresh_epoch" not in st.session_state:
    st.session_state["last_refresh_epoch"] = time.time()
if "last_calibration_report" not in st.session_state:
    st.session_state["last_calibration_report"] = None

# -------------------------
# HEADER
# -------------------------
c1, c2 = st.columns([1, 10])
with c1:
    st.title("⚡")
with c2:
    st.title("ALPHA PREDATOR // BUY+SHORT GOD MODE")
    st.markdown("**AUTO-SCANNED OPPORTUNITY RADAR + DETERMINISTIC CNE KERNEL**")
    st.caption(f"{APP_VERSION} · Not financial advice · Logged · Timezone: America/Chicago")

# -------------------------
# SIDEBAR
# -------------------------
s: Settings = st.session_state["settings"]
wl: List[dict] = st.session_state["watchlist"]

with st.sidebar:
    st.header("🎛️ Controls")

    s.refresh_interval_sec = int(st.slider("Refresh interval (sec)", 10, 180, int(s.refresh_interval_sec)))
    s.top_n = int(st.slider("Top N (BUY + SHORT)", 5, 50, int(s.top_n)))
    s.candidates_per_chain = int(st.slider("Candidates per chain", 10, 250, int(s.candidates_per_chain)))

    st.markdown("---")
    st.subheader("Radar Settings")
    s.auto_calibrate = st.toggle("v2 Auto-Calibrate", value=bool(s.auto_calibrate))
    s.aggressiveness = float(st.slider("Aggressive ↔ Defensive", 0.0, 100.0, float(s.aggressiveness)))
    st.caption("Auto-calibrate adjusts only existing thresholds within hard bounds. Deterministic + logged.")

    st.markdown("---")
    st.subheader("Watchable Chains")
    s.chains = st.multiselect("Chains", DEFAULT_CHAINS, default=s.chains)

    st.markdown("---")
    st.subheader("Kernel Settings")
    st.markdown("**Gate (NO_TRADE unless passes)**")
    s.gate.min_liquidity_usd = float(st.number_input("Min liquidity (USD)", min_value=0.0, value=float(s.gate.min_liquidity_usd), step=1000.0))
    s.gate.min_volume_24h_usd = float(st.number_input("Min volume 24h (USD)", min_value=0.0, value=float(s.gate.min_volume_24h_usd), step=1000.0))
    s.gate.min_txns_24h = int(st.number_input("Min txns 24h", min_value=0, value=int(s.gate.min_txns_24h), step=5))

    st.markdown("**Integrity (anti-garbage)**")
    s.integrity.max_fdv_usd = float(st.number_input("Max FDV (USD)", min_value=1e6, value=float(s.integrity.max_fdv_usd), step=1e9, format="%.0f"))
    s.integrity.reject_email_names = st.toggle("Reject email-like tokens", value=bool(s.integrity.reject_email_names))

    st.markdown("**Signal thresholds (time-series)**")
    s.signals.buy_momo_pc1 = float(st.number_input("BUY min pc1h", value=float(s.signals.buy_momo_pc1), step=0.25))
    s.signals.buy_momo_pc6 = float(st.number_input("BUY min pc6h", value=float(s.signals.buy_momo_pc6), step=0.25))
    s.signals.buy_momo_pc24 = float(st.number_input("BUY min pc24h", value=float(s.signals.buy_momo_pc24), step=0.5))
    s.signals.short_momo_pc1 = float(st.number_input("SHORT max pc1h", value=float(s.signals.short_momo_pc1), step=0.25))
    s.signals.short_momo_pc6 = float(st.number_input("SHORT max pc6h", value=float(s.signals.short_momo_pc6), step=0.25))
    s.signals.short_momo_pc24 = float(st.number_input("SHORT max pc24h", value=float(s.signals.short_momo_pc24), step=0.5))
    s.signals.min_buy_pressure = float(st.slider("Min buy pressure", 0.45, 0.75, float(s.signals.min_buy_pressure), 0.01))
    s.signals.min_sell_pressure = float(st.slider("Min sell pressure", 0.45, 0.80, float(s.signals.min_sell_pressure), 0.01))

    st.markdown("---")
    st.subheader("Entropy Integration (BUY/SHORT)")
    modes = ["Standalone only", "Veto (risk-off)", "Generator (BUY/SHORT)"]
    s.entropy_mode = st.selectbox("Mode", modes, index=modes.index(s.entropy_mode) if s.entropy_mode in modes else 1)
    s.entropy_stress = float(st.slider("Whale stress test", 1.0, 5.0, float(s.entropy_stress), 0.1))
    s.entropy_short_hz = int(st.slider("SHORT horizon (days)", 1, 14, int(s.entropy_short_hz)))
    s.entropy_buy_hz = int(st.slider("BUY horizon (days)", 10, 60, int(s.entropy_buy_hz)))

    st.markdown("---")
    st.caption(f"Version: {APP_VERSION}")
    st.caption(f"DB: {DB_PATH} · Watchlist: {WATCHLIST_PATH} · Settings: {SETTINGS_PATH}")

    colx, coly = st.columns(2)
    with colx:
        if st.button("💾 Save settings"):
            save_settings(s)
            st.success("Saved settings.json")
    with coly:
        if st.button("🧨 Reset DB"):
            db_reset()
            st.success("DB reset. (Old data removed)")

    st.session_state["settings"] = s

# -------------------------
# TABS
# -------------------------
tab_home, tab_forecast, tab_entropy, tab_discover, tab_manage = st.tabs(
    ["🏠 Home", "⚠️ Forecast", "⏳ Entropy (BUY/SHORT)", "🔎 Discover", "🧰 Manage"]
)

# -------------------------
# HOME
# -------------------------
with tab_home:
    st.subheader(f"Auto-scanned Opportunity Radar (Top {s.top_n})")
    st.markdown(f"<div class='muted'>Chains: {', '.join(s.chains)}</div>", unsafe_allow_html=True)

    with st.expander("📋 Optional: paste DexScreener page text to boost discovery", expanded=False):
        pasted = st.text_area("Paste raw page text (addresses/names). Used only during Scan.", height=180)

    colA, colB, colC = st.columns([1, 1, 1.3])
    with colA:
        scan_now = st.button("🚀 Scan radar now")
    with colB:
        st.session_state["auto_refresh"] = st.toggle("Auto-refresh enabled", value=st.session_state["auto_refresh"])
    with colC:
        st.write(f"Last scan: **{st.session_state['last_scan_time'] or '—'}**")

    if scan_now:
        with st.spinner("Scanning candidates + running deterministic kernel..."):
            decisions, _feats = scan_radar(s, wl, pasted_text=pasted)
        st.session_state["last_scan"] = decisions
        st.session_state["last_scan_time"] = now_hms()
        st.session_state["last_refresh_epoch"] = time.time()
        st.success(f"SCAN COMPLETE: {len(decisions)} candidates evaluated")
        st_rerun_safe()

    if st.session_state["auto_refresh"]:
        elapsed = time.time() - st.session_state["last_refresh_epoch"]
        if elapsed >= max(10, int(s.refresh_interval_sec)):
            st.session_state["last_refresh_epoch"] = time.time()
            st_rerun_safe()

    decisions = st.session_state.get("last_scan") or []
    if not decisions:
        st.info("System idle. Click **Scan radar now** to populate Top BUY/SHORT.")
    else:
        buy_rows = [r for r in decisions if r["decision"]["action"] == "BUY"]
        short_rows = [r for r in decisions if r["decision"]["action"] == "SHORT"]

        buy_rows = sorted(buy_rows, key=lambda x: (x["decision"]["priority"], x["decision"]["confidence"]), reverse=True)[:s.top_n]
        short_rows = sorted(short_rows, key=lambda x: (x["decision"]["priority"], x["decision"]["confidence"]), reverse=True)[:s.top_n]

        st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
        st.markdown(f"### Top {s.top_n} BUY")
        if not buy_rows:
            st.write("No items to show.")
        else:
            cols = st.columns(3)
            for i, r in enumerate(buy_rows):
                f = r["features"]; d = r["decision"]
                with cols[i % 3]:
                    st.markdown(f"""
                    <div class="coin-card">
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div style="font-weight:bold;font-size:1.05em;">
                          {f['baseSymbol']} <span class="small">{f['chainId']}/{f['quoteSymbol']} · {f['dexId']}</span>
                        </div>
                        <span class="badge badge-buy">BUY</span>
                      </div>
                      <div class="muted" style="margin-top:6px;">
                        pc1={f['pc1h']:.2f}% · pc6={f['pc6h']:.2f}% · pc24={f['pc24h']:.2f}%
                      </div>
                      <div class="muted" style="margin-top:6px;">
                        Hazard: {d['hazard']['hazard_window']} · HZ={d['hazard']['hazard_score']:.0f}
                        · Entropy: {d['entropy']['verdict']} ({d['entropy']['crash_days']}d)
                      </div>
                      <div class="metric-row"><span class="metric-label">PRICE (USD):</span><span class="metric-val">{compact_num(f['priceUsd'])}</span></div>
                      <div class="metric-row"><span class="metric-label">LIQ (USD):</span><span class="metric-val">{compact_num(f['liquidityUsd'])}</span></div>
                      <div class="metric-row"><span class="metric-label">VOL 24H:</span><span class="metric-val">{compact_num(f['volumeH24'])}</span></div>
                      <div class="metric-row"><span class="metric-label">TX 24H:</span><span class="metric-val">{f['txnsH24Buys']} buys / {f['txnsH24Sells']} sells</span></div>
                      <div class="muted" style="margin-top:8px;">{d['stop_hint']} · {d['tp_hint']}</div>
                      <a href="{f['url']}" target="_blank" class="trade-btn">OPEN PAIR</a>
                      <div class="muted" style="margin-top:8px;">Strategy: {d['strategy']} · Priority: {d['priority']:.3f} · Size: {d['sizing']}</div>
                      <div class="muted" style="margin-top:8px;">Reasons: {", ".join(d["reasons"]) or "-"}</div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
        st.markdown(f"### Top {s.top_n} SHORT")
        if not short_rows:
            st.write("No items to show.")
        else:
            cols = st.columns(3)
            for i, r in enumerate(short_rows):
                f = r["features"]; d = r["decision"]
                with cols[i % 3]:
                    st.markdown(f"""
                    <div class="coin-card">
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div style="font-weight:bold;font-size:1.05em;">
                          {f['baseSymbol']} <span class="small">{f['chainId']}/{f['quoteSymbol']} · {f['dexId']}</span>
                        </div>
                        <span class="badge badge-short">SHORT</span>
                      </div>
                      <div class="muted" style="margin-top:6px;">
                        pc1={f['pc1h']:.2f}% · pc6={f['pc6h']:.2f}% · pc24={f['pc24h']:.2f}%
                      </div>
                      <div class="muted" style="margin-top:6px;">
                        Hazard: {d['hazard']['hazard_window']} · HZ={d['hazard']['hazard_score']:.0f}
                        · Entropy: {d['entropy']['verdict']} ({d['entropy']['crash_days']}d)
                      </div>
                      <div class="metric-row"><span class="metric-label">PRICE (USD):</span><span class="metric-val">{compact_num(f['priceUsd'])}</span></div>
                      <div class="metric-row"><span class="metric-label">LIQ (USD):</span><span class="metric-val">{compact_num(f['liquidityUsd'])}</span></div>
                      <div class="metric-row"><span class="metric-label">VOL 24H:</span><span class="metric-val">{compact_num(f['volumeH24'])}</span></div>
                      <div class="metric-row"><span class="metric-label">TX 24H:</span><span class="metric-val">{f['txnsH24Buys']} buys / {f['txnsH24Sells']} sells</span></div>
                      <div class="muted" style="margin-top:8px;">{d['stop_hint']} · {d['tp_hint']}</div>
                      <a href="{f['url']}" target="_blank" class="trade-btn">OPEN PAIR</a>
                      <div class="muted" style="margin-top:8px;">Strategy: {d['strategy']} · Priority: {d['priority']:.3f} · Size: {d['sizing']}</div>
                      <div class="muted" style="margin-top:8px;">Reasons: {", ".join(d["reasons"]) or "-"}</div>
                    </div>
                    """, unsafe_allow_html=True)

# -------------------------
# FORECAST
# -------------------------
with tab_forecast:
    st.subheader("Forecast (Hazard windows + Entropy horizon)")
    decisions = st.session_state.get("last_scan") or []
    if not decisions:
        st.info("Run a scan first.")
    else:
        rows = []
        for r in decisions:
            f = r["features"]; d = r["decision"]
            rows.append({
                "ts": r["ts"],
                "chain": f["chainId"],
                "pairId": f["pairId"],
                "token": f["baseSymbol"],
                "quote": f["quoteSymbol"],
                "dex": f["dexId"],
                "action": d["action"],
                "priority": round(d["priority"], 4),
                "confidence": round(d["confidence"], 4),
                "hz": round(d["hazard"]["hazard_score"], 1),
                "hz_window": d["hazard"]["hazard_window"],
                "short_ready": d["hazard"]["short_ready"],
                "entropy_verdict": d["entropy"]["verdict"],
                "entropy_bias": d["entropy"]["bias"],
                "entropy_crash_days": d["entropy"]["crash_days"],
                "pc1h": round(f["pc1h"], 3),
                "pc6h": round(f["pc6h"], 3),
                "pc24h": round(f["pc24h"], 3),
                "liqUsd": round(f["liquidityUsd"], 2),
                "vol24h": round(f["volumeH24"], 2),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "⬇️ Download forecast CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="alpha_predator_forecast.csv",
            mime="text/csv"
        )

# -------------------------
# ENTROPY
# -------------------------
with tab_entropy:
    st.subheader("Entropy Monitor (BUY/SHORT overlay)")
    decisions = st.session_state.get("last_scan") or []
    if not decisions:
        st.info("Run a scan first.")
    else:
        rows = []
        for r in decisions:
            f = r["features"]; d = r["decision"]; e = d["entropy"]
            rows.append({
                "chain": f["chainId"],
                "token": f["baseSymbol"],
                "quote": f["quoteSymbol"],
                "action": d["action"],
                "entropy_verdict": e["verdict"],
                "entropy_bias": e["bias"],
                "crash_days": e["crash_days"],
                "peak_days": e["peak_days"],
                "vol_ratio": round(e["vol_ratio"], 4),
                "hype": round(e["hype_score"], 1),
                "liqUsd": round(f["liquidityUsd"], 2),
                "vol24h": round(f["volumeH24"], 2),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

# -------------------------
# DISCOVER
# -------------------------
with tab_discover:
    st.subheader("Discover / Quick Add")
    st.caption("Watchlist is saved to watchlist.json automatically.")

    col1, col2 = st.columns([1, 2.2])
    with col1:
        chain_pick = st.selectbox(
            "chainId",
            DEFAULT_CHAINS,
            index=DEFAULT_CHAINS.index("solana") if "solana" in DEFAULT_CHAINS else 0
        )
        st.caption(CHAIN_QUICK_HINTS.get(chain_pick, ""))

    with col2:
        pair_id = st.text_input("pair address / pairId", placeholder="0x... or base58...")

    if st.button("➕ Add to watchlist"):
        if chain_pick and pair_id:
            entry = {"chainId": chain_pick, "pairId": pair_id.strip()}
            if entry not in wl:
                wl.append(entry)
                st.session_state["watchlist"] = wl
                save_watchlist(wl)
                st.success("Added and saved to watchlist.json")
            else:
                st.warning("Already in watchlist.")
        else:
            st.error("Provide chainId and pairId.")

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.subheader("Pinned Watchlist")
    if not wl:
        st.info("Watchlist is empty.")
    else:
        st.dataframe(pd.DataFrame(wl), use_container_width=True)

# -------------------------
# MANAGE
# -------------------------
with tab_manage:
    st.subheader("Manage / Ledger")
    st.caption("Recent decisions stored in SQLite (includes evidence).")

    limit = st.slider("Ledger rows", 50, 1000, 250, 50)
    try:
        ledger_df = db_recent_decisions(limit=int(limit))
        st.dataframe(ledger_df, use_container_width=True)
        st.download_button(
            "⬇️ Download ledger CSV",
            ledger_df.to_csv(index=False).encode("utf-8"),
            file_name="alpha_predator_ledger.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Ledger read failed: {e}")

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.subheader("Maintenance")

    colm1, colm2 = st.columns(2)
    with colm1:
        if st.button("💾 Save watchlist"):
            save_watchlist(wl)
            st.success("Saved watchlist.json")
    with colm2:
        if st.button("🧹 Clear watchlist"):
            st.session_state["watchlist"] = []
            save_watchlist([])
            st.success("Cleared watchlist.json")

    if st.session_state.get("last_calibration_report"):
        st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
        st.subheader("Last Auto-Calibrate Report")
        st.json(st.session_state["last_calibration_report"])
