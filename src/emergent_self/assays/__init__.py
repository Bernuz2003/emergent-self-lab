"""Frozen causal assays: evolve once, then ask many controlled questions.

    spec.py      declare a controlled test as data
    runner.py    execute it against a frozen controller, through Simulation hooks
    measures.py  outcomes computed from a trajectory
    library.py   the standard assays, each a pair of specs differing in one field
"""
from emergent_self.assays.cohorts import (
    AssayConfig,
    CohortResult,
    TrialResult,
    assay_cohort,
    evolve_and_assay,
    run_trial,
)
from emergent_self.assays.library import (
    STANDARD_ASSAYS,
    PairedResult,
    actuator_remap,
    body_contingency,
    memory_necessity,
    sensor_dissociation,
    viability_after_falsification,
)
from emergent_self.assays.runner import Trajectory, run_paired, run_spec, run_spec_all_worlds
from emergent_self.assays.spec import (
    AddSensorNoise,
    AssaySpec,
    DisableAction,
    FalsifySensor,
    InitialState,
    Intervention,
    RemapActuator,
    ResetMemory,
    SetBody,
)

__all__ = [
    "AssayConfig", "CohortResult", "TrialResult", "assay_cohort",
    "evolve_and_assay", "run_trial",
    "AssaySpec", "InitialState", "Intervention", "SetBody", "FalsifySensor",
    "ResetMemory", "RemapActuator", "DisableAction", "AddSensorNoise",
    "Trajectory", "run_spec", "run_spec_all_worlds", "run_paired",
    "PairedResult", "STANDARD_ASSAYS", "body_contingency", "sensor_dissociation",
    "viability_after_falsification", "memory_necessity", "actuator_remap",
]
