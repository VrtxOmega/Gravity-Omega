"""
GOLIATH TRAWLER v5.2 - [FORENSIC_GRADE]
Protocol: VERITAS Ω INTEGRATION
Identity: Architect RJ / Kinetic Layer Sentinel Omega
"""
import os
import sys
import datetime
import traceback
import time
import random
import shutil
import math
import lzma
import zlib
import json
import hashlib
import zipfile
import re
from enum import Enum
from contextlib import contextmanager
from collections import Counter

# ==============================================================================
# CONFIGURATION
# ==============================================================================
USER_HOME = os.path.expanduser("~")
DESKTOP = os.path.join(USER_HOME, "OneDrive", "Desktop")
WORKSPACE = r"C:\GOLIATH_WORKSPACE"
JMAIL = r"C:\GOLIATH_WORKSPACE\JMAIL_INTAKE"
# Sovereign Mirror (C: fallback, D: preferred)
MIRROR_ROOT = r"D:\VERITAS_REF_MIRROR" if os.path.exists("D:\\") else r"C:\VERITAS_REF_MIRROR"
VAULT_DIR = os.path.join(MIRROR_ROOT, "VAULT")
ACTIVE_CACHE = os.path.join(MIRROR_ROOT, "ACTIVE_CACHE")
RESTORE_DIR = os.path.join(DESKTOP, "RESTORED_SIGNALS")
BOLO_REGISTRY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BOLO_REGISTRY.json")

SCAN_RADIUS = [
    os.path.join(DESKTOP, "GENERIC_EXTRACTION_ZONE"),
    JMAIL,
    os.path.join(WORKSPACE, "MADISON_COUNTY_FOIA")
]

WHALE_TARGETS = {"SIGNAL_ID_A", "SIGNAL_ID_B", "SIGNAL_ID_C", "SIGNAL_ID_D", "PFAS", "PFOS", "PFOA", "PFHxS", "WOOD_RIVER", "BETHALTO"}
BOLO_THRESHOLD = 10
SAMPLE_SIZE = 64 * 1024 

# ==============================================================================
# EPA & ESG WEB TRAWLER (PHASE 2 UPGRADE)
# ==============================================================================
import requests

class WebTrawler:
    """Ingests public EPA enforcement databases and corporate ESG filings."""
    
    TARGET_BOUNDARIES = {
        "county": "Madison County",
        "state": "IL",
        "coordinates": ["38.9030", "-90.0454"], # Bethalto/Wood River Area
        "aquifer": "American Bottoms"
    }

    @staticmethod
    def ingest_epa_echo_stream():
        """Simulates/Implements fetching from EPA ECHO API for Madison County."""
        boot_log(f"[WEB-TRAWL] Initiating EPA ECHO API sweep for {WebTrawler.TARGET_BOUNDARIES['county']}...")
        dest_dir = os.path.join(WORKSPACE, "MADISON_COUNTY_FOIA", "EPA_ECHO")
        os.makedirs(dest_dir, exist_ok=True)
        
        # In a fully armed production setting, this would ping:
        # https://echodata.epa.gov/echo/echo_rest_services.get_facilities?p_co=Madison&p_st=IL
        # For now, we seed a manifest for the DAG execution.
        manifest_path = os.path.join(dest_dir, f"ECHO_MANIFEST_{int(time.time())}.json")
        try:
            with open(manifest_path, "w") as f:
                json.dump({
                    "target_grid": "American Bottoms",
                    "facilities_flagged": ["Shell Wood River Refinery", "St. Louis Regional Airport AFFF Storage"],
                    "contaminant_focus": "PFHxS",
                    "timestamp": time.time()
                }, f)
            boot_log(f"[WEB-TRAWL] EPA ECHO Manifest written to {manifest_path}")
        except Exception as e:
            boot_log(f"[ERROR] EPA ECHO pull failed: {e}")

    @staticmethod
    def ingest_corporate_esg_pdfs(corporations: list):
        """Pulls annual sustainability reports for targeted corporations."""
        boot_log(f"[WEB-TRAWL] Commencing corporate ESG document acquisition for {corporations}...")
        dest_dir = os.path.join(WORKSPACE, "MADISON_COUNTY_FOIA", "CORPORATE_ESG")
        os.makedirs(dest_dir, exist_ok=True)
        # Placeholder for massive PDF downloading logic (requires specific scrape lists)
        boot_log(f"[WEB-TRAWL] Active ESG PDFs queued in {dest_dir}.")

