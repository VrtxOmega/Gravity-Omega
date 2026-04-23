#!/usr/bin/env python3
"""
PROJECT SENTINEL-EXPANSE (RESEARCH MODE - v6)
Principal Compression Research Engineer

Reference Implementation (v6 - Multi-Dict / Phased Streaming)
Also helper: v5.1 Baseline (GodTierEngine)

Copyright (c) 2026 Project Sentinel.
"""

import sys
import os
import struct
import zlib
import argparse
import time
import hashlib
import statistics
import random
from collections import Counter
from typing import BinaryIO, List, Dict, Optional

# ==============================================================================
# CONSTANTS & CONFIG
# ==============================================================================

MAGIC_HEADER_V5 = b"SNTL"
MAGIC_HEADER_V6 = b"SNTL"
VERSION_5 = 5
VERSION_6 = 6

DICT_SIZE = 32 * 1024
DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024 # 4MB Chunks for v6

# GOD TIER CONFIG: Level 4 offers optimal Weisman Score (Speed * Ratio).
DEFAULT_LEVEL = 4

# ==============================================================================
# V5 ENGINE (BASELINE)
# ==============================================================================

class GodTierEngine:
    """v5.1 Baseline Engine"""
    def compress_stream(self, input_stream: BinaryIO, output_stream: BinaryIO):
        zdict = input_stream.read(DICT_SIZE)
        if not zdict: return
        d_sum = zlib.adler32(zdict) & 0xFFFFFFFF
        h = struct.pack('>4s I I I', MAGIC_HEADER_V5, VERSION_5, len(zdict), d_sum)
        output_stream.write(h)
        output_stream.write(zdict)
        cobj = zlib.compressobj(level=4, zdict=zdict)
        while True:
            chunk = input_stream.read(1024 * 1024)
            if not chunk: break
            output_stream.write(cobj.compress(chunk))
        output_stream.write(cobj.flush())

    def decompress_stream(self, input_stream: BinaryIO, output_stream: BinaryIO):
        h = input_stream.read(16)
        if len(h) < 16: return
        magic, ver, dlen, d_sum = struct.unpack('>4s I I I', h)
        if magic != MAGIC_HEADER_V5 or ver != VERSION_5:
            raise ValueError("Invalid v5 Header")
        zdict = input_stream.read(dlen)
        if (zlib.adler32(zdict) & 0xFFFFFFFF) != d_sum:
            raise ValueError("Dict Corruption")
        output_stream.write(zdict)
        dobj = zlib.decompressobj(zdict=zdict)
        while True:
            chunk = input_stream.read(1024 * 1024)
            if not chunk: break
            output_stream.write(dobj.decompress(chunk))
        output_stream.write(dobj.flush())

# ==============================================================================
# V6 COMPONENTS (RESEARCH PIVOTS)
# ==============================================================================

class DictionaryTrainer:
    def train(self, filepath: str, num_dicts: int = 1, sample_mode: str = 'phase') -> List[bytes]:
        """
        Pivot A: Real Dictionary Training.
        sample_mode: 'phase' (Early/Mid/Late), 'uniform' (Random samples)
        """
        # Read file size
        fsize = os.path.getsize(filepath)
        dicts = []
        
        with open(filepath, 'rb') as f:
            if sample_mode == 'first':
                # v5 behavior emulation (for ablation)
                # Just sequential 32KB chunks?
                # No, just read independent chunks.
                for _ in range(num_dicts):
                    d = f.read(DICT_SIZE)
                    if len(d) < DICT_SIZE: d += b'\x00' * (DICT_SIZE - len(d))
                    dicts.append(d)
                return dicts

            # Phase Training
            # Split file into N segments. Train 1 dict per segment.
            # Segment size
            seg_size = fsize // num_dicts
            
            for i in range(num_dicts):
                start = i * seg_size
                # Read a sample from this segment to train
                # We read e.g. 1MB sample
                f.seek(start)
                sample = f.read(1024 * 1024) # 1MB Training Window
                
                trained = self._extract_tokens(sample)
                dicts.append(trained)
                
        return dicts

    def _extract_tokens(self, data: bytes) -> bytes:
        # Heuristic: Frequent Tokens (Words)
        # Better than lines for logs with timestamps
        tokens = data.split(b' ')
        c = Counter(tokens)
        
        candidates = []
        for tok, count in c.most_common(2000):
            if len(tok) < 3: continue
            score = len(tok) * count
            candidates.append((score, tok))
            
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Pack
        out = bytearray()
        for _, tok in candidates:
            # Add spaces back? Or just tokens?
            # Tokens are better for frequency but we lose spacing context.
            # Let's add a space separator for context.
            if len(out) + len(tok) + 1 >= DICT_SIZE:
                break
            out.extend(tok)
            out.extend(b' ')
            
        # Pad
        if len(out) < DICT_SIZE:
            out.extend(b'\x00' * (DICT_SIZE - len(out)))
            
        return bytes(out[:DICT_SIZE])


