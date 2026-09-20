"""Evolve, snapshot controllers at checkpoints, and score each cohort.

This is the *evolution* half of the two-phase design. The controlled questions
asked of the snapshotted controllers live in `emergent_self.assays`, which has
the general spec/runner/measures framework; this module only produces the
cohorts and runs the simple standardised survival trial used to compare them.

Why the split exists
--------------------
Every endpoint measured *during* evolution is measured on a moving population.
Organisms are being born, dying, mutating and competing for the same resources
while the measurement is taken, so a condition's score mixes together the
controller's behaviour, the density it happens to live at, the lineage that
happened to win, and survivorship. Asking "did the controller get better?" of
such a number is not really answerable.

The assay separates the two phases:

    EVOLUTION  ->  snapshot controllers at checkpoints  ->  FROZEN ASSAY

In the assay there is no mutation, no reproduction and no selection. One
controller at a time is placed in a standardised world, alone, across a fixed
set of assay seeds that are the same for every controller. Differences between
controllers are then differences between controllers.

This is what makes the comparison the project actually needs available at all:

    ancestral (step 0)  ->  mid evolution  ->  late evolution

measured on identical ground.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace
from typing import Any

import numpy as np

from emergent_self.agents.body import in_viable_band
from emergent_self.config import ReproductionConfig, RunConfig
from emergent_self.sim import Simulation

#: Reproduction is made physically impossible rather than switched off with a
#: flag, so the assay runs the same code path as evolution.
_NO_REPRODUCTION = ReproductionConfig(energy_threshold=float("inf"), population_cap=1)


@dataclass
class TrialResult:
    steps_survived: int
    died: bool
    steps_in_band: int
    steps_ambient_in_band: int
    steps_shadow_in_band: int
    resources_eaten: int
    moves: int
    recovery_steps: float | None
    final_integrity: float

    @property
    def index(self) -> float:
        n = self.steps_survived
        return (self.steps_in_band - self.steps_ambient_in_band) / n if n else math.nan

    @property
    def vs_passive(self) -> float:
        n = self.steps_survived
        return (self.steps_in_band - self.steps_shadow_in_band) / n if n else math.nan

    @property
    def move_fraction(self) -> float:
        return self.moves / self.steps_survived if self.steps_survived else math.nan


@dataclass
class AssayConfig:
    steps: int = 800
    seeds: tuple[int, ...] = (1000, 1001, 1002, 1003, 1004, 1005)
    shock_step: int = 400
    shock_value: float = 0.92
    recovery_window: int = 200
    #: Band occupancy over the 50 steps before the shock defines the level the
    #: organism has to return to; recovery is measured against its own baseline,
    #: not against an absolute number.
    baseline_window: int = 50


@dataclass
class CohortResult:
    label: str
    checkpoint_step: int
    n_controllers: int
    trials: list[dict] = field(default_factory=list)
    summary: dict[str, float] = field(default_factory=dict)


def _assay_run_config(base: RunConfig, assay_seed: int, steps: int) -> RunConfig:
    return replace(
        base,
        seed=assay_seed,
        steps=steps,
        initial_agents=0,
        log_every=0,
        reproduction=_NO_REPRODUCTION,
        interventions=replace(base.interventions, thermal_shock_steps=[], false_body_from_step=None),
    )


def run_trial(controller, base: RunConfig, assay_seed: int, cfg: AssayConfig) -> TrialResult:
    """One controller, alone, in one standardised world."""
    sim = Simulation(_assay_run_config(base, assay_seed, cfg.steps))
    org = sim.inject(controller)

    in_band = amb_band = shadow_band = moves = eaten = 0
    band_history: list[int] = []
    recovery = None
    shock_baseline = None

    for step in range(cfg.steps):
        if step == cfg.shock_step:
            lo = max(0, len(band_history) - cfg.baseline_window)
            window = band_history[lo:]
            shock_baseline = (sum(window) / len(window)) if window else 0.0
            org.body.temperature = cfg.shock_value

        before = org.body.energy
        sim.step()
        if not sim.agents:
            return TrialResult(step + 1, True, in_band, amb_band, shadow_band, eaten,
                               moves, recovery, org.body.integrity)

        moves += int(org.last_moved)
        if org.body.energy > before - base.body.basal_cost:
            eaten += 1
        hit = int(in_viable_band(org.body.temperature, base.body))
        in_band += hit
        band_history.append(hit)
        amb_band += int(in_viable_band(sim.world.ambient_at(org.x, org.y), base.body))
        shadow_band += int(in_viable_band(org.shadow_temperature, base.body))

        if (shock_baseline is not None and recovery is None
                and step > cfg.shock_step and step <= cfg.shock_step + cfg.recovery_window):
            recent = band_history[-cfg.baseline_window:]
            if recent and (sum(recent) / len(recent)) >= shock_baseline * 0.9:
                recovery = float(step - cfg.shock_step)

    return TrialResult(cfg.steps, False, in_band, amb_band, shadow_band, eaten,
                       moves, recovery, org.body.integrity)


def assay_cohort(controllers, base: RunConfig, cfg: AssayConfig, label: str,
                 checkpoint_step: int) -> CohortResult:
    """Every controller against every assay seed. Same worlds for everyone."""
    trials = []
    for i, ctrl in enumerate(controllers):
        for assay_seed in cfg.seeds:
            t = run_trial(ctrl, base, assay_seed, cfg)
            trials.append({
                "controller": i, "assay_seed": assay_seed,
                **asdict(t),
                "index": t.index, "vs_passive": t.vs_passive, "move_fraction": t.move_fraction,
            })

    def col(key):
        return [t[key] for t in trials if t[key] is not None and math.isfinite(t[key])]

    survived = [t["steps_survived"] for t in trials]
    return CohortResult(
        label=label,
        checkpoint_step=checkpoint_step,
        n_controllers=len(controllers),
        trials=trials,
        summary={
            "n_trials": float(len(trials)),
            "mean_steps_survived": float(np.mean(survived)) if survived else math.nan,
            "death_rate": float(np.mean([t["died"] for t in trials])) if trials else math.nan,
            "thermoregulation_index": float(np.mean(col("index"))) if col("index") else math.nan,
            "regulation_vs_passive": float(np.mean(col("vs_passive"))) if col("vs_passive") else math.nan,
            "move_fraction": float(np.mean(col("move_fraction"))) if col("move_fraction") else math.nan,
            "resources_eaten": float(np.mean([t["resources_eaten"] for t in trials])) if trials else math.nan,
            "final_integrity": float(np.mean([t["final_integrity"] for t in trials])) if trials else math.nan,
            "recovery_steps": float(np.mean(col("recovery_steps"))) if col("recovery_steps") else math.nan,
            "n_recovered": float(len(col("recovery_steps"))),
        },
    )


def evolve_and_assay(base: RunConfig, checkpoints: list[int], k_per_checkpoint: int = 8,
                     cfg: AssayConfig | None = None) -> dict[str, Any]:
    """Run evolution, snapshot controllers at `checkpoints`, then assay each cohort.

    The checkpoint at step 0 is the ancestral cohort: the founding population
    before selection has acted on it. It is the comparison that makes any later
    cohort's number mean something.
    """
    cfg = cfg or AssayConfig()
    sim = Simulation(base)
    rng = np.random.default_rng(base.seed)
    cohorts: list[CohortResult] = []
    pending = sorted(set(checkpoints))

    snapshots: list[tuple[int, list]] = []
    if 0 in pending:
        snapshots.append((0, sim.snapshot_controllers(k_per_checkpoint, rng)))
        pending.remove(0)

    for _ in range(base.steps):
        sim.step()
        if pending and sim.step_index >= pending[0]:
            step = pending.pop(0)
            snapshots.append((step, sim.snapshot_controllers(k_per_checkpoint, rng)))
        if not sim.agents:
            break

    for step, controllers in snapshots:
        if not controllers:
            continue
        label = "ancestral" if step == 0 else f"step_{step}"
        cohorts.append(assay_cohort(controllers, base, cfg, label, step))

    from emergent_self.provenance import provenance

    return {
        "config": asdict(base),
        "provenance": provenance(),
        "assay_config": asdict(cfg),
        "extinct_at": sim.extinct_step,
        "cohorts": [{"label": c.label, "checkpoint_step": c.checkpoint_step,
                     "n_controllers": c.n_controllers, "summary": c.summary,
                     "trials": c.trials} for c in cohorts],
    }
