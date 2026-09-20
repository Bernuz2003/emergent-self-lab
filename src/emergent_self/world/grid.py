"""World state and transition laws.

Owns the torus grid, the ambient thermal field, and the resource process. Knows
nothing about controllers, observations, selection or metrics.
"""
from __future__ import annotations

import numpy as np

from emergent_self.config import WorldConfig
from emergent_self.world.thermal import build_ambient_field, build_resource_density

# stay, north, east, south, west
ACTIONS: tuple[tuple[int, int], ...] = ((0, 0), (0, -1), (1, 0), (0, 1), (-1, 0))


class GridWorld:
    def __init__(self, cfg: WorldConfig, init_rng: np.random.Generator,
                 dynamics_rng: np.random.Generator):
        """`init_rng` draws the field and the starting resources; `dynamics_rng`
        drives respawn during the run. Keeping them apart means a run's resource
        history cannot be shifted by anything that happens earlier in setup."""
        self.cfg = cfg
        self.rng = init_rng
        self.size = cfg.size
        self.ambient = build_ambient_field(cfg, init_rng)
        self.density = build_resource_density(self.ambient, cfg)
        self.resources = np.zeros((self.size, self.size), dtype=bool)
        self._flat_index = np.arange(self.size * self.size)
        self._flat_density = self.density.ravel()
        for _ in range(cfg.max_resources):
            self.spawn_resource()
        # Everything from here on uses the dynamics stream.
        self.rng = dynamics_rng

    def spawn_resource(self) -> bool:
        if self.resources.sum() >= self.cfg.max_resources:
            return False
        flat = int(self.rng.choice(self._flat_index, p=self._flat_density))
        x, y = divmod(flat, self.size)
        if self.resources[x, y]:
            return False
        self.resources[x, y] = True
        return True

    def respawn(self) -> None:
        """Stochastic regrowth; the fractional part of the rate is a Bernoulli draw."""
        rate = self.cfg.respawn_per_step
        n = int(rate) + int(self.rng.random() < (rate - int(rate)))
        for _ in range(n):
            self.spawn_resource()

    def consume(self, x: int, y: int) -> bool:
        if self.resources[x, y]:
            self.resources[x, y] = False
            return True
        return False

    def wrap(self, x: int, y: int) -> tuple[int, int]:
        return x % self.size, y % self.size

    def _patch(self, field: np.ndarray, x: int, y: int, radius: int) -> np.ndarray:
        idx = np.arange(-radius, radius + 1)
        rows = (x + idx) % self.size
        cols = (y + idx) % self.size
        return field[np.ix_(rows, cols)]

    def resource_patch(self, x: int, y: int, radius: int) -> np.ndarray:
        return self._patch(self.resources.astype(float), x, y, radius)

    def ambient_patch(self, x: int, y: int, radius: int) -> np.ndarray:
        return self._patch(self.ambient, x, y, radius)

    def ambient_at(self, x: int, y: int) -> float:
        return float(self.ambient[x, y])
