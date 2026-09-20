"""Outcomes computed from a Trajectory. Pure functions, no simulation.

Roadmap section 2 asks that homeostasis stop being one scalar. The measures here
keep the strategies apart: decoupling the body from the occupied cell, choosing
which cell to occupy, passive persistence from thermal inertia, and recovery
after a perturbation.

Roadmap section 1 asks for the piece that was missing: whether an induced choice
*improves or worsens subsequent viability*. `viability_outcome` answers that,
and it is the measure that turns "the intervention changed behaviour" into "the
intervention changed behaviour in a direction that mattered".
"""
from __future__ import annotations

import math

import numpy as np

from emergent_self.agents.body import in_viable_band
from emergent_self.assays.runner import Trajectory

NAN = float("nan")


def _band(values, body_cfg) -> np.ndarray:
    return np.array([in_viable_band(float(v), body_cfg) for v in values], dtype=float)


def homeostasis(traj: Trajectory, body_cfg) -> dict[str, float]:
    """The decomposition, computed per trajectory rather than per population.

        thermal_decoupling = P(body in band)     - P(ambient occupied in band)
        microenvironment   = P(ambient occupied) - P(field in band)
        ------------------------------------------------------------------
        homeostatic_advantage = P(body in band)  - P(field in band)
    """
    if not len(traj):
        return {k: NAN for k in ("body_in_band", "occupied_in_band", "thermal_decoupling",
                                 "microenvironment", "homeostatic_advantage",
                                 "vs_passive", "mean_excursion")}
    body = _band(traj.column("temperature"), body_cfg).mean()
    occ = _band(traj.column("ambient"), body_cfg).mean()
    shadow = _band(traj.column("shadow_temperature"), body_cfg).mean()
    field = traj.field_band_fraction
    lo, hi = body_cfg.viable_temp_lo, body_cfg.viable_temp_hi
    exc = np.maximum(0.0, lo - traj.column("temperature")) + \
          np.maximum(0.0, traj.column("temperature") - hi)
    return {
        "body_in_band": float(body),
        "occupied_in_band": float(occ),
        "thermal_decoupling": float(body - occ),
        "microenvironment": float(occ - field),
        "homeostatic_advantage": float(body - field),
        # Against a same-path body that generated no metabolic heat: isolates
        # the contribution of modulating *when* to move.
        "vs_passive": float(body - shadow),
        "mean_excursion": float(exc.mean()),
    }


def behaviour(traj: Trajectory) -> dict[str, float]:
    if not len(traj):
        return {k: NAN for k in ("move_fraction", "policy_entropy", "resources_eaten")}
    probs = traj.probs()
    ent = -(probs * np.log(probs + 1e-12)).sum(axis=1)
    actions = traj.column("action")
    energy = traj.column("energy")
    # An energy rise larger than any metabolic cost can only be ingestion.
    eaten = int((np.diff(energy) > 0.5).sum()) if len(energy) > 1 else 0
    return {
        "move_fraction": float((actions != 0).mean()),
        "policy_entropy": float(ent.mean()),
        "resources_eaten": float(eaten),
    }


def survival(traj: Trajectory, horizon: int) -> dict[str, float]:
    return {
        "steps_survived": float(len(traj)),
        "died": float(traj.died_at is not None),
        "survival_fraction": float(len(traj) / horizon) if horizon else NAN,
        "final_integrity": float(traj.column("integrity")[-1]) if len(traj) else NAN,
        "final_energy": float(traj.column("energy")[-1]) if len(traj) else NAN,
    }


def recovery_time(traj: Trajectory, body_cfg, shock_step: int,
                  window: int = 24, tolerance: float = 0.9) -> float:
    """Steps after `shock_step` until band occupancy over a trailing window
    returns to `tolerance` of its pre-shock level. NaN if it never does.

    Measured per organism in a standardised world, which is what makes it a
    property of the controller rather than of a population's turnover.
    """
    if len(traj) <= shock_step + 1:
        return NAN
    hits = _band(traj.column("temperature"), body_cfg)
    pre = hits[max(0, shock_step - window):shock_step]
    if pre.size == 0:
        return NAN
    target = float(pre.mean()) * tolerance
    for t in range(shock_step + 1, len(hits)):
        trailing = hits[max(shock_step, t - window):t + 1]
        if trailing.mean() >= target:
            return float(t - shock_step)
    return NAN


def time_to_band(traj: Trajectory, body_cfg, from_step: int = 0) -> float:
    """Steps until the body first re-enters the viable band after `from_step`.

    `recovery_time` needs a pre-shock baseline to recover *to*, so it is
    undefined when the perturbation is applied at step 0 — which is exactly what
    an assay that starts the organism out of band does. Here the target is
    absolute: the band itself. NaN means it never got back inside.
    """
    hits = [s for s in traj.steps if s["step"] >= from_step]
    for s in hits:
        if in_viable_band(float(s["temperature"]), body_cfg):
            return float(s["step"] - from_step)
    return NAN


def viability_outcome(traj: Trajectory, body_cfg, from_step: int) -> dict[str, float]:
    """Did what happened after `from_step` leave the organism better or worse off?

    The missing half of a causal-use claim. Showing that an intervention changes
    the action distribution says the channel is *read*. It does not say the
    reading is *useful*. These are the consequences over the remainder of the
    rollout: time in band, integrity retained, energy retained, survival.
    """
    tail = [s for s in traj.steps if s["step"] >= from_step]
    if not tail:
        return {k: NAN for k in ("post_in_band", "post_integrity_change",
                                 "post_energy_change", "post_steps", "post_died")}
    temps = np.array([s["temperature"] for s in tail])
    integ = np.array([s["integrity"] for s in tail])
    energy = np.array([s["energy"] for s in tail])
    return {
        "post_in_band": float(_band(temps, body_cfg).mean()),
        "post_integrity_change": float(integ[-1] - integ[0]),
        "post_energy_change": float(energy[-1] - energy[0]),
        "post_steps": float(len(tail)),
        "post_died": float(traj.died_at is not None),
    }


def policy_divergence(a: Trajectory, b: Trajectory) -> dict[str, float]:
    """How far two arms' action distributions diverge, step by step.

    `tv_first` is the divergence on the very first step, where the two arms still
    share everything except the declared manipulation. Later steps mix in the
    consequences of having acted differently, which is a different quantity and
    is reported as `tv_mean`.
    """
    n = min(len(a), len(b))
    if n == 0:
        return {"tv_mean": NAN, "tv_first": NAN, "tv_max": NAN, "n_compared": 0.0,
                "position_divergence": NAN}
    pa, pb = a.probs()[:n], b.probs()[:n]
    tv = 0.5 * np.abs(pa - pb).sum(axis=1)
    dx = np.abs(a.column("x")[:n] - b.column("x")[:n])
    dy = np.abs(a.column("y")[:n] - b.column("y")[:n])
    return {
        "tv_mean": float(tv.mean()),
        "tv_first": float(tv[0]),
        "tv_max": float(tv.max()),
        "n_compared": float(n),
        "position_divergence": float((dx + dy).mean()),
    }


def summarise(traj: Trajectory, body_cfg, horizon: int) -> dict[str, float]:
    return {**homeostasis(traj, body_cfg), **behaviour(traj), **survival(traj, horizon)}
