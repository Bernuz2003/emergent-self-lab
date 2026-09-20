"""The primary endpoint must measure regulation, not survival."""
from __future__ import annotations

import pytest

from emergent_self.analysis.metrics import exposure_weighted_index
from emergent_self.analysis.stats import cliffs_delta, compare, hedges_g


def test_index_is_zero_when_body_merely_tracks_environment():
    # (steps_alive, steps_body_in_band, steps_ambient_in_band, birth_step)
    assert exposure_weighted_index([(100, 60, 60, 0), (50, 20, 20, 0)]) == pytest.approx(0.0)


def test_index_is_positive_only_when_body_beats_its_environment():
    assert exposure_weighted_index([(100, 90, 40, 0)]) == pytest.approx(0.5)


def test_index_is_negative_when_body_is_worse_than_its_environment():
    assert exposure_weighted_index([(100, 10, 70, 0)]) == pytest.approx(-0.6)


def test_index_weights_by_exposure_not_by_organism():
    """A long-lived organism must not count the same as a one-step one, or a
    burst of short-lived deaths would dominate the endpoint."""
    rows = [(1000, 900, 400, 0), (1, 0, 1, 0)]
    assert exposure_weighted_index(rows) > 0.49


def test_index_respects_the_birth_window():
    early, late = (100, 100, 0, 0), (100, 0, 100, 900)
    assert exposure_weighted_index([early, late], born_after=900) == pytest.approx(-1.0)


def test_empty_exposure_is_nan_not_zero():
    """Absence of measurement is not a measurement of zero. Returning 0.0 here
    once dragged 11 of 12 random-controller runs to an invented index and
    manufactured a Hedges g of -0.92 against them."""
    import math

    assert math.isnan(exposure_weighted_index([]))
    assert math.isnan(exposure_weighted_index([(100, 50, 50, 0)], born_after=999))


def test_eligible_organism_count_exposes_an_empty_window():
    from emergent_self.analysis.metrics import eligible_organisms

    exposure = [(100, 50, 40, 0), (80, 30, 20, 5000)]
    assert eligible_organisms(exposure, born_after=4500) == 1
    assert eligible_organisms(exposure, born_after=9999) == 0


def test_effect_sizes_have_the_expected_sign():
    a, b = [1.0, 1.1, 0.9, 1.2], [0.1, 0.0, 0.2, -0.1]
    assert hedges_g(a, b) > 1.0
    assert cliffs_delta(a, b) == pytest.approx(1.0)
    assert compare(a, b)["diff"] > 0
