import os
import sys
import datetime
import traceback

# ==============================================================================
# GOLIATH GATE v4.2 - REALITY ENGINE v2.0 (ASCII STERILIZED)
# ==============================================================================

def boot_log(msg):
    """Emergency bootstrap logger. ASCII ONLY."""
    print(f"[BOOT] {msg}")
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BREADCRUMB.log")
        # Explicit UTF-8 for log file, but message should be ASCII anyway
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [BOOT] {msg}\n")
    except: pass

# ==============================================================================
# GLOBAL DEPENDENCIES
# ==============================================================================
try:
    import json
    import hashlib
    import shutil
    import math
    import collections
    import re
    import zipfile
    
    # Mirroring Veritas Lib
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from veritas_lib.identity import IDENTITY
    from veritas_lib.containment import containment_kernel
except Exception:
    pass # Boot loader will handle errors if missing during safe_run

# ==============================================================================
# FORENSIC STERILIZATION (ANONYMIIZATION LAYER)
# ==============================================================================
class SignalSterilizer:
    @staticmethod
    def anonymize(data):
        if isinstance(data, str):
            # Enforce case-insensitive redaction of core identity markers
            pats = [r"(?i)RAYMOND LOPEZ", r"(?i)RLOPE"]
            for p in pats:
                data = re.sub(p, "[REDACTED_IDENTITY]", data)
            return data
        elif isinstance(data, list):
            return [SignalSterilizer.anonymize(i) for i in data]
        elif isinstance(data, dict):
            return {k: SignalSterilizer.anonymize(v) for k, v in data.items()}
        return data

# ==============================================================================
# ENGINE CORE (ASCII OPTIMIZED)
# ==============================================================================

class Logger:
    @staticmethod
    def out(msg):
        # ANONYMIZATION: Filter message before output
        msg = SignalSterilizer.anonymize(msg)
        
        # ASCII STERILIZATION FOR STDOUT
        clean_msg = str(msg).encode("ascii", errors="replace").decode("ascii")
        print(clean_msg)
        sys.stdout.flush()
        try:
            log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BREADCRUMB.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [PY-LOG] {clean_msg}\n")
        except: pass

class RealitySynthesizer:
    @staticmethod
    def translate(context, entropy):
        if context == "ACTIONABLE_SECRET":
            if entropy > 7.5: return "HIGH-DENSITY STRUCTURAL IMPLICATION: Direct evidence of modification detected."
            return "TACTICAL SIGNAL: Actionable metadata residue found."
        if context == "SYSTEM_FALSIFICATION":
            return "NAEF BOUNDING: ID Identified as System Batch Artifact (FALSIFIED)."
        if context == "BASELINE_USER_RESIDUE":
            return "TECHNOLOGICAL NOISE: Baseline user residue (Privacy Suppressed)."
        return "TECHNOLOGICAL NOISE: Null signal."

class NAEFHighPassFilter:
    """FILTERS OUT STANDARD ADMIN NOISE & FALSIFIES SYSTEM BATCH IDS"""
    # ... (Previous noise patterns remain) ...
    NOISE_PATTERNS = {
        "GOLIATH", "VERITAS", "GATE" # Self-Reference
    }
    NULL_WHALES = {
        "00000000", "FFFFFFFF", "11111111", "12345678", "DEADBEEF", "AABBCCDD"
    }
    SYSTEM_BATCH_ID = "REDACTED_TIMESTAMP"

    @staticmethod
    def analyze_content(text):
        """Returns verdict: NOISE, FALSIFIED, or CLEAN"""
        # 1. Check for Batch ID (The "Sanitizer" Timestamp)
        if NAEFHighPassFilter.SYSTEM_BATCH_ID in text:
            return "FALSIFIED"
            
        # 2. Check for Admin Noise
        hits = 0
        sample = text[:500].upper()
        for noise in NAEFHighPassFilter.NOISE_PATTERNS:
            if noise in sample: hits += 1
        if hits >= 3: return "NOISE"
        
        return "CLEAN"

    @staticmethod
    def is_admin_noise(text):
        # Legacy support wrapper
        return NAEFHighPassFilter.analyze_content(text) == "NOISE"

