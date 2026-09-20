"""Evolve, snapshot controllers at checkpoints, then evaluate them frozen.

This answers the question that cannot be asked of a live population: is the
controller at the end of evolution actually better than its ancestor, measured
on identical ground with no mutation, reproduction or competition running?
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import replace
from pathlib import Path

from emergent_self.assay import AssayConfig, evolve_and_assay
from emergent_self.config import ControllerConfig, SensorConfig, load_run_config


def _fmt(x, width=9, prec=3):
    return f"{'--':>{width}}" if x is None or not math.isfinite(x) else f"{x:>{width}.{prec}f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="configs/e0_validity.json")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-seeds", type=int, default=1,
                    help="evolution seeds to run; >1 aggregates with seed-paired statistics")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--steps", type=int, default=6000)
    ap.add_argument("--checkpoints", type=int, nargs="+", default=None)
    ap.add_argument("--controllers", type=int, default=8, help="snapshots per checkpoint")
    ap.add_argument("--assay-steps", type=int, default=800)
    ap.add_argument("--assay-seeds", type=int, default=6)
    ap.add_argument("--interoception", default=None, choices=("true", "shuffled", "noisy", "constant"))
    ap.add_argument("--controller-kind", default=None, choices=("mlp", "gru"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    base = load_run_config(args.config)
    base = replace(base, seed=args.seed, steps=args.steps)
    if args.interoception:
        base = replace(base, sensors=replace(base.sensors, interoception=args.interoception))
    if args.controller_kind:
        base = replace(base, controller=replace(base.controller, kind=args.controller_kind))

    checkpoints = args.checkpoints or [0, args.steps // 4, args.steps // 2,
                                       3 * args.steps // 4, args.steps]
    cfg = AssayConfig(steps=args.assay_steps,
                      seeds=tuple(1000 + i for i in range(args.assay_seeds)),
                      shock_step=args.assay_steps // 2)

    if args.n_seeds > 1:
        _multi_seed(args, base, checkpoints, cfg)
        return

    print(f"evolving {args.steps} steps (seed {args.seed}), snapshotting at {checkpoints}")
    print(f"assay: {args.controllers} controllers x {args.assay_seeds} standardised worlds "
          f"x {args.assay_steps} steps, thermal shock at {cfg.shock_step}\n")

    out = evolve_and_assay(base, checkpoints, args.controllers, cfg)
    _print_cohorts(out)
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=2))
        print(f"\nwrote {args.out}")


def _print_cohorts(out) -> None:
    if out["extinct_at"] is not None:
        print(f"note: the evolving population went extinct at step {out['extinct_at']}; "
              f"later checkpoints have no cohort.\n")
    print(f"{'cohort':<14}{'ctrls':>6}{'survived':>10}{'death':>8}{'index':>9}"
          f"{'vs passive':>12}{'move frac':>11}{'eaten':>8}{'recovery':>10}")
    print("-" * 88)
    for c in out["cohorts"]:
        s = c["summary"]
        print(f"{c['label']:<14}{c['n_controllers']:>6}"
              f"{_fmt(s['mean_steps_survived'], 10, 1)}{_fmt(s['death_rate'], 8, 2)}"
              f"{_fmt(s['thermoregulation_index'])}{_fmt(s['regulation_vs_passive'], 12)}"
              f"{_fmt(s['move_fraction'], 11)}{_fmt(s['resources_eaten'], 8, 1)}"
              f"{_fmt(s['recovery_steps'], 10, 1)}")

    cohorts = {c["label"]: c["summary"] for c in out["cohorts"]}
    if "ancestral" in cohorts and len(cohorts) > 1:
        last = out["cohorts"][-1]["label"]
        a, b = cohorts["ancestral"], cohorts[last]
        print(f"\n{last} minus ancestral, on identical ground:")
        for k in ("mean_steps_survived", "thermoregulation_index",
                  "regulation_vs_passive", "move_fraction", "resources_eaten"):
            if math.isfinite(a[k]) and math.isfinite(b[k]):
                print(f"  {k:<26}{b[k] - a[k]:+.3f}")


def _one_seed(payload):
    base, seed, checkpoints, k, cfg = payload
    out = evolve_and_assay(replace(base, seed=seed), checkpoints, k, cfg)
    return seed, {c["label"]: c["summary"] for c in out["cohorts"]}, out["extinct_at"]


METRICS = ("mean_steps_survived", "thermoregulation_index", "regulation_vs_passive",
           "move_fraction", "resources_eaten", "death_rate", "final_integrity")


def _multi_seed(args, base, checkpoints, cfg) -> None:
    from concurrent.futures import ProcessPoolExecutor

    from emergent_self.analysis.stats import paired_compare

    seeds = list(range(args.seed, args.seed + args.n_seeds))
    final_label = f"step_{checkpoints[-1]}"
    print(f"{args.n_seeds} evolution seeds x {args.steps} steps, "
          f"snapshots at {checkpoints}")
    print(f"assay: {args.controllers} controllers x {args.assay_seeds} standardised worlds "
          f"x {args.assay_steps} steps\n")
    print(f"Comparing '{final_label}' against 'ancestral' within each evolution seed, so "
          f"every\ncontrast is paired on the world the lineage actually evolved in.\n")

    payloads = [(base, s, checkpoints, args.controllers, cfg) for s in seeds]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(_one_seed, payloads))

    anc = {m: {} for m in METRICS}
    fin = {m: {} for m in METRICS}
    usable = 0
    for seed, cohorts, extinct in results:
        if "ancestral" not in cohorts or final_label not in cohorts:
            print(f"  seed {seed}: no final cohort"
                  f"{f' (extinct at {extinct})' if extinct else ''}; dropped")
            continue
        usable += 1
        for m in METRICS:
            anc[m][seed] = cohorts["ancestral"][m]
            fin[m][seed] = cohorts[final_label][m]

    print(f"\n{usable}/{len(seeds)} seeds produced both cohorts\n")
    print(f"{'metric':<26}{'ancestral':>11}{'evolved':>10}{'diff':>9}"
          f"{'95% CI':>20}{'dz':>7}{'wins':>6}")
    print("-" * 89)
    for m in METRICS:
        c = paired_compare(fin[m], anc[m])
        a_mean = sum(v for v in anc[m].values() if math.isfinite(v)) / max(1, len(anc[m]))
        f_mean = sum(v for v in fin[m].values() if math.isfinite(v)) / max(1, len(fin[m]))
        ci = f"[{_fmt(c['ci_lo'], 6)},{_fmt(c['ci_hi'], 6)}]".replace(" ", "")
        print(f"{m:<26}{_fmt(a_mean, 11)}{_fmt(f_mean, 10)}{_fmt(c['mean_diff'], 9)}"
              f"{ci:>20}{_fmt(c['dz'], 7, 2)}{int(c['sign_wins']):>4}/{int(c['n_pairs'])}")

    if args.out:
        Path(args.out).write_text(json.dumps(
            {"seeds": seeds, "final_label": final_label,
             "ancestral": anc, "evolved": fin}, indent=2))
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
