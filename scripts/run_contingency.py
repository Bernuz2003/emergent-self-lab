"""Does an evolved controller act on its own internal state?

Two frozen tests, run on controllers snapshotted from an evolutionary run and
compared against their own ancestors:

  body contingency     Same world, same position, same everything - except the
                       organism's sensed body temperature, cold versus hot. If
                       the channel is used at all, the two action distributions
                       must differ. Reported against `tv_null`, a
                       magnitude-matched change to the age channel, because any
                       large enough input change moves a softmax policy.

  sensor dissociation  Physical body hot, sensed body cold. Do the actions track
                       the sensed reading while the body tracks the physical one?

A positive result here is the first real milestone of the project: an evolved
agent using a representation of its own internal state to choose different
actions under identical external conditions. It is not consciousness and not
self-awareness.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np

from emergent_self.assay import ContingencyConfig, body_contingency, sensor_dissociation
from emergent_self.config import load_run_config
from emergent_self.sim import Simulation


def _fmt(x, w=9, p=3):
    return f"{'--':>{w}}" if x is None or not math.isfinite(x) else f"{x:>{w}.{p}f}"


def _cohorts(base, checkpoints, k, rng):
    """Evolve once, returning {label: [controllers]} at each checkpoint."""
    sim = Simulation(base)
    out, pending = {}, sorted(set(checkpoints))
    if 0 in pending:
        out["ancestral"] = sim.snapshot_controllers(k, rng)
        pending.remove(0)
    for _ in range(base.steps):
        sim.step()
        if pending and sim.step_index >= pending[0]:
            step = pending.pop(0)
            out[f"step_{step}"] = sim.snapshot_controllers(k, rng)
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
    ap.add_argument("--sites", type=int, default=30)
    ap.add_argument("--assay-seeds", type=int, default=4)
    ap.add_argument("--horizon", type=int, default=100)
    ap.add_argument("--interoception", default="true")
    ap.add_argument("--controller-kind", default=None, choices=("mlp", "gru"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    base = load_run_config(args.config)
    base = replace(base, steps=args.steps,
                   sensors=replace(base.sensors, interoception=args.interoception))
    if args.controller_kind:
        base = replace(base, controller=replace(base.controller, kind=args.controller_kind))
    ccfg = ContingencyConfig(sites_per_world=args.sites,
                             seeds=tuple(1000 + i for i in range(args.assay_seeds)))

    rows = []
    for seed in range(args.seed, args.seed + args.n_seeds):
        cohorts, extinct = _cohorts(replace(base, seed=seed), [0, args.steps],
                                    args.controllers, np.random.default_rng(seed))
        if extinct is not None:
            print(f"  seed {seed}: extinct at {extinct}")
        for label, controllers in cohorts.items():
            bc = [body_contingency(c, base, ccfg) for c in controllers]
            sd = [sensor_dissociation(c, base, ccfg, horizon=args.horizon) for c in controllers]
            rows.append({
                "seed": seed, "cohort": label, "n_controllers": len(controllers),
                "tv_body": float(np.nanmean([r["tv_body"] for r in bc])),
                "tv_null": float(np.nanmean([r["tv_null"] for r in bc])),
                "tv_ratio": float(np.nanmean([r["tv_ratio"] for r in bc
                                              if math.isfinite(r["tv_ratio"])])),
                "follows_sensed_margin": float(np.nanmean(
                    [r.get("follows_sensed_margin", math.nan) for r in sd])),
                "integrity_dissociated": float(np.nanmean(
                    [r.get("integrity_dissociated", math.nan) for r in sd])),
                "integrity_veridical_hot": float(np.nanmean(
                    [r.get("integrity_veridical_hot", math.nan) for r in sd])),
                "integrity_veridical_cold": float(np.nanmean(
                    [r.get("integrity_veridical_cold", math.nan) for r in sd])),
            })

    print(f"\n{'cohort':<14}{'seeds':>6}{'tv_body':>10}{'tv_null':>9}{'ratio':>8}"
          f"{'sensed margin':>15}{'integ diss':>12}{'integ hot':>11}{'integ cold':>12}")
    print("-" * 97)
    for label in sorted({r["cohort"] for r in rows},
                        key=lambda s: (s != "ancestral", s)):
        sub = [r for r in rows if r["cohort"] == label]
        m = lambda k: float(np.nanmean([r[k] for r in sub]))
        print(f"{label:<14}{len(sub):>6}{_fmt(m('tv_body'), 10)}{_fmt(m('tv_null'))}"
              f"{_fmt(m('tv_ratio'), 8, 2)}{_fmt(m('follows_sensed_margin'), 15)}"
              f"{_fmt(m('integrity_dissociated'), 12)}{_fmt(m('integrity_veridical_hot'), 11)}"
              f"{_fmt(m('integrity_veridical_cold'), 12)}")

    print("\n  tv_body > tv_null          : the temperature channel matters more than a")
    print("                               magnitude-matched change to a meaningless one")
    print("  sensed margin < 0          : actions track the sensed reading, not the body")
    print("  integ diss ~ integ hot     : meanwhile the physical body follows physics")

    if args.n_seeds > 1 and len({r["cohort"] for r in rows}) > 1:
        from emergent_self.analysis.stats import paired_compare

        print(f"\n{'metric':<26}{'evolved - ancestral':>20}{'95% CI':>20}{'dz':>7}{'pairs':>7}")
        print("-" * 80)
        final = f"step_{args.steps}"
        for k in ("tv_body", "tv_ratio", "follows_sensed_margin"):
            a = {r["seed"]: r[k] for r in rows if r["cohort"] == "ancestral"}
            b = {r["seed"]: r[k] for r in rows if r["cohort"] == final}
            c = paired_compare(b, a)
            ci = f"[{_fmt(c['ci_lo'], 6)},{_fmt(c['ci_hi'], 6)}]".replace(" ", "")
            print(f"{k:<26}{_fmt(c['mean_diff'], 20)}{ci:>20}"
                  f"{_fmt(c['dz'], 7, 2)}{int(c['n_pairs']):>7}")

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
