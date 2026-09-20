"""One evolutionary run.

Order of a step, for every living organism:
  1. build observation under the current sensor condition
  2. controller picks an action
  3. world transition: motion, ingestion
  4. body physics: metabolism, thermal coupling, damage, repair, senescence
  5. local reproduction check
  6. removal of non-viable organisms, resource regrowth, logging

Termination is simply the removal of an organism from the update loop. It is
never signalled to the controller and carries no penalty.
"""
from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from emergent_self.agents import sensors
from emergent_self.agents.body import Body, StepLedger, advance, in_viable_band, thermal_excursion
from emergent_self.agents.controller import Controller, build_controller
from emergent_self.config import RunConfig
from emergent_self.evolution.lineage import LineageLog
from emergent_self.evolution.reproduction import free_adjacent_cell, may_reproduce
from emergent_self.rng import RngBundle
from emergent_self.world.grid import ACTIONS, GridWorld

INTERO_INDEX = {"energy": 0, "integrity": 1, "temperature": 2, "age": 3}


@dataclass
class Organism:
    ident: int
    founder: int
    parent: int | None
    x: int
    y: int
    body: Body
    controller: Controller
    last_action: int = 0
    last_moved: bool = False
    steps_since_birth: int = 0
    #: The interoceptive slice of the observation actually delivered this step,
    #: stored so a viewer can show the *sensed* body beside the physical one.
    #: A viewer must never call `_observe` to obtain this: that would consume
    #: sensor RNG and change the run it is supposed to be watching.
    sensed_intero: tuple[float, ...] = ()
    # Counterfactual body that follows the same path under the same thermal
    # relaxation but generates no metabolic heat. Measurement only: nothing in
    # the simulation ever reads it, and no controller can sense it.
    shadow_temperature: float = 0.5


@dataclass
class RunResult:
    config: dict[str, Any]
    #: git commit, dirty flag and library versions of the code that produced this.
    provenance: dict[str, Any]
    digest: str
    seed: int
    condition: str
    timeseries: list[dict[str, float]] = field(default_factory=list)
    lifespans: list[int] = field(default_factory=list)
    band_occupancies: list[float] = field(default_factory=list)
    # (steps_alive, steps_body_in_band, steps_ambient_in_band, birth_step) per organism
    exposure: list[tuple[int, int, int, int]] = field(default_factory=list)
    # Same shape, but the third element counts steps a passive no-metabolic-heat
    # body would have spent in band along the identical path.
    shadow_exposure: list[tuple[int, int, int, int]] = field(default_factory=list)
    energy_ledger: dict[str, float] = field(default_factory=dict)
    probe_samples: list[dict[str, list[float]]] = field(default_factory=list)
    extinct_at: int | None = None
    #: Fraction of the world's cells whose ambient temperature is inside the
    #: viable band. The baseline for microenvironment selection; constant per
    #: world, so it is recorded once rather than per step.
    field_band_fraction: float = float("nan")
    summary: dict[str, float] = field(default_factory=dict)


