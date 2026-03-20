import sys
sys.path.append('/home/veritas/gravity-omega-v2/backend')
import omega_sentinel
sentinel = omega_sentinel.get_sentinel('/home/veritas/gravity-omega-v2')
sentinel.create_baseline(force=True)
print("V4.1 Baseline Resealed Successfully.")
