"""E0 simulator-validity checks.

These must pass before any result from E1 onward is interpretable. Each returns
(passed, detail).
"""
from __future__ import annotations

import json
from dataclasses import replace

import numpy as np

from emergent_self.config import ControllerConfig, RunConfig
from emergent_self.sim import Simulation


def _fingerprint(result) -> str:
    return json.dumps(result.timeseries, sort_keys=True)


def check_determinism(cfg: RunConfig) -> tuple[bool, str]:
    """Two runs of the same config must produce byte-identical trajectories."""
    a, b = Simulation(cfg).run(), Simulation(cfg).run()
    same = _fingerprint(a) == _fingerprint(b)
    return same, "identical replay" if same else "REPLAY DIVERGED"


def check_rng_independence(cfg: RunConfig) -> tuple[bool, str]:
    """The world must be identical across controller architectures at a fixed
    seed. If mutation draws leak into the world stream, architecture comparisons
    are confounded (research program, failure mode 14.5)."""
    small = Simulation(replace(cfg, controller=ControllerConfig(kind="mlp", hidden_dim=4)))
    large = Simulation(replace(cfg, controller=ControllerConfig(kind="mlp", hidden_dim=64)))
    same_field = np.array_equal(small.world.ambient, large.world.ambient)
    same_res = np.array_equal(small.world.resources, large.world.resources)
    ok = same_field and same_res
    return ok, "world identical across architectures" if ok else "WORLD DEPENDS ON CONTROLLER SIZE"


def check_energy_accounting(cfg: RunConfig, tol: float = 1e-6) -> tuple[bool, str]:
    """Energy in must equal energy out plus energy still embodied."""
    sim = Simulation(cfg)
    initial = sum(a.body.energy for a in sim.agents)
    result = sim.run()
    led = result.energy_ledger
    remaining = sum(a.body.energy for a in sim.agents)
    # Children are endowed from the parent's reproduction cost, so the child's
    # share stays inside the pool and only the non-inherited part is booked out.
    inflow = initial + led["intake"]
    outflow = led["basal"] + led["motion"] + led["repair"] + led["reproduction"] + led["remains"] + led["clamped"]
    residual = inflow - outflow - remaining
    ok = abs(residual) < tol * max(1.0, inflow)
    return ok, f"residual={residual:.3e} (inflow={inflow:.2f})"


def check_neutral_baseline(cfg: RunConfig, tol: float = 0.10) -> tuple[bool, str]:
    """A uniformly random controller must not score positively on the primary
    endpoint: unregulated behaviour must not look like regulation.

    The check is one-sided and its tolerance is loose on purpose. The floor is
    not zero and is not expected to be: metabolic heat of motion pushes a random
    walker's body above the band, while thermal inertia lets any body linger in
    band after entering a hostile cell. Which of the two dominates depends on the
    calibration, so the floor can sit on either side of zero.

    What the check enforces is that the floor stays well below the range evolved
    populations reach, so the endpoint still has headroom to detect regulation.
    The floor itself is measured per experiment by the `floor_condition`, and
    contrasts are taken against it rather than against zero."""
    sim = Simulation(replace(cfg, controller=ControllerConfig(kind="random")))
    result = sim.run()
    # Pooled over every organism from step 0: a random population usually dies
    # back too far for the late-window slice to contain any data at all.
    idx = result.summary["early_thermoregulation_index"]
    raw = result.summary["late_band_occupancy"]
    n = len(result.exposure)
    passive = result.summary["regulation_vs_passive"]
    ok = idx < tol
    return ok, (f"random-controller index={idx:+.3f} over {n} organisms "
                f"(must stay below {tol:+.2f}); regulation_vs_passive={passive:+.3f}; "
                f"raw band occupancy={raw:.3f}")


def check_no_interoception_leak(cfg: RunConfig) -> tuple[bool, str]:
    """Under an ablated interoception condition, the interoception slice of the
    observation must not equal this organism's true body state."""
    from emergent_self.agents import sensors

    ablated = replace(cfg, sensors=replace(cfg.sensors, interoception="shuffled"))
    sim = Simulation(ablated)
    for _ in range(25):
        sim.step()
    if len(sim.agents) < 2:
        return False, "population too small to test"
    lo, hi = sensors.channel_layout(ablated.sensors)["interoception"]
    donors = sim._build_donor_map()
    mismatches = 0
    for a in sim.agents:
        obs = sim._observe(a, donors)
        truth = sensors.interoceptive_vector(a.body, ablated.body)
        if not np.allclose(obs[lo:hi], truth):
            mismatches += 1
    frac = mismatches / len(sim.agents)
    # A derangement guarantees this is every organism, not merely most of them.
    ok = frac == 1.0 and sim.donor_fallbacks == 0
    return ok, (f"{frac:.0%} of organisms receive a body reading that is not their own; "
                f"{sim.donor_fallbacks} donor fallback(s)")


CHECKS = {
    "determinism": check_determinism,
    "rng_independence": check_rng_independence,
    "energy_accounting": check_energy_accounting,
    "neutral_baseline": check_neutral_baseline,
    "no_interoception_leak": check_no_interoception_leak,
}


def run_all(cfg: RunConfig) -> dict[str, tuple[bool, str]]:
    return {name: fn(cfg) for name, fn in CHECKS.items()}