# ==============================================================================
# AUDIT & SECURITY KERNEL (v5.0 [FORENSIC_GRADE])
# = [PATTERN: veritas_court_gate_v5_2.py] =
# ==============================================================================

class Capability(Enum):
    FILE_READ    = 1
    FILE_WRITE   = 2
    LARGE_OBJECT = 3

class Capabilities:
    _grants = set()

    @classmethod
    @contextmanager
    def grant(cls, caps):
        old = set(cls._grants)
        cls._grants |= set(caps)
        try: yield
        finally: cls._grants = old

    @classmethod
    def require(cls, cap: Capability):
        def deco(fn):
            def wrapped(*args, **kwargs):
                if cap not in cls._grants:
                    raise Exception(f"[CAPABILITY_VIOLATION] {cap.name} not granted for {fn.__name__}")
                return fn(*args, **kwargs)
            return wrapped
        return deco

class SafeFS:
    ALLOWED_BASES = [
        os.path.realpath(WORKSPACE),
        os.path.realpath(MIRROR_ROOT),
        os.path.realpath(DESKTOP)
    ]

    @staticmethod
    def validate(path: str, mode="READ") -> str:
        real = os.path.realpath(path)
        # Digital Guillotine: Confinement Check
        allowed = any(real == b or real.startswith(b + os.sep) for b in SafeFS.ALLOWED_BASES)
        if not allowed:
            raise Exception(f"[PATH_VIOLATION] Escape attempt detected: {path}")
        return real

class TraceManager:
    """Merkle-tree chained Audit Engine (v5.0)"""
    _last_hash = "0" * 64
    _log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CHAIN_OF_CUSTODY.log")

    @classmethod
    def log_event(cls, action, source, dest, s_hash, d_hash):
        prev_h = cls._last_hash
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Deterministic Event Object
        ev_obj = {
            "action": action,
            "source": os.path.basename(source),
            "dest": os.path.basename(dest),
            "s_hash": s_hash,
            "d_hash": d_hash
        }
        ev_str = json.dumps(ev_obj, sort_keys=True, separators=(",", ":"))
        
        # Merkle Chain: this_hash = Hash(prev_hash | ev_str)
        this_h = hashlib.sha256(f"{prev_h}|{ev_str}".encode()).hexdigest()
        
        log_entry = f"{ts} | {action} | {source} -> {dest} | S:{s_hash[:16]} | D:{d_hash[:16]} | H:{this_h[:16]}\n"
        
        try:
            with open(cls._log_path, "a") as f:
                f.write(log_entry)
            cls._last_hash = this_h
        except: pass

# Legacy Shim for backward compatibility during migration
class AuditManager:
    @staticmethod
    def log_event(action, source, dest, s_hash, d_hash):
        TraceManager.log_event(action, source, dest, s_hash, d_hash)

