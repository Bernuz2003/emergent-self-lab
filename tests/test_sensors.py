"""The sensor layer is where an experiment's manipulation lives, so its
invariants are load-bearing: equal width across conditions, and no leakage of
true body state into an ablated channel."""
from __future__ import annotations

import numpy as np
import pytest

from emergent_self.agents.body import Body
from emergent_self.agents.sensors import (
    apply_interoception_mode,
    channel_layout,
    interoceptive_vector,
    observation_dim,
)
from emergent_self.config import BodyConfig, SensorConfig

MODES = ("true", "shuffled", "noisy", "constant", "false_body")


@pytest.mark.parametrize("mode", MODES)
def test_observation_width_is_identical_across_conditions(mode):
    """Controller input capacity must be matched by construction."""
    assert observation_dim(SensorConfig(interoception=mode)) == observation_dim(SensorConfig())


@pytest.mark.parametrize("mode", ("true", "shuffled", "constant"))
def test_exteroception_width_is_identical_across_conditions(mode):
    assert observation_dim(SensorConfig(ambient=mode)) == observation_dim(SensorConfig())


def test_channels_do_not_overlap_and_cover_the_vector():
    layout = channel_layout(SensorConfig())
    spans = sorted(layout.values())
    assert spans[0][0] == 0
    for (_, prev_stop), (next_start, _) in zip(spans, spans[1:]):
        assert prev_stop == next_start
    assert spans[-1][1] == observation_dim(SensorConfig())


def test_shuffled_interoception_returns_the_donor_not_the_self():
    """The core E1 control: same marginal distribution, no self-coupling."""
    rng = np.random.default_rng(0)
    own = interoceptive_vector(Body(energy=2.0, integrity=0.3, temperature=0.9), BodyConfig())
    donor = interoceptive_vector(Body(energy=20.0, integrity=1.0, temperature=0.4), BodyConfig())
    out = apply_interoception_mode(
        own, cfg=SensorConfig(interoception="shuffled"), rng=rng, donor_vec=donor, false_body=None
    )
    assert np.allclose(out, donor)
    assert not np.allclose(out, own)


def test_false_body_overrides_only_the_targeted_channel():
    rng = np.random.default_rng(0)
    own = interoceptive_vector(Body(energy=2.0, integrity=0.3, temperature=0.9), BodyConfig())
    out = apply_interoception_mode(
        own, cfg=SensorConfig(interoception="false_body"), rng=rng, donor_vec=None, false_body=(0, 0.85)
    )
    assert out[0] == pytest.approx(0.85)
    assert np.allclose(out[1:], own[1:])


def test_noisy_interoception_stays_in_range_but_differs():
    rng = np.random.default_rng(0)
    own = interoceptive_vector(Body(energy=12.0, integrity=0.5, temperature=0.5), BodyConfig())
    out = apply_interoception_mode(
        own, cfg=SensorConfig(interoception="noisy"), rng=rng, donor_vec=None, false_body=None
    )
    assert 0.0 <= out.min() and out.max() <= 1.0
    assert not np.allclose(out, own)


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError):
        apply_interoception_mode(
            np.zeros(4), cfg=SensorConfig(interoception="wishful"),
            rng=np.random.default_rng(0), donor_vec=None, false_body=None,
        )
