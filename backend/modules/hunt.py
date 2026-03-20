#!/usr/bin/env python3
"""
GOLIATH HUNTER — CLI Entry Point
Run from repo root: python backend/modules/hunt.py --seed "..." --depth 1

This wrapper handles the sys.path setup so all package imports work
regardless of how Python is invoked.
"""

import sys
import os

# Ensure backend/modules is on path so `goliath_hunter` resolves as a package
_modules_dir = os.path.dirname(os.path.abspath(__file__))
if _modules_dir not in sys.path:
    sys.path.insert(0, _modules_dir)

# Now safe to import the package
from goliath_hunter.omega_conductor import HuntRun, mirror_module  # noqa: E402

import argparse, json

def main():
    ap = argparse.ArgumentParser(
        description="GOLIATH HUNTER — Self-directing OSINT engine"
    )
    ap.add_argument("--seed",    required=False, default="",
                    help="Comma-separated seed terms (e.g. 'Phillips66 PFAS,Bethalto IL')")
    ap.add_argument("--depth",   type=int, default=1,
                    help="Re-search cycles (0 = seed only, default=1)")
    ap.add_argument("--domains", default="",
                    help="Comma-separated domains for Wayback + subdomain enum")
    ap.add_argument("--county",  default="", help="County name for EPA ECHO")
    ap.add_argument("--state",   default="", help="2-letter state for EPA ECHO")
    ap.add_argument("--dry-run", action="store_true",
                    help="Skip all real HTTP — use mock nodes (fast self-test)")
    ap.add_argument("--mirror",  default="",
                    help="Clone a GOLIATH module for fine-tuning, e.g. GOLIATH_TRAWLER")
    args = ap.parse_args()

    # Module mirror utility
    if args.mirror:
        dest = mirror_module(args.mirror)
        print(f"[MIRROR] Cloned to: {dest}")
        return

    if not args.seed:
        ap.print_help()
        sys.exit(1)

    seeds = [s.strip() for s in args.seed.split(",") if s.strip()]
    domain_list = [d.strip() for d in args.domains.split(",") if d.strip()]

    hunt = HuntRun(
        seeds=seeds,
        depth=args.depth,
        domains=domain_list,
        county=args.county,
        state=args.state,
        dry_run=args.dry_run,
    )
    result = hunt.execute()
    print("\n" + "=" * 60)
    print("HUNT COMPLETE")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