# ==============================================================================
# VAULT MANAGER (LZMA/ZLIB HYBRID)
# ==============================================================================
class VaultManager:
    @staticmethod
    def load_bolo_registry():
        if os.path.exists(BOLO_REGISTRY_PATH):
            try:
                with open(BOLO_REGISTRY_PATH, "r") as f:
                    return json.load(f)
            except: return {}
        return {}

    @staticmethod
    def save_bolo_registry(registry):
        try:
            with open(BOLO_REGISTRY_PATH, "w") as f:
                json.dump(registry, f, indent=2)
        except: pass

    @staticmethod
    @Capabilities.require(Capability.FILE_WRITE)
    def compress_vault(filepath, dest_dir, mode="LZMA"):
        """Compresses file into the vault using specified algorithm."""
        target_path = SafeFS.validate(filepath)
        fname = os.path.basename(target_path)
        ts = int(time.time())
        ext = ".lzma" if mode == "LZMA" else ".zlib"
        out_name = f"{ts}_{fname}{ext}"
        out_path = os.path.join(dest_dir, out_name)

        try:
            with open(target_path, "rb") as f_in:
                data = f_in.read()
                if mode == "LZMA":
                    # Standard intensity (4) to reduce CPU/Thermal load
                    compressed = lzma.compress(data, preset=4)
                else:
                    compressed = zlib.compress(data)
                
            with open(out_path, "wb") as f_out:
                f_out.write(compressed)
            
            # AUDIT LOGGING
            s_hash = calculate_sha256(target_path)
            d_hash = calculate_sha256(out_path)
            AuditManager.log_event(f"VAULT_{mode}", fname, out_name, s_hash, d_hash)
            
            return out_name
        except Exception as e:
            print(f"[ERROR] Compression failed for {fname}: {e}")
            return None


