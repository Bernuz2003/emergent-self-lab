"""Physical invariants. These guard the properties the research claims rest on."""
from __future__ import annotations

import numpy as np
import pytest

from emergent_self.agents.body import Body, StepLedger, advance, in_viable_band, thermal_excursion
from emergent_self.config import BodyConfig


def test_energy_zero_is_not_viable():
    assert not Body(energy=0.0).viable


def test_integrity_zero_is_not_viable():
    assert not Body(energy=5.0, integrity=0.0).viable


def test_positive_body_is_viable():
    assert Body(energy=1.0, integrity=1.0).viable


def test_excursion_is_zero_inside_band():
    cfg = BodyConfig()
    assert thermal_excursion(0.5, cfg) == 0.0
    assert in_viable_band(0.5, cfg)


def test_excursion_grows_outside_band():
    cfg = BodyConfig()
    assert thermal_excursion(cfg.viable_temp_hi + 0.2, cfg) == pytest.approx(0.2)
    assert thermal_excursion(cfg.viable_temp_lo - 0.1, cfg) == pytest.approx(0.1)


def test_temperature_relaxes_toward_ambient_when_resting():
    """A resting body must converge on its environment, not drift on its own."""
    cfg = BodyConfig()
    body = Body(energy=10.0, temperature=0.9)
    for _ in range(400):
        advance(body, moved=False, ambient=0.5, cfg=cfg, ledger=StepLedger())
        body.energy = 10.0  # hold energy fixed; this test is about temperature
    assert body.temperature == pytest.approx(0.5, abs=1e-3)


def test_motion_generates_heat():
    """Motion must be thermally costly, otherwise there is no trade-off between
    foraging and staying inside the viable band."""
    cfg = BodyConfig()
    resting, moving = Body(energy=10.0, temperature=0.5), Body(energy=10.0, temperature=0.5)
    for _ in range(50):
        advance(resting, moved=False, ambient=0.5, cfg=cfg, ledger=StepLedger())
        advance(moving, moved=True, ambient=0.5, cfg=cfg, ledger=StepLedger())
        resting.energy = moving.energy = 10.0
    assert moving.temperature > resting.temperature


def test_thermal_excursion_damages_integrity():
    cfg = BodyConfig()
    body = Body(energy=1.0, integrity=1.0, temperature=0.95)
    advance(body, moved=False, ambient=0.95, cfg=cfg, ledger=StepLedger())
    assert body.integrity < 1.0


def test_integrity_and_temperature_are_live_variables():
    """Regression guard for the v0.1 defect: both were declared but never written
    by any transition law, so energy was the only live variable and nothing could
    be regulated."""
    cfg = BodyConfig()
    body = Body(energy=20.0, integrity=1.0, temperature=0.5)
    before = (body.integrity, body.temperature)
    for _ in range(30):
        advance(body, moved=True, ambient=0.95, cfg=cfg, ledger=StepLedger())
    assert (body.integrity, body.temperature) != before
    assert body.integrity < before[0]


def test_energy_never_exceeds_capacity():
    cfg = BodyConfig()
    body = Body(energy=cfg.energy_max, temperature=0.5)
    ledger = StepLedger()
    body.energy += 100.0
    advance(body, moved=False, ambient=0.5, cfg=cfg, ledger=ledger)
    assert body.energy <= cfg.energy_max
    assert ledger.clamped > 0.0


def test_ledger_records_every_energy_movement():
    cfg = BodyConfig()
    body = Body(energy=20.0, integrity=0.5, temperature=0.5)
    ledger = StepLedger()
    start = body.energy
    advance(body, moved=True, ambient=0.5, cfg=cfg, ledger=ledger)
    spent = ledger.basal + ledger.motion + ledger.repair + ledger.clamped
    assert start - body.energy == pytest.approx(spent)
