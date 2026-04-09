import sys
import os

SCRIPT = r"C:\Users\rlope\.gemini\antigravity\scratch\VERITAS_COMMAND_CENTER\veritas_canonical.py"
sys.path.append(os.path.dirname(SCRIPT))

from veritas_canonical import run_canonical_9_gate, calibrate_canonical

source_code = """
from typing import List

def fibonacci_sequence(n: int) -> List[int]:
    '''Calculate the Fibonacci sequence up to N.
    '''
    if n <= 0: return []
    elif n == 1: return [0]
    elif n == 2: return [0, 1]
    
    sequence = [0, 1]
    for i in range(2, n):
        next_value = sequence[-1] + sequence[-2]
        sequence.append(next_value)
    return sequence
"""

import time
start = time.time()
print("Starting run_canonical_9_gate...")
results, fhash = run_canonical_9_gate(source_code, "clean_math.py")
report = calibrate_canonical(results)
print(f"Time taken: {time.time() - start:.2f}s")
print("Report Envelope:", report.envelope)
print("Gate Summary:", report.gate_summary)
