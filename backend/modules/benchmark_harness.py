
import os
import time
import random
import zlib
import lzma
import shutil
import hashlib
import sys
from sentinel_expanse import GodTierEngine

TEST_FILE = "test_data_god.log"
COMPRESSED_FILE = "test_data.god"
DECOMPRESSED_FILE = "restored_data.log"
SIZE_MB = 10 

def generate_structured_data(filename, size_mb):
    print(f"Generating {size_mb}MB of synthetic structured logs...")
    templates = [
        "[{timestamp}] INFO Service.Auth: User {user_id} logged in from {ip} latency={lat}ms",
        "[{timestamp}] ERROR Database.Connection: Timeout on query {query_id} retrying {retry}",
        "[{timestamp}] DEBUG Kernel: Syscall {syscall} returned {ret} at {addr}",
    ]
    with open(filename, "wb") as f:
        bytes_written = 0
        limit = size_mb * 1024 * 1024
        while bytes_written < limit:
            tmpl = random.choice(templates)
            line = tmpl.format(
                timestamp=time.time(),
                user_id=random.randint(1000, 9999),
                ip=f"192.168.1.{random.randint(1, 255)}",
                lat=random.randint(10, 500),
                query_id=random.randint(100000, 999999),
                retry=random.randint(1, 5),
                syscall="sys_read",
                ret=0,
                addr=hex(random.randint(0, 0xFFFFFFFF))
            ) + "\n"
            data = line.encode('utf-8')
            f.write(data)
            bytes_written += len(data)

def get_weisman(name, orig_size, comp_size, time_sec):
    ratio = orig_size / comp_size
    mb_s = (orig_size / 1024 / 1024) / time_sec
    score = ratio * mb_s
    print(f"{name: <15} | Ratio: {ratio:.2f}x | Speed: {mb_s:.2f} MB/s | WEISMAN: {score:.2f}")
    return score

def benchmark_disk():
    import statistics
    
    generate_structured_data(TEST_FILE, SIZE_MB)
    orig_size = os.path.getsize(TEST_FILE)
    
    print("-" * 60)
    print("WEISMAN EVALUATION (Disk-to-Disk) - 5 Repetitions")
    print("-" * 60)
    
    def run_zlib(i, o):
        with open(i, 'rb') as f_in, open(o, 'wb') as f_out:
            f_out.write(zlib.compress(f_in.read(), level=6))
            
    def run_lzma(i, o):
        with open(i, 'rb') as f_in, open(o, 'wb') as f_out:
            f_out.write(lzma.compress(f_in.read(), preset=1))

    engines = [
        ("ZLIB (Level 6)", run_zlib),
        ("LZMA (Preset 1)", run_lzma),
        ("SENTINEL (v5)", lambda i,o: GodTierEngine().compress(i, o))
    ]
    
    results = {}
    
    for name, func in engines:
        speeds = []
        ratios = []
        scores = []
        
        for i in range(5):
            # Cleanup output
            outfile = COMPRESSED_FILE + ".bin"
            if os.path.exists(outfile): os.remove(outfile)
            
            # Run
            start = time.time()
            func(TEST_FILE, outfile)
            dt = time.time() - start
            
            # Metrics
            c_sz = os.path.getsize(outfile)
            ratio = orig_size / c_sz
            mb_s = (orig_size / 1024 / 1024) / dt
            score = ratio * mb_s
            
            speeds.append(mb_s)
            ratios.append(ratio)
            scores.append(score)
            
        # Stats
        mean_score = statistics.mean(scores)
        std_score = statistics.stdev(scores)
        mean_speed = statistics.mean(speeds)
        mean_ratio = statistics.mean(ratios)
        
        print(f"{name: <15} | Ratio: {mean_ratio:.2f}x | Speed: {mean_speed:.2f} MB/s | WEISMAN: {mean_score:.2f} (±{std_score:.1f})")
        results[name] = mean_score

    # Final Verification of Sentinel
    eng = GodTierEngine()
    eng.decompress(COMPRESSED_FILE + ".bin", DECOMPRESSED_FILE)
    h1 = hashlib.sha256(open(TEST_FILE,'rb').read()).hexdigest()
    h2 = hashlib.sha256(open(DECOMPRESSED_FILE,'rb').read()).hexdigest()
    
    if h1 == h2:
        print("\nVERIFICATION: PASS (Bit-Perfect)")
    else:
        print("\nVERIFICATION: FAIL (Hash Mismatch)")
        sys.exit(1)

if __name__ == "__main__":
    benchmark_disk()
