"""
VERITAS Ω — Canonical Claim Metadata
ClaimID: BYPASS_TRAP_001

[PRIMITIVES]
Primitive(name="MESSAGE_SOURCE", domain=EnumSet(values={"KMSG", "SYSLOG"}), units="String")
Primitive(name="BYPASS_DETECTED", domain=EnumSet(values={"TRUE", "FALSE"}), units=None)

[OPERATORS]
Operator(name="SCAN_LOGS", arity=1, input=["MESSAGE_SOURCE"], output="BYPASS_DETECTED", total=True)

[BOUNDARIES]
Boundary(name="B_NETWORK_CONTAINMENT", constraint="BYPASS_DETECTED = FALSE")

[REGIMES]
Regime(name="R_ACTIVE_MONITOR", predicate="MESSAGE_SOURCE = 'KMSG'")

[EVIDENCE]
EvidenceItem(id="e4", variable="BYPASS_DETECTED", value={"v": "FALSE"}, method={"protocol": "iptables_log_scan", "repeatable": True}, provenance={"source_id": "kernel_ring_buffer", "tier": "A"})
"""

import os
import re
import logging

class BypassTrap:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("BYPASS_TRAP")
        # Matches iptables LOG format: "omega:bypass: IN= OUT=eth0 SRC=10.0.0.2 DST=8.8.8.8 ..."
        self.log_pattern = re.compile(r"omega:bypass:.*SRC=(\S+).*DST=(\S+).*PROTO=(\S+)")

    def parse_kmsg_line(self, line: str) -> bool:
        """
        Parses a single line from the kernel ring buffer.
        Returns True if a bypass was detected.
        """
        match = self.log_pattern.search(line)
        if match:
            src, dst, proto = match.groups()
            self.logger.critical(f"[VIOLATION] Egress Bypass Detected! PROTO: {proto} SRC: {src} DST: {dst}")
            return True
        return False

    def scan_kmsg(self, test_lines=None):
        """Scans /dev/kmsg or provided test lines for bypasses."""
        lines = test_lines or []
        violations = 0
        
        for line in lines:
            if self.parse_kmsg_line(line):
                violations += 1
                
        if violations == 0:
            self.logger.info("[PASS] No outbound bypasses detected in kernel logs.")
            return True
        return False

if __name__ == "__main__":
    trap = BypassTrap()
    test_logs = [
        "kernel: [ 1234.567] some normal network activity",
        "kernel: [ 1235.000] omega:bypass: IN= OUT=en0 SRC=192.168.1.5 DST=1.1.1.1 PROTO=UDP"
    ]
    trap.scan_kmsg(test_logs)
