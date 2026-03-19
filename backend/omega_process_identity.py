"""
VERITAS Ω — Canonical Claim Metadata
ClaimID: PROCESS_IDENTITY_001

[PRIMITIVES]
Primitive(name="PID", domain=Interval(low=1.0, high=4194304.0, inclusive_low=True, inclusive_high=True), units="ProcessID")
Primitive(name="EXE_PATH", domain=EnumSet(values={"KNOWN_BINARIES", "UNKNOWN"}), units="String")
Primitive(name="EXE_HASH", domain=EnumSet(values={"MATCH", "MISMATCH", "UNTRACKED"}), units="String")

[OPERATORS]
Operator(name="INSPECT_AND_HASH", arity=1, input=["PID"], output="EXE_HASH", total=True)

[BOUNDARIES]
Boundary(name="B_IDENTITY_SPOOF", constraint="EXE_HASH = MATCH OR EXE_HASH = UNTRACKED")

[REGIMES]
Regime(name="R_EVALUATE_PROC", predicate="PID >= 1.0")

[EVIDENCE]
EvidenceItem(id="e2", variable="EXE_HASH", value={"v": "MATCH"}, method={"protocol": "sha256_tofu", "repeatable": True}, provenance={"source_id": "procfs", "tier": "A"})
"""

import os
import hashlib
import logging

class BinaryIdentityCache:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("BINARY_IDENTITY")
        self.cache = {}

    def get_exe_path(self, pid: int) -> str:
        """Reads /proc/<pid>/exe to get the absolute path of the executable."""
        proc_exe = f"/proc/{pid}/exe"
        try:
            return os.readlink(proc_exe)
        except OSError as e:
            self.logger.warning(f"[WARNING] Could not read {proc_exe}: {e}")
            return "UNKNOWN"

    def hash_file(self, path: str) -> str:
        """Returns SHA256 hash of a file."""
        if path == "UNKNOWN" or not os.path.exists(path):
            return "UNTRACKED"
        
        sha256 = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except OSError as e:
            self.logger.error(f"[ERROR] Could not hash {path}: {e}")
            return "UNTRACKED"

    def verify_process(self, pid: int) -> bool:
        """
        TOFU verification. 
        Returns True if the process binary hash matches the cached hash or is new.
        Returns False if the hash has changed (spoofed/tampered).
        """
        path = self.get_exe_path(pid)
        if path == "UNKNOWN":
            return False
            
        current_hash = self.hash_file(path)
        if current_hash == "UNTRACKED":
            return False
            
        if path not in self.cache:
            # Trust On First Use
            self.cache[path] = current_hash
            self.logger.info(f"[PASS] TOFU Registered: {path} -> {current_hash[:8]}...")
            return True
        else:
            # Verify against cache
            expected_hash = self.cache[path]
            if current_hash != expected_hash:
                # Boundary violation: EXE_HASH = MISMATCH
                self.logger.critical(f"[VIOLATION] Identity Drift! {path} hash changed.")
                return False
                
            self.logger.info(f"[PASS] Identity Verified: {path}")
            return True

if __name__ == "__main__":
    cache = BinaryIdentityCache()
    cache.verify_process(os.getpid())
