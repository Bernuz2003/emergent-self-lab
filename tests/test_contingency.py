"""The frozen causal assays: body contingency and sensor dissociation."""
from __future__ import annotations

import math

import numpy as np
import pytest

from emergent_self.agents.controller import build_controller
from emergent_self.agents.sensors import observation_dim
from emergent_self.assays import body_contingency, measures as M, sensor_dissociation
from emergent_self.assays.library import (
    body_contingency_specs,
    sensor_dissociation_specs,
    viability_after_falsification,
)
from emergent_self.assays.runner import run_paired
from emergent_self.config import ControllerConfig, RunConfig, SensorConfig
from emergent_self.world.grid import ACTIONS

BASE = RunConfig(steps=1, seed=0)
WORLDS = (1000, 1001)


def _ctrl(seed=1, kind="mlp"):
    return build_controller(ControllerConfig(kind=kind, hidden_dim=12),
                            observation_dim(SensorConfig()), len(ACTIONS),
                            np.random.default_rng(seed))


def test_paired_specs_differ_in_exactly_one_field():
    cold, hot = body_contingency_specs(world_seeds=WORLDS)
    assert hot.differs_from(cold) == ["interventions"]
    v_cold, v_hot, dissoc = sensor_dissociation_specs(world_seeds=WORLDS)
    assert dissoc.differs_from(v_hot) == ["interventions"]


@pytest.mark.parametrize("kind", ("mlp", "gru"))
def test_dissociated_and_sensed_matching_arms_are_identical_at_step_zero(kind):
    """A structural guarantee, and the check that the design is wired correctly.

    Sensed temperature is the only route body temperature takes into an
    observation, so an organism that is physically hot but told it is cold must
    receive exactly what a veridically-cold one receives - provided the split
    begins at step 0. An earlier version imposed it before a warmup, and twelve
    steps of physically different bodies moved the arms apart before measurement
    started.
    """
    v_cold, _, dissoc = sensor_dissociation_specs(world_seeds=WORLDS, horizon=40)
    pairs = run_paired(_ctrl(kind=kind), BASE, dissoc, v_cold)
    assert pairs
    for a, b in pairs:
        assert M.policy_divergence(a, b)["tv_first"] == 0.0


def test_body_contingency_reports_a_matched_null():
    r = body_contingency(_ctrl(), BASE, world_seeds=WORLDS)
    assert r.n_worlds == len(WORLDS)
    for k in ("tv_body", "tv_null", "tv_excess"):
        assert math.isfinite(r.metrics[k])
    assert 0.0 <= r.metrics["tv_body"] <= 1.0


def test_body_contingency_is_deterministic():
    a = body_contingency(_ctrl(), BASE, world_seeds=WORLDS)
    b = body_contingency(_ctrl(), BASE, world_seeds=WORLDS)
    assert a.metrics == b.metrics


def test_sensor_dissociation_actions_track_the_sensed_reading():
    r = sensor_dissociation(_ctrl(), BASE, world_seeds=WORLDS, horizon=60)
    assert r.metrics["follows_sensed_margin"] < 0.0


def test_viability_assay_reports_both_arms():
    """Roadmap section 1's missing half: a changed policy is not yet a useful one."""
    r = viability_after_falsification(_ctrl(), BASE, world_seeds=WORLDS, horizon=60)
    for k in ("in_band_truthful", "in_band_blinded", "in_band_benefit",
              "integrity_benefit"):
        assert math.isfinite(r.metrics[k])


def test_assays_do_not_mutate_the_supplied_controller():
    c = _ctrl()
    before = c.genome().copy()
    body_contingency(c, BASE, world_seeds=WORLDS)
    sensor_dissociation(c, BASE, world_seeds=WORLDS, horizon=40)
    viability_after_falsification(c, BASE, world_seeds=WORLDS, horizon=40)
    assert np.allclose(c.genome(), before)
