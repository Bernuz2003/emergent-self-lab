"""E0: simulator validity. Nothing downstream is interpretable until this passes."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from emergent_self.analysis.validity import run_all
from emergent_self.config import load_run_config


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=str(Path(__file__).parents[1] / "configs/e0_validity.json"))
    args = ap.parse_args()

    cfg = load_run_config(args.config)
    print(f"E0 validity  config={Path(args.config).name}  digest={cfg.digest()}  steps={cfg.steps}\n")

    failures = 0
    for name, (ok, detail) in run_all(cfg).items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<24} {detail}")
        failures += not ok

    print()
    if failures:
        print(f"{failures} check(s) failed. Do not interpret E1+ results until they pass.")
        return 1
    print("All validity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
