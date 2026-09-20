"""Frozen assay: evaluate a controller as it was, in a standardised world.

Why this exists
---------------
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
from emergent_self.world.grid import ACTIONS

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


# ---------------------------------------------------------------------------
# Body contingency: does the same controller act differently on the same world
# when only its body differs?
# ---------------------------------------------------------------------------

@dataclass
class ContingencyConfig:
    cold: float = 0.25
    hot: float = 0.75
    #: Positions sampled per world; each gives one matched pair of observations.
    sites_per_world: int = 40
    seeds: tuple[int, ...] = (1000, 1001, 1002, 1003)
    #: Steps of free running before a site is measured, so a recurrent
    #: controller is not always probed from a zeroed hidden state.
    warmup: int = 12


def _observation_at(sim, org, body_temperature: float, sensed_override: float | None = None):
    """Build the observation an organism would receive at its current position
    with its body temperature set to `body_temperature`.

    `sensed_override` falsifies only the sensed temperature, leaving the physical
    value alone. Returned observation, nothing mutated that the caller does not
    restore.
    """
    from emergent_self.agents import sensors

    saved = org.body.temperature
    org.body.temperature = body_temperature
    true_vec = sensors.interoceptive_vector(org.body, sim.cfg.body)
    if sensed_override is not None:
        true_vec = true_vec.copy()
        true_vec[2] = sensed_override
    s = sim.cfg.sensors
    obs = sensors.assemble(
        resource_patch=sim.world.resource_patch(org.x, org.y, s.view_radius),
        ambient_patch=sim.world.ambient_patch(org.x, org.y, s.view_radius),
        last_action=org.last_action,
        moved=org.last_moved,
        sensed_intero=true_vec,
        cfg=s,
    )
    org.body.temperature = saved
    return obs


def body_contingency(controller, base: RunConfig, cfg: ContingencyConfig | None = None,
                     assay_steps: int = 400) -> dict[str, float]:
    """Hold the world fixed, vary only the body, and compare action distributions.

    At each sampled site the controller is shown two observations that differ in
    exactly one number: its own sensed body temperature, cold versus hot. If it
    uses that channel at all, the two action distributions must differ.

    `tv_null` is the same comparison with the *age* channel displaced by the same
    amount instead. Any large enough input change moves a softmax policy
    somewhat, so a bare `tv_body` is not interpretable; what matters is whether
    it exceeds a magnitude-matched change to a channel with no thermal meaning.
    """
    import copy

    cfg = cfg or ContingencyConfig()
    delta = cfg.hot - cfg.cold
    tv_body, tv_null, move_cold, move_hot = [], [], [], []

    for assay_seed in cfg.seeds:
        sim = Simulation(_assay_run_config(base, assay_seed, assay_steps))
        org = sim.inject(copy.deepcopy(controller))
        for _ in range(cfg.warmup):
            sim.step()
            if not sim.agents:
                break
        if not sim.agents:
            continue

        for _ in range(cfg.sites_per_world):
            saved_h = org.controller.latent().copy()

            p_cold = org.controller.action_probs(_observation_at(sim, org, cfg.cold))
            org.controller._h = saved_h.copy()
            p_hot = org.controller.action_probs(_observation_at(sim, org, cfg.hot))
            org.controller._h = saved_h.copy()

            # Magnitude-matched change to a thermally meaningless channel.
            base_obs = _observation_at(sim, org, cfg.cold)
            null_obs = base_obs.copy()
            from emergent_self.agents.sensors import channel_layout

            lo, _ = channel_layout(sim.cfg.sensors)["interoception"]
            null_obs[lo + 3] = min(1.0, null_obs[lo + 3] + delta)   # age
            p_null = org.controller.action_probs(null_obs)
            org.controller._h = saved_h.copy()

            tv_body.append(0.5 * float(np.abs(p_cold - p_hot).sum()))
            tv_null.append(0.5 * float(np.abs(p_cold - p_null).sum()))
            move_cold.append(1.0 - float(p_cold[0]))
            move_hot.append(1.0 - float(p_hot[0]))

            sim.step()
            if not sim.agents:
                break

    if not tv_body:
        return {"tv_body": math.nan, "tv_null": math.nan, "tv_ratio": math.nan,
                "delta_move": math.nan, "n_sites": 0.0}
    tvb, tvn = float(np.mean(tv_body)), float(np.mean(tv_null))
    return {
        "tv_body": tvb,
        "tv_body_sd": float(np.std(tv_body)),
        "tv_null": tvn,
        "tv_ratio": tvb / tvn if tvn > 1e-9 else math.inf,
        "delta_move": float(np.mean(move_hot)) - float(np.mean(move_cold)),
        "n_sites": float(len(tv_body)),
    }


def sensor_dissociation(controller, base: RunConfig, cfg: ContingencyConfig | None = None,
                        horizon: int = 100, assay_steps: int = 400) -> dict[str, float]:
    """Does behaviour follow the sensed body or the physical one?

    Three arms share a world, a starting position and a frozen controller:

      veridical_cold   physical cold, sensed cold
      veridical_hot    physical hot,  sensed hot
      dissociated      physical hot,  sensed cold

    A single observation cannot separate these: sensed temperature is the only
    route body temperature takes into an observation, so the dissociated arm's
    first observation is identical to veridical_cold's by construction. The
    separation is dynamic. Physical temperature drives integrity damage and
    death, so over a horizon the three arms diverge, and the question is whether
    the dissociated arm's *actions* track the arm it shares a sensed state with.

    The dissociated arm is a third trajectory, not a hybrid of the other two. Its
    physics are the hot arm's and its actions are the cold arm's, so it visits
    cells neither of the others visits and can end up in better condition than
    both. `follows_sensed_margin` is therefore the endpoint; the integrity
    figures are descriptive context, not a test of anything.
    """
    import copy

    cfg = cfg or ContingencyConfig()
    rows = []

    for assay_seed in cfg.seeds:
        arms = {}
        for label, physical, sensed in (
            ("veridical_cold", cfg.cold, None),
            ("veridical_hot", cfg.hot, None),
            ("dissociated", cfg.hot, cfg.cold),
        ):
            sim = Simulation(_assay_run_config(base, assay_seed, assay_steps))
            org = sim.inject(copy.deepcopy(controller))
            org.body.temperature = physical

            actions, integ, survived = [], [], 0
            for _ in range(horizon):
                obs = _observation_at(sim, org, org.body.temperature, sensed)
                probs = org.controller.action_probs(obs)
                actions.append(probs)
                # Drive the world with the action the controller actually chose
                # under its (possibly falsified) reading.
                a_idx = int(np.argmax(probs))
                dx, dy = ACTIONS[a_idx]
                if a_idx != 0:
                    org.x, org.y = sim.world.wrap(org.x + dx, org.y + dy)
                org.last_action, org.last_moved = a_idx, a_idx != 0
                advance_body(org, sim)
                survived += 1
                integ.append(org.body.integrity)
                if not org.body.viable:
                    break
            arms[label] = {"actions": np.array(actions), "integrity": integ,
                           "survived": survived}

        d, vc, vh = arms["dissociated"], arms["veridical_cold"], arms["veridical_hot"]
        n_c = min(len(d["actions"]), len(vc["actions"]))
        n_h = min(len(d["actions"]), len(vh["actions"]))
        if n_c == 0 or n_h == 0:
            continue
        rows.append({
            "tv_vs_sensed_match": float(np.mean(
                0.5 * np.abs(d["actions"][:n_c] - vc["actions"][:n_c]).sum(axis=1))),
            "tv_vs_physical_match": float(np.mean(
                0.5 * np.abs(d["actions"][:n_h] - vh["actions"][:n_h]).sum(axis=1))),
            "integrity_dissociated": d["integrity"][-1] if d["integrity"] else math.nan,
            "integrity_veridical_hot": vh["integrity"][-1] if vh["integrity"] else math.nan,
            "integrity_veridical_cold": vc["integrity"][-1] if vc["integrity"] else math.nan,
            "survived_dissociated": float(d["survived"]),
            "survived_veridical_hot": float(vh["survived"]),
        })

    if not rows:
        return {"n_worlds": 0.0}
    out = {k: float(np.mean([r[k] for r in rows if math.isfinite(r[k])])) for k in rows[0]}
    out["n_worlds"] = float(len(rows))
    # Negative means actions track the sensed reading rather than the physical one.
    out["follows_sensed_margin"] = out["tv_vs_sensed_match"] - out["tv_vs_physical_match"]
    return out


def advance_body(org, sim) -> None:
    """One step of body physics for a single organism, outside the population loop."""
    from emergent_self.agents.body import StepLedger, advance

    ambient = sim.world.ambient_at(org.x, org.y)
    advance(org.body, moved=org.last_moved, ambient=ambient, cfg=sim.cfg.body,
            ledger=StepLedger())
    if sim.world.consume(org.x, org.y):
        org.body.energy += sim.cfg.body.resource_energy
