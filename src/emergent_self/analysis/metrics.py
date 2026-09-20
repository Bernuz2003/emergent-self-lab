"""Run-level metrics.

Nothing here feeds back into the simulation.

Why the primary endpoint is an *index* and not raw band occupancy
-----------------------------------------------------------------
Averaging "fraction of living organisms currently inside the viable temperature
band" is a survivorship-biased statistic: organisms that leave the band lose
integrity and are removed, so whoever is still alive is in band almost by
construction. A pilot confirmed it - a uniformly random controller scored as
high as evolved populations on that measure.

The primary endpoint is therefore

    thermoregulation_index = P(body in band) - P(ambient at the occupied cell in band)

pooled over every agent-step that ever occurred, including the steps of
organisms that later died, and weighted by exposure.

Missing data is NaN, never zero
-------------------------------
The late window can contain no eligible organism at all, because the population
died before reaching it. That is *absence of measurement*, and it is not the
same statement as "this population achieved an index of zero".

Treating it as zero was a real defect in an earlier version and it manufactured
a headline result: 11 of 12 random-controller runs reported exactly 0.0000 from
the empty-window path, which dragged the random condition's mean toward zero and
produced a spurious Hedges g of -0.92 against it. The correct value is NaN, the
correct number of usable seeds is smaller than 12, and the statistics layer
reports both.

Whether a population survives at all is a separate question from how well it
regulates, so it is a separate endpoint (`population_persisted`,
`survival_fraction`) rather than something smuggled into the regulation index.

Absolute windows, not relative ones
-----------------------------------
"The last 25% of logged rows" is a different stretch of time for a run that
ended at step 1200 than for one that reached 6000. Windows are therefore defined
against the preregistered `cfg.steps`, so every condition is measured over the
same interval of simulated time.

No endpoint here has a meaningful absolute zero
-----------------------------------------------
Thermal inertia lets any body linger in band after entering a hostile cell, and
in cold regions the metabolic heat of motion warms a body toward the band for
free. Both give a random controller a non-zero score. Every experiment config
declares a `floor_condition`, and conditions are read against that floor
measured in the same worlds under the same calibration.
"""
from __future__ import annotations

import numpy as np

from emergent_self.config import RunConfig

#: Renamed from `thermoregulation_index`, which overclaimed what it measures.
#: It scores zero for an organism that senses it is too hot, walks to a cool
#: cell and stays there - a textbook case of behavioural thermoregulation, in
#: which body and ambient are both in band and the difference is zero. What it
#: actually measures is how far the body has decoupled from the cell it is
#: standing in. The complementary half of homeostasis is measured separately by
#: `microenvironment_selection`, and the two add up:
#:
#:   thermal_decoupling_advantage  = P(body in band) - P(ambient occupied in band)
#:   microenvironment_selection    = P(ambient occupied in band) - P(field in band)
#:   -------------------------------------------------------------------------
#:   homeostatic_advantage         = P(body in band) - P(field in band)
#:
#: The field baseline is the fraction of the whole world whose ambient sits in
#: band, which is what a non-selecting walker on a torus experiences.
PRIMARY_ENDPOINT = "thermal_decoupling_advantage"
#: Old name, still emitted with the identical value so reports and configs
#: written before the rename keep resolving.
LEGACY_PRIMARY = "thermoregulation_index"
NAN = float("nan")

#: Endpoints about whether a population continued to exist. Kept separate from
#: the regulation endpoints so that "something was selected for" and "that
#: something was thermoregulation" cannot be conflated.
PERSISTENCE_ENDPOINTS = ("population_persisted", "survival_fraction", "late_population",
                         "total_births", "median_lifespan")
REGULATION_ENDPOINTS = (PRIMARY_ENDPOINT, "microenvironment_selection",
                        "homeostatic_advantage", "regulation_vs_passive",
                        "index_gain", "late_mean_excursion", "mean_recovery_time")


def _window(rows: list[dict], start: int, stop: int) -> list[dict]:
    return [r for r in rows if start <= r["step"] <= stop]


def exposure_weighted_index(exposure, born_after: int = 0, born_before: int | None = None) -> float:
    """Pooled P(body in band) - P(ambient in band) over all matching agent-steps.

    Returns NaN when no organism qualifies. Weighting by steps_alive rather than
    averaging per-organism ratios keeps a short-lived organism from counting as
    much as one that lived for thousands of steps.
    """
    rows = [
        (alive, body, amb)
        for alive, body, amb, birth in exposure
        if alive > 0 and birth >= born_after and (born_before is None or birth <= born_before)
    ]
    if not rows:
        return NAN
    total = sum(r[0] for r in rows)
    return (sum(r[1] for r in rows) - sum(r[2] for r in rows)) / total


def eligible_organisms(exposure, born_after: int = 0) -> int:
    """How many organisms the index was actually computed from. Reported next to
    every index so an empty window is visible rather than inferred."""
    return sum(1 for alive, _, _, birth in exposure if alive > 0 and birth >= born_after)


