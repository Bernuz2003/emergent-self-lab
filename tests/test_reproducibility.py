"""Reproducibility and stream-separation guarantees."""
from __future__ import annotations

import numpy as np
import pytest

from emergent_self.analysis.validity import (
    check_determinism,
    check_energy_accounting,
    check_no_interoception_leak,
    check_rng_independence,
)
from emergent_self.config import ControllerConfig, RunConfig
from dataclasses import replace

from emergent_self.rng import STREAMS, RngBundle
from emergent_self.sim import Simulation

QUICK = RunConfig(steps=250, initial_agents=30, log_every=5, seed=11)


@pytest.mark.parametrize("drained", STREAMS)
def test_draining_one_stream_never_moves_another(drained):
    """The guarantee the whole seed-matched design rests on: adding draws to one
    concern cannot shift the sequence any other concern sees."""
    a, b = RngBundle.from_seed(5), RngBundle.from_seed(5)
    getattr(a, drained).random(1000)
    for name in STREAMS:
        if name != drained:
            assert getattr(a, name).random() == getattr(b, name).random(), name


def test_sensor_draws_do_not_perturb_action_draws():
    """Regression guard: `shuffled` interoception draws a donor every step while
    `true` draws none. When both shared a stream, the two conditions received
    different action randomness for a reason unrelated to the manipulation."""
    from emergent_self.config import SensorConfig

    base = RunConfig(steps=1, seed=3)
    true_sim = Simulation(replace(base, sensors=SensorConfig(interoception="true")))
    shuf_sim = Simulation(replace(base, sensors=SensorConfig(interoception="shuffled")))
    true_sim._build_donor_map()
    shuf_sim._build_donor_map()
    assert true_sim.rng.action.random() == shuf_sim.rng.action.random()


def test_reproduction_placement_does_not_perturb_resource_dynamics():
    """Regression guard: child placement once drew from the resource stream, so a
    population that reproduced more silently shifted every later resource."""
    a, b = RngBundle.from_seed(9), RngBundle.from_seed(9)
    a.reproduction_placement.random(500)
    assert a.resource_dynamics.random() == b.resource_dynamics.random()


def test_different_seeds_give_different_worlds():
    assert not np.array_equal(
        Simulation(RunConfig(steps=1, seed=1)).world.ambient,
        Simulation(RunConfig(steps=1, seed=2)).world.ambient,
    )


def test_run_is_deterministic():
    ok, detail = check_determinism(QUICK)
    assert ok, detail


def test_world_does_not_depend_on_controller_size():
    """Regression guard for the v0.1 confound: mutation drew from the world RNG,
    so parameter count changed resource placement and any architecture
    comparison was confounded."""
    ok, detail = check_rng_independence(QUICK)
    assert ok, detail


def test_energy_is_conserved():
    ok, detail = check_energy_accounting(QUICK)
    assert ok, detail


def test_ablated_interoception_does_not_leak_true_body_state():
    ok, detail = check_no_interoception_leak(QUICK)
    assert ok, detail


def test_controllers_are_capacity_comparable():
    from emergent_self.agents.controller import build_controller, match_hidden_dim
    from emergent_self.agents.sensors import observation_dim
    from emergent_self.config import SensorConfig

    dim = observation_dim(SensorConfig())
    rng = np.random.default_rng(0)
    mlp = build_controller(ControllerConfig(kind="mlp", hidden_dim=24), dim, 5, rng)
    h = match_hidden_dim("gru", dim, 5, mlp.param_count())
    gru = build_controller(ControllerConfig(kind="gru", hidden_dim=h), dim, 5, rng)
    assert abs(gru.param_count() - mlp.param_count()) / mlp.param_count() < 0.05


def test_recurrent_controller_has_persistent_state():
    from emergent_self.agents.controller import build_controller

    rng = np.random.default_rng(0)
    gru = build_controller(ControllerConfig(kind="gru", hidden_dim=8), 29, 5, rng)
    obs = rng.random(29)
    gru.act(obs, rng)
    first = gru.latent().copy()
    gru.act(obs, rng)
    assert not np.allclose(first, gru.latent())
    gru.reset()
    assert np.allclose(gru.latent(), 0.0)
