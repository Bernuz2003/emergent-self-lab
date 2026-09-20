"""Per-channel interoceptive ablation, the independent-marginal control, and the
sensor RNG split. These are what make a thermal experiment thermal rather than
partly an energetic one."""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from emergent_self.agents.body import Body
from emergent_self.agents.sensors import (
    INTERO_CHANNELS,
    apply_interoception_mode,
    channel_layout,
    channel_mask,
    interoceptive_vector,
)
from emergent_self.config import BodyConfig, RunConfig, SensorConfig
from emergent_self.sim import Simulation

OWN = interoceptive_vector(Body(energy=4.0, integrity=0.30, temperature=0.90, age=50), BodyConfig())
DONOR = interoceptive_vector(Body(energy=22.0, integrity=1.0, temperature=0.40, age=200), BodyConfig())


def _apply(mode, channels, **kw):
    return apply_interoception_mode(
        OWN, cfg=SensorConfig(interoception=mode, interoception_channels=channels),
        rng=np.random.default_rng(0), donor_vec=DONOR, false_body=None, **kw)


def test_default_ablates_every_channel():
    assert channel_mask(SensorConfig()).all()


@pytest.mark.parametrize("channels", (["temperature"], ["energy"], ["energy", "integrity"]))
def test_only_named_channels_are_ablated(channels):
    out = _apply("shuffled", channels)
    for i, name in enumerate(INTERO_CHANNELS):
        if name in channels:
            assert out[i] == pytest.approx(DONOR[i]), name
        else:
            assert out[i] == pytest.approx(OWN[i]), name


def test_unknown_channel_is_rejected():
    with pytest.raises(ValueError, match="unknown interoceptive channel"):
        _apply("shuffled", ["hunger"])


def test_independent_mode_uses_the_marginal_not_the_donor():
    marginal = np.array([0.11, 0.22, 0.33, 0.44])
    out = _apply("independent", ["temperature"], marginal_vec=marginal)
    assert out[2] == pytest.approx(marginal[2])
    assert out[2] != pytest.approx(DONOR[2])


def test_temperature_only_ablation_leaves_energy_veridical_in_a_run():
    cfg = RunConfig(steps=1, seed=3, initial_agents=25,
                    sensors=SensorConfig(interoception="shuffled",
                                         interoception_channels=["temperature"]))
    sim = Simulation(cfg)
    for _ in range(30):
        sim.step()
    lo, _ = channel_layout(cfg.sensors)["interoception"]
    donors = sim._build_donor_map()
    temp_ablated = energy_ablated = 0
    for a in sim.agents:
        obs = sim._observe(a, donors)
        truth = interoceptive_vector(a.body, cfg.body)
        temp_ablated += int(not np.isclose(obs[lo + 2], truth[2]))
        energy_ablated += int(not np.isclose(obs[lo + 0], truth[0]))
    assert temp_ablated == len(sim.agents)
    assert energy_ablated == 0


def test_interoception_mode_does_not_shift_exteroceptive_decoys():
    """Regression guard: `shuffled` consumes draws building its derangement. When
    that shared a stream with the decoy locations, C (intero true, ambient
    shuffled) and D (intero shuffled, ambient shuffled) saw different decoy
    sequences - contaminating exactly the contrast the E1 interaction rests on."""
    base = RunConfig(steps=1, seed=5, initial_agents=8)

    def decoys(mode):
        sim = Simulation(replace(base, sensors=SensorConfig(interoception=mode,
                                                            ambient="shuffled")))
        sim._build_donor_map()
        return [int(sim.rng.extero_decoy.integers(sim.world.size)) for _ in range(8)]

    assert decoys("true") == decoys("shuffled")


def test_snapshot_reports_the_sensed_body_not_the_physical_one():
    cfg = RunConfig(steps=1, seed=4, log_every=0, initial_agents=20,
                    sensors=SensorConfig(interoception="shuffled",
                                         interoception_channels=["temperature"]))
    sim = Simulation(cfg)
    for _ in range(20):
        sim.step()
    views = [a for a in sim.snapshot().agents if a.sensed_intero]
    assert views
    assert any(abs(v.sensed_intero[2] - v.temperature) > 1e-3 for v in views)
