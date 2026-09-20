"""The general assay framework: specs are data, the runner reuses real physics,
and a paired assay differs only in what it declares."""
from __future__ import annotations

import numpy as np
import pytest

from emergent_self.agents.controller import build_controller
from emergent_self.agents.sensors import channel_layout, observation_dim
from emergent_self.assays import measures as M
from emergent_self.assays.runner import assay_run_config, run_paired, run_spec
from emergent_self.assays.spec import (
    AddSensorNoise,
    AssaySpec,
    DisableAction,
    FalsifySensor,
    InitialState,
    RemapActuator,
    ResetMemory,
    SetBody,
)
from emergent_self.config import ControllerConfig, RunConfig, SensorConfig
from emergent_self.sim import Simulation
from emergent_self.world.grid import ACTIONS

BASE = RunConfig(steps=1, seed=0)


def _ctrl(seed=1, kind="mlp"):
    return build_controller(ControllerConfig(kind=kind, hidden_dim=12),
                            observation_dim(SensorConfig()), len(ACTIONS),
                            np.random.default_rng(seed))


def _spec(**kw):
    kw.setdefault("world_seeds", (1000,))
    kw.setdefault("horizon", 40)
    return AssaySpec(name="t", **kw)


# --- spec layer ------------------------------------------------------------

def test_with_produces_a_single_field_difference():
    a = _spec()
    b = a.with_(horizon=80)
    assert b.differs_from(a) == ["horizon"]
    assert a.horizon == 40  # the original is untouched


def test_identical_specs_differ_in_nothing():
    assert _spec().differs_from(_spec()) == []


def test_intervention_windows():
    iv = SetBody(start=10, stop=20)
    assert not iv.active(9)
    assert iv.active(10) and iv.active(19)
    assert not iv.active(20)


# --- runner ----------------------------------------------------------------

def test_assay_config_forbids_reproduction_and_inherited_interventions():
    cfg = assay_run_config(BASE, _spec(), 1000)
    assert cfg.reproduction.energy_threshold == float("inf")
    assert cfg.interventions.thermal_shock_steps == []
    assert cfg.interventions.hidden_perturbation_prob == 0.0
    assert cfg.initial_agents == 0


def test_population_never_grows_during_an_assay():
    cfg = assay_run_config(BASE, _spec(horizon=120), 1000)
    sim = Simulation(cfg)
    sim.inject(_ctrl())
    for _ in range(120):
        sim.step()
        assert len(sim.agents) <= 1
        if not sim.agents:
            break


def test_rollout_is_deterministic():
    a = run_spec(_ctrl(), BASE, _spec(), 1000)
    b = run_spec(_ctrl(), BASE, _spec(), 1000)
    assert len(a) == len(b)
    assert np.allclose(a.probs(), b.probs())


def test_same_world_seed_gives_the_same_world():
    w1 = Simulation(assay_run_config(BASE, _spec(), 1000)).world
    w2 = Simulation(assay_run_config(BASE, _spec(), 1000)).world
    assert np.array_equal(w1.ambient, w2.ambient)
    assert np.array_equal(w1.resources, w2.resources)


def test_paired_requires_matching_worlds():
    with pytest.raises(ValueError, match="same worlds"):
        run_paired(_ctrl(), BASE, _spec(world_seeds=(1,)), _spec(world_seeds=(2,)))


def test_runner_does_not_mutate_the_supplied_controller():
    c = _ctrl()
    before = c.genome().copy()
    run_spec(c, BASE, _spec(), 1000)
    assert np.allclose(c.genome(), before)


# --- interventions actually intervene --------------------------------------

def test_set_body_changes_the_physical_variable():
    t = run_spec(_ctrl(), BASE,
                 _spec(interventions=(SetBody(start=0, channel="temperature", value=0.95),)),
                 1000)
    assert t.steps[0]["temperature"] > 0.8


