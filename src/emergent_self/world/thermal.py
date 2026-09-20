"""Static ambient temperature field and the resource density it induces.

The field is a sum of Gaussian hot and cold blobs on a torus, drawn once per
seed. Resource density is deliberately coupled to thermal hostility: the richest
cells sit where ambient temperature is furthest from the viable band. Without
this coupling the environment admits exactly one strategy ("eat as much as
possible"), which is failure mode 14.8 in the research program.
"""
from __future__ import annotations

import numpy as np

from emergent_self.config import WorldConfig


def _torus_sq_distance(size: int, cx: float, cy: float) -> np.ndarray:
    axis = np.arange(size)
    dx = np.minimum(np.abs(axis - cx), size - np.abs(axis - cx))
    dy = np.minimum(np.abs(axis - cy), size - np.abs(axis - cy))
    return dx[:, None] ** 2 + dy[None, :] ** 2


def build_ambient_field(cfg: WorldConfig, rng: np.random.Generator) -> np.ndarray:
    """Ambient temperature in [0, 1], shape (size, size), 0.5 = thermally neutral.

    Two balancing steps make seeds exchangeable replicates rather than worlds of
    wildly different difficulty:

    * blob polarities alternate instead of being drawn independently, so a seed
      cannot happen to place four hot blobs and one cold one;
    * the field is centred on its own *mean* before rescaling, not on the midpoint
      of its range.

    Without them, a seed's habitable fraction ranged from 0.18 to 0.71 and roughly
    a third of runs went extinct within 300 steps with founders starting at a body
    temperature of 0.8 - an uncontrolled nuisance factor that inflates
    between-seed variance and has nothing to do with any manipulated variable.
    """
    field = np.zeros((cfg.size, cfg.size))
    polarities = np.resize([1.0, -1.0], cfg.thermal_blobs)
    rng.shuffle(polarities)
    for polarity in polarities:
        cx, cy = rng.uniform(0, cfg.size, size=2)
        amplitude = rng.uniform(0.45, 0.95)
        d2 = _torus_sq_distance(cfg.size, cx, cy)
        field += polarity * amplitude * np.exp(-d2 / (2.0 * cfg.thermal_blob_sigma**2))
    field -= field.mean()
    span = np.abs(field).max()
    if span > 0:
        field = field / span * 0.5
    return np.clip(field + 0.5, 0.0, 1.0)


def build_resource_density(ambient: np.ndarray, cfg: WorldConfig) -> np.ndarray:
    """Normalized spawn probability per cell, rising with thermal hostility."""
    hostility = np.abs(ambient - 0.5) * 2.0
    density = 0.05 + hostility**cfg.hostility_coupling
    return density / density.sum()
