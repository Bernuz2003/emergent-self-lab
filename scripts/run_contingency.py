"""Does an evolved controller act on its own internal state?

Runs the standard frozen assays on controllers snapshotted from an evolutionary
run, and compares each cohort against its own ancestors on identical ground.

  body_contingency               same world, different body temperature: does
                                 the action distribution differ, and by more
                                 than a magnitude-matched change to a channel
                                 with no thermal meaning?

  sensor_dissociation            physically hot, told cold: do the actions
                                 follow the reading rather than the body?

  viability_after_falsification  body forced out of band, then either told the
                                 truth or told it is comfortable. Does reading
                                 the channel truthfully actually help?

The third is the one that turns "the channel is read" into "reading it matters".
A positive result across all three is the roadmap's next concrete horizon: an
evolved agent using a representation of its own internal state. It is not
self-awareness and not consciousness.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np

from emergent_self.assays import (
    body_contingency,
    memory_necessity,
    sensor_dissociation,
    viability_after_falsification,
)
from emergent_self.config import load_run_config
from emergent_self.sim import Simulation

ASSAYS = {
    "body_contingency": (body_contingency, ("tv_body", "tv_null", "tv_ratio", "tv_excess")),
    "sensor_dissociation": (sensor_dissociation,
                            ("tv_vs_sensed_match", "tv_vs_physical_match",
                             "follows_sensed_margin")),
    "viability_after_falsification": (viability_after_falsification,
                                      ("in_band_benefit", "integrity_benefit",
                                       "time_to_band_truthful", "time_to_band_blinded")),
    "memory_necessity": (memory_necessity, ("tv_after_wipe", "in_band_cost")),
}


def _fmt(x, w=10, p=4):
    return f"{'--':>{w}}" if x is None or not math.isfinite(x) else f"{x:>{w}.{p}f}"


def _cohorts(base, checkpoints, k, rng):
    sim = Simulation(base)
    out, pending = {}, sorted(set(checkpoints))
    if 0 in pending:
        out["ancestral"] = sim.snapshot_controllers(k, rng)
        pending.remove(0)
    for _ in range(base.steps):
        sim.step()
        if pending and sim.step_index >= pending[0]:
            out[f"step_{pending.pop(0)}"] = sim.snapshot_controllers(k, rng)
        if not sim.agents:
            break
    return {k_: v for k_, v in out.items() if v}, sim.extinct_step


def main() -> None:
    _banner()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="configs/e0_validity.json")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-seeds", type=int, default=1)
    ap.add_argument("--steps", type=int, default=6000)
    ap.add_argument("--controllers", type=int, default=6)
    ap.add_argument("--assay-worlds", type=int, default=4)
    ap.add_argument("--horizon", type=int, default=120)
    ap.add_argument("--interoception", default="true")
    ap.add_argument("--interoception-channels", nargs="*", default=None)
    ap.add_argument("--controller-kind", default=None, choices=("mlp", "gru"))
    ap.add_argument("--assays", nargs="+", default=list(ASSAYS), choices=list(ASSAYS))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    base = load_run_config(args.config)
    sensors = replace(base.sensors, interoception=args.interoception)
    if args.interoception_channels is not None:
        sensors = replace(sensors, interoception_channels=args.interoception_channels or None)
    base = replace(base, steps=args.steps, sensors=sensors)
    if args.controller_kind:
        base = replace(base, controller=replace(base.controller, kind=args.controller_kind))
    worlds = tuple(1000 + i for i in range(args.assay_worlds))

    rows = []
    for seed in range(args.seed, args.seed + args.n_seeds):
        cohorts, extinct = _cohorts(replace(base, seed=seed), [0, args.steps],
                                    args.controllers, np.random.default_rng(seed))
        if extinct is not None:
            print(f"  seed {seed}: population extinct at step {extinct}")
        for label, controllers in cohorts.items():
            row = {"seed": seed, "cohort": label, "n_controllers": len(controllers)}
            for name in args.assays:
                fn, keys = ASSAYS[name]
                results = [fn(c, base, world_seeds=worlds,
                              **({} if name == "body_contingency" else {"horizon": args.horizon}))
                           for c in controllers]
                for k in keys:
                    vals = [r.metrics[k] for r in results if math.isfinite(r.metrics[k])]
                    row[f"{name}.{k}"] = float(np.mean(vals)) if vals else math.nan
            rows.append(row)

    labels = sorted({r["cohort"] for r in rows}, key=lambda s: (s != "ancestral", s))
    for name in args.assays:
        _, keys = ASSAYS[name]
        print(f"\n{name}")
        print(f"  {'cohort':<14}{'seeds':>6}" + "".join(f"{k[:16]:>18}" for k in keys))
        print("  " + "-" * (20 + 18 * len(keys)))
        for label in labels:
            sub = [r for r in rows if r["cohort"] == label]
            cells = "".join(_fmt(float(np.nanmean([r[f'{name}.{k}'] for r in sub])), 18)
                            for k in keys)
            print(f"  {label:<14}{len(sub):>6}{cells}")

    if args.n_seeds > 1 and len(labels) > 1:
        from emergent_self.analysis.stats import paired_compare

        final = labels[-1]
        print(f"\n{final} minus ancestral, seed-paired")
        print(f"  {'metric':<44}{'diff':>10}{'95% CI':>22}{'dz':>7}{'pairs':>7}")
        print("  " + "-" * 88)
        for name in args.assays:
            for k in ASSAYS[name][1]:
                col = f"{name}.{k}"
                a = {r["seed"]: r[col] for r in rows if r["cohort"] == "ancestral"}
                b = {r["seed"]: r[col] for r in rows if r["cohort"] == final}
                c = paired_compare(b, a)
                ci = f"[{_fmt(c['ci_lo'], 7)},{_fmt(c['ci_hi'], 7)}]".replace(" ", "")
                print(f"  {col:<44}{_fmt(c['mean_diff'])}{ci:>22}"
                      f"{_fmt(c['dz'], 7, 2)}{int(c['n_pairs']):>7}")

    print("\n  tv_ratio > 1            temperature matters more than a matched null change")
    print("  follows_sensed_margin<0 actions track the reading, not the body")
    print("  in_band_benefit > 0     reading the channel truthfully actually helps")

    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=2))
        print(f"\nwrote {args.out}")


def _banner() -> None:
    from emergent_self.provenance import describe, warn_if_dirty

    print(describe())
    warn_if_dirty()
    print()


if __name__ == "__main__":
    main()
