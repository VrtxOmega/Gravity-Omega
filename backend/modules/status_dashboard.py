#!/usr/bin/env python3
"""
VERITAS HYBRID - System Status Dashboard
Shows running processes and coordinator activity
"""

import subprocess
import time
from pathlib import Path

def show_status():
    print("=" * 60)
    print("VERITAS HYBRID SYSTEM STATUS")
    print("=" * 60)
    
    # Check processes
    result = subprocess.run(
        ["powershell", "-Command", "Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, @{Name='Cmd';Expression={(Get-CimInstance Win32_Process -Filter \"ProcessId = $($_.Id)\").CommandLine}}"],
        capture_output=True,
        text=True
    )
    
    processes = []
    for line in result.stdout.split('\n'):
        if 'hybrid_coordinator' in line:
            processes.append("✓ COORDINATOR RUNNING")
        elif 'python_monitor' in line:
            if 'AAVE' in line:
                processes.append("✓ AAVE Monitor")
            elif 'MORPHO' in line:
                processes.append("✓ MORPHO Monitor")
    
    if not processes:
        print("\n⚠️  NO PROCESSES RUNNING")
    else:
        print("\nActive Components:")
        for p in processes:
            print(f"  {p}")
    
    # Check queue
    queue_dir = Path("c:/Veritas_Lab/candidate_queue")
    if queue_dir.exists():
        queue_count = len(list(queue_dir.glob("*.json")))
        print(f"\nCandidate Queue: {queue_count} reports")
    
    # Show recent coordinator log
    log_file = Path("c:/Veritas_Lab/coordinator.log")
    if log_file.exists():
        print("\nRecent Coordinator Activity:")
        lines = log_file.read_text().split('\n')[-5:]
        for line in lines:
            if line.strip():
                print(f"  {line[:100]}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    while True:
        show_status()
        time.sleep(10)
