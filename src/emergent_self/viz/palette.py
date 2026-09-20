"""Colour maps, implemented directly so the visualiser needs no plotting library.

The thermal map is diverging around the viable band because that is the
scientifically meaningful midpoint here, not because it looks pleasant: cold and
hot excursions are different failures and should not share a hue. Viability maps
are sequential. Lineage colours are categorical and deliberately unordered.
"""
from __future__ import annotations

import numpy as np

Color = tuple[int, int, int]


def _lerp(a: Color, b: Color, t: float) -> Color:
    t = min(1.0, max(0.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))  # type: ignore


def _ramp(stops: list[tuple[float, Color]], t: float) -> Color:
    t = min(1.0, max(0.0, t))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            span = p1 - p0
            return _lerp(c0, c1, (t - p0) / span if span else 0.0)
    return stops[-1][1]


_THERMAL = [
    (0.00, (24, 52, 112)),    # deep cold
    (0.30, (62, 124, 176)),
    (0.45, (120, 168, 176)),
    (0.50, (142, 150, 132)),  # neutral
    (0.55, (184, 158, 108)),
    (0.70, (196, 112, 64)),
    (1.00, (140, 34, 30)),    # deep heat
]

_VIABILITY = [
    (0.00, (92, 26, 34)),
    (0.35, (168, 78, 48)),
    (0.70, (206, 168, 82)),
    (1.00, (128, 188, 132)),
]

#: Categorical, for lineage identity. Unordered on purpose: a lineage id carries
#: no magnitude and a sequential ramp would invent one.
LINEAGE_COLORS: list[Color] = [
    (214, 96, 77), (69, 117, 180), (145, 191, 106), (223, 165, 58),
    (152, 110, 178), (86, 180, 172), (222, 128, 170), (140, 148, 158),
    (176, 94, 60), (104, 152, 200), (190, 186, 92), (120, 170, 140),
]


def thermal(value: float) -> Color:
    return _ramp(_THERMAL, value)


def viability(value: float) -> Color:
    return _ramp(_VIABILITY, value)


def lineage(founder: int) -> Color:
    return LINEAGE_COLORS[founder % len(LINEAGE_COLORS)]


def ambient_surface_array(ambient: np.ndarray, dim: float = 0.55) -> np.ndarray:
    """(size, size, 3) uint8 array of the thermal field, dimmed to sit behind
    the agents rather than compete with them."""
    size = ambient.shape[0]
    out = np.zeros((size, size, 3), dtype=np.uint8)
    for x in range(size):
        for y in range(size):
            r, g, b = thermal(float(ambient[x, y]))
            out[x, y] = (int(r * dim), int(g * dim), int(b * dim))
    return out
