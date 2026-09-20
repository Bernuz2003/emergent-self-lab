"""Declarative specification of a controlled test on a frozen controller.

Roadmap section 3: frozen assays become a general research primitive rather than
an experiment-specific utility — *evolve once, then ask many controlled
questions of the frozen controller*.

A spec says what to hold fixed, what to change, how long to run and what to
measure. Everything a later stage needs is expressible here: false-body
experiments, memory ablations, body remapping, tool incorporation, self/world
causal tests, novel-threat experiments.

Nothing in this module runs a simulation. It only describes one, so that two
conditions can be written down side by side and compared for what actually
differs between them.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal

import numpy as np

BodyChannel = Literal["energy", "integrity", "temperature", "age"]
CHANNEL_INDEX = {"energy": 0, "integrity": 1, "temperature": 2, "age": 3}


@dataclass(frozen=True)
class InitialState:
    """Where the organism starts and in what condition.

    `None` means "leave whatever the simulator produced", so a spec only pins
    down the variables the experiment is about. `warmup` runs the organism freely
    before the clock starts, which matters for a recurrent controller: probing it
    from a permanently zeroed hidden state measures a state it never occupies in
    life.
    """

    x: int | None = None
    y: int | None = None
    energy: float | None = None
    integrity: float | None = None
    temperature: float | None = None
    warmup: int = 0
    reset_memory_before_start: bool = True


# --------------------------------------------------------------------------
# Interventions. Each declares when it applies and what it touches. They compose:
# a spec holds a list and they are applied in order.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Intervention:
    """Base class. `start`/`stop` are step indices into the rollout."""

    start: int = 0
    stop: int | None = None

    def active(self, step: int) -> bool:
        return step >= self.start and (self.stop is None or step < self.stop)

    def label(self) -> str:
        return type(self).__name__


@dataclass(frozen=True)
class SetBody(Intervention):
    """Force a physical body variable. This changes the world, not a reading."""

    channel: BodyChannel = "temperature"
    value: float = 0.5
    #: Once at `start`, or held at `value` for the whole window.
    hold: bool = False

    def label(self) -> str:
        return f"SetBody({self.channel}={self.value:g}{'·held' if self.hold else ''})"


@dataclass(frozen=True)
class FalsifySensor(Intervention):
    """Force what the controller *reads* for a body channel, leaving the physical
    value untouched. The difference between this and SetBody is the whole point
    of the false-body paradigm."""

    channel: BodyChannel = "temperature"
    value: float = 0.5

    def label(self) -> str:
        return f"FalsifySensor({self.channel}={self.value:g})"


@dataclass(frozen=True)
class ResetMemory(Intervention):
    """Clear the controller's persistent state. A no-op for a reactive controller,
    which is itself a useful control."""

    def label(self) -> str:
        return f"ResetMemory@{self.start}"


@dataclass(frozen=True)
class RemapActuator(Intervention):
    """Permute the action space, so the same policy output produces a different
    movement. The body-schema manipulation of roadmap section 10."""

    permutation: tuple[int, ...] = (0, 1, 2, 3, 4)

    def label(self) -> str:
        return f"RemapActuator{self.permutation}"


@dataclass(frozen=True)
class DisableAction(Intervention):
    """Make one action impossible; it is replaced by staying put."""

    action: int = 1

    def label(self) -> str:
        return f"DisableAction({self.action})"


@dataclass(frozen=True)
class AddSensorNoise(Intervention):
    """Gaussian noise on the interoceptive slice."""

    sigma: float = 0.1
    channels: tuple[BodyChannel, ...] = ()

    def label(self) -> str:
        which = ",".join(self.channels) if self.channels else "all"
        return f"AddSensorNoise(sigma={self.sigma:g},{which})"


@dataclass(frozen=True)
class AssaySpec:
    """One controlled question, fully specified.

    Two specs that differ in a single field are a matched counterfactual pair,
    which is the comparison the whole framework exists to make cheap to write.
    """

    name: str = "unnamed"
    world_seeds: tuple[int, ...] = (1000, 1001, 1002, 1003)
    horizon: int = 200
    initial: InitialState = field(default_factory=InitialState)
    interventions: tuple[Intervention, ...] = ()
    #: Sensor and actuator wiring for the whole rollout, distinct from the
    #: timed interventions above.
    sensor_mode: str | None = None
    sensor_channels: list[str] | None = None
    notes: str = ""

    def with_(self, **changes: Any) -> "AssaySpec":
        """A copy differing in the named fields. The idiom for building a pair."""
        return replace(self, **changes)

    def differs_from(self, other: "AssaySpec") -> list[str]:
        """Which fields differ. Printed beside every paired result so a claim
        about 'only X changed' can be checked rather than trusted."""
        out = []
        for f in ("world_seeds", "horizon", "initial", "interventions",
                  "sensor_mode", "sensor_channels"):
            if getattr(self, f) != getattr(other, f):
                out.append(f)
        return out

    def describe(self) -> str:
        bits = [f"horizon={self.horizon}", f"worlds={len(self.world_seeds)}"]
        if self.sensor_mode:
            bits.append(f"intero={self.sensor_mode}")
        if self.interventions:
            bits.append("+".join(i.label() for i in self.interventions))
        return f"{self.name}: " + ", ".join(bits)
