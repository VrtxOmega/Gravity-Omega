"""
VERITAS Ω — Canonical Claim Metadata
ClaimID: ANCESTOR_VERIFY_001

[PRIMITIVES]
Primitive(name="START_PID", domain=Interval(low=1.0, high=4194304.0, inclusive_low=True, inclusive_high=True), units="ProcessID")
Primitive(name="FORBIDDEN_FOUND", domain=EnumSet(values={"TRUE", "FALSE"}), units=None)

[OPERATORS]
Operator(name="WALK_ANCESTORS", arity=1, input=["START_PID"], output="FORBIDDEN_FOUND", total=True)

[BOUNDARIES]
Boundary(name="B_NO_SHELL_ESCAPES", constraint="FORBIDDEN_FOUND = FALSE")

[REGIMES]
Regime(name="R_EVALUATE_TREE", predicate="START_PID >= 1.0")

[EVIDENCE]
EvidenceItem(id="e3", variable="FORBIDDEN_FOUND", value={"v": "FALSE"}, method={"protocol": "procfs_stat_traversal", "repeatable": True}, provenance={"source_id": "procfs", "tier": "A"})
"""

import os
import logging
from typing import List

class AncestorVerification:
    def __init__(self, forbidden_binaries: List[str] = None):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("ANCESTOR_VERIFY")
        self.forbidden = forbidden_binaries or ["/bin/bash", "/bin/sh", "/usr/bin/bash", "/usr/bin/sh"]

    def _get_ppid_and_exe(self, pid: int):
        try:
            with open(f"/proc/{pid}/stat", "r") as f:
                stat = f.read().split()
                ppid = int(stat[3])
                
            exe = os.readlink(f"/proc/{pid}/exe")
            return ppid, exe
        except OSError:
            return 0, "UNKNOWN"

    def verify_chain(self, start_pid: int) -> bool:
        """
        Walks up the PPID chain to PID 1.
        Returns False if any ancestor is in the forbidden list.
        Returns True if the chain is clean.
        """
        current_pid = start_pid
        chain = []
        
        while current_pid > 1:
            ppid, exe = self._get_ppid_and_exe(current_pid)
            if exe == "UNKNOWN" and ppid == 0:
                break
                
            chain.append((current_pid, exe))
            if exe in self.forbidden:
                self.logger.critical(f"[VIOLATION] Forbidden ancestor detected in chain: {exe} (PID: {current_pid})")
                return False
                
            current_pid = ppid

        formatted = " -> ".join([f"{e}({p})" for p, e in chain])
        self.logger.info(f"[PASS] Ancestor chain verified: {formatted}")
        return True

if __name__ == "__main__":
    av = AncestorVerification()
    av.verify_chain(os.getpid())
