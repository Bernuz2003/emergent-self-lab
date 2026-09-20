"""Evolve a population, freeze it, then probe and intervene on its latent state."""
from __future__ import annotations

import argparse
import json
from dataclasses import replace

from emergent_self.analysis.probes import run_probe_suite
from emergent_self.config import ControllerConfig, load_run_config


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="configs/e0_validity.json")
    ap.add_argument("--controller", default="gru", choices=("mlp", "gru"))
    ap.add_argument("--hidden", type=int, default=24)
    ap.add_argument("--evolve-steps", type=int, default=3000)
    ap.add_argument("--probe-steps", type=int, default=800)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    cfg = replace(
        load_run_config(args.config),
        seed=args.seed,
        controller=ControllerConfig(kind=args.controller, hidden_dim=args.hidden),
    )
    out = run_probe_suite(cfg, args.evolve_steps, args.probe_steps)
    if "error" in out:
        print(out["error"])
        return

    print(f"controller={args.controller} hidden={args.hidden} seed={args.seed}")
    print(f"{out['n_samples']} samples from {out['n_lineages']} lineages; "
          f"R2 held out across lineages\n")
    print(f"{'variable':<16}{'grouped R2':>12}{'pooled R2':>11}{'chance':>9}   reading")
    print("-" * 78)
    for group in ("body", "world"):
        for name, p in out[group].items():
            g, pl = p["r2_grouped"], p["r2_pooled"]
            if g > p["r2_shuffled"] + 0.05:
                reading = "lineage-general code"
            elif pl > 0.1:
                reading = "lineage identity, not a shared code"
            else:
                reading = "not decodable"
            print(f"  {name:<14}{g:>12.3f}{pl:>11.3f}{p['r2_shuffled']:>9.3f}   {reading}")
    print()
    print("  grouped = held out across whole lineages; pooled = held out across random")
    print("  observations, which leaks because samples within a lineage are correlated.")
    print()

    e = out["energy_direction_intervention"]
    print("Causal check - push the latent along the decoded energy direction:")
    sd = e.get("total_variation_sd")
    print(f"  total variation in action distribution : {e['total_variation']:.3f}"
          + (f" (sd {sd:.3f})" if sd is not None else ""))
    print(f"  change in fraction of steps moving     : {e['delta_move_fraction']:+.3f}")
    print(f"\n{out['note']}")


if __name__ == "__main__":
    main()
