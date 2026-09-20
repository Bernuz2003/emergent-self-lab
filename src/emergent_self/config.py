"""Declarative run configuration.

A config is a plain dataclass tree loaded from JSON. It is hashed and written
into every result file so a run can be reproduced from its output alone.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, get_type_hints


@dataclass
class BodyConfig:
    """Physical constants of an organism. Owned by the simulator, not the controller."""

    energy_max: float = 24.0
    initial_energy: float = 10.0
    basal_cost: float = 0.045
    move_cost: float = 0.055
    resource_energy: float = 3.2

    # Thermal coupling. Body temperature relaxes toward local ambient and motion
    # adds metabolic heat. These two are calibrated together and should not be
    # changed independently:
    #   * the steady-state offset of a mover is roughly
    #     (fraction of steps moving) * heat_per_move / thermal_coupling,
    #     so a large ratio cooks the whole population within a few hundred steps;
    #   * a large thermal_coupling makes body temperature a near-copy of the
    #     ambient value the organism can already see in its exteroceptive patch,
    #     which makes interoception redundant and forces E1 to a null.
    # Measured with scripts/diagnose_redundancy.py: at coupling 0.18 the current
    # cell explained 76% of body-temperature variance; at 0.06 it explains ~42%,
    # the remainder being the organism's own recent thermal and motor history.
    thermal_coupling: float = 0.06
    heat_per_move: float = 0.013
    viable_temp_lo: float = 0.35
    viable_temp_hi: float = 0.65

    # Integrity is damaged by thermal excursion and repaired metabolically.
    thermal_damage: float = 0.14
    repair_rate: float = 0.006
    repair_energy_cost: float = 8.0
    repair_energy_floor: float = 6.0

    # Senescence gives lineages turnover so evolution keeps moving.
    maturity_age: int = 40
    senescence_onset: int = 260
    senescence_rate: float = 0.0035


@dataclass
class WorldConfig:
    size: int = 32
    # Calibrated against extinction rate: at max_resources 110 / respawn 2.2 /
    # 40 founders, a third of seeds died out inside 300 steps before selection
    # could act on anything. At these values extinction was 0/8 across the whole
    # calibration sweep (scripts/calibrate.py).
    max_resources: int = 150
    respawn_per_step: float = 5.0
    # Resource density is concentrated where ambient temperature is extreme, so
    # the richest foraging is thermally hostile. This is what makes regulation a
    # trade-off rather than a free lunch.
    hostility_coupling: float = 2.0
    thermal_blobs: int = 5
    thermal_blob_sigma: float = 5.0


@dataclass
class ReproductionConfig:
    """Local, ecological reproduction. No global fitness ranking exists anywhere."""

    energy_threshold: float = 17.0
    energy_cost: float = 9.0
    child_energy_share: float = 0.55
    integrity_threshold: float = 0.55
    refractory_steps: int = 25
    local_density_radius: int = 2
    local_density_max: int = 5
    population_cap: int = 220
    mutation_sigma: float = 0.045


@dataclass
class SensorConfig:
    """Declarative observation channels. Dimensionality is identical in every
    condition, so controller input capacity is held constant by construction."""

    view_radius: int = 1
    proprioception: bool = True
    # Each exteroceptive channel is manipulable on its own. Ablating the ambient
    # channel while keeping interoception is what separates "regulate by standing
    # somewhere mild" from "regulate by sensing your own body".
    # true | shuffled | constant
    resources: str = "true"
    ambient: str = "true"
    # true | shuffled | noisy | constant | false_body
    interoception: str = "true"
    interoception_noise: float = 0.15


@dataclass
class ControllerConfig:
    kind: str = "mlp"  # mlp | gru | random
    hidden_dim: int = 24
    policy_temperature: float = 0.35
    init_scale: float = 0.4


@dataclass
class InterventionConfig:
    """Researcher-applied perturbations. Disabled by default; the analysis layer
    never touches the simulation unless an intervention is declared here."""

    thermal_shock_steps: list[int] = field(default_factory=list)
    thermal_shock_value: float = 0.92
    recovery_window: int = 120
    # Hidden internal perturbation (E1b). With probability `p` per organism per
    # step, body temperature is displaced by +/- `magnitude`. Nothing external
    # changes: the ambient field, the resource layout and the organism's position
    # are untouched, so two organisms standing on the same cell can need opposite
    # actions. This is the manipulation that makes body state impossible to infer
    # from the world, which is precisely what E1 turned out to lack.
    hidden_perturbation_prob: float = 0.0
    hidden_perturbation_magnitude: float = 0.0

    false_body_from_step: int | None = None
    false_body_channel: str = "energy"
    false_body_value: float = 0.85


@dataclass
class RunConfig:
    name: str = "unnamed"
    condition: str = "default"
    seed: int = 0
    steps: int = 4000
    initial_agents: int = 60
    log_every: int = 10
    probe_sample_every: int = 0
    body: BodyConfig = field(default_factory=BodyConfig)
    world: WorldConfig = field(default_factory=WorldConfig)
    reproduction: ReproductionConfig = field(default_factory=ReproductionConfig)
    sensors: SensorConfig = field(default_factory=SensorConfig)
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    interventions: InterventionConfig = field(default_factory=InterventionConfig)

    def digest(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:16]


def _build(cls, data: dict[str, Any]):
    kwargs = {}
    # `from __future__ import annotations` makes field.type a string, so resolve
    # the real types before deciding whether to recurse into a nested dataclass.
    hints = get_type_hints(cls)
    known = {f.name for f in fields(cls)}
    for key, value in data.items():
        if key not in known:
            raise ValueError(f"unknown config key '{key}' for {cls.__name__}")
        ftype = hints[key]
        if is_dataclass(ftype) and isinstance(value, dict):
            kwargs[key] = _build(ftype, value)
        else:
            kwargs[key] = value
    return cls(**kwargs)


def load_run_config(path: str | Path) -> RunConfig:
    return _build(RunConfig, json.loads(Path(path).read_text()))


def run_config_from_dict(data: dict[str, Any]) -> RunConfig:
    return _build(RunConfig, data)
