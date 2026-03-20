# GOLIATH HUNTER — Standalone Self-Directing OSINT Module
# Package init. Import the conductor and expose the public API surface.
from .omega_conductor import Conductor, run_hunt, mirror_module

__version__ = "1.0.0"
__all__ = ["Conductor", "run_hunt", "mirror_module"]
