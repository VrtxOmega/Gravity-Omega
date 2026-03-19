import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from omega_sentinel import get_sentinel

sentinel = get_sentinel()
sentinel.accept_changes()
sentinel.create_baseline(force=True)
print("Changes accepted and baseline successfully sealed.")
