"""Run a preregistered multi-condition, multi-seed experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from emergent_self.experiment import Experiment, run_experiment


def main() -> None:
    _banner()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("config", help="path to an experiment config, e.g. configs/e1_interoception.json")
    ap.add_argument("--out", default=None, help="output directory (default runs/<experiment name>)")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--seeds", type=int, default=None, help="use only the first N seeds (quick check)")
    ap.add_argument("--steps", type=int, default=None, help="override steps (quick check)")
    args = ap.parse_args()

    spec = json.loads(Path(args.config).read_text())
    if args.seeds:
        spec["seeds"] = spec["seeds"][: args.seeds]
    if args.steps:
        spec.setdefault("base", {})["steps"] = args.steps

    exp = Experiment(spec)
    out = Path(args.out or Path("runs") / exp.name)
    n = len(exp.conditions) * len(exp.seeds)
    print(f"{exp.name}: {len(exp.conditions)} conditions x {len(exp.seeds)} seeds = {n} runs -> {out}")
    if exp.prereg.get("hypothesis"):
        print(f"\nH : {exp.prereg['hypothesis']}")
        print(f"H0: {exp.prereg.get('null_hypothesis', '-')}")
        print(f"Primary endpoint: {exp.endpoint}\n")

    run_experiment(exp, out, workers=args.workers)
    print(f"\nWrote {out}/runs.jsonl and {out}/report.json")
    print(f"Next: python scripts/analyze.py {out}")


def _banner() -> None:
    from emergent_self.provenance import describe, warn_if_dirty

    print(describe())
    warn_if_dirty()
    print()


if __name__ == "__main__":
    main()
