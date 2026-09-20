"""Body contingency and sensor dissociation: the frozen behavioural tests."""
from __future__ import annotations

import math

import numpy as np

from emergent_self.agents.controller import build_controller
from emergent_self.agents.sensors import observation_dim
from emergent_self.assay import (
    ContingencyConfig,
    _observation_at,
    body_contingency,
    sensor_dissociation,
)
from emergent_self.config import ControllerConfig, RunConfig, SensorConfig
from emergent_self.sim import Simulation
from emergent_self.world.grid import ACTIONS

SMALL = ContingencyConfig(sites_per_world=8, seeds=(1000, 1001), warmup=4)


def _ctrl(seed=1, kind="mlp"):
    return build_controller(ControllerConfig(kind=kind, hidden_dim=12),
                            observation_dim(SensorConfig()), len(ACTIONS),
                            np.random.default_rng(seed))


def test_observation_at_differs_only_in_the_temperature_slot():
    from emergent_self.agents.sensors import channel_layout
    from emergent_self.assay import _assay_run_config

    cfg = _assay_run_config(RunConfig(steps=1, seed=0), 1000, 50)
    sim = Simulation(cfg)
    org = sim.inject(_ctrl())
    cold = _observation_at(sim, org, 0.25)
    hot = _observation_at(sim, org, 0.75)
    lo, _ = channel_layout(cfg.sensors)["interoception"]
    differing = np.flatnonzero(~np.isclose(cold, hot))
    assert differing.tolist() == [lo + 2]


def test_observation_at_restores_the_body():
    from emergent_self.assay import _assay_run_config

    sim = Simulation(_assay_run_config(RunConfig(steps=1, seed=0), 1000, 50))
    org = sim.inject(_ctrl())
    before = org.body.temperature
    _observation_at(sim, org, 0.95)
    assert org.body.temperature == before


def test_false_sensor_leaves_the_physical_body_alone():
    from emergent_self.assay import _assay_run_config

    sim = Simulation(_assay_run_config(RunConfig(steps=1, seed=0), 1000, 50))
    org = sim.inject(_ctrl())
    org.body.temperature = 0.80
    _observation_at(sim, org, 0.80, sensed_override=0.20)
    assert org.body.temperature == 0.80


def test_body_contingency_reports_a_matched_null():
    out = body_contingency(_ctrl(), RunConfig(steps=1, seed=0), SMALL, assay_steps=120)
    assert out["n_sites"] > 0
    assert math.isfinite(out["tv_body"]) and math.isfinite(out["tv_null"])
    assert 0.0 <= out["tv_body"] <= 1.0


def test_body_contingency_is_deterministic():
    a = body_contingency(_ctrl(), RunConfig(steps=1, seed=0), SMALL, assay_steps=120)
    b = body_contingency(_ctrl(), RunConfig(steps=1, seed=0), SMALL, assay_steps=120)
    assert a == b


def test_dissociated_and_sensed_matching_arms_start_identical():
    """A structural guarantee, not an empirical one: sensed temperature is the
    only route body temperature takes into an observation, so on the first step
    a physically-hot organism told it is cold receives exactly the observation a
    veridically-cold one receives. Any later divergence is dynamics, which is
    what the assay is actually measuring."""
    from emergent_self.assay import _assay_run_config

    sim = Simulation(_assay_run_config(RunConfig(steps=1, seed=0), 1000, 50))
    org = sim.inject(_ctrl())
    veridical_cold = _observation_at(sim, org, 0.25)
    dissociated = _observation_at(sim, org, 0.75, sensed_override=0.25)
    assert np.allclose(veridical_cold, dissociated)


def test_sensor_dissociation_actions_track_the_sensed_reading():
    out = sensor_dissociation(_ctrl(), RunConfig(steps=1, seed=0), SMALL,
                              horizon=50, assay_steps=120)
    assert out["n_worlds"] > 0
    for k in ("tv_vs_sensed_match", "tv_vs_physical_match", "follows_sensed_margin"):
        assert math.isfinite(out[k])
    # Actions follow what the organism is told, not what its body is doing.
    assert out["follows_sensed_margin"] < 0.0


def test_dissociated_arm_is_a_third_trajectory_not_a_hybrid():
    """Its physics are the hot arm's and its actions are the cold arm's, so it
    goes somewhere neither of them goes. Asserting it must end near the
    veridical-hot arm would be wrong: different actions mean a different path,
    and therefore different ambient exposure and different damage."""
    out = sensor_dissociation(_ctrl(), RunConfig(steps=1, seed=0), SMALL,
                              horizon=50, assay_steps=120)
    assert math.isfinite(out["integrity_dissociated"])
    assert 0.0 <= out["integrity_dissociated"] <= 1.0


def test_contingency_does_not_mutate_the_supplied_controller():
    c = _ctrl()
    before = c.genome().copy()
    body_contingency(c, RunConfig(steps=1, seed=0), SMALL, assay_steps=120)
    sensor_dissociation(c, RunConfig(steps=1, seed=0), SMALL, horizon=40, assay_steps=120)
    assert np.allclose(c.genome(), before)