class Simulation:
    def __init__(self, cfg: RunConfig):
        self.cfg = cfg
        self.rng = RngBundle.from_seed(cfg.seed)
        self.world = GridWorld(cfg.world, self.rng.world_init, self.rng.resource_dynamics)
        self.obs_dim = sensors.observation_dim(cfg.sensors)
        self.lineage = LineageLog()
        self.agents: list[Organism] = []
        self.next_id = 0
        self.step_index = 0
        self.ledger = StepLedger()
        self.deaths = 0
        self.births = 0
        self._rows: list[dict[str, float]] = []
        self.donor_fallbacks = 0
        #: Set the first time the population empties, so callers that drive the
        #: loop themselves can tell extinction from "still running".
        self.extinct_step: int | None = None
        self.hidden_perturbations = 0
        #: Events produced by the most recent step. Cleared at the top of each
        #: step and read by whatever is watching; nothing in the simulation
        #: consumes them.
        self.events: list[tuple] = []

        # --- controlled-experiment hooks -----------------------------------
        # All None during an ordinary evolutionary run, so nothing observes or
        # perturbs a scored run unless an experiment declares it (see
        # docs/ARCHITECTURE.md, "Separation of concerns"). The assay framework
        # installs these rather than re-implementing the step loop, so there is
        # exactly one copy of the physics.
        #
        #   sensor_filter(organism, obs)            -> obs            (before act)
        #   action_filter(organism, action, probs)  -> action         (after act)
        #   step_observer(organism, record)         -> None           (after physics)
        self.sensor_filter = None
        self.action_filter = None
        self.step_observer = None
        # Recent body readings, used only when the population is too small for a
        # derangement to exist.
        self._donor_history: collections.deque = collections.deque(maxlen=2048)
        self._shock_steps = set(cfg.interventions.thermal_shock_steps)
        for _ in range(cfg.initial_agents):
            self._spawn_founder()

    # ---------------------------------------------------------------- spawning

    def _spawn_founder(self) -> None:
        x = int(self.rng.init.integers(self.world.size))
        y = int(self.rng.init.integers(self.world.size))
        body = Body(
            energy=self.cfg.body.initial_energy,
            integrity=1.0,
            temperature=self.world.ambient_at(x, y),
        )
        ctrl = build_controller(self.cfg.controller, self.obs_dim, len(ACTIONS), self.rng.init)
        ctrl.reset()
        ident = self.next_id
        self.next_id += 1
        self.agents.append(Organism(ident, ident, None, x, y, body, ctrl,
                                    shadow_temperature=body.temperature))
        self.lineage.birth(ident, ident, None, self.step_index)

    def snapshot(self):
        """A serialisable picture of the current state, for viewers and recorders."""
        from emergent_self.snapshot import AgentView, SimulationSnapshot

        b = self.cfg.body
        agents = [
            AgentView(
                ident=a.ident, founder=a.founder, x=a.x, y=a.y,
                energy=round(a.body.energy, 4), integrity=round(a.body.integrity, 4),
                temperature=round(a.body.temperature, 4), age=a.body.age,
                action=a.last_action, in_band=in_viable_band(a.body.temperature, b),
                sensed_intero=list(a.sensed_intero),
            )
            for a in self.agents
        ]
        xs, ys = np.nonzero(self.world.resources)
        return SimulationSnapshot(
            step=self.step_index,
            population=len(self.agents),
            agents=agents,
            resources=[(int(x), int(y)) for x, y in zip(xs, ys)],
            events=list(self.events),
            stats={
                "births": float(self.births), "deaths": float(self.deaths),
                "n_founders": float(len(self.lineage.living_founders([a.ident for a in self.agents]))),
                "mean_energy": float(np.mean([a.body.energy for a in self.agents])) if self.agents else 0.0,
                "mean_integrity": float(np.mean([a.body.integrity for a in self.agents])) if self.agents else 0.0,
                "band_occupancy": float(np.mean([x.in_band for x in agents])) if agents else 0.0,
            },
        )

    def recording_header(self):
        from dataclasses import asdict as _asdict

        from emergent_self.snapshot import RecordingHeader

        from emergent_self.provenance import provenance

        return RecordingHeader(
            provenance=provenance(),
            size=self.world.size,
            ambient=[[round(float(v), 4) for v in row] for row in self.world.ambient],
            viable_temp_lo=self.cfg.body.viable_temp_lo,
            viable_temp_hi=self.cfg.body.viable_temp_hi,
            energy_max=self.cfg.body.energy_max,
            config=_asdict(self.cfg),
        )

    def inject(self, controller, *, x: int | None = None, y: int | None = None,
               energy: float | None = None) -> Organism:
        """Place a supplied controller into the world as a new organism.

        Used by the frozen assay to evaluate a snapshotted controller in a
        standardised environment. The controller is used as given: nothing here
        mutates it or reads anything back out of it.
        """
        if x is None:
            x = int(self.rng.init.integers(self.world.size))
        if y is None:
            y = int(self.rng.init.integers(self.world.size))
        body = Body(
            energy=self.cfg.body.initial_energy if energy is None else energy,
            integrity=1.0,
            temperature=self.world.ambient_at(x, y),
        )
        controller.reset()
        ident = self.next_id
        self.next_id += 1
        org = Organism(ident, ident, None, x, y, body, controller,
                       shadow_temperature=body.temperature)
        self.agents.append(org)
        self.lineage.birth(ident, ident, None, self.step_index)
        return org

    def snapshot_controllers(self, k: int, rng) -> list:
        """Deep copies of up to k living controllers, frozen at this step.

        Copies, not references: the originals keep evolving after the snapshot is
        taken, and an assay must measure the controller as it was.
        """
        import copy

        if not self.agents:
            return []
        picks = rng.choice(len(self.agents), size=min(k, len(self.agents)), replace=False)
        return [copy.deepcopy(self.agents[int(i)].controller) for i in picks]

    # ------------------------------------------------------------- observation

    def _occupancy(self) -> np.ndarray:
        occ = np.zeros((self.world.size, self.world.size), dtype=bool)
        for a in self.agents:
            occ[a.x, a.y] = True
        return occ

    def _false_body_spec(self) -> tuple[int, float] | None:
        iv = self.cfg.interventions
        if iv.false_body_from_step is None or self.step_index < iv.false_body_from_step:
            return None
        return INTERO_INDEX[iv.false_body_channel], iv.false_body_value

    def _marginal_vector(self) -> np.ndarray | None:
        """A body reading drawn from the empirical marginal built up over the run.

        The `independent` interoception control. `shuffled` borrows from a
        currently living organism, which destroys the self signal but preserves
        a population signal: another body's readings still encode the present
        density, ecological phase and thermal regime. Sampling each channel
        independently from a long history destroys that too, at the cost of no
        longer preserving the joint distribution across channels.
        """
        if self.cfg.sensors.interoception != "independent" or not self._donor_history:
            return None
        hist = np.array([v for _, v in self._donor_history])
        idx = self.rng.intero_donor.integers(len(hist), size=hist.shape[1])
        return hist[idx, np.arange(hist.shape[1])]

    def _observe(self, a: Organism, donors: dict[int, np.ndarray]) -> np.ndarray:
        s = self.cfg.sensors
        true_vec = sensors.interoceptive_vector(a.body, self.cfg.body)
        sensed = sensors.apply_interoception_mode(
            true_vec,
            cfg=s,
            rng=self.rng.sensor_noise,
            donor_vec=donors.get(a.ident),
            false_body=self._false_body_spec(),
            marginal_vec=self._marginal_vector(),
        )
        dx = int(self.rng.extero_decoy.integers(self.world.size))
        dy = int(self.rng.extero_decoy.integers(self.world.size))
        return sensors.assemble(
            resource_patch=sensors.apply_extero_mode(
                self.world.resource_patch(a.x, a.y, s.view_radius), s.resources,
                self.world.resource_patch(dx, dy, s.view_radius), 0.0),
            ambient_patch=sensors.apply_extero_mode(
                self.world.ambient_patch(a.x, a.y, s.view_radius), s.ambient,
                self.world.ambient_patch(dx, dy, s.view_radius), 0.5),
            last_action=a.last_action,
            moved=a.last_moved,
            sensed_intero=sensed,
            cfg=s,
        )

    def _build_donor_map(self) -> dict[int, np.ndarray]:
        """Reassign body readings across the living population without fixed points.

        This is the `shuffled` interoception control. A derangement preserves the
        population's marginal distribution of body readings exactly while
        guaranteeing that no organism receives its own.

        When only one organism is alive no derangement exists. Rather than
        silently handing it its own reading - which would turn the control back
        into true interoception exactly when the population is most fragile - a
        reading is taken from another organism seen recently. If even that is
        unavailable the fallback is counted in `self.donor_fallbacks` and
        surfaced by the E0 validity gate, so it can never pass unnoticed.
        """
        mode = self.cfg.sensors.interoception
        if mode not in ("shuffled", "independent") or not self.agents:
            return {}
        vecs = [sensors.interoceptive_vector(a.body, self.cfg.body) for a in self.agents]
        for a, v in zip(self.agents, vecs):
            self._donor_history.append((a.ident, v))
        if mode == "independent":
            # The history is the whole point of this mode; no derangement needed.
            return {}

        n = len(self.agents)
        if n >= 2:
            perm = sensors.derangement(n, self.rng.intero_donor)
            return {a.ident: vecs[perm[i]] for i, a in enumerate(self.agents)}

        lone = self.agents[0]
        others = [v for ident, v in self._donor_history if ident != lone.ident]
        if others:
            pick = int(self.rng.intero_donor.integers(len(others)))
            return {lone.ident: others[pick]}
        self.donor_fallbacks += 1
        return {}

    # -------------------------------------------------------------------- step

    def step(self) -> None:
        cfg = self.cfg
        # Clear first: an event appended before this line is discarded, which is
        # what silently swallowed every shock event.
        self.events = []

        if self.step_index in self._shock_steps:
            for a in self.agents:
                a.body.temperature = cfg.interventions.thermal_shock_value
            self.events.append(("shock", cfg.interventions.thermal_shock_value))

        iv = cfg.interventions
        if iv.hidden_perturbation_prob > 0.0 and iv.hidden_perturbation_magnitude > 0.0:
            for a in self.agents:
                if self.rng.intervention.random() < iv.hidden_perturbation_prob:
                    sign = 1.0 if self.rng.intervention.random() < 0.5 else -1.0
                    delta = sign * iv.hidden_perturbation_magnitude
                    a.body.temperature = min(1.0, max(0.0, a.body.temperature + delta))
                    # The passive counterfactual takes the same displacement, so
                    # `regulation_vs_passive` still isolates the organism's own
                    # behaviour rather than crediting it for the perturbation.
                    a.shadow_temperature = min(1.0, max(0.0, a.shadow_temperature + delta))
                    self.hidden_perturbations += 1

        occupancy = self._occupancy()
        newborns: list[Organism] = []
        donors = self._build_donor_map()

        for a in list(self.agents):
            obs = self._observe(a, donors)
            if self.sensor_filter is not None:
                obs = self.sensor_filter(a, obs)
            lo, hi = sensors.channel_layout(cfg.sensors)["interoception"]
            a.sensed_intero = tuple(round(float(v), 4) for v in obs[lo:hi])

            probs = a.controller.action_probs(obs)
            action = int(self.rng.action.choice(len(probs), p=probs))
            if self.action_filter is not None:
                action = self.action_filter(a, action, probs)
            dx, dy = ACTIONS[action]
            moved = action != 0
            if moved:
                a.x, a.y = self.world.wrap(a.x + dx, a.y + dy)
            a.last_action, a.last_moved = action, moved

            if self.world.consume(a.x, a.y):
                self.events.append(("consume", a.x, a.y))
                a.body.energy += cfg.body.resource_energy
                self.ledger.intake += cfg.body.resource_energy
                self.lineage.records[a.ident].energy_intake += cfg.body.resource_energy

            ambient = self.world.ambient_at(a.x, a.y)
            advance(a.body, moved=moved, ambient=ambient, cfg=cfg.body, ledger=self.ledger)
            a.shadow_temperature += cfg.body.thermal_coupling * (ambient - a.shadow_temperature)
            a.steps_since_birth += 1

            if self.step_observer is not None:
                self.step_observer(a, {
                    "step": self.step_index, "x": a.x, "y": a.y,
                    "action": action, "probs": probs, "obs": obs,
                    "ambient": ambient,
                    "energy": a.body.energy, "integrity": a.body.integrity,
                    "temperature": a.body.temperature, "age": a.body.age,
                    "shadow_temperature": a.shadow_temperature,
                    "sensed_intero": a.sensed_intero,
                })

            rec = self.lineage.records[a.ident]
            rec.steps_alive += 1
            if in_viable_band(a.body.temperature, cfg.body):
                rec.steps_in_band += 1
            if in_viable_band(ambient, cfg.body):
                rec.steps_ambient_in_band += 1
            if in_viable_band(a.shadow_temperature, cfg.body):
                rec.steps_shadow_in_band += 1

            if may_reproduce(
                body=a.body,
                steps_since_birth=a.steps_since_birth,
                x=a.x, y=a.y,
                occupancy=occupancy,
                population=len(self.agents) + len(newborns),
                maturity_age=cfg.body.maturity_age,
                cfg=cfg.reproduction,
            ):
                newborns.append(self._reproduce(a, occupancy))

        self.agents.extend(newborns)
        self._cull()
        if not self.agents and self.extinct_step is None:
            self.extinct_step = self.step_index
        self.world.respawn()
        self.step_index += 1
        self._log()

    def _reproduce(self, parent: Organism, occupancy: np.ndarray) -> Organism:
        r = self.cfg.reproduction
        parent.body.energy -= r.energy_cost
        self.ledger.reproduction += r.energy_cost * (1.0 - r.child_energy_share)
        parent.steps_since_birth = 0
        cx, cy = free_adjacent_cell(parent.x, parent.y, occupancy, self.rng.reproduction_placement)
        occupancy[cx, cy] = True
        child_body = Body(
            energy=r.energy_cost * r.child_energy_share,
            integrity=1.0,
            temperature=parent.body.temperature,
        )
        ctrl = parent.controller.clone_mutated(self.rng.mutation, r.mutation_sigma)
        ctrl.reset()
        ident = self.next_id
        self.next_id += 1
        self.lineage.birth(ident, parent.founder, parent.ident, self.step_index)
        self.births += 1
        self.events.append(("birth", ident))
        return Organism(ident, parent.founder, parent.ident, cx, cy, child_body, ctrl,
                        shadow_temperature=child_body.temperature)

    def _cull(self) -> None:
        survivors = []
        for a in self.agents:
            if a.body.viable:
                survivors.append(a)
            else:
                # Whatever is still in the body leaves the accounted pool. This
                # can be negative: the last metabolic charge may overdraw the
                # store, which is exactly what makes the organism non-viable.
                self.ledger.remains += a.body.energy
                self.lineage.death(a.ident, self.step_index)
                self.deaths += 1
                # Carry the position: by the time a consumer sees this event the
                # organism is gone from the snapshot, so an id alone cannot be
                # located and the death can never be drawn.
                self.events.append(("death", a.ident, a.x, a.y))
        self.agents = survivors

    # ----------------------------------------------------------------- logging

    def _log(self) -> None:
        if self.cfg.log_every <= 0 or self.step_index % self.cfg.log_every:
            return
        self.timeseries_append()

    def timeseries_append(self) -> None:
        n = len(self.agents)
        if n:
            temps = np.array([a.body.temperature for a in self.agents])
            ambs = np.array([self.world.ambient_at(a.x, a.y) for a in self.agents])
            band = float(np.mean([in_viable_band(t, self.cfg.body) for t in temps]))
            amb_band = float(np.mean([in_viable_band(t, self.cfg.body) for t in ambs]))
            excursion = float(np.mean([thermal_excursion(t, self.cfg.body) for t in temps]))
            row = {
                "step": self.step_index,
                "population": n,
                "mean_energy": float(np.mean([a.body.energy for a in self.agents])),
                "mean_integrity": float(np.mean([a.body.integrity for a in self.agents])),
                "mean_temperature": float(np.mean(temps)),
                "band_occupancy": band,
                "ambient_band_occupancy": amb_band,
                "thermoregulation_index": band - amb_band,
                "mean_excursion": excursion,
                "mean_age": float(np.mean([a.body.age for a in self.agents])),
                "lineage_entropy": self.lineage.lineage_entropy([a.ident for a in self.agents]),
                "n_founders": len(self.lineage.living_founders([a.ident for a in self.agents])),
                "births": self.births,
                "deaths": self.deaths,
                "resources": int(self.world.resources.sum()),
            }
        else:
            row = {"step": self.step_index, "population": 0, "mean_energy": 0.0,
                   "mean_integrity": 0.0, "mean_temperature": 0.0, "band_occupancy": 0.0,
                   "mean_excursion": 0.0, "mean_age": 0.0, "lineage_entropy": 0.0,
                   "n_founders": 0, "births": self.births, "deaths": self.deaths,
                   "resources": int(self.world.resources.sum())}
        self._rows.append(row)

    def run(self) -> RunResult:
        from dataclasses import asdict

        for _ in range(self.cfg.steps):
            self.step()
            if not self.agents:
                break
        extinct_at = self.extinct_step

        finished = [r for r in self.lineage.records.values() if r.steps_alive > 0]
        from emergent_self.provenance import provenance

        result = RunResult(
            config=asdict(self.cfg),
            provenance=provenance(),
            digest=self.cfg.digest(),
            seed=self.cfg.seed,
            condition=self.cfg.condition,
            timeseries=self._rows,
            lifespans=[r.lifespan for r in finished],
            band_occupancies=[r.band_occupancy for r in finished],
            exposure=[(r.steps_alive, r.steps_in_band, r.steps_ambient_in_band, r.birth_step)
                      for r in finished],
            shadow_exposure=[(r.steps_alive, r.steps_in_band, r.steps_shadow_in_band, r.birth_step)
                             for r in finished],
            energy_ledger={
                "intake": self.ledger.intake,
                "basal": self.ledger.basal,
                "motion": self.ledger.motion,
                "repair": self.ledger.repair,
                "reproduction": self.ledger.reproduction,
                "remains": self.ledger.remains,
                "clamped": self.ledger.clamped,
            },
            extinct_at=extinct_at,
            field_band_fraction=self.world.field_band_fraction(self.cfg.body),
        )
        from emergent_self.analysis.metrics import summarise

        result.summary = summarise(result, self.cfg)
        return result
