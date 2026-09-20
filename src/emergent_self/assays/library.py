"""Standard assays, expressed as specs.

Each is a pair of AssaySpecs differing in exactly one declared field, plus the
measures that answer the question. Writing them this way is the point of the
framework: the manipulation is a value, not a bespoke loop, so `differs_from`
can check that nothing else moved.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from emergent_self.assays import measures as M
from emergent_self.assays.runner import Trajectory, run_paired, run_spec_all_worlds
from emergent_self.assays.spec import (
    AssaySpec,
    FalsifySensor,
    InitialState,
    Intervention,
    RemapActuator,
    ResetMemory,
    SetBody,
)
from emergent_self.config import RunConfig

NAN = float("nan")


@dataclass
class PairedResult:
    name: str
    question: str
    differs_in: list[str]
    n_worlds: int
    metrics: dict[str, float]

    def __str__(self) -> str:
        rows = "\n".join(f"    {k:<28}{v:>10.4f}" for k, v in self.metrics.items()
                         if isinstance(v, float) and math.isfinite(v))
        return (f"{self.name} ({self.n_worlds} worlds, differs in "
                f"{self.differs_in or ['nothing']})\n  {self.question}\n{rows}")


def _finite_mean(values):
    v = [x for x in values if x is not None and math.isfinite(x)]
    return float(np.mean(v)) if v else NAN


def _mean(rows, key):
    vals = [r[key] for r in rows if key in r and math.isfinite(r[key])]
    return float(np.mean(vals)) if vals else NAN


# ---------------------------------------------------------------------------
# 1. Body contingency: same world, different body
# ---------------------------------------------------------------------------

def body_contingency_specs(cold: float = 0.25, hot: float = 0.75,
                           horizon: int = 1, warmup: int = 12,
                           world_seeds=(1000, 1001, 1002, 1003)) -> tuple[AssaySpec, AssaySpec]:
    """Hold everything fixed, vary only physical body temperature.

    `horizon=1` by default on purpose. At one step the two arms are identical in
    every respect except the manipulated variable; from step two onward they have
    also acted differently, and the divergence mixes the direct effect with its
    consequences. Both are worth measuring, but they are different quantities.
    """
    init = InitialState(warmup=warmup, reset_memory_before_start=False)
    base = AssaySpec(name="body_cold", world_seeds=world_seeds, horizon=horizon,
                     initial=init,
                     interventions=(SetBody(start=0, channel="temperature", value=cold),))
    return base, base.with_(
        name="body_hot",
        interventions=(SetBody(start=0, channel="temperature", value=hot),))


def null_contingency_specs(cold: float = 0.25, hot: float = 0.75, horizon: int = 1,
                           warmup: int = 12,
                           world_seeds=(1000, 1001, 1002, 1003)) -> tuple[AssaySpec, AssaySpec]:
    """Magnitude-matched change to a channel with no thermal meaning.

    Any large enough input change moves a softmax policy, so a bare divergence
    along the temperature channel is not interpretable on its own.
    """
    delta = hot - cold
    init = InitialState(warmup=warmup, reset_memory_before_start=False)
    set_cold = SetBody(start=0, channel="temperature", value=cold)
    base = AssaySpec(name="null_low", world_seeds=world_seeds, horizon=horizon,
                     initial=init, interventions=(set_cold,))
    return base, base.with_(
        name="null_high",
        interventions=(set_cold, FalsifySensor(channel="age", value=min(1.0, delta))))


def body_contingency(controller, base_cfg: RunConfig, **kw) -> PairedResult:
    cold, hot = body_contingency_specs(**kw)
    nlo, nhi = null_contingency_specs(**kw)
    pairs = run_paired(controller, base_cfg, cold, hot)
    nulls = run_paired(controller, base_cfg, nlo, nhi)

    d = [M.policy_divergence(a, b) for a, b in pairs]
    n = [M.policy_divergence(a, b) for a, b in nulls]
    tv, tv_null = _mean(d, "tv_first"), _mean(n, "tv_first")
    return PairedResult(
        name="body_contingency",
        question="Same world, different body temperature: does the policy differ?",
        differs_in=hot.differs_from(cold),
        n_worlds=len(pairs),
        metrics={
            "tv_body": tv,
            "tv_null": tv_null,
            "tv_ratio": tv / tv_null if tv_null > 1e-9 else NAN,
            "tv_excess": tv - tv_null,
        },
    )


# ---------------------------------------------------------------------------
# 2. Sensor dissociation: same body, different reading
# ---------------------------------------------------------------------------

def sensor_dissociation_specs(cold: float = 0.25, hot: float = 0.75, horizon: int = 100,
                              warmup: int = 12,
                              world_seeds=(1000, 1001, 1002, 1003)):
    """Three arms. The dissociated one is physically hot and told it is cold.

    Sensed temperature is the only route body temperature takes into an
    observation, so if the three arms are otherwise in identical states then at
    step 0 the dissociated arm's observation equals the veridical-cold arm's
    *exactly*, and their action distributions are identical. That identity is a
    structural check on the design, asserted in the tests.

    Getting it requires the divergence to begin at step 0, not before it. So the
    warmup is run at the *same* temperature in all three arms and the split is
    imposed by a SetBody at step 0, rather than by a different InitialState. An
    earlier version set the temperature before the warmup, and twelve steps of
    physically different bodies moved the arms to different positions with
    different energy before measurement even started - so the first measured
    observations differed in far more than the manipulated variable.
    """
    init = InitialState(warmup=warmup, reset_memory_before_start=False)
    v_cold = AssaySpec(name="veridical_cold", world_seeds=world_seeds,
                       horizon=horizon, initial=init,
                       interventions=(SetBody(start=0, channel="temperature", value=cold),))
    v_hot = v_cold.with_(
        name="veridical_hot",
        interventions=(SetBody(start=0, channel="temperature", value=hot),))
    dissoc = v_cold.with_(
        name="dissociated",
        interventions=(SetBody(start=0, channel="temperature", value=hot),
                       FalsifySensor(channel="temperature", value=cold)))
    return v_cold, v_hot, dissoc


def sensor_dissociation(controller, base_cfg: RunConfig, **kw) -> PairedResult:
    v_cold, v_hot, dissoc = sensor_dissociation_specs(**kw)
    vs_sensed = run_paired(controller, base_cfg, dissoc, v_cold)
    vs_physical = run_paired(controller, base_cfg, dissoc, v_hot)

    s = [M.policy_divergence(a, b) for a, b in vs_sensed]
    p = [M.policy_divergence(a, b) for a, b in vs_physical]
    body = base_cfg.body
    d_traj = [a for a, _ in vs_sensed]
    h_traj = [b for _, b in vs_physical]
    c_traj = [b for _, b in vs_sensed]

    tv_s, tv_p = _mean(s, "tv_mean"), _mean(p, "tv_mean")
    return PairedResult(
        name="sensor_dissociation",
        question="Physically hot, told cold: do actions follow the reading?",
        differs_in=dissoc.differs_from(v_hot),
        n_worlds=len(vs_sensed),
        metrics={
            "tv_vs_sensed_match": tv_s,
            "tv_vs_physical_match": tv_p,
            # Negative means the actions track what the organism was told.
            "follows_sensed_margin": tv_s - tv_p,
            "tv_first_vs_sensed": _mean(s, "tv_first"),
            "integrity_dissociated": float(np.nanmean(
                [M.survival(t, dissoc.horizon)["final_integrity"] for t in d_traj])),
            "integrity_veridical_hot": float(np.nanmean(
                [M.survival(t, v_hot.horizon)["final_integrity"] for t in h_traj])),
            "integrity_veridical_cold": float(np.nanmean(
                [M.survival(t, v_cold.horizon)["final_integrity"] for t in c_traj])),
        },
    )


# ---------------------------------------------------------------------------
# 3. Does acting on the reading help? (roadmap section 1, the missing piece)
# ---------------------------------------------------------------------------

def viability_after_falsification(controller, base_cfg: RunConfig,
                                  falsified: float = 0.5, horizon: int = 120,
                                  warmup: int = 12, shock: float = 0.9,
                                  world_seeds=(1000, 1001, 1002, 1003)) -> PairedResult:
    """Push the body out of band, then either tell the truth or lie about it.

    Both arms are physically identical: body temperature forced to `shock` at
    step 0. One arm reads its true temperature; the other reads a comfortable
    value and so has no sensory reason to correct. The difference in what happens
    next is the consequence of being able to read the channel.

    This is what separates "the channel is read" from "reading it is useful",
    which a divergence in action distributions alone cannot establish.
    """
    truthful = AssaySpec(
        name="shocked_truthful", world_seeds=world_seeds, horizon=horizon,
        initial=InitialState(warmup=warmup, reset_memory_before_start=False),
        interventions=(SetBody(start=0, channel="temperature", value=shock),))
    blinded = truthful.with_(
        name="shocked_blinded",
        interventions=(SetBody(start=0, channel="temperature", value=shock),
                       FalsifySensor(channel="temperature", value=falsified)))

    pairs = run_paired(controller, base_cfg, truthful, blinded)
    body = base_cfg.body
    t_out = [M.viability_outcome(a, body, 0) for a, _ in pairs]
    b_out = [M.viability_outcome(b, body, 0) for _, b in pairs]
    # The body starts out of band by construction, so there is no pre-shock
    # baseline to recover to and `recovery_time` is undefined. The target here is
    # the band itself.
    rec_t = [M.time_to_band(a, body, 0) for a, _ in pairs]
    rec_b = [M.time_to_band(b, body, 0) for _, b in pairs]

    return PairedResult(
        name="viability_after_falsification",
        question="Body forced out of band. Does reading it truthfully help recovery?",
        differs_in=blinded.differs_from(truthful),
        n_worlds=len(pairs),
        metrics={
            "in_band_truthful": _mean(t_out, "post_in_band"),
            "in_band_blinded": _mean(b_out, "post_in_band"),
            "in_band_benefit": _mean(t_out, "post_in_band") - _mean(b_out, "post_in_band"),
            "integrity_truthful": _mean(t_out, "post_integrity_change"),
            "integrity_blinded": _mean(b_out, "post_integrity_change"),
            "integrity_benefit": (_mean(t_out, "post_integrity_change")
                                  - _mean(b_out, "post_integrity_change")),
            # All-NaN means nothing recovered inside the window, which is a
            # result, not an error; nanmean would warn and return NaN anyway.
            "time_to_band_truthful": _finite_mean(rec_t),
            "time_to_band_blinded": _finite_mean(rec_b),
            "never_recovered_truthful": float(sum(math.isnan(x) for x in rec_t)),
            "never_recovered_blinded": float(sum(math.isnan(x) for x in rec_b)),
            "steps_truthful": _mean(t_out, "post_steps"),
            "steps_blinded": _mean(b_out, "post_steps"),
        },
    )


# ---------------------------------------------------------------------------
# 4. Memory necessity, ready for E2
# ---------------------------------------------------------------------------

def memory_necessity(controller, base_cfg: RunConfig, reset_at: int = 40,
                     horizon: int = 120, warmup: int = 20,
                     world_seeds=(1000, 1001, 1002, 1003)) -> PairedResult:
    """Wipe persistent state mid-rollout and measure what it costs.

    A no-op for a reactive controller, which makes it its own control: a
    recurrent controller that is also unaffected is not using its memory.
    """
    intact = AssaySpec(name="memory_intact", world_seeds=world_seeds, horizon=horizon,
                       initial=InitialState(warmup=warmup, reset_memory_before_start=False))
    wiped = intact.with_(name="memory_wiped", interventions=(ResetMemory(start=reset_at),))
    pairs = run_paired(controller, base_cfg, intact, wiped)
    body = base_cfg.body
    div = [M.policy_divergence(a, b) for a, b in pairs]
    a_out = [M.viability_outcome(a, body, reset_at) for a, _ in pairs]
    b_out = [M.viability_outcome(b, body, reset_at) for _, b in pairs]
    return PairedResult(
        name="memory_necessity",
        question="Wipe persistent state mid-rollout: does behaviour and viability change?",
        differs_in=wiped.differs_from(intact),
        n_worlds=len(pairs),
        metrics={
            "tv_after_wipe": _mean(div, "tv_mean"),
            "in_band_intact": _mean(a_out, "post_in_band"),
            "in_band_wiped": _mean(b_out, "post_in_band"),
            "in_band_cost": _mean(a_out, "post_in_band") - _mean(b_out, "post_in_band"),
            "integrity_cost": (_mean(a_out, "post_integrity_change")
                               - _mean(b_out, "post_integrity_change")),
        },
    )


# ---------------------------------------------------------------------------
# 5. Actuator remapping, ready for body-schema work
# ---------------------------------------------------------------------------

def actuator_remap(controller, base_cfg: RunConfig, permutation=(0, 3, 4, 1, 2),
                   horizon: int = 120, warmup: int = 20,
                   world_seeds=(1000, 1001, 1002, 1003)) -> PairedResult:
    """Reverse the motor mapping and measure the cost. A reactive controller
    cannot recover within a lifetime; a plastic one might. Recording the intact
    baseline now makes that future comparison possible."""
    intact = AssaySpec(name="actuator_intact", world_seeds=world_seeds, horizon=horizon,
                       initial=InitialState(warmup=warmup, reset_memory_before_start=False))
    remapped = intact.with_(name="actuator_remapped",
                            interventions=(RemapActuator(permutation=permutation),))
    pairs = run_paired(controller, base_cfg, intact, remapped)
    body = base_cfg.body
    a_out = [M.summarise(a, body, horizon) for a, _ in pairs]
    b_out = [M.summarise(b, body, horizon) for _, b in pairs]
    return PairedResult(
        name="actuator_remap",
        question="Reverse the motor mapping: how much control is lost?",
        differs_in=remapped.differs_from(intact),
        n_worlds=len(pairs),
        metrics={
            "homeostatic_intact": _mean(a_out, "homeostatic_advantage"),
            "homeostatic_remapped": _mean(b_out, "homeostatic_advantage"),
            "homeostatic_cost": (_mean(a_out, "homeostatic_advantage")
                                 - _mean(b_out, "homeostatic_advantage")),
            "eaten_intact": _mean(a_out, "resources_eaten"),
            "eaten_remapped": _mean(b_out, "resources_eaten"),
            "survival_cost": _mean(a_out, "steps_survived") - _mean(b_out, "steps_survived"),
        },
    )


STANDARD_ASSAYS = {
    "body_contingency": body_contingency,
    "sensor_dissociation": sensor_dissociation,
    "viability_after_falsification": viability_after_falsification,
    "memory_necessity": memory_necessity,
    "actuator_remap": actuator_remap,
}
