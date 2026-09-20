"""Interventions must actually fire, and only when scheduled.

An intervention that silently no-ops produces three identical conditions and a
confident null, which is worse than an error.
"""
from __future__ import annotations

import numpy as np
import pytest

from emergent_self.agents import sensors
from emergent_self.config import run_config_from_dict
from emergent_self.sim import Simulation

SPEC = {
    "steps": 400, "seed": 0, "log_every": 50,
    "sensors": {"interoception": "false_body"},
    "interventions": {"false_body_from_step": 200,
                      "false_body_channel": "energy", "false_body_value": 0.9},
}


def _sensed_and_true(sim, cfg):
    lo, _ = sensors.channel_layout(cfg.sensors)["interoception"]
    a = sim.agents[0]
    return sim._observe(a, {})[lo], sensors.interoceptive_vector(a.body, cfg.body)[0]


def test_false_body_is_inert_before_its_scheduled_step():
    cfg = run_config_from_dict(SPEC)
    sim = Simulation(cfg)
    while sim.step_index < 100:
        sim.step()
    sensed, true = _sensed_and_true(sim, cfg)
    assert sensed == pytest.approx(true)


def test_false_body_clamps_the_channel_after_its_scheduled_step():
    cfg = run_config_from_dict(SPEC)
    sim = Simulation(cfg)
    while sim.step_index < 300:
        sim.step()
    sensed, true = _sensed_and_true(sim, cfg)
    assert sensed == pytest.approx(0.9)
    assert sensed != pytest.approx(true)


def test_false_body_leaves_physical_energy_untouched():
    """The discrepancy must be in the sensor, not in the body. If physics changed
    too, the manipulation would not separate sensed state from real state."""
    cfg = run_config_from_dict(SPEC)
    sim = Simulation(cfg)
    while sim.step_index < 300:
        sim.step()
    assert all(a.body.energy <= cfg.body.energy_max for a in sim.agents)
    assert any(a.body.energy / cfg.body.energy_max < 0.9 for a in sim.agents)


def test_thermal_shock_moves_every_body():
    spec = {"steps": 60, "seed": 0, "log_every": 5,
            "interventions": {"thermal_shock_steps": [30], "thermal_shock_value": 0.92}}
    cfg = run_config_from_dict(spec)
    sim = Simulation(cfg)
    while sim.step_index < 30:
        sim.step()
    before = np.mean([a.body.temperature for a in sim.agents])
    sim.step()
    after = np.mean([a.body.temperature for a in sim.agents])
    assert after > before
    assert after > 0.7


def test_shadow_temperature_never_feeds_back_into_physics():
    """The passive counterfactual is measurement only. Corrupting it must not
    change the simulation."""
    cfg = run_config_from_dict({"steps": 120, "seed": 4, "log_every": 10})
    clean = Simulation(cfg)
    for _ in range(120):
        clean.step()

    dirty = Simulation(cfg)
    for _ in range(120):
        for a in dirty.agents:
            a.shadow_temperature = 999.0
        dirty.step()

    assert [a.ident for a in clean.agents] == [a.ident for a in dirty.agents]
    assert np.allclose([a.body.temperature for a in clean.agents],
                       [a.body.temperature for a in dirty.agents])