def recovery_time(rows: list[dict], shock_step: int, window: int, threshold: float) -> float | None:
    """Steps after a thermal shock until mean band occupancy first returns above
    `threshold`. None if it never recovers inside the window."""
    for r in rows:
        if shock_step < r["step"] <= shock_step + window and r["band_occupancy"] >= threshold:
            return float(r["step"] - shock_step)
    return None


def _mean_or_nan(values) -> float:
    v = [x for x in values if x is not None and np.isfinite(x)]
    return float(np.mean(v)) if v else NAN


def occupied_band_fraction(exposure, born_after: int = 0) -> float:
    """P(ambient at the occupied cell in band), pooled over matching agent-steps."""
    rows = [(alive, amb) for alive, _, amb, birth in exposure
            if alive > 0 and birth >= born_after]
    if not rows:
        return NAN
    return sum(a for _, a in rows) / sum(n for n, _ in rows)


def summarise(result, cfg: RunConfig) -> dict[str, float]:
    rows = result.timeseries
    late_start = int(cfg.steps * 0.75)
    early_stop = int(cfg.steps * 0.25)

    # Absolute windows against the preregistered run length.
    late_rows = _window(rows, late_start, cfg.steps)
    early_rows = _window(rows, 0, early_stop)
    late_alive = [r for r in late_rows if r["population"] > 0]

    extinct_at = result.extinct_at
    persisted = extinct_at is None
    # After extinction the population is genuinely zero, so the late-window mean
    # counts those steps as zero rather than skipping them. This is the one place
    # where a missing row is real data rather than missing data.
    # The window is inclusive at both ends, so it holds one more row than the
    # span divided by the interval. Dropping the +1 inflated late_population by
    # (n+1)/n - 10% at the default log_every of 10 - for every run that did not
    # go extinct, while runs that did were unaffected. That is a bias in the
    # direction of the surviving conditions.
    expected_rows = max(1, (cfg.steps - late_start) // max(1, cfg.log_every) + 1)
    late_pop_sum = sum(r["population"] for r in late_rows)

    baseline = _mean_or_nan([r["band_occupancy"] for r in early_rows])
    thr = baseline * 0.9 if np.isfinite(baseline) else NAN
    recoveries = (
        []
        if not np.isfinite(thr)
        else [
            rt
            for s in cfg.interventions.thermal_shock_steps
            if (rt := recovery_time(rows, s, cfg.interventions.recovery_window, thr)) is not None
        ]
    )

    late_index = exposure_weighted_index(result.exposure, born_after=late_start)
    early_index = exposure_weighted_index(result.exposure, born_after=0, born_before=early_stop)

    # Fraction of the whole world whose ambient is in band: what a walker that
    # does not select its microenvironment would experience.
    field = result.field_band_fraction
    occupied = occupied_band_fraction(result.exposure, born_after=late_start)
    micro = occupied - field if np.isfinite(occupied) and np.isfinite(field) else NAN

    out = {
        # --- regulation -------------------------------------------------------
        PRIMARY_ENDPOINT: late_index,
        LEGACY_PRIMARY: late_index,
        # The other half of homeostasis: choosing where to stand.
        "microenvironment_selection": micro,
        "homeostatic_advantage": (late_index + micro
                                  if np.isfinite(late_index) and np.isfinite(micro) else NAN),
        "field_band_fraction": field,
        "occupied_band_fraction": occupied,
        "regulation_vs_passive": exposure_weighted_index(result.shadow_exposure, born_after=late_start),
        "early_thermoregulation_index": early_index,
        "all_exposure_index": exposure_weighted_index(result.exposure, born_after=0),
        "index_gain": late_index - early_index,
        "n_late_organisms": float(eligible_organisms(result.exposure, born_after=late_start)),
        "late_mean_excursion": _mean_or_nan([r["mean_excursion"] for r in late_alive]),
        "mean_recovery_time": _mean_or_nan(recoveries),
        "n_recoveries": float(len(recoveries)),
        # --- persistence ------------------------------------------------------
        "population_persisted": float(persisted),
        "survival_fraction": float((extinct_at if extinct_at is not None else cfg.steps) / cfg.steps),
        "extinction_step": float(extinct_at) if extinct_at is not None else NAN,
        "late_population": late_pop_sum / expected_rows,
        "total_births": float(rows[-1]["births"]) if rows else 0.0,
        "median_lifespan": float(np.median(result.lifespans)) if result.lifespans else NAN,
        "p90_lifespan": float(np.percentile(result.lifespans, 90)) if result.lifespans else NAN,
        # --- descriptive ------------------------------------------------------
        "late_band_occupancy": _mean_or_nan([r["band_occupancy"] for r in late_alive]),
        "late_ambient_band_occupancy": _mean_or_nan([r["ambient_band_occupancy"] for r in late_alive]),
        "late_mean_integrity": _mean_or_nan([r["mean_integrity"] for r in late_alive]),
        "late_lineage_entropy": _mean_or_nan([r["lineage_entropy"] for r in late_alive]),
    }
    intake = result.energy_ledger.get("intake", 0.0)
    out["energy_efficiency"] = out["total_births"] / intake if intake > 0 else NAN
    return out