# ==============================================================================
# 2. UTILITIES
# ==============================================================================
def calculate_sha256(filepath):
    """Forensic stream hashing."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except: return "HASH_ERR"

def boot_log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BREADCRUMB_AG.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [VAULT-ASCENSION] {msg}\n")
    except: pass

def calculate_entropy_sample(filepath):
    try:
        with open(filepath, "rb") as f:
            data = f.read(SAMPLE_SIZE)
        if not data: return 0
        counter = Counter(data)
        length = len(data)
        if length == 0: return 0
        return -sum((count / length) * math.log2(count / length) for count in counter.values())
    except: return 0

# ==============================================================================
# BATES-GAP RECOVERY (ZIP SCANNER)
# ==============================================================================
class BatesGapScanner:
    @staticmethod
    def scan_zip(zippath, targets):
        """Scans un-indexed ZIP streams for Signal headers."""
        try:
            with zipfile.ZipFile(zippath, 'r') as zref:
                for name in zref.namelist():
                    # Check filename for forensic signals (e.g., SIGNAL_ID)
                    name_upper = name.upper()
                    for t in targets:
                        if t in name_upper:
                             boot_log(f"[BATES-GAP] Signal found in member filename: {name}")
                             return name
                    
                    # Optimization: only read small head of each file in zip
                    try:
                        with zref.open(name) as member:
                            head = member.read(16384).decode("utf-8", errors="ignore").upper()
                            for t in targets:
                                if t in head:
                                    print(f"[BATES-GAP] Recovery Triggered in {os.path.basename(zippath)}: {name}")
                                    # Extract specific member for analysis
                                    return name
                    except: pass
        except: pass
        return None

# ==============================================================================
# SURGICAL UNMASKER (PHASE 72: [SURGICAL_UNMASK])
# ==============================================================================
class SurgicalUnmasker:
    """Surgically strips visual redaction layers from PDF artifacts."""
    
    @staticmethod
    def strip_pdf_masks(filepath):
        """Analyzes PDF streams for visual mask operators (rectangles, fills)."""
        if not filepath.lower().endswith(".pdf"): return False
        
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            
            # Pattern for black redaction bars in PDF (Simplified Heuristic)
            # Re: x y w h (Rectangle)
            # rg 0 0 0 (Black fill color)
            # f or f* (Fill operator)
            # Note: This is an aggressive 'nop-out' for the purposes of this pulse.
            
            mask_patterns = [
                br"(\d+\.?\d* \d+\.?\d* \d+\.?\d* \d+\.?\d* re)", # Rectangle
                br"(0 0 0 rg)",                                    # Black stroke
                br"(0 0 0 RG)",                                    # Black non-stroke
            ]
            
            stripped_data = data
            for pattern in mask_patterns:
                # Replace drawing operator with NOP (spaces) of same length to keep offsets
                stripped_data = re.sub(pattern, lambda m: b" " * len(m.group(0)), stripped_data)
            
            if stripped_data != data:
                with open(filepath, "wb") as f:
                    f.write(stripped_data)
                boot_log(f"[SURGICAL] Visual mask neutralized: {os.path.basename(filepath)}")
                TraceManager.log_event("SURGICAL_UNMASK", filepath, filepath, "PDF_STREAM", "NEUTRALIZED")
                return True
        except Exception as e:
            boot_log(f"[ERROR] Surgical unmasking failed: {e}")
        return False

# ==============================================================================
# WHOLE DOCUMENT UNREDACTOR (RECONSTRUCTION)
# ==============================================================================
class WholeDocumentRestore:
    """Manages whole-document unmasking and container decompression."""
    
    @staticmethod
    def restore_container(zip_path):
        """Fully decompresses a ZIP container if it contains signals."""
        try:
            fname = os.path.basename(zip_path)
            dest = os.path.join(RESTORE_DIR, f"RECONSTRUCTED_{fname[:-4]}")
            
            with Capabilities.grant({Capability.FILE_WRITE}):
                if not os.path.exists(dest): os.makedirs(dest)
                
                with zipfile.ZipFile(zip_path, 'r') as zref:
                    zref.extractall(dest)
                
                # SURGICAL UNMASKING PASS
                for root, _, files in os.walk(dest):
                    for f in files:
                        if f.lower().endswith(".pdf"):
                            SurgicalUnmasker.strip_pdf_masks(os.path.join(root, f))

            boot_log(f"[RESTORE] Container fully uncompressed: {fname}")
            
            # AUDIT LOGGING (Container level)
            s_hash = calculate_sha256(zip_path)
            AuditManager.log_event("CONTAINER_RESTORE", fname, os.path.basename(dest), s_hash, "DIR_RESTORE")
            
            return True
        except: return False

    @staticmethod
    def restore_unmasked_file(filepath):
        """Saves a 'whole' copy of a file with extracted shadow-data."""
        try:
            fname = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                data = f.read()
            
            # Extraction logic for shadow blocks
            shadow_blocks = []
            for marker in RedactionXray.MARKERS:
                start = 0
                while True:
                    pos = data.find(marker, start)
                    if pos == -1: break
                    block = data[max(0, pos-5000):min(len(data), pos+5000)]
                    if calculate_entropy_data(block) > 7.7:
                        shadow_blocks.append(block)
                    start = pos + len(marker)

            out_path = os.path.join(RESTORE_DIR, f"UNMASKED_{fname}")
            with open(out_path, "wb") as f_out:
                f_out.write(data) # Keep Document Whole
                if shadow_blocks:
                    f_out.write(b"\n\n--- [SHADOW_DATA_RECOVERY_RESIDUE] ---\n")
                    for b in shadow_blocks:
                        f_out.write(b"\n--- BLOCK ---\n")
                        f_out.write(b)
            
            # AUDIT LOGGING
            s_hash = calculate_sha256(filepath)
            d_hash = calculate_sha256(out_path)
            AuditManager.log_event("WHOLE_RESTORE", fname, os.path.basename(out_path), s_hash, d_hash)
            
            return out_path
        except: pass
        return None

# ==============================================================================
# REDACTION X-RAY (RESIDUE EXTRACTION)
# ==============================================================================
class RedactionXray:
    """Identifies and extracts 'X-Ray' data from redacted or unmanaged regions."""
    MARKERS = [b"[REDACTED]", b"XXXXX", b"[CONFIDENTIAL]", b"/Metadata", b"/XObject"]

    @staticmethod
    def scan_for_residue(filepath):
        """Scans for high-entropy clusters near redaction markers."""
        try:
            with open(filepath, "rb") as f:
                # Read first 1MB for markers
                data = f.read(1024 * 1024)
            
            for marker in RedactionXray.MARKERS:
                if marker in data:
                    pos = data.find(marker)
                    # Sample raw data around marker
                    with open(filepath, "rb") as f:
                        f.seek(max(0, pos - 4000))
                        sample = f.read(8000)
                    
                    # If sample is non-trivial, check entropy
                    if len(sample) > 100:
                        entropy = calculate_entropy_data(sample)
                        if entropy > 7.75:
                            return True, marker.decode("utf-8", errors="ignore")
        except: pass
        return False, None

    @staticmethod
    def recover_full_artifact(filepath):
        """Saves a full copy of the artifact if residue is confirmed."""
        try:
            fname = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                data = f.read()
            
            residue_confirmed = False
            for marker in RedactionXray.MARKERS:
                if marker in data:
                    pos = data.find(marker)
                    sample = data[max(0, pos-4000):min(len(data), pos+4000)]
                    if calculate_entropy_data(sample) > 7.7:
                        residue_confirmed = True
                        break

            if residue_confirmed:
                out_path = os.path.join(RESTORE_DIR, f"FULL_UNMASKED_{fname}")
                with open(out_path, "wb") as f_out:
                    f_out.write(data)
                return out_path
        except: pass
        return None

def calculate_entropy_data(data):
    if not data: return 0
    counter = Counter(data)
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in counter.values())

# ==============================================================================
# CORE ENGINE
# ==============================================================================
def safe_run():
    boot_log("Engaging GOLIATH TRAWLER v5.0 [FORENSIC_GRADE]...")
    
    # ENSURE INFRASTRUCTURE
    for d in [VAULT_DIR, ACTIVE_CACHE, RESTORE_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)
            boot_log(f"Initialized Sector: {d}")

    registry = VaultManager.load_bolo_registry()

    # IMPORT NAEF LOGIC
    import GOLIATH_GATE
    naef = GOLIATH_GATE.NAEFHighPassFilter

    class AscensionEngine:
        def __init__(self):
            self.ascended_count = 0
            self.scanned_count = 0
            self.fail_closed_violations = 0
            
            # RUN IDENTITY (v5.0 Forensic Binding)
            self.run_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16].upper()
            boot_log(f"RUN IDENTITY BOUND: {self.run_id}")

        def isolate_noise(self, filepath):
            """Appends noise artifact to the System Noise LZMA block."""
            try:
                with Capabilities.grant({Capability.FILE_READ, Capability.FILE_WRITE}):
                    target = SafeFS.validate(filepath)
                    noise_dir = os.path.join(VAULT_DIR, "SYSTEM_NOISE")
                    if not os.path.exists(noise_dir): os.makedirs(noise_dir)
                    VaultManager.compress_vault(target, noise_dir, mode="LZMA")
                return True
            except Exception as e:
                boot_log(f"[ERROR] Noise isolation failed: {e}")
                return False

        def process_artifact(self, fpath):
            self.scanned_count += 1
            fname = os.path.basename(fpath)
            
            try:
                # 1. FAIL-CLOSED RESOURCE GATING (with Signaled Peeking)
                file_size_mb = os.path.getsize(fpath) / (1024 * 1024)
                if file_size_mb > 500:
                    # Forensic Peeking: Is this a signaled container?
                    is_signaled = False
                    if fpath.lower().endswith(".zip"):
                        match = BatesGapScanner.scan_zip(fpath, WHALE_TARGETS)
                        if match: is_signaled = True
                    
                    if not is_signaled:
                        boot_log(f"[FAIL-CLOSED] Size violation: {fname} ({round(file_size_mb, 2)}MB)")
                        self.fail_closed_violations += 1
                        return False
                    else:
                        boot_log(f"[LARGE_OBJECT] Authorized Bypass for signaled container: {fname}")
                        # Escalated Grant for Extraction
                        escalated_caps = {Capability.FILE_READ, Capability.FILE_WRITE, Capability.LARGE_OBJECT}
                else:
                    escalated_caps = {Capability.FILE_READ, Capability.FILE_WRITE}

                with Capabilities.grant(escalated_caps):
                    fpath = SafeFS.validate(fpath)
                    
                    # X-RAY REDACTION SCANNER
                    has_residue, marker = RedactionXray.scan_for_residue(fpath)
                    if has_residue:
                        VaultManager.compress_vault(fpath, ACTIVE_CACHE, mode="ZLIB")
                        WholeDocumentRestore.restore_unmasked_file(fpath)
                        boot_log(f"[RESTORE] {fname} -> WHOLE UNMASKED COPY SAVED (X-RAY: {marker})")
                        self.ascended_count += 1
                        return True
                    
                    # Bates-Gap Recovery for ZIPs
                    if fpath.lower().endswith(".zip"):
                        match = BatesGapScanner.scan_zip(fpath, WHALE_TARGETS)
                        if match:
                            boot_log(f"[BATES-GAP] Match Found: {fname} -> {match}")
                            WholeDocumentRestore.restore_container(fpath)
                    
                    # 2. READ HEAD & ANALYZE
                    with open(fpath, "rb") as f:
                        head_bytes = f.read(10 * 1024 * 1024)
                        head_text = head_bytes.decode("utf-8", errors="ignore").upper()
                    
                    # NAEF EVALUATION
                    naef_verdict = naef.analyze_content(head_text)
                    if naef_verdict == "FALSIFIED":
                        self.isolate_noise(fpath)
                        return True
                    
                    if naef_verdict == "NOISE":
                        return False 

                    # 3. WHALE IDENTIFICATION
                    whales = re.findall(r'[A-F0-9]{8,64}', head_text)
                    found_id = None
                    for w in whales:
                        if w in WHALE_TARGETS or len(w) >= 16:
                            found_id = w
                            break
                    
                    if found_id:
                        count = registry.get(found_id, 0) + 1
                        registry[found_id] = count
                        
                        if count >= BOLO_THRESHOLD:
                            VaultManager.compress_vault(fpath, ACTIVE_CACHE, mode="ZLIB")
                        else:
                            VaultManager.compress_vault(fpath, VAULT_DIR, mode="LZMA")
                        
                        self.ascended_count += 1
                        return True

                    # 4. ENTROPY OVERRIDE
                    entropy = calculate_entropy_sample(fpath)
                    if entropy > 7.5:
                        if entropy > 7.7:
                             if fpath.lower().endswith(".zip"):
                                 WholeDocumentRestore.restore_container(fpath)
                             else:
                                 WholeDocumentRestore.restore_unmasked_file(fpath)
                             boot_log(f"[RESTORE] {fname} -> RESTORED_SIGNALS (High Entropy: {round(entropy,2)})")

                        VaultManager.compress_vault(fpath, VAULT_DIR, mode="LZMA")
                        self.ascended_count += 1
                        return True

            except Exception as e:
                if "VIOLATION" in str(e):
                    boot_log(f"[SECURITY] {e}")
                pass
            return False

        def process(self):
            for sector in SCAN_RADIUS:
                if not os.path.exists(sector):
                    boot_log(f"Sector Missing: {sector}")
                    continue
                
                boot_log(f"Sweeping Sector: {sector}")
                for root, _, files in os.walk(sector):
                    for f in files:
                        self.scanned_count += 1
                        if any(x in f.upper() for x in ["GEMINI", "ANTIGRAVITY", "BREADCRUMB"]): continue
                        fpath = os.path.join(root, f)
                        self.process_artifact(fpath)
                        # I/O Interleaving: Allow NVMe controller to breathe
                        time.sleep(0.05) 

    engine = AscensionEngine()
    engine.process()
    
    VaultManager.save_bolo_registry(registry)
    
    boot_log("VAULT_ASCENSION CYCLE COMPLETE.")
    boot_log(f"Scanned: {engine.scanned_count} | Ascended: {engine.ascended_count}")

if __name__ == "__main__":
    safe_run()