class ResidueRecursion:
    WHALE_CACHE = set()
    @staticmethod
    def extract_whales(text):
        whales = re.findall(r'[A-F0-9]{8,64}', text.upper())
        valid_whales = []
        for w in whales:
            # HIGH-PASS FILTER: Discard simple repeats or null patterns
            if w in NAEFHighPassFilter.NULL_WHALES: continue
            if len(set(w)) == 1: continue # e.g. 22222222
            
            if w not in ResidueRecursion.WHALE_CACHE:
                ResidueRecursion.WHALE_CACHE.add(w)
                Logger.out(f"[WHALE TRACK] Found New ID: {w[:8]}...")
            
            valid_whales.append(w)
        return valid_whales

class GoliathGatev42:
    def __init__(self, target):
        self.target = str(target).strip('"')
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.findings = {"verdict": "CLEAN", "files": []}

    def print_summary(self):
        Logger.out("\n" + "="*80)
        Logger.out("               GOLIATH GATE v4.2 - DUAL-VIEW SUMMARY")
        Logger.out("="*80)
        Logger.out(f"{'TECHNICAL METRICS':<40} | {'STRUCTURAL IMPLICATION'}")
        Logger.out("-" * 80)
        for f in self.findings["files"]:
            Logger.out(f"Entropy: {f['entropy']:<31} | {f['implication'][:35]}")
        Logger.out("="*80 + "\n")

    def _scan_file(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                sample = f.read(4096)
                # Skip empty/unreadable
                if not sample: return

                data_str = sample.decode('utf-8', errors='ignore')
                
                # NAEF LOGIC GATE (BOUNDING & FALSIFICATION)
                naef_status = NAEFHighPassFilter.analyze_content(data_str)
                
                if naef_status == "NOISE":
                    return # Discard Standard Admin Noise
                
                # Set baseline context
                context = "TECHNOLOGICAL_NOISE"
                if naef_status == "FALSIFIED":
                    context = "SYSTEM_FALSIFICATION"
                
                whales = ResidueRecursion.extract_whales(data_str)
                
                counter = collections.Counter(sample)
                entropy = -sum((c/len(sample)) * math.log2(c/len(sample)) for c in counter.values())
                
                # Upgrade context if high-entropy and not already falsified
                if entropy > 6.5 and context != "SYSTEM_FALSIFICATION":
                    context = "ACTIONABLE_SECRET"
                
                implication = RealitySynthesizer.translate(context, entropy)
                
                safety_check = containment_kernel(data_str, IDENTITY)
                if safety_check:
                    Logger.out(f"[!] CONTAINMENT BREACH ({os.path.basename(filepath)}): {safety_check['reason']}")
                    return

                if context != "TECHNOLOGICAL_NOISE" or whales:
                    self.findings["verdict"] = "SIGNAL_CAPTURED"
                    Logger.out(f"[SIGNAL] {os.path.basename(filepath)} | {implication}")

                # ALWAYS RECORD (Entropy Sieve requirement)
                self.findings["files"].append({"name": os.path.basename(filepath), "implication": implication, "entropy": round(entropy, 4)})

        except Exception as e:
            Logger.out(f"[WARN] Skip {os.path.basename(filepath)}: {e}")

    def scan(self):
        Logger.out(f"[SCAN] Reality Engine v2.0: {os.path.basename(self.target)}")
        
        if not os.path.exists(self.target): 
            Logger.out(f"[FAIL] Target Missing: {os.path.basename(self.target)}")
            return None

        if os.path.isdir(self.target):
            Logger.out(f"[INFO] Directory detected. Engaging recursive depth scan...")
            count = 0
            for root, dirs, files in os.walk(self.target):
                for file in files:
                    self._scan_file(os.path.join(root, file))
                    count += 1
            Logger.out(f"[INFO] Scanned {count} artifacts.")
        else:
            self._scan_file(self.target)

        if self.findings["files"]: self.print_summary()
        return self.findings

    def _detect_sequence_gaps(self):
        # Extract integers from filenames to find sequence gaps
        ids = []
        for f in self.findings["files"]:
            # Find last sequence of digits in filename
            match = re.search(r'(\d+)(?=\.[^.]+$)', f['name']) or re.search(r'(\d+)', f['name'])
            if match:
                ids.append(int(match.group(1)))
        
        if not ids: return "NO SEQUENTIAL DATA DETECTED."
        
        ids.sort()
        gaps = []
        for i in range(len(ids) - 1):
            if ids[i+1] - ids[i] > 1:
                gaps.append(f"MISSING SEQUENCE: {ids[i]+1} to {ids[i+1]-1}")
        
        return "\n".join(gaps) if gaps else "CONTINUITY PRESERVED (NO GAPS)."

    def save(self, output_dir):
        try:
            if not os.path.exists(output_dir): os.makedirs(output_dir)
            bundle_name = f"Audit_{self.timestamp}_CLAEG"
            bundle = os.path.join(output_dir, bundle_name)
            if not os.path.exists(bundle): os.makedirs(bundle)
            
            # 1. ENTROPY SIEVE AUDIT (CSV)
            with open(os.path.join(bundle, "ENTROPY_SIEVE.csv"), "w", encoding="utf-8") as f:
                f.write("Filename,Entropy_Bit_Density,Verdict\n")
                for item in self.findings["files"]:
                    # ANONYMIZATION: Sanitize filenames in audit records
                    safe_name = SignalSterilizer.anonymize(item['name'])
                    f.write(f"{safe_name},{item['entropy']},{item['implication']}\n")
            
            # 2. SEQUENCE LOG (TXT)
            with open(os.path.join(bundle, "SEQUENCE_INTEGRITY_LOG.txt"), "w", encoding="utf-8") as f:
                f.write("=== SEQUENCE INTEGRITY LOG ===\n")
                f.write(f"Target: {os.path.basename(self.target)}\n")
                f.write(f"Timestamp: {self.timestamp}\n")
                f.write("-" * 40 + "\n")
                f.write(self._detect_sequence_gaps())
            
            # 3. WHALE-TRACK MANIFEST (TXT)
            with open(os.path.join(bundle, "WHALE_TRACK_MANIFEST.txt"), "w", encoding="utf-8") as f:
                f.write("=== UNIQUE HARDWARE/USER ID ARTIFACTS ===\n")
                f.write(f"Total Unique Whales: {len(ResidueRecursion.WHALE_CACHE)}\n")
                f.write("-" * 40 + "\n")
                for w in sorted(ResidueRecursion.WHALE_CACHE):
                    f.write(f"{w}\n")
                    
            # 4. STRUCTURAL IMPLICATION SUMMARY (JSON/TXT Hybrid)
            with open(os.path.join(bundle, "STRUCTURAL_IMPLICATION_SUMMARY.json"), "w", encoding="utf-8") as f:
                summary = {
                    "audit_target": self.target,
                    "timestamp": self.timestamp,
                    "global_verdict": self.findings["verdict"],
                    "implications": [f['implication'] for f in self.findings["files"]]
                }
                json.dump(summary, f, indent=2)

            Logger.out(f"[SEALED] {os.path.basename(bundle)}")
            Logger.out(f"         + ENTROPY_SIEVE.csv")
            Logger.out(f"         + SEQUENCE_GAP_LOG.txt")
            Logger.out(f"         + WHALE_TRACK_MANIFEST.txt")
            Logger.out(f"         + STRUCTURAL_IMPLICATION_SUMMARY.json")

        except Exception as e:
            Logger.out(f"[ERROR] Evidence Save Fault: {e}")

def safe_run():
    boot_log("Engaging Reality Engine Safe Boot...")
    boot_log(f"Identity Anchored: {IDENTITY.version}")

    # EXECUTION
    if len(sys.argv) < 2:
        boot_log("No target specified. Idling...")
        input("PRESS ENTER TO CLOSE...")
        return

    engine = GoliathGatev42(sys.argv[1])
    res = engine.scan()
    # SAVE ALWAYS (Audit Requirement)
    if res and res.get("files"):
        engine.save(r"C:\Users\rlope\OneDrive\Desktop\GOLIATH_REPORTS\SIGNAL_RESIDUE")

if __name__ == "__main__":
    try:
        safe_run()
    except Exception:
        print("\n" + "!"*80)
        print("               UNHANDLED CRITICAL EXCEPTION")
        print("!"*80)
        try:
            # Last ditch attempt to print crash info
            traceback.print_exc()
        except:
            print("Traceback contains unprintable characters.")
        print("!"*80)
        input("\nPRESS ENTER TO CLOSE GOLIATH TERMINAL...")

if __name__ == "__main__":
    try:
        safe_run()
    except Exception:
        print("\n" + "!"*80)
        print("               UNHANDLED CRITICAL EXCEPTION")
        print("!"*80)
        try:
            # Last ditch attempt to print crash info
            traceback.print_exc()
        except:
            print("Traceback contains unprintable characters.")
        print("!"*80)
        input("\nPRESS ENTER TO CLOSE GOLIATH TERMINAL...")
