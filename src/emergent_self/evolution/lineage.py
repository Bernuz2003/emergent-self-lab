"""Lineage bookkeeping.

Measurement only. Nothing recorded here is visible to any controller and no
quantity here is used to decide who reproduces; reproduction is decided locally
by physics (see evolution/reproduction.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class LifeRecord:
    ident: int
    founder: int
    parent: int | None
    birth_step: int
    death_step: int | None = None
    offspring: int = 0
    steps_in_band: int = 0
    steps_ambient_in_band: int = 0
    steps_shadow_in_band: int = 0
    steps_alive: int = 0
    energy_intake: float = 0.0

    @property
    def lifespan(self) -> int:
        return self.steps_alive

    @property
    def band_occupancy(self) -> float:
        return self.steps_in_band / self.steps_alive if self.steps_alive else 0.0

    @property
    def ambient_band_occupancy(self) -> float:
        """Fraction of this organism's steps spent on cells whose *ambient*
        temperature is itself inside the viable band. This is the passive
        baseline the organism's own regulation has to beat."""
        return self.steps_ambient_in_band / self.steps_alive if self.steps_alive else 0.0

    @property
    def thermoregulation_index(self) -> float:
        """Body-in-band minus environment-in-band over the same steps.

        Zero means the body simply tracks wherever it happens to be. Positive
        means the organism holds its body inside the band more often than its
        occupied environment would passively produce."""
        return self.band_occupancy - self.ambient_band_occupancy


@dataclass
class LineageLog:
    records: dict[int, LifeRecord] = field(default_factory=dict)

    def birth(self, ident, founder, parent, step) -> LifeRecord:
        rec = LifeRecord(ident=ident, founder=founder, parent=parent, birth_step=step)
        self.records[ident] = rec
        if parent is not None and parent in self.records:
            self.records[parent].offspring += 1
        return rec

    def death(self, ident: int, step: int) -> None:
        if ident in self.records:
            self.records[ident].death_step = step

    def living_founders(self, living_idents) -> set[int]:
        return {self.records[i].founder for i in living_idents if i in self.records}

    def lineage_entropy(self, living_idents) -> float:
        """Shannon entropy (nats) of founder shares among the living population."""
        founders = [self.records[i].founder for i in living_idents if i in self.records]
        if not founders:
            return 0.0
        _, counts = np.unique(founders, return_counts=True)
        p = counts / counts.sum()
        return float(-(p * np.log(p)).sum())