def test_falsify_sensor_changes_the_reading_not_the_body():
    lo, _ = channel_layout(SensorConfig())["interoception"]
    truthful = run_spec(_ctrl(), BASE,
                        _spec(interventions=(SetBody(start=0, channel="temperature", value=0.9),)),
                        1000)
    lied = run_spec(_ctrl(), BASE,
                    _spec(interventions=(SetBody(start=0, channel="temperature", value=0.9),
                                         FalsifySensor(channel="temperature", value=0.2))),
                    1000)
    assert truthful.steps[0]["temperature"] == pytest.approx(lied.steps[0]["temperature"])
    assert lied.steps[0]["obs"][lo + 2] == pytest.approx(0.2)
    assert truthful.steps[0]["obs"][lo + 2] != pytest.approx(0.2)


def test_disable_action_removes_it_from_the_realised_actions():
    t = run_spec(_ctrl(), BASE,
                 _spec(horizon=120, interventions=(DisableAction(action=1),)), 1000)
    assert 1 not in set(t.column("action").tolist())


def test_remap_actuator_changes_realised_movement_not_the_policy():
    plain = run_spec(_ctrl(), BASE, _spec(horizon=60), 1000)
    remapped = run_spec(_ctrl(), BASE,
                        _spec(horizon=60, interventions=(RemapActuator(permutation=(0, 3, 4, 1, 2)),)),
                        1000)
    # The first decision is made before any movement, so the policy is identical.
    assert np.allclose(plain.probs()[0], remapped.probs()[0])
    assert list(plain.column("x")) != list(remapped.column("x")) or \
           list(plain.column("y")) != list(remapped.column("y"))


def test_reset_memory_is_a_noop_for_a_reactive_controller():
    """Which makes it its own control: a recurrent controller that is equally
    unaffected is not using its memory."""
    plain = run_spec(_ctrl(kind="mlp"), BASE, _spec(horizon=60), 1000)
    wiped = run_spec(_ctrl(kind="mlp"), BASE,
                     _spec(horizon=60, interventions=(ResetMemory(start=20),)), 1000)
    assert np.allclose(plain.probs(), wiped.probs())


def test_sensor_noise_perturbs_only_the_named_channel():
    lo, _ = channel_layout(SensorConfig())["interoception"]
    clean = run_spec(_ctrl(), BASE, _spec(horizon=30), 1000)
    noisy = run_spec(_ctrl(), BASE,
                     _spec(horizon=30,
                           interventions=(AddSensorNoise(sigma=0.2, channels=("energy",)),)),
                     1000)
    assert clean.steps[0]["obs"][lo + 0] != pytest.approx(noisy.steps[0]["obs"][lo + 0])
    assert clean.steps[0]["obs"][lo + 2] == pytest.approx(noisy.steps[0]["obs"][lo + 2])


# --- measures --------------------------------------------------------------

def test_homeostasis_decomposition_is_exact():
    t = run_spec(_ctrl(), BASE, _spec(horizon=120), 1000)
    h = M.homeostasis(t, BASE.body)
    assert h["homeostatic_advantage"] == pytest.approx(
        h["thermal_decoupling"] + h["microenvironment"])


def test_policy_divergence_of_a_trajectory_with_itself_is_zero():
    t = run_spec(_ctrl(), BASE, _spec(), 1000)
    d = M.policy_divergence(t, t)
    assert d["tv_mean"] == 0.0 and d["tv_first"] == 0.0


def test_viability_outcome_only_covers_the_tail():
    t = run_spec(_ctrl(), BASE, _spec(horizon=100), 1000)
    full = M.viability_outcome(t, BASE.body, 0)
    tail = M.viability_outcome(t, BASE.body, 60)
    assert tail["post_steps"] < full["post_steps"]


def test_measures_on_an_empty_trajectory_are_nan_not_zero():
    from emergent_self.assays.runner import Trajectory

    empty = Trajectory("x", 0, [])
    assert np.isnan(M.homeostasis(empty, BASE.body)["thermal_decoupling"])
    assert np.isnan(M.behaviour(empty)["move_fraction"])
