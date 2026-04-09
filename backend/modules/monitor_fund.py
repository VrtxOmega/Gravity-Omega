#!/usr/bin/env python3
"""
Veritas Fund Monitor
Autonomous tracker for Hardware Fund progress
Monitors sovereign wallet and logs strikes until 4.0 ETH target achieved
"""

import time
from datetime import datetime
from web3 import Web3

# CONSTANTS
SOVEREIGN_WALLET = "0x36c54AF7aCe58E04eebc1cc593547d02803e5a7d"
HARDWARE_TARGET_ETH = 4.0
BASE_RPC = "https://mainnet.base.org"
POLL_INTERVAL = 30  # seconds

def monitor_hardware_fund():
    """Monitor wallet balance until hardware fund target is reached."""
    w3 = Web3(Web3.HTTPProvider(BASE_RPC))
    
    if not w3.is_connected():
        print("[ERROR] Failed to connect to Base RPC")
        return
    
    print(f"[MONITOR] Veritas Fund Monitor - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[TARGET] Hardware Fund: {HARDWARE_TARGET_ETH} ETH (Dual RTX 5090)")
    print(f"[WALLET] {SOVEREIGN_WALLET}")
    print("-" * 80)
    
    last_balance = 0
    strike_count = 0
    
    while True:
        try:
            # Get current balance
            balance_wei = w3.eth.get_balance(SOVEREIGN_WALLET)
            balance_eth = w3.from_wei(balance_wei, 'ether')
            
            # Detect strikes (balance increase)
            if balance_eth > last_balance:
                profit = balance_eth - last_balance
                strike_count += 1
                print(f"\n[STRIKE #{strike_count}] Profit: {profit:.6f} ETH")
                print(f"[BALANCE] Current: {balance_eth:.6f} ETH | Target: {HARDWARE_TARGET_ETH} ETH")
                progress = (balance_eth / HARDWARE_TARGET_ETH) * 100
                print(f"[PROGRESS] {progress:.2f}% to Hardware Fund")
                
                if balance_eth >= HARDWARE_TARGET_ETH:
                    print("\n" + "=" * 80)
                    print(f"[SUCCESS] HARDWARE FUND ACHIEVED!")
                    print(f"[FINAL] {balance_eth:.6f} ETH after {strike_count} strikes")
                    print(f"[TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print("=" * 80)
                    break
                
                last_balance = balance_eth
            
            # Heartbeat (every 5 minutes)
            current_time = datetime.now()
            if current_time.second < POLL_INTERVAL:
                print(f"[HEARTBEAT] {current_time.strftime('%H:%M:%S')} | Balance: {balance_eth:.6f} ETH | Strikes: {strike_count}")
            
            time.sleep(POLL_INTERVAL)
            
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(60)

if __name__ == "__main__":
    monitor_hardware_fund()
