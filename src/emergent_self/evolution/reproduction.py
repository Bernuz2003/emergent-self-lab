"""Ecological reproduction.

No global fitness function, no ranking, no top-k selection. An organism
reproduces when local physical conditions permit: enough stored energy, enough
structural integrity to gestate, maturity, a refractory period since the last
birth, and room in the immediate neighbourhood. Differential reproduction is
therefore a consequence of how organisms interact with the environment, not of
a score computed by the researcher.

Lineage success is measured afterwards and is never available to any agent.
"""
from __future__ import annotations

import numpy as np

from emergent_self.config import ReproductionConfig


def local_density(x: int, y: int, occupancy: np.ndarray, radius: int) -> int:
    size = occupancy.shape[0]
    idx = np.arange(-radius, radius + 1)
    rows = (x + idx) % size
    cols = (y + idx) % size
    return int(occupancy[np.ix_(rows, cols)].sum())


def may_reproduce(
    *, body, steps_since_birth: int, x: int, y: int, occupancy: np.ndarray,
    population: int, maturity_age: int, cfg: ReproductionConfig,
) -> bool:
    if population >= cfg.population_cap:
        return False
    if body.energy < cfg.energy_threshold:
        return False
    if body.integrity < cfg.integrity_threshold:
        return False
    if body.age < maturity_age or steps_since_birth < cfg.refractory_steps:
        return False
    return local_density(x, y, occupancy, cfg.local_density_radius) <= cfg.local_density_max


def free_adjacent_cell(x, y, occupancy, rng) -> tuple[int, int]:
    """Place the child next to the parent, preferring an unoccupied cell."""
    size = occupancy.shape[0]
    offsets = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    rng.shuffle(offsets)
    for dx, dy in offsets:
        cx, cy = (x + dx) % size, (y + dy) % size
        if not occupancy[cx, cy]:
            return cx, cy
    return x, y
