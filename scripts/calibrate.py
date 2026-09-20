"""Sweep environment parameters and report extinction rate, population and the
primary endpoint.

Use this after changing any body or world constant. A configuration where a
large share of seeds goes extinct early is not usable for E1+: extinct runs
carry no information about the manipulated variable and simply destroy power.
Target extinction near zero with the primary endpoint clearly above the random
controller's floor.
"""
from __future__ import annotations

import argparse
import itertools
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from emergent_self.config import InterventionConfig, RunConfig, WorldConfig
from emergent_self.sim import Simulation


def _trial(args):
    hostility, respawn, resources, agents, prob, mag, steps, seed = args
    cfg = RunConfig(
        steps=steps, seed=seed, log_every=25, initial_agents=agents,
        world=WorldConfig(hostility_coupling=hostility, respawn_per_step=respawn,
                          max_resources=resources),
        interventions=InterventionConfig(hidden_perturbation_prob=prob,
                                         hidden_perturbation_magnitude=mag),
    )
    sim = Simulation(cfg)
    r = sim.run()
    # Redundancy is the other half of the calibration: a perturbation that does
    # not lower R^2(ambient -> body) has not made body state unknowable, and an
    # interoception ablation under it stays uninformative however many seeds run.
    return ((hostility, respawn, resources, agents, prob, mag),
            r.extinct_at is not None,
            r.summary["late_population"],
            r.summary["thermal_decoupling_advantage"],
            r.summary["microenvironment_selection"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hostility", type=float, nargs="+", default=[1.0, 2.0])
    ap.add_argument("--respawn", type=float, nargs="+", default=[3.0, 5.0])
    ap.add_argument("--resources", type=int, nargs="+", default=[150])
    ap.add_argument("--agents", type=int, nargs="+", default=[60])
    ap.add_argument("--perturb-prob", type=float, nargs="+", default=[0.0],
                    help="E1b/E1c hidden body perturbation probability per organism per step")
    ap.add_argument("--perturb-mag", type=float, nargs="+", default=[0.0])
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--seeds", type=int, default=8)
    args = ap.parse_args()

    combos = [(*c, args.steps, s)
              for c in itertools.product(args.hostility, args.respawn, args.resources,
                                         args.agents, args.perturb_prob, args.perturb_mag)
              for s in range(args.seeds)]
    with ProcessPoolExecutor() as pool:
        rows = list(pool.map(_trial, combos))

    agg: dict[tuple, list] = {}
    for key, ext, pop, idx, micro in rows:
        agg.setdefault(key, []).append((ext, pop, idx, micro))

    print(f"{'hostil':>7}{'respawn':>8}{'res':>6}{'agents':>7}{'p_pert':>8}{'mag':>6}"
          f"{'extinct':>10}{'late pop':>10}{'decouple':>10}{'micro':>9}")
    print("-" * 81)
    for key, v in sorted(agg.items()):
        ext = sum(e for e, _, _, _ in v)
        idx = [i for _, _, i, _ in v if np.isfinite(i)]
        mic = [m for _, _, _, m in v if np.isfinite(m)]
        # Extinct runs have no index, and averaging them in as zero would be the
        # same defect the metrics layer exists to avoid.
        shown = f"{np.mean(idx):>10.3f}" if idx else f"{'--':>10}"
        shown_m = f"{np.mean(mic):>9.3f}" if mic else f"{'--':>9}"
        print(f"{key[0]:>7}{key[1]:>8}{key[2]:>6}{key[3]:>7}{key[4]:>8}{key[5]:>6}"
              f"{f'{ext}/{len(v)}':>10}{np.mean([p for _, p, _, _ in v]):>10.1f}"
              f"{shown}{shown_m}{f'  (n={len(idx)})' if len(idx) < len(v) else ''}")

    print("\n  Target for E1c: extinction 1-2 per 12 in the perturbed cells, no worse")
    print("  than the unperturbed ones. Then check with scripts/diagnose_redundancy.py")
    print("  that the perturbation actually lowered R^2(ambient -> body).")


if __name__ == "__main__":
    main()