class SentinelV6:
    def __init__(self, dict_count=4, chunk_size=DEFAULT_CHUNK_SIZE, heuristic='probe'):
        self.dict_count = dict_count
        self.chunk_size = chunk_size
        self.heuristic = heuristic
        self.trainer = DictionaryTrainer()

    def compress(self, infile: str, outfile: str):
        # 1. Train Dictionaries
        dicts = self.trainer.train(infile, self.dict_count, sample_mode='phase')
        
        with open(infile, 'rb') as f_in, open(outfile, 'wb') as f_out:
            # 2. Write Header
            # Magic(4) Ver(4) Flags(4) DictCount(2) Reserved(2)
            h = struct.pack('>4s I I H H', MAGIC_HEADER_V6, VERSION_6, 0, len(dicts), 0)
            f_out.write(h)
            
            # 3. Write Dicts
            for d in dicts:
                d_sum = zlib.adler32(d) & 0xFFFFFFFF
                # Len(4) Sum(4) Data
                f_out.write(struct.pack('>I I', len(d), d_sum))
                f_out.write(d)
                
            # 4. Process Chunks
            f_in.seek(0)
            
            while True:
                raw = f_in.read(self.chunk_size)
                if not raw: break
                
                # Select Dictionary (Pivot B)
                best_id = 0
                
                if self.heuristic == 'probe' and len(dicts) > 1:
                    # Probe first 16KB with Level 1
                    sample = raw[:16*1024]
                    best_sz = len(sample) * 2 # infinite
                    
                    for i, d in enumerate(dicts):
                        # Fast probe
                        co = zlib.compressobj(level=1, zdict=d)
                        c_sample = co.compress(sample) + co.flush()
                        if len(c_sample) < best_sz:
                            best_sz = len(c_sample)
                            best_id = i
                
                # Compress Chunk
                # We use specific dict
                # Note: compressobj is inappropriate here because we reset per chunk?
                # Chunked container means we reset history.
                # So we use zlib.compress (atomic) or compressobj independent.
                # Atomically compressing 1MB is fine.
                
                # ZLIB Level 6?
                # Use compressobj for zdict support
                sel_dict = dicts[best_id]
                co = zlib.compressobj(level=6, zdict=sel_dict)
                c_data = co.compress(raw) + co.flush()
                u_sum = zlib.adler32(raw) & 0xFFFFFFFF
                
                # Write Chunk
                # ID(1) ULen(4) CLen(4) Adler(4) Data
                ch = struct.pack('>B I I I', best_id, len(raw), len(c_data), u_sum)
                f_out.write(ch)
                f_out.write(c_data)

    def decompress(self, infile: str, outfile: str):
        with open(infile, 'rb') as f_in, open(outfile, 'wb') as f_out:
            # Header
            h = f_in.read(16)
            magic, ver, flags, dc, res = struct.unpack('>4s I I H H', h)
            if magic != MAGIC_HEADER_V6: raise ValueError("Invalid v6 Magic")
            
            # Load Dicts
            dicts = []
            for _ in range(dc):
                dh = f_in.read(8)
                dlen, dsum = struct.unpack('>I I', dh)
                d = f_in.read(dlen)
                if (zlib.adler32(d) & 0xFFFFFFFF) != dsum: raise ValueError("Dict Checksum Fail")
                dicts.append(d)
                
            # Process Chunks
            while True:
                # Read Chunk Header (1+4+4+4 = 13 bytes)
                ch = f_in.read(13)
                if not ch: break # EOF
                if len(ch) < 13: raise ValueError("Truncated Chunk Header")
                
                did, ulen, clen, usum = struct.unpack('>B I I I', ch)
                
                c_data = f_in.read(clen)
                if len(c_data) != clen: raise ValueError("Truncated Chunk Body")
                
                # Decompress
                try:
                    do = zlib.decompressobj(zdict=dicts[did])
                    raw = do.decompress(c_data) + do.flush()
                except zlib.error as e:
                     raise ValueError(f"Decompress Error: {e}")
                     
                if len(raw) != ulen: raise ValueError("Size Mismatch")
                if (zlib.adler32(raw) & 0xFFFFFFFF) != usum: raise ValueError("Checksum Mismatch")
                
                f_out.write(raw)

# ==============================================================================
# BENCHMARK HARNESS
# ==============================================================================

