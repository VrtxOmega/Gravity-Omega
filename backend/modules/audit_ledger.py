"""
Omega Claw — Audit Ledger
==========================
Append-only JSONL hash-chain audit trail.

Pattern: SovereignSpeak gate_seal (SHA-256 GENESIS chain).
Every assessment gets one immutable record. Never edited, only appended.
Chain integrity verifiable offline — no network, no LLM.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any


# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════

LEDGER_DIR = Path.home() / ".omega_claw"
LEDGER_PATH = LEDGER_DIR / "audit_ledger.jsonl"
GENESIS_HASH = "GENESIS"


# ══════════════════════════════════════════════════════════════
# DATA TYPES
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AuditRecord:
    """One immutable record per assessment."""
    timestamp: float
    filename: str
    file_hash: str
    gate_verdicts: List[Dict[str, Any]]
    envelope: str               # SOVEREIGN | SHIELDED | CONTAINED
    risk_score: float
    prev_hash: str
    seal_hash: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ══════════════════════════════════════════════════════════════
# CORE LEDGER
# ══════════════════════════════════════════════════════════════

class AuditLedger:
    """Append-only JSONL audit trail with SHA-256 hash chain.

    Invariants:
      - Records are NEVER deleted or edited.
      - Each record's seal_hash = SHA-256(prev_hash + canonical(payload)).
      - Chain starts from GENESIS.
      - verify_chain() proves no tampering.
    """

    def __init__(self, ledger_path: Optional[Path] = None):
        self._path = ledger_path or LEDGER_PATH
        os.makedirs(self._path.parent, exist_ok=True)

    def _get_prev_hash(self) -> str:
        """Read last seal_hash from ledger, or GENESIS if empty."""
        if not self._path.exists():
            return GENESIS_HASH
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines:
                    return GENESIS_HASH
                last = json.loads(lines[-1])
                return last.get("seal_hash", GENESIS_HASH)
        except (json.JSONDecodeError, IOError):
            return GENESIS_HASH

    def _compute_seal(self, prev_hash: str, payload: dict) -> str:
        """SHA-256(prev_hash + canonical(payload))."""
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(
            (prev_hash + canonical).encode("utf-8")
        ).hexdigest()

    def append(
        self,
        filename: str,
        file_hash: str,
        gate_verdicts: List[Dict[str, Any]],
        envelope: str,
        risk_score: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditRecord:
        """Create and append one assessment record. Returns the record."""
        prev = self._get_prev_hash()
        ts = time.time()

        payload = {
            "ts": ts,
            "filename": filename,
            "file_hash": file_hash,
            "gate_verdicts": gate_verdicts,
            "envelope": envelope,
            "risk_score": risk_score,
        }
        if metadata:
            payload["metadata"] = metadata

        seal = self._compute_seal(prev, payload)

        record = AuditRecord(
            timestamp=ts,
            filename=filename,
            file_hash=file_hash,
            gate_verdicts=gate_verdicts,
            envelope=envelope,
            risk_score=risk_score,
            prev_hash=prev,
            seal_hash=seal,
            metadata=metadata,
        )

        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=True) + "\n")

        return record

    def read_all(self) -> List[AuditRecord]:
        """Read all records. Returns empty list if no ledger."""
        if not self._path.exists():
            return []
        records = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                records.append(AuditRecord(**d))
        return records

    def read_last_n(self, n: int) -> List[AuditRecord]:
        """Read last N records efficiently."""
        if not self._path.exists():
            return []
        with open(self._path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        results = []
        for line in lines[-n:]:
            line = line.strip()
            if line:
                results.append(AuditRecord(**json.loads(line)))
        return results

    def verify_chain(self) -> tuple:
        """Verify entire hash chain from GENESIS.

        Returns:
            (is_valid: bool, records_checked: int, failure_index: int or -1)
        """
        records = self.read_all()
        if not records:
            return (True, 0, -1)

        expected_prev = GENESIS_HASH
        for i, rec in enumerate(records):
            if rec.prev_hash != expected_prev:
                return (False, i + 1, i)

            # Recompute seal
            payload = {
                "ts": rec.timestamp,
                "filename": rec.filename,
                "file_hash": rec.file_hash,
                "gate_verdicts": rec.gate_verdicts,
                "envelope": rec.envelope,
                "risk_score": rec.risk_score,
            }
            if rec.metadata:
                payload["metadata"] = rec.metadata

            recomputed = self._compute_seal(expected_prev, payload)
            if recomputed != rec.seal_hash:
                return (False, i + 1, i)

            expected_prev = rec.seal_hash

        return (True, len(records), -1)

    @property
    def count(self) -> int:
        """Number of records in ledger."""
        if not self._path.exists():
            return 0
        with open(self._path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())

    def clear(self):
        """DANGEROUS: Wipe the ledger. Only for testing."""
        if self._path.exists():
            self._path.unlink()
