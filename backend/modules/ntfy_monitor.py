#!/usr/bin/env python3
"""
Veritas ntfy Monitor
Sends push notifications for liquidation events and fund progress
"""

import time
import requests
from web3 import Web3

# CONSTANTS
SOVEREIGN_WALLET = "0x36c54AF7aCe58E04eebc1cc593547d02803e5a7d"
HARDWARE_TARGET_ETH = 4.0
BASE_RPC = "https://mainnet.base.org"
NTFY_TOPIC = "project_pipeline"
NTFY_SERVER = "https://ntfy.sh"
POLL_INTERVAL = 30  # seconds

def send_ntfy(title, message, priority=3, tags=None):
    """Send notification to ntfy"""
    try:
        headers = {
            "Title": title,
            "Priority": str(priority),
        }
        if tags:
            headers["Tags"] = ",".join(tags)
        
        response = requests.post(
            f"{NTFY_SERVER}/{NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers=headers
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[NTFY ERROR] {e}")
        return False

def monitor_with_notifications():
    """Monitor wallet and send ntfy notifications"""
    w3 = Web3(Web3.HTTPProvider(BASE_RPC))
    
    if not w3.is_connected():
        send_ntfy(
            "⚠️ Veritas Monitor Error",
            "Failed to connect to Base RPC",
            priority=4,
            tags=["warning"]
        )
        return
    
    # Startup notification
    send_ntfy(
        "🟢 Veritas V3 Online",
        f"Monitoring started\nTarget: {HARDWARE_TARGET_ETH} ETH\nWallet: {SOVEREIGN_WALLET[:10]}...",
        priority=3,
        tags=["white_check_mark"]
    )
    
    print(f"[NTFY] Monitor started - Topic: {NTFY_TOPIC}")
    print(f"[NTFY] Subscribe at: {NTFY_SERVER}/{NTFY_TOPIC}")
    
    last_balance = 0
    strike_count = 0
    last_heartbeat = time.time()
    
    while True:
        try:
            balance_wei = w3.eth.get_balance(SOVEREIGN_WALLET)
            balance_eth = float(w3.from_wei(balance_wei, 'ether'))
            
            # Detect strikes
            if balance_eth > last_balance and last_balance > 0:
                profit = balance_eth - last_balance
                strike_count += 1
                progress = (balance_eth / HARDWARE_TARGET_ETH) * 100
                
                send_ntfy(
                    f"💰 Strike #{strike_count}",
                    f"Profit: {profit:.6f} ETH\nBalance: {balance_eth:.6f} ETH\nProgress: {progress:.1f}%",
                    priority=4,
                    tags=["moneybag", "chart_with_upwards_trend"]
                )
                
                print(f"[STRIKE #{strike_count}] {profit:.6f} ETH | Balance: {balance_eth:.6f} ETH")
                
                # Check if target achieved
                if balance_eth >= HARDWARE_TARGET_ETH:
                    send_ntfy(
                        "🎯 HARDWARE FUND ACHIEVED!",
                        f"Final Balance: {balance_eth:.6f} ETH\nTotal Strikes: {strike_count}\n\nDual RTX 5090 fund complete!",
                        priority=5,
                        tags=["tada", "rocket", "fire"]
                    )
                    print("[SUCCESS] Hardware fund target achieved!")
                    break
            
            last_balance = balance_eth
            
            # Hourly heartbeat
            if time.time() - last_heartbeat > 3600:
                send_ntfy(
                    "💓 Heartbeat",
                    f"Balance: {balance_eth:.6f} ETH\nStrikes: {strike_count}\nStatus: Scanning",
                    priority=1,
                    tags=["heartbeat"]
                )
                last_heartbeat = time.time()
            
            time.sleep(POLL_INTERVAL)
            
        except Exception as e:
            print(f"[ERROR] {e}")
            send_ntfy(
                "⚠️ Monitor Error",
                str(e),
                priority=3,
                tags=["warning"]
            )
            time.sleep(60)

if __name__ == "__main__":
    monitor_with_notifications()
