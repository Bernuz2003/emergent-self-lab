"""Across-seed statistics.

Reports distributions, effect sizes and uncertainty rather than a single p-value
or a best run (docs/METHODOLOGY.md, "Statistics").

Two rules this module enforces:

* **NaN is dropped, never coerced.** A run whose late window contained no
  organism has no value for the endpoint. Every function reports how many seeds
  actually contributed, so a contrast computed from four usable seeds cannot be
  mistaken for one computed from twelve.

* **Contrasts are paired by seed where possible.** A seed fixes the ambient
  field, the resource layout and the founding positions, so conditions sharing a
  seed face the same world. Pairing removes between-world variance, which is the
  largest source of noise in these runs.
"""
from __future__ import annotations

import numpy as np


def _finite(values) -> np.ndarray:
    v = np.asarray(list(values), dtype=float)
    return v[np.isfinite(v)]


def bootstrap_ci(values, n_boot: int = 10_000, alpha: float = 0.05, seed: int = 0):
    v = _finite(values)
    if v.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    draws = rng.choice(v, size=(n_boot, v.size), replace=True).mean(axis=1)
    return float(v.mean()), float(np.quantile(draws, alpha / 2)), float(np.quantile(draws, 1 - alpha / 2))


def hedges_g(a, b) -> float:
    """Bias-corrected standardised mean difference (a - b)."""
    a, b = _finite(a), _finite(b)
    na, nb = a.size, b.size
    if na < 2 or nb < 2:
        return float("nan")
    pooled = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    if pooled == 0:
        return 0.0
    d = (a.mean() - b.mean()) / pooled
    return float(d * (1 - 3 / (4 * (na + nb) - 9)))


def cliffs_delta(a, b) -> float:
    """Non-parametric dominance of a over b, in [-1, 1]."""
    a, b = _finite(a), _finite(b)
    if a.size == 0 or b.size == 0:
        return float("nan")
    return float(np.sign(a[:, None] - b[None, :]).mean())


def diff_bootstrap_ci(a, b, n_boot: int = 10_000, alpha: float = 0.05, seed: int = 0):
    """CI on the difference of means, resampling each group independently."""
    a, b = _finite(a), _finite(b)
    if a.size == 0 or b.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    da = rng.choice(a, size=(n_boot, a.size), replace=True).mean(axis=1)
    db = rng.choice(b, size=(n_boot, b.size), replace=True).mean(axis=1)
    d = da - db
    return float(a.mean() - b.mean()), float(np.quantile(d, alpha / 2)), float(np.quantile(d, 1 - alpha / 2))


def paired_differences(a_by_seed: dict[int, float], b_by_seed: dict[int, float]) -> dict[int, float]:
    """Per-seed a - b, keeping only seeds where both conditions produced a value."""
    return {
        s: a_by_seed[s] - b_by_seed[s]
        for s in sorted(set(a_by_seed) & set(b_by_seed))
        if np.isfinite(a_by_seed[s]) and np.isfinite(b_by_seed[s])
    }


def paired_compare(a_by_seed: dict[int, float], b_by_seed: dict[int, float],
                   n_boot: int = 10_000, alpha: float = 0.05, seed: int = 0) -> dict[str, float]:
    """Seed-paired contrast: bootstrap the mean of the within-seed differences.

    `n_pairs` is the number of seeds that actually contributed. It is reported
    alongside every result because an endpoint that is NaN in one arm silently
    drops that seed from the comparison.
    """
    diffs = paired_differences(a_by_seed, b_by_seed)
    n = len(diffs)
    out = {
        "n_pairs": float(n),
        "n_a_usable": float(sum(np.isfinite(v) for v in a_by_seed.values())),
        "n_b_usable": float(sum(np.isfinite(v) for v in b_by_seed.values())),
    }
    if n == 0:
        return {**out, "mean_diff": float("nan"), "ci_lo": float("nan"),
                "ci_hi": float("nan"), "dz": float("nan"), "sign_wins": float("nan")}
    d = np.array(list(diffs.values()))
    rng = np.random.default_rng(seed)
    draws = rng.choice(d, size=(n_boot, n), replace=True).mean(axis=1)
    sd = d.std(ddof=1) if n > 1 else 0.0
    return {
        **out,
        "mean_diff": float(d.mean()),
        "ci_lo": float(np.quantile(draws, alpha / 2)),
        "ci_hi": float(np.quantile(draws, 1 - alpha / 2)),
        "dz": float(d.mean() / sd) if sd > 0 else float("nan"),  # paired Cohen's dz
        "sign_wins": float((d > 0).sum()),
    }


def interaction_contrast(cells: dict[str, dict[int, float]], a_plus: str, a_minus: str,
                         b_plus: str, b_minus: str, n_boot: int = 10_000,
                         alpha: float = 0.05, seed: int = 0) -> dict[str, float]:
    """Seed-paired double difference (a_plus - a_minus) - (b_plus - b_minus).

    For the E1 design this asks whether interoception buys more when the ambient
    channel is unavailable than when it is available - the interaction, which is
    the form H2 has to take once the main effect is known to be absent.
    """
    seeds = set.intersection(*(set(cells[k]) for k in (a_plus, a_minus, b_plus, b_minus)))
    d = np.array([
        (cells[a_plus][s] - cells[a_minus][s]) - (cells[b_plus][s] - cells[b_minus][s])
        for s in sorted(seeds)
        if all(np.isfinite(cells[k][s]) for k in (a_plus, a_minus, b_plus, b_minus))
    ])
    if d.size == 0:
        return {"n_pairs": 0.0, "interaction": float("nan"),
                "ci_lo": float("nan"), "ci_hi": float("nan"), "dz": float("nan")}
    rng = np.random.default_rng(seed)
    draws = rng.choice(d, size=(n_boot, d.size), replace=True).mean(axis=1)
    sd = d.std(ddof=1) if d.size > 1 else 0.0
    return {
        "n_pairs": float(d.size),
        "interaction": float(d.mean()),
        "ci_lo": float(np.quantile(draws, alpha / 2)),
        "ci_hi": float(np.quantile(draws, 1 - alpha / 2)),
        "dz": float(d.mean() / sd) if sd > 0 else float("nan"),
    }


def compare(a, b, seed: int = 0) -> dict[str, float]:
    """Unpaired contrast. Prefer `paired_compare` when seeds are matched."""
    mean, lo, hi = diff_bootstrap_ci(a, b, seed=seed)
    fa, fb = _finite(a), _finite(b)
    return {
        "n_a": len(fa), "n_b": len(fb),
        "n_a_dropped": len(list(a)) - len(fa), "n_b_dropped": len(list(b)) - len(fb),
        "mean_a": float(fa.mean()) if fa.size else float("nan"),
        "mean_b": float(fb.mean()) if fb.size else float("nan"),
        "diff": mean, "diff_ci_lo": lo, "diff_ci_hi": hi,
        "hedges_g": hedges_g(a, b), "cliffs_delta": cliffs_delta(a, b),
    }
