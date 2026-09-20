"""A serialisable picture of the simulation at one step.

`Simulation` knows nothing about this module's consumers. It produces a
snapshot; a renderer, a recorder or an analysis script consumes one. That
one-way dependency is what keeps the visualiser from becoming a second,
divergent implementation of the simulation's state, and it is why a recorded run
can be replayed later with no simulator running at all.

A snapshot holds only what a viewer needs. The static ambient field is not part
of it - it never changes during a run, so it belongs in a recording's header.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator

import numpy as np


@dataclass
class AgentView:
    ident: int
    founder: int
    x: int
    y: int
    energy: float
    integrity: float
    temperature: float
    age: int
    action: int
    in_band: bool
    #: (energy, integrity, temperature, age) as the controller actually received
    #: them this step. Differs from the physical values under any interoceptive
    #: ablation or false-body intervention, which is exactly what makes a
    #: sensed-versus-physical view possible. Recorded at the start of the step,
    #: before body physics ran, so it lags the physical fields in this same
    #: snapshot by one metabolic update - that is what the controller saw.
    sensed_intero: list[float] = field(default_factory=list)


@dataclass
class SimulationSnapshot:
    step: int
    population: int
    agents: list[AgentView]
    resources: list[tuple[int, int]]
    #: ("birth", ident) | ("death", ident) | ("consume", x, y) | ("shock", value)
    events: list[tuple] = field(default_factory=list)
    stats: dict[str, float] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "population": self.population,
            "agents": [asdict(a) for a in self.agents],
            "resources": self.resources,
            "events": [list(e) for e in self.events],
            "stats": self.stats,
        }

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "SimulationSnapshot":
        return cls(
            step=d["step"],
            population=d["population"],
            agents=[AgentView(**a) for a in d["agents"]],
            resources=[tuple(r) for r in d["resources"]],
            events=[tuple(e) for e in d["events"]],
            stats=d.get("stats", {}),
        )


#: Bumped when the frame or header layout changes incompatibly, so an old
#: recording is rejected with a clear message instead of rendering wrongly.
SCHEMA_VERSION = 2


@dataclass
class RecordingHeader:
    """Everything constant for a whole run, written once."""

    size: int
    ambient: list[list[float]]
    viable_temp_lo: float
    viable_temp_hi: float
    energy_max: float
    config: dict[str, Any]
    schema_version: int = SCHEMA_VERSION
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def ambient_array(self) -> np.ndarray:
        return np.array(self.ambient)


class Recorder:
    """Write a run to JSONL: one header line, then one line per snapshot."""

    def __init__(self, path: str | Path, header: RecordingHeader, every: int = 1):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.every = max(1, every)
        self._fh = self.path.open("w")
        self._fh.write(json.dumps({"header": asdict(header)}) + "\n")
        self.frames = 0

    def write(self, snap: SimulationSnapshot) -> None:
        if snap.step % self.every:
            return
        self._fh.write(json.dumps(snap.to_json()) + "\n")
        self.frames += 1

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "Recorder":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def load_recording(path: str | Path) -> tuple[RecordingHeader, list[SimulationSnapshot]]:
    lines = Path(path).read_text().splitlines()
    if not lines:
        raise ValueError(f"{path} is empty")
    head = json.loads(lines[0])["header"]
    got = head.get("schema_version", 0)
    if got != SCHEMA_VERSION:
        raise ValueError(
            f"{path} uses recording schema v{got}, this build reads v{SCHEMA_VERSION}. "
            f"Re-record it with scripts/visualize.py --record."
        )
    header = RecordingHeader(**head)
    frames = [SimulationSnapshot.from_json(json.loads(l)) for l in lines[1:] if l.strip()]
    return header, frames


def iter_recording(path: str | Path) -> Iterator[SimulationSnapshot]:
    """Stream frames without holding the whole run in memory."""
    with Path(path).open() as fh:
        head = json.loads(next(fh))["header"]
        got = head.get("schema_version", 0)
        if got != SCHEMA_VERSION:
            raise ValueError(
                f"{path} uses recording schema v{got}, this build reads v{SCHEMA_VERSION}."
            )
        for line in fh:
            if line.strip():
                yield SimulationSnapshot.from_json(json.loads(line))
