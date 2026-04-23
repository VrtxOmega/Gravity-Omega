import hid
import sys
import time

# SYSTEM INVARIANT: Aggressive Fuzzing Node
# Target: MSI Raider GE78 HX RGB Controller
VID = 0x1038
PID = 0x2050

print("============================================================")
print("VERITAS Ω - INITIATING VECTOR DELTA: AGGRESSIVE FUZZER")
print("WARNING: May freeze keyboard EC. Hard-reset if unresponsive.")
print("============================================================\n")

# Phase A: Enumerate and isolate the control node (Usage Page 65472)
interfaces = hid.enumerate(VID, PID)
target_path = None

for info in interfaces:
    if info.get('usage_page') == 65472:
        target_path = info['path']
        print(f"[+] RGB Control Interface Found (MI_00/Usage 65472): {target_path}")
        break

if not target_path:
    print("CRITICAL VIOLATION: RGB Control Interface not found.")
    sys.exit(1)

# Phase B: The SteelSeries KLC Opcode Fuzzing Dictionary
# We are testing the most common proprietary handshakes for modern MSI/SteelSeries boards.
# Attempting to set a solid RED state.
test_opcodes = [
    0x0B, # KLC standard color init
    0x0D, # KLC commit state
    0x11, # KLC reactive state override
    0x0E  # Legacy MSI fallback
]

try:
    device = hid.device()
    device.open_path(target_path)
    device.set_nonblocking(1)
    print("\n[+] Connection Established. Initiating Fuzzing Sequence...\n")

    for opcode in test_opcodes:
        print(f"[*] Firing Payload -> Opcode: {hex(opcode)}")
        
        # Build standard 64-byte KLC Feature Report
        # Byte 0 is the Report ID (0x00)
        # Byte 1 is the Opcode
        payload = bytearray([0x00] * 65)
        payload[1] = opcode
        payload[2] = 0x00 # Zone All
        payload[3] = 0xFF # Red Max
        payload[4] = 0x00 # Green
        payload[5] = 0x00 # Blue
        
        try:
            # SteelSeries KLC primarily uses Feature Reports, not Output Reports
            bytes_sent = device.send_feature_report(payload)
            if bytes_sent > 0:
                print(f"    -> SUCCESS: {bytes_sent} bytes accepted via Feature Report.")
            else:
                # Fallback to standard write if Feature Report is rejected
                bytes_written = device.write(payload)
                if bytes_written > 0:
                    print(f"    -> SUCCESS: {bytes_written} bytes accepted via Output Report.")
                else:
                    print("    -> FAILED: Payload silently discarded.")
        except Exception as e:
            print(f"    -> BLOCKED: {e}")
            
        time.sleep(0.5) # Throttle to prevent EC flooding

    device.close()
    print("\nSequence Complete.")
    
except Exception as e:
    print(f"CRITICAL VIOLATION: Execution failed -> {e}")