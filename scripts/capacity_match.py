"""Print the hidden width that capacity-matches one controller family to another.

Run this before any architecture comparison, and after any change to the sensor
layout, so that a difference cannot be attributed to parameter count.
"""
from __future__ import annotations

import argparse

from emergent_self.agents.controller import build_controller, match_hidden_dim
from emergent_self.agents.sensors import observation_dim
from emergent_self.config import ControllerConfig, SensorConfig
from emergent_self.world.grid import ACTIONS
import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference-kind", default="mlp")
    ap.add_argument("--reference-hidden", type=int, default=24)
    ap.add_argument("--target-kind", default="gru")
    ap.add_argument("--view-radius", type=int, default=1)
    args = ap.parse_args()

    dim = observation_dim(SensorConfig(view_radius=args.view_radius))
    rng = np.random.default_rng(0)
    ref = build_controller(ControllerConfig(kind=args.reference_kind, hidden_dim=args.reference_hidden),
                           dim, len(ACTIONS), rng)
    target_params = ref.param_count()
    h = match_hidden_dim(args.target_kind, dim, len(ACTIONS), target_params)
    matched = build_controller(ControllerConfig(kind=args.target_kind, hidden_dim=h), dim, len(ACTIONS), rng)

    print(f"observation_dim         = {dim}")
    print(f"{args.reference_kind} hidden={args.reference_hidden:<4} params = {target_params}")
    print(f"{args.target_kind} hidden={h:<4} params = {matched.param_count()}")
    print(f"mismatch                = {abs(matched.param_count() - target_params) / target_params:.1%}")
if __name__ == "__main__":
    main()
