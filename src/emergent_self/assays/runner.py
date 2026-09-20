"""Execute an AssaySpec against a frozen controller.

The rollout drives the ordinary `Simulation` through its experiment hooks rather
than reimplementing the step loop, so assay physics and evolution physics are
the same code by construction. Reproduction is made physically impossible, so
the population cannot grow and the trial stays a measurement of one controller.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from emergent_self.agents.sensors import channel_layout
from emergent_self.assays.spec import (
    CHANNEL_INDEX,
    AddSensorNoise,
    AssaySpec,
    DisableAction,
    FalsifySensor,
    RemapActuator,
    ResetMemory,
    SetBody,
)
from emergent_self.config import ReproductionConfig, RunConfig, SensorConfig
from emergent_self.sim import Simulation
from emergent_self.world.grid import ACTIONS

#: Reproduction is denied by physics, not by a flag, so the same code path runs.
FROZEN_REPRODUCTION = ReproductionConfig(energy_threshold=float("inf"), population_cap=1)


@dataclass
class Trajectory:
    """Everything one rollout produced. Measures are pure functions of this."""

    spec_name: str
    world_seed: int
    steps: list[dict[str, Any]] = field(default_factory=list)
    died_at: int | None = None
    field_band_fraction: float = float("nan")

    def __len__(self) -> int:
        return len(self.steps)

    def column(self, key: str) -> np.ndarray:
        return np.array([s[key] for s in self.steps])

    def probs(self) -> np.ndarray:
        """(T, n_actions) action distributions, not sampled actions."""
        return np.array([s["probs"] for s in self.steps])


def assay_run_config(base: RunConfig, spec: AssaySpec, world_seed: int) -> RunConfig:
    sensors = base.sensors
    if spec.sensor_mode is not None:
        sensors = replace(sensors, interoception=spec.sensor_mode)
    if spec.sensor_channels is not None:
        sensors = replace(sensors, interoception_channels=spec.sensor_channels)
    return replace(
        base,
        seed=world_seed,
        steps=spec.horizon + spec.initial.warmup + 1,
        initial_agents=0,
        log_every=0,
        sensors=sensors,
        reproduction=FROZEN_REPRODUCTION,
        # Population-level interventions belong to evolution, not to an assay;
        # an assay states its own perturbations in `spec.interventions`.
        interventions=replace(base.interventions, thermal_shock_steps=[],
                              false_body_from_step=None,
                              hidden_perturbation_prob=0.0),
    )


class SpecSession:
    """A spec set up and ready to step, one step at a time.

    Exists so the batch runner and the live paired viewer share one copy of the
    setup: the same world, the same injection, the same hooks. A viewer that
    built its own would be a second implementation of the experiment, free to
    drift from the one that produces the numbers.
    """

    def __init__(self, controller, base: RunConfig, spec: AssaySpec, world_seed: int):
        self.spec = spec
        self.cfg = assay_run_config(base, spec, world_seed)
        self.sim = Simulation(self.cfg)
        self.org = self.sim.inject(copy.deepcopy(controller), x=spec.initial.x,
                                   y=spec.initial.y, energy=spec.initial.energy)
        if spec.initial.integrity is not None:
            self.org.body.integrity = spec.initial.integrity
        if spec.initial.temperature is not None:
            self.org.body.temperature = spec.initial.temperature
            self.org.shadow_temperature = spec.initial.temperature

        self.traj = Trajectory(spec.name, world_seed,
                               field_band_fraction=self.sim.world.field_band_fraction(base.body))
        self.dead = False
        for _ in range(spec.initial.warmup):
            self.sim.step()
            if not self.sim.agents:
                self.dead = True
                self.traj.died_at = 0
                break
        if not self.dead and spec.initial.reset_memory_before_start:
            self.org.controller.reset()

        self._start = self.sim.step_index
        self._lo, _ = channel_layout(self.cfg.sensors)["interoception"]
        self._noise_rng = np.random.default_rng(world_seed ^ 0x5EED)
        self.sim.sensor_filter = self._sensor_filter
        self.sim.action_filter = self._action_filter
        self.sim.step_observer = self._observer

    @property
    def local_step(self) -> int:
        return self.sim.step_index - self._start

    def _sensor_filter(self, a, obs):
        obs = obs.copy()
        for iv in self.spec.interventions:
            if not iv.active(self.local_step):
                continue
            if isinstance(iv, FalsifySensor):
                obs[self._lo + CHANNEL_INDEX[iv.channel]] = iv.value
            elif isinstance(iv, AddSensorNoise):
                idx = ([CHANNEL_INDEX[c] for c in iv.channels] if iv.channels
                       else list(range(len(CHANNEL_INDEX))))
                for i in idx:
                    obs[self._lo + i] = float(np.clip(
                        obs[self._lo + i] + self._noise_rng.normal(0.0, iv.sigma), 0.0, 1.0))
        return obs

    def _action_filter(self, a, action, probs):
        for iv in self.spec.interventions:
            if not iv.active(self.local_step):
                continue
            if isinstance(iv, RemapActuator):
                action = iv.permutation[action % len(iv.permutation)]
            elif isinstance(iv, DisableAction) and action == iv.action:
                action = 0
        return action

    def _observer(self, a, rec):
        r = dict(rec)
        r["step"] = self.local_step
        self.traj.steps.append(r)

    def step(self) -> bool:
        """Advance one step. Returns False once the organism is gone."""
        if self.dead:
            return False
        st = self.local_step
        for iv in self.spec.interventions:
            if isinstance(iv, SetBody):
                if (iv.hold and iv.active(st)) or (not iv.hold and st == iv.start):
                    if iv.channel == "age":
                        self.org.body.age = int(iv.value)
                    else:
                        setattr(self.org.body, iv.channel, iv.value)
                    if iv.channel == "temperature":
                        self.org.shadow_temperature = iv.value
            elif isinstance(iv, ResetMemory) and st == iv.start:
                self.org.controller.reset()

        self.sim.step()
        if not self.sim.agents:
            self.dead = True
            self.traj.died_at = len(self.traj.steps)
            return False
        return True


def run_spec(controller, base: RunConfig, spec: AssaySpec,
             world_seed: int) -> Trajectory:
    """One controller, one world, one spec."""
    session = SpecSession(controller, base, spec, world_seed)
    for _ in range(spec.horizon):
        if not session.step():
            break
    return session.traj


def run_spec_all_worlds(controller, base: RunConfig, spec: AssaySpec) -> list[Trajectory]:
    return [run_spec(controller, base, spec, s) for s in spec.world_seeds]


def run_paired(controller, base: RunConfig, spec_a: AssaySpec,
               spec_b: AssaySpec) -> list[tuple[Trajectory, Trajectory]]:
    """Both specs from the identical starting condition in each world.

    The pair shares the controller, the world seed and everything the two specs
    do not explicitly differ in. `spec_b.differs_from(spec_a)` names what does,
    so 'only one variable changed' is checkable rather than asserted.
    """
    if spec_a.world_seeds != spec_b.world_seeds:
        raise ValueError("a paired assay must use the same worlds in both arms")
    return [(run_spec(controller, base, spec_a, s),
             run_spec(controller, base, spec_b, s)) for s in spec_a.world_seeds]
