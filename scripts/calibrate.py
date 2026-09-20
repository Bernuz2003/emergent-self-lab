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

from emergent_self.config import RunConfig, WorldConfig
from emergent_self.sim import Simulation


def _trial(args):
    hostility, respawn, resources, agents, steps, seed = args
    cfg = RunConfig(
        steps=steps, seed=seed, log_every=25, initial_agents=agents,
        world=WorldConfig(hostility_coupling=hostility, respawn_per_step=respawn,
                          max_resources=resources),
    )
    r = Simulation(cfg).run()
    return ((hostility, respawn, resources, agents),
            r.extinct_at is not None,
            r.summary["late_population"],
            r.summary["thermoregulation_index"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hostility", type=float, nargs="+", default=[1.0, 2.0])
    ap.add_argument("--respawn", type=float, nargs="+", default=[3.0, 5.0])
    ap.add_argument("--resources", type=int, nargs="+", default=[150])
    ap.add_argument("--agents", type=int, nargs="+", default=[60])
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--seeds", type=int, default=8)
    args = ap.parse_args()

    combos = [(*c, args.steps, s)
              for c in itertools.product(args.hostility, args.respawn, args.resources, args.agents)
              for s in range(args.seeds)]
    with ProcessPoolExecutor() as pool:
        rows = list(pool.map(_trial, combos))

    agg: dict[tuple, list] = {}
    for key, ext, pop, idx in rows:
        agg.setdefault(key, []).append((ext, pop, idx))

    print(f"{'hostility':>10}{'respawn':>9}{'resources':>11}{'agents':>8}"
          f"{'extinct':>10}{'late pop':>10}{'index':>9}")
    print("-" * 67)
    for key, v in sorted(agg.items()):
        ext = sum(e for e, _, _ in v)
        idx = [i for _, _, i in v if np.isfinite(i)]
        # Extinct runs have no index, and averaging them in as zero would be the
        # same defect the metrics layer exists to avoid.
        shown = f"{np.mean(idx):>9.3f}" if idx else f"{'--':>9}"
        print(f"{key[0]:>10}{key[1]:>9}{key[2]:>11}{key[3]:>8}"
              f"{f'{ext}/{len(v)}':>10}{np.mean([p for _, p, _ in v]):>10.1f}{shown}"
              f"{f'  (n={len(idx)})' if len(idx) < len(v) else ''}")


if __name__ == "__main__":
    main()