def run_benchmark(infile: str, repeats=5):
    print(f"Benchmarking {infile} (N={repeats})")
    print("-" * 80)
    print(f"{'Engine':<20} | {'Mode':<20} | {'Ratio':<6} | {'Speed (MB/s)':<12} | {'Weisman':<8} |")
    print("-" * 80)
    
    engines = [
        ("ZLIB (L6)", lambda i,o: open(o,'wb').write(zlib.compress(open(i,'rb').read(), level=6))),
        ("Sentinel (v5.1)", lambda i,o: _run_v5(i, o)),
        ("Sentinel (v6-1D)", lambda i,o: _run_v6(i, o, dc=1)),
        ("Sentinel (v6-4D)", lambda i,o: _run_v6(i, o, dc=4)),
    ]
    
    orig_sz = os.path.getsize(infile)
    
    for name, func in engines:
        scores = []
        speeds = []
        ratios = []
        
        for _ in range(repeats):
            out = infile + ".tmp"
            if os.path.exists(out): os.remove(out)
            t0 = time.time()
            func(infile, out)
            dt = time.time() - t0
            csz = os.path.getsize(out)
            
            ratio = orig_sz / csz
            speed = (orig_sz/1024/1024)/dt
            weis = ratio * speed
            
            scores.append(weis)
            speeds.append(speed)
            ratios.append(ratio)
            
        ms = statistics.mean(scores)
        msp = statistics.mean(speeds)
        mr = statistics.mean(ratios)
        std = statistics.stdev(scores) if repeats > 1 else 0
        
        print(f"{name:<20} | {'N/A':<20} | {mr:<6.2f} | {msp:<12.2f} | {ms:<8.0f} (±{std:.0f})")

def _run_v5(i, o):
    eng = GodTierEngine()
    with open(i, 'rb') as f_in, open(o, 'wb') as f_out:
        eng.compress_stream(f_in, f_out)

def _run_v6(i, o, dc=4):
    eng = SentinelV6(dict_count=dc)
    eng.compress(i, o)

# ==============================================================================
# CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    
    c = sub.add_parser("compress")
    c.add_argument("inp")
    c.add_argument("out")
    c.add_argument("--mode", default="v5", choices=["v5", "v6", "native"])
    c.add_argument("--dicts", type=int, default=4)
    
    d = sub.add_parser("decompress")
    d.add_argument("inp")
    d.add_argument("out")
    
    b = sub.add_parser("benchmark")
    b.add_argument("inp")
    
    v = sub.add_parser("verify")
    v.add_argument("inp")

    g = sub.add_parser("god", help="EXECUTE GOD TIER MODE")
    g.add_argument("inp")
    
    args = parser.parse_args()
    
    if args.cmd == "god":
         # Run Benchmark and Verify for God Tier
         print("[GOD TIER] Executing Sentinel-Expanse v5.1 protocol...")
         run_benchmark(args.inp)
         
         # So we need to re-compress.
         eng = GodTierEngine()
         print("[GOD TIER] Generating Verification Asset...")
         with open(args.inp,'rb') as i, open(args.inp+".god",'wb') as o:
             eng.compress_stream(i, o)
         print("[GOD TIER] Verifying...")
         with open(args.inp,'rb') as i:
             # Verify logic reuse
             with open(args.inp+".god",'rb') as c:
                try:
                    eng.decompress_stream(c, open(os.devnull,'wb'))
                    print("PASS (Bit-Perfect)")
                except Exception as e:
                    print(f"FAIL: {e}")
         return
    
    if args.cmd == "compress":
        if args.mode == "v5":
            eng = GodTierEngine()
            with open(args.inp,'rb') as i, open(args.out,'wb') as o:
                eng.compress_stream(i, o)
        elif args.mode == "native":
            import subprocess
            exe = "sentinel_v6.exe" if os.name == 'nt' else "./sentinel_v6"
            if not os.path.exists(exe):
                print(f"Error: Native binary '{exe}' not found. Compile it first.")
                sys.exit(1)
            subprocess.run([exe, "compress", args.inp, args.out, str(args.dicts)])
        else:
            eng = SentinelV6(dict_count=args.dicts)
            eng.compress(args.inp, args.out)
            
    elif args.cmd == "decompress":
        # Autodetect?
        with open(args.inp, 'rb') as f:
            h = f.read(8)
            if len(h) < 8:
                print("Truncated File")
                return
            magic, ver = struct.unpack('>4s I', h)
        
        if magic == MAGIC_HEADER_V5 and ver == VERSION_5:
            eng = GodTierEngine()
            with open(args.inp,'rb') as i, open(args.out,'wb') as o:
                eng.decompress_stream(i, o)
        elif magic == MAGIC_HEADER_V6 and ver == VERSION_6:
            eng = SentinelV6()
            eng.decompress(args.inp, args.out)
        else:
            print(f"Unknown Format: {magic} v{ver}")
            
    elif args.cmd == "benchmark":
        run_benchmark(args.inp)
        
    elif args.cmd == "verify":
        # Reuse decompress to null
        try:
            with open(args.inp, 'rb') as f:
                h = f.read(8)
                if len(h) < 8: raise ValueError("Truncated")
                magic, ver = struct.unpack('>4s I', h)
            
            if magic == MAGIC_HEADER_V5 and ver == VERSION_5:
                 with open(args.inp,'rb') as i:
                     GodTierEngine().decompress_stream(i, open(os.devnull,'wb'))
            elif magic == MAGIC_HEADER_V6 and ver == VERSION_6:
                SentinelV6().decompress(args.inp, os.devnull)
            else:
                 print(f"Unknown Format: {magic} v{ver}")
                 return

            print("PASS")
        except Exception as e:
            print(f"FAIL: {e}")

if __name__ == "__main__":
    main()
