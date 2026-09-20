"""Multi-condition, multi-seed experiment runner.

An experiment file declares a base config, a set of named conditions (each a
sparse override of the base), the seeds to run, and a preregistration block
naming the primary endpoint and the hypothesis before any data exist.
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

from emergent_self.analysis.metrics import (
    PERSISTENCE_ENDPOINTS,
    PRIMARY_ENDPOINT,
    REGULATION_ENDPOINTS,
)
from emergent_self.analysis.stats import bootstrap_ci, interaction_contrast, paired_compare
from emergent_self.config import RunConfig, run_config_from_dict
from emergent_self.sim import Simulation


#: Bumped when the stored result layout changes incompatibly, so an old
#: report is rejected with a clear message rather than misread. Endpoint
#: renames count: a reader that silently finds no `thermal_decoupling_advantage`
#: would report a blank column instead of an error.
RESULT_SCHEMA_VERSION = 1


def deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


class Experiment:
    def __init__(self, spec: dict[str, Any]):
        self.name: str = spec["name"]
        self.base: dict = spec.get("base", {})
        self.conditions: dict[str, dict] = spec["conditions"]
        self.seeds: list[int] = spec["seeds"]
        self.prereg: dict = spec.get("preregistration", {})
        self.endpoint: str = self.prereg.get("primary_endpoint", PRIMARY_ENDPOINT)
        self.reference: str | None = self.prereg.get("reference_condition")
        self.floor: str | None = self.prereg.get("floor_condition")
        self.interaction: dict | None = self.prereg.get("interaction")

    @classmethod
    def load(cls, path: str | Path) -> "Experiment":
        return cls(json.loads(Path(path).read_text()))

    def run_configs(self) -> list[RunConfig]:
        cfgs = []
        for cond, override in self.conditions.items():
            merged = deep_merge(self.base, override)
            for seed in self.seeds:
                merged_run = deep_merge(merged, {"name": self.name, "condition": cond, "seed": seed})
                cfgs.append(run_config_from_dict(merged_run))
        return cfgs


def _execute(cfg: RunConfig) -> dict:
    result = Simulation(cfg).run()
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "condition": result.condition,
        "seed": result.seed,
        "digest": result.digest,
        "provenance": result.provenance,
        "summary": result.summary,
        "energy_ledger": result.energy_ledger,
        "extinct_at": result.extinct_at,
        "timeseries": result.timeseries,
        "config": asdict(cfg),
    }


def run_experiment(exp: Experiment, out_dir: Path, workers: int | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    cfgs = exp.run_configs()
    workers = workers or min(len(cfgs), os.cpu_count() or 1)

    results: list[dict] = []
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for i, res in enumerate(pool.map(_execute, cfgs), 1):
                results.append(res)
                print(f"  [{i}/{len(cfgs)}] {res['condition']} seed={res['seed']} "
                      f"{exp.endpoint}={res['summary'].get(exp.endpoint, float('nan')):.3f}")
    else:
        for i, cfg in enumerate(cfgs, 1):
            res = _execute(cfg)
            results.append(res)
            print(f"  [{i}/{len(cfgs)}] {res['condition']} seed={res['seed']} "
                  f"{exp.endpoint}={res['summary'].get(exp.endpoint, float('nan')):.3f}")

    with (out_dir / "runs.jsonl").open("w") as fh:
        for res in results:
            fh.write(json.dumps(res) + "\n")

    report = build_report(exp, results)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2))
    return report


def build_report(exp: Experiment, results: list[dict]) -> dict:
    import math

    by_cond: dict[str, list[dict]] = {}
    for r in results:
        by_cond.setdefault(r["condition"], []).append(r)

    def by_seed(cond: str, endpoint: str) -> dict[int, float]:
        return {r["seed"]: r["summary"].get(endpoint, float("nan")) for r in by_cond[cond]}

    per_condition = {}
    for cond, runs in by_cond.items():
        vals = [r["summary"].get(exp.endpoint, float("nan")) for r in runs]
        usable = [v for v in vals if math.isfinite(v)]
        mean, lo, hi = bootstrap_ci(vals)
        per_condition[cond] = {
            "n_seeds": len(runs),
            # A seed whose late window held no organism contributes nothing to
            # the endpoint. Reporting it keeps an empty window from reading as a
            # measured zero.
            "n_usable": len(usable),
            "n_missing": len(vals) - len(usable),
            "endpoint_values": vals,
            "mean": mean, "ci_lo": lo, "ci_hi": hi,
            "extinctions": sum(1 for r in runs if r["extinct_at"] is not None),
            "regulation": {k: _cond_mean(runs, k) for k in REGULATION_ENDPOINTS},
            "persistence": {k: _cond_mean(runs, k) for k in PERSISTENCE_ENDPOINTS},
        }

    contrasts = {}
    for ref, label in ((exp.reference, "reference"), (exp.floor, "floor")):
        if not ref or ref not in by_cond:
            continue
        for cond in by_cond:
            if cond == ref:
                continue
            contrasts[f"{cond}_vs_{ref}"] = {
                **paired_compare(by_seed(cond, exp.endpoint), by_seed(ref, exp.endpoint)),
                "kind": label,
            }

    # Persistence is reported as its own contrast family. "A population survived"
    # and "a population regulated" are different claims and must not be merged.
    persistence_contrasts = {}
    if exp.floor and exp.floor in by_cond:
        for cond in by_cond:
            if cond == exp.floor:
                continue
            persistence_contrasts[f"{cond}_vs_{exp.floor}"] = paired_compare(
                by_seed(cond, "survival_fraction"), by_seed(exp.floor, "survival_fraction")
            )

    interaction = None
    spec = exp.interaction
    if spec and all(spec[k] in by_cond for k in ("a_plus", "a_minus", "b_plus", "b_minus")):
        cells = {c: by_seed(c, exp.endpoint) for c in by_cond}
        interaction = {
            **interaction_contrast(cells, spec["a_plus"], spec["a_minus"],
                                   spec["b_plus"], spec["b_minus"]),
            "description": spec.get("description", ""),
        }

    from emergent_self.provenance import provenance

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "experiment": exp.name,
        "provenance": provenance(),
        "preregistration": exp.prereg,
        "primary_endpoint": exp.endpoint,
        "per_condition": per_condition,
        "contrasts": contrasts,
        "persistence_contrasts": persistence_contrasts,
        "interaction": interaction,
    }


def _cond_mean(runs: list[dict], key: str) -> float:
    import math

    vals = [r["summary"].get(key, float("nan")) for r in runs]
    usable = [v for v in vals if math.isfinite(v)]
    return float(sum(usable) / len(usable)) if usable else float("nan")
