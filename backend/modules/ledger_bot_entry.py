import sys
import os

# Deterministic Path Resolution for PyInstaller
if hasattr(sys, '_MEIPASS'):
    # Running in PyInstaller bundle
    root = sys._MEIPASS
else:
    # Running as script
    root = os.path.dirname(os.path.abspath(__file__))

if root not in sys.path:
    sys.path.insert(0, root)

# Top-level import for PyInstaller analysis
from tools.ledger_bot.ledger_bot import main

if __name__ == "__main__":
    sys.exit(main())
