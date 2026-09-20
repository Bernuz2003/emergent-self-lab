"""Body physics.

The simulator owns every variable here. Whether a controller can sense any of
them is decided independently, in sensors.py, by the experimental condition.

Design note: in v0.1 `integrity` and `temperature` existed but were never
written by any transition law, so `energy` was the only live variable and
monotonically good. Nothing could be regulated because nothing traded off. Here
motion generates heat and costs energy, ambient temperature pulls body
temperature toward the local environment, excursion outside the viable band
damages integrity, and repair consumes energy. Resource density is highest where
ambient temperature is most hostile (see world/thermal.py), so "forage more" and
"stay in band" genuinely compete.
"""
from __future__ import annotations

from dataclasses import dataclass

from emergent_self.config import BodyConfig


@dataclass
class Body:
    energy: float = 10.0
    integrity: float = 1.0
    temperature: float = 0.5
    age: int = 0

    @property
    def viable(self) -> bool:
        return self.energy > 0.0 and self.integrity > 0.0


@dataclass
class StepLedger:
    """Per-step energy bookkeeping, used by the E0 conservation check."""

    basal: float = 0.0
    motion: float = 0.0
    repair: float = 0.0
    intake: float = 0.0
    reproduction: float = 0.0
    remains: float = 0.0   # energy still in a body at termination; negative when
                           # the final metabolic charge overdrew the store
    clamped: float = 0.0  # energy discarded at the energy_max ceiling


def thermal_excursion(temperature: float, cfg: BodyConfig) -> float:
    """Distance outside the viable temperature band; 0.0 while inside it."""
    return max(0.0, cfg.viable_temp_lo - temperature) + max(0.0, temperature - cfg.viable_temp_hi)


def in_viable_band(temperature: float, cfg: BodyConfig) -> bool:
    return cfg.viable_temp_lo <= temperature <= cfg.viable_temp_hi


def advance(body: Body, *, moved: bool, ambient: float, cfg: BodyConfig, ledger: StepLedger) -> None:
    """Apply one step of body physics in place.

    No term in here refers to survival, goals, or reward. Termination is the
    absence of subsequent dynamics, not a penalty.
    """
    body.energy -= cfg.basal_cost
    ledger.basal += cfg.basal_cost
    if moved:
        body.energy -= cfg.move_cost
        ledger.motion += cfg.move_cost

    # Newton-style relaxation toward local ambient, plus metabolic heat of motion.
    body.temperature += cfg.thermal_coupling * (ambient - body.temperature)
    if moved:
        body.temperature += cfg.heat_per_move
    body.temperature = min(1.0, max(0.0, body.temperature))

    excursion = thermal_excursion(body.temperature, cfg)
    if excursion > 0.0:
        body.integrity -= cfg.thermal_damage * excursion

    body.age += 1
    if body.age > cfg.senescence_onset:
        body.integrity -= cfg.senescence_rate

    # Repair is metabolism, not policy: it runs whenever the substrate is there.
    if body.integrity < 1.0 and body.energy > cfg.repair_energy_floor:
        delta = min(cfg.repair_rate, 1.0 - body.integrity)
        cost = delta * cfg.repair_energy_cost
        if body.energy - cost > 0.0:
            body.integrity += delta
            body.energy -= cost
            ledger.repair += cost

    body.integrity = min(1.0, body.integrity)
    if body.energy > cfg.energy_max:
        ledger.clamped += body.energy - cfg.energy_max
        body.energy = cfg.energy_max
