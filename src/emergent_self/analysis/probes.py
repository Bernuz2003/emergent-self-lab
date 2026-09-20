"""Post-hoc representation probes and causal latent interventions.

The distinction this module exists to keep sharp (research program, section 8):
a probe that decodes energy from a controller's hidden state shows the
information is *present*. It does not show the controller *uses* it. Only an
intervention that changes the latent and changes behaviour supports the stronger
claim, and even that is a claim about causal role, not about experience.

Every function here runs after evolution, on a frozen population, and never
feeds anything back into a scored run.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from emergent_self.agents.sensors import interoceptive_vector
from emergent_self.config import ReproductionConfig, RunConfig
from emergent_self.sim import Simulation
from emergent_self.world.grid import ACTIONS

#: Reproduction is made physically impossible so the probed population really is
#: frozen: no births, no mutation, no turnover while it is being measured.
_FROZEN_REPRODUCTION = ReproductionConfig(energy_threshold=float("inf"), population_cap=0)

BODY_TARGETS = ("energy", "integrity", "temperature", "age")
WORLD_TARGETS = ("ambient", "resource_here")


@dataclass
class ProbeResult:
    """Two R^2 values, because the gap between them is the actual result.

    `r2_pooled` holds out random observations. Consecutive samples of one
    organism are strongly autocorrelated and a whole lineage shares a controller
    up to mutation, so this number is inflated by leakage and mostly reports
    "the latent identifies which organism this is".

    `r2_grouped` holds out whole lineages. It asks the question a representation
    claim needs answered: is there a lineage-general code for this variable, one
    that a decoder fit on some organisms reads correctly in others?

    A large pooled R^2 next to a negative grouped R^2 means the latent carries
    lineage identity, not a shared encoding of the variable.
    """

    target: str
    r2_grouped: float
    r2_pooled: float
    r2_shuffled: float          # grouped fit on permuted labels: the chance level
    n_samples: int
    n_groups: int
    latent_dim: int

    @property
    def above_chance(self) -> float:
        return self.r2_grouped - self.r2_shuffled

    def __str__(self) -> str:
        return (f"{self.target:<14} grouped={self.r2_grouped:+.3f}  "
                f"pooled={self.r2_pooled:+.3f}  chance={self.r2_shuffled:+.3f}")


def collect_latents(sim: Simulation, steps: int, sample_every: int = 5):
    """Roll a genuinely frozen population forward, recording samples.

    Reproduction and mutation are disabled on the passed simulation before the
    first step. An earlier version documented itself as frozen while still
    calling `sim.step()` with reproduction live, so the population under the
    probe kept mutating and turning over while it was being measured.

    Returns (latents, bodies, worlds, groups), where `groups` is each sample's
    founder id. Splitting on it is what keeps consecutive samples of the same
    organism out of both halves of a probe fit.
    """
    sim.cfg = replace(sim.cfg, reproduction=_FROZEN_REPRODUCTION)

    latents, bodies, worlds, groups = [], [], [], []
    for _ in range(steps):
        if sim.step_index % sample_every == 0:
            for a in sim.agents:
                z = a.controller.latent()
                if z.size == 0:
                    continue
                latents.append(z)
                bodies.append(interoceptive_vector(a.body, sim.cfg.body))
                worlds.append([sim.world.ambient_at(a.x, a.y),
                               float(sim.world.resources[a.x, a.y])])
                groups.append(a.founder)
        sim.step()
        if not sim.agents:
            break
    if not latents:
        return np.zeros((0, 0)), np.zeros((0, 4)), np.zeros((0, 2)), np.zeros(0, dtype=int)
    return np.array(latents), np.array(bodies), np.array(worlds), np.array(groups)


def _group_split(groups: np.ndarray, rng) -> tuple[np.ndarray, np.ndarray]:
    """Split indices so that no group appears in both halves.

    Grouping is by founder. Samples from one organism at consecutive steps are
    strongly autocorrelated, and an entire lineage shares a controller up to
    mutation, so a split taken uniformly over observations leaks the test set
    into the training set and inflates every R^2.
    """
    uniq = np.unique(groups)
    rng.shuffle(uniq)
    cut = max(1, len(uniq) // 2)
    train_groups = set(uniq[:cut].tolist())
    mask = np.array([g in train_groups for g in groups])
    return np.where(mask)[0], np.where(~mask)[0]


ALPHAS = (1e-2, 1e-1, 1.0, 10.0, 100.0, 1000.0)


def _fit_predict(x_tr, y_tr, x_te, alpha: float) -> np.ndarray:
    """Ridge with an intercept, on features standardised by the training half.

    Standardising on the training half only, and choosing alpha by an inner
    split of that half, keeps every decision about the fit out of the test data.
    Without standardisation the penalty falls unevenly across latent units and
    the fit extrapolates wildly onto held-out lineages.
    """
    mu, sd = x_tr.mean(axis=0), x_tr.std(axis=0)
    sd[sd < 1e-9] = 1.0
    a_tr, a_te = (x_tr - mu) / sd, (x_te - mu) / sd
    ym = y_tr.mean()
    g = a_tr.T @ a_tr + alpha * np.eye(a_tr.shape[1])
    w = np.linalg.solve(g, a_tr.T @ (y_tr - ym))
    return a_te @ w + ym


def _ridge_r2(x: np.ndarray, y: np.ndarray, *, groups=None, rng, repeats: int = 8) -> float:
    """Held-out R^2, averaged over several group-disjoint splits.

    A single split over a handful of lineages is extremely high variance, so the
    score is averaged over `repeats` independent splits. The ridge penalty is
    selected inside the training half, never on the held-out half.
    """
    n = len(x)
    if n < 20:
        return float("nan")
    scores = []
    for _ in range(repeats):
        if groups is not None and len(np.unique(groups)) >= 4:
            tr, te = _group_split(groups, rng)
        elif groups is not None and len(np.unique(groups)) >= 2:
            tr, te = _group_split(groups, rng)
        else:
            order = rng.permutation(n)
            tr, te = order[: n // 2], order[n // 2:]
        if len(tr) < 20 or len(te) < 20:
            continue

        # Inner split of the training half to pick alpha.
        inner = rng.permutation(len(tr))
        cut = max(10, len(tr) // 2)
        i_tr, i_te = tr[inner[:cut]], tr[inner[cut:]]
        best_alpha, best_err = ALPHAS[-1], None
        if len(i_te) >= 10:
            for alpha in ALPHAS:
                err = float(((y[i_te] - _fit_predict(x[i_tr], y[i_tr], x[i_te], alpha)) ** 2).mean())
                if best_err is None or err < best_err:
                    best_alpha, best_err = alpha, err

        pred = _fit_predict(x[tr], y[tr], x[te], best_alpha)
        ss_res = float(((y[te] - pred) ** 2).sum())
        ss_tot = float(((y[te] - y[te].mean()) ** 2).sum())
        if ss_tot > 0:
            scores.append(1.0 - ss_res / ss_tot)
    return float(np.mean(scores)) if scores else float("nan")


def probe(latents: np.ndarray, targets: np.ndarray, names, groups=None, seed: int = 0) -> list[ProbeResult]:
    """Linear-decode each target from the latent state, against a permuted control.

    The permuted fit is not decoration. With a wide latent and few samples a
    ridge fit recovers noise, and the shuffled R^2 is what tells you how much.
    """
    rng = np.random.default_rng(seed)
    n_groups = int(len(np.unique(groups))) if groups is not None else 0
    out = []
    for i, name in enumerate(names):
        y = targets[:, i]
        grouped = _ridge_r2(latents, y, groups=groups, rng=np.random.default_rng(seed))
        pooled = _ridge_r2(latents, y, groups=None, rng=np.random.default_rng(seed))
        # Permuting within the same grouped split is the chance level for it.
        chance = _ridge_r2(latents, rng.permutation(y), groups=groups,
                           rng=np.random.default_rng(seed))
        out.append(ProbeResult(name, grouped, pooled, chance, len(latents), n_groups,
                               latents.shape[1] if latents.ndim > 1 else 0))
    return out


def intervention_with_null(sim: Simulation, direction: np.ndarray, magnitude: float,
                           trials: int = 400, n_null: int = 12, seed: int = 0) -> dict[str, float]:
    """`latent_intervention` against norm-matched random directions.

    A bare total variation is not interpretable. Any sufficiently large push to a
    hidden state moves a softmax policy somewhat, so TV = 0.29 along a decoded
    direction says nothing until it is compared with TV along random directions
    of the same norm. This matters especially here, where the grouped probe shows
    the decoded "energy direction" does not generalise across lineages and so may
    not be a shared axis for anything.

    Reports the decoded direction's TV, the null distribution's mean and spread,
    and the z-score of the former against the latter.
    """
    rng = np.random.default_rng(seed)
    real = latent_intervention(sim, direction, magnitude, trials=trials, seed=seed)
    d = len(direction)
    nulls = []
    for i in range(n_null):
        r = rng.normal(size=d)
        nulls.append(latent_intervention(sim, r, magnitude, trials=trials, seed=seed)["total_variation"])
    nulls = np.array([x for x in nulls if np.isfinite(x)])
    if nulls.size == 0:
        return {**real, "tv_null_mean": float("nan"), "tv_null_sd": float("nan"),
                "z_vs_null": float("nan"), "n_null": 0.0}
    sd = float(nulls.std(ddof=1)) if nulls.size > 1 else 0.0
    return {
        **real,
        "tv_null_mean": float(nulls.mean()),
        "tv_null_sd": sd,
        "z_vs_null": (real["total_variation"] - float(nulls.mean())) / sd if sd > 1e-9 else float("nan"),
        "n_null": float(nulls.size),
    }


def latent_intervention(sim: Simulation, direction: np.ndarray, magnitude: float,
                        trials: int = 400, seed: int = 0) -> dict[str, float]:
    """Push the hidden state along `direction` and measure the behavioural change.

    Returns the total-variation distance between the action distribution with and
    without the push, plus the change in the fraction of steps spent moving. A
    decodable latent that moves behaviour when perturbed is causally involved; a
    decodable latent that does nothing when perturbed is not.
    """
    rng = np.random.default_rng(seed)
    unit = direction / (np.linalg.norm(direction) or 1.0)
    tvs, move_deltas = [], []
    donors = sim._build_donor_map()

    for _ in range(trials):
        if not sim.agents:
            break
        a = sim.agents[int(rng.integers(len(sim.agents)))]
        obs = sim._observe(a, donors)

        # Run the encoder once to get this observation's hidden state, then read
        # out both distributions from that state. Comparing distributions rather
        # than sampled actions is the whole point: at a softmax temperature of
        # 0.35, two identical distributions disagree on most single draws.
        base = a.controller.action_probs(obs)
        h = a.controller.latent().copy()
        pushed = a.controller.probs_from_latent(h + magnitude * unit)
        a.controller._h = h

        tvs.append(0.5 * float(np.abs(base - pushed).sum()))
        move_deltas.append(float((1.0 - pushed[0]) - (1.0 - base[0])))

    if not tvs:
        return {"total_variation": float("nan"), "delta_move_fraction": float("nan"),
                "trials": 0.0}
    return {
        "total_variation": float(np.mean(tvs)),
        "total_variation_sd": float(np.std(tvs)),
        "delta_move_fraction": float(np.mean(move_deltas)),
        "trials": float(len(tvs)),
    }


def run_probe_suite(cfg: RunConfig, evolve_steps: int, probe_steps: int = 600) -> dict:
    """Evolve, freeze, then probe body and world variables from the latent state."""
    sim = Simulation(cfg)
    for _ in range(evolve_steps):
        sim.step()
        if not sim.agents:
            return {"error": "population went extinct before probing"}

    latents, bodies, worlds, groups = collect_latents(sim, probe_steps)
    if latents.size == 0:
        return {"error": "controller exposes no latent state (is it the random controller?)"}
    if len(np.unique(groups)) < 2:
        return {"error": f"only {len(np.unique(groups))} lineage(s) survived; a "
                         f"group-split probe needs at least two"}

    body_probes = probe(latents, bodies, BODY_TARGETS, groups=groups)
    world_probes = probe(latents, worlds, WORLD_TARGETS, groups=groups)

    # Intervene along the direction the energy probe found, if it found anything.
    rng = np.random.default_rng(0)
    mu, sd = latents.mean(axis=0), latents.std(axis=0)
    sd[sd < 1e-9] = 1.0
    z = (latents - mu) / sd
    w = np.linalg.solve(z.T @ z + 1.0 * np.eye(z.shape[1]), z.T @ (bodies[:, 0] - bodies[:, 0].mean()))
    effect = intervention_with_null(sim, w / sd, magnitude=2.0)

    return {
        "body": {p.target: p.__dict__ for p in body_probes},
        "world": {p.target: p.__dict__ for p in world_probes},
        "energy_direction_intervention": effect,
        "n_samples": int(len(latents)),
        "n_lineages": int(len(np.unique(groups))),
        "note": ("Decodability shows information is present; the intervention says "
                 "whether it is used. R^2 is held out across lineages, not "
                 "observations, and the intervention is scored against "
                 "norm-matched random directions."),
    }
