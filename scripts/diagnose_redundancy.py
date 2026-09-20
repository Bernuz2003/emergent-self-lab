"""How much of body temperature is already visible in the exteroceptive channel?

If the ambient temperature of the cell an organism occupies predicts that
organism's body temperature well, then interoception carries almost no extra
information and an interoception ablation cannot produce an effect. Run this
before interpreting a null in E1: a null under high redundancy says something
about the environment, not about interoception.
"""
from __future__ import annotations

import argparse

import numpy as np

from emergent_self.config import load_run_config
from emergent_self.sim import Simulation


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="configs/e0_validity.json")
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()

    base = load_run_config(args.config)
    r2s, lags = [], []
    for seed in range(args.seeds):
        cfg = type(base)(**{**base.__dict__, "seed": seed})
        sim = Simulation(cfg)
        pairs = []
        for _ in range(cfg.steps):
            sim.step()
            if sim.step_index % 5 == 0:
                pairs += [(sim.world.ambient_at(a.x, a.y), a.body.temperature) for a in sim.agents]
            if not sim.agents:
                break
        if len(pairs) < 100:
            continue
        p = np.array(pairs)
        r2s.append(float(np.corrcoef(p[:, 0], p[:, 1])[0, 1] ** 2))
        lags.append(float(np.abs(p[:, 1] - p[:, 0]).mean()))

    if not r2s:
        print("populations collapsed before enough samples were collected")
        return

    r2 = float(np.mean(r2s))
    print(f"seeds with data        : {len(r2s)}/{args.seeds}")
    print(f"R^2(ambient -> body)   : {r2:.3f}")
    print(f"mean |body - ambient|  : {np.mean(lags):.3f}")
    print()
    if r2 > 0.6:
        print("HIGH redundancy. The current cell already reveals most of body temperature,")
        print("so interoception adds little and E1 is expected to return a null. Lower")
        print("body.thermal_coupling (and body.heat_per_move with it) before concluding")
        print("anything about interoception.")
    else:
        print("Body temperature carries substantial state not visible in the current cell.")
        print("An interoception ablation is informative here.")


if __name__ == "__main__":
    main()
