"""The frozen assay must really be frozen, and must be the same for everyone."""
from __future__ import annotations

import numpy as np
import pytest

from emergent_self.agents.controller import build_controller
from emergent_self.agents.sensors import derangement, observation_dim
from emergent_self.assay import AssayConfig, run_trial
from emergent_self.config import ControllerConfig, RunConfig, SensorConfig
from emergent_self.sim import Simulation
from emergent_self.world.grid import ACTIONS

SMALL = AssayConfig(steps=120, seeds=(1000, 1001), shock_step=60, recovery_window=40)


def _controller(seed=0):
    return build_controller(ControllerConfig(kind="mlp", hidden_dim=12),
                            observation_dim(SensorConfig()), len(ACTIONS),
                            np.random.default_rng(seed))


def test_assay_is_deterministic():
    base = RunConfig(steps=1, seed=0)
    a = run_trial(_controller(), base, 1000, SMALL)
    b = run_trial(_controller(), base, 1000, SMALL)
    assert a == b


def test_assay_has_no_reproduction():
    """If the population can grow, the trial stops being a measurement of one
    controller and becomes another evolutionary run."""
    from dataclasses import replace

    from emergent_self.assay import _assay_run_config

    cfg = _assay_run_config(RunConfig(steps=1, seed=0), 1000, 200)
    sim = Simulation(cfg)
    sim.inject(_controller())
    for _ in range(200):
        sim.step()
        assert len(sim.agents) <= 1
        if not sim.agents:
            break


def test_same_assay_seed_gives_every_controller_the_same_world():
    base = RunConfig(steps=1, seed=0)
    from emergent_self.assay import _assay_run_config

    w1 = Simulation(_assay_run_config(base, 1000, 50)).world
    w2 = Simulation(_assay_run_config(base, 1000, 50)).world
    assert np.array_equal(w1.ambient, w2.ambient)
    assert np.array_equal(w1.resources, w2.resources)


def test_different_controllers_produce_different_behaviour():
    base = RunConfig(steps=1, seed=0)
    a = run_trial(_controller(1), base, 1000, SMALL)
    b = run_trial(_controller(99), base, 1000, SMALL)
    assert (a.moves, a.resources_eaten) != (b.moves, b.resources_eaten)


def test_snapshotted_controller_is_a_copy_not_a_reference():
    """A snapshot must record the controller as it was; the original keeps
    evolving after the checkpoint."""
    sim = Simulation(RunConfig(steps=30, seed=4, log_every=0, initial_agents=20))
    for _ in range(30):
        sim.step()
    snaps = sim.snapshot_controllers(3, np.random.default_rng(0))
    assert snaps
    before = snaps[0].genome().copy()
    for a in sim.agents:
        a.controller.w2 += 5.0
    assert np.allclose(snaps[0].genome(), before)


def test_trial_metrics_are_bounded():
    t = run_trial(_controller(), RunConfig(steps=1, seed=0), 1000, SMALL)
    assert 0 < t.steps_survived <= SMALL.steps
    assert 0.0 <= t.move_fraction <= 1.0
    assert t.steps_in_band <= t.steps_survived


@pytest.mark.parametrize("n", (2, 3, 7, 40))
def test_derangement_has_no_fixed_point(n):
    rng = np.random.default_rng(0)
    for _ in range(200):
        p = derangement(n, rng)
        assert sorted(p) == list(range(n))
        assert not (p == np.arange(n)).any()


def test_derangement_rejects_impossible_sizes():
    rng = np.random.default_rng(0)
    for n in (0, 1):
        with pytest.raises(ValueError):
            derangement(n, rng)
