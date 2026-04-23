"""
TITAN MONITOR — Scheduled check-in loop
Phase 1: Every 2 min for 30 min (15 checks)
Phase 2: Every 5 min for 2.5 hours (30 checks)
Stops early if gas wallet is drained.
"""
import time, sys, os, datetime
from pathlib import Path
from web3 import Web3

# Load credentials from .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass  # Fall back to system env vars

DRPC_KEY = os.environ.get("DRPC_KEY")
if not DRPC_KEY:
    print("[FATAL] DRPC_KEY not set. Export it or add to backend/.env")
    sys.exit(1)

HOT_WALLET = "0x36c54AF7aCe58E04eebc1cc593547d02803e5a7d"
CONTRACT = "0x669E67C644175F17b9664038681530B3042413AE"
LOG_FILE = r"c:\Veritas_Lab\titan_monitor.log"

w3 = Web3(Web3.HTTPProvider(f"https://lb.drpc.live/base/{DRPC_KEY}"))

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def check():
    try:
        balance = w3.eth.get_balance(HOT_WALLET)
        eth = Web3.from_wei(balance, 'ether')
        
        # Check contract code still exists
        code_len = len(w3.eth.get_code(CONTRACT))
        
        # Check latest block
        block = w3.eth.block_number
        
        status = "OK" if balance > 0 else "DRAINED"
        log(f"[{status}] Gas Wallet: {eth:.6f} ETH | Contract: {code_len} bytes | Block: {block}")
        
        if balance == 0:
            log("[ALERT] GAS WALLET DRAINED — SWAP REQUIRED")
            return False  # Signal to stop
        return True
    except Exception as e:
        log(f"[ERROR] Check failed: {e}")
        return True  # Keep running on transient errors

def main():
    log("=" * 60)
    log("TITAN MONITOR STARTED")
    log(f"  Hot Wallet: {HOT_WALLET}")
    log(f"  Contract:   {CONTRACT}")
    log(f"  Phase 1: Every 2 min for 30 min")
    log(f"  Phase 2: Every 5 min for 2.5 hours")
    log("=" * 60)
    
    # Phase 1: Every 2 minutes for 30 minutes (15 checks)
    log("[PHASE 1] Starting — 2 min intervals, 30 min duration")
    for i in range(15):
        if not check():
            log("[STOP] Wallet drained. Monitor exiting.")
            return
        if i < 14:
            time.sleep(120)  # 2 minutes
    
    # Phase 2: Every 5 minutes for 2.5 hours (30 checks)
    log("[PHASE 2] Starting — 5 min intervals, 2.5 hour duration")
    for i in range(30):
        if not check():
            log("[STOP] Wallet drained. Monitor exiting.")
            return
        if i < 29:
            time.sleep(300)  # 5 minutes
    
    log("[COMPLETE] Monitoring period finished. All checks passed.")

if __name__ == "__main__":
    main()
