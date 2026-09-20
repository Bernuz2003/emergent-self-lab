"""Render a finished experiment's report: distributions, effect sizes, verdict.

Persistence and regulation are printed as separate families on purpose. "This
population survived" and "this population regulated its body temperature" are
different claims, and merging them is how an ecological result gets reported as
a homeostatic one.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def _fmt(x: float, width: int = 8, prec: int = 3) -> str:
    return f"{'--':>{width}}" if x is None or not math.isfinite(x) else f"{x:>{width}.{prec}f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir")
    args = ap.parse_args()

    report = json.loads((Path(args.run_dir) / "report.json").read_text())
    prereg = report.get("preregistration", {})

    print(f"=== {report['experiment']} ===")
    if prereg.get("hypothesis"):
        print(f"\nH : {prereg['hypothesis']}")
        print(f"H0: {prereg.get('null_hypothesis', '-')}")
    print(f"\nPrimary endpoint: {report['primary_endpoint']}")
    print("Read against the floor condition, not against zero: no endpoint here "
          "has a meaningful absolute zero.\n")

    print("REGULATION")
    print(f"{'condition':<30}{'seeds':>7}{'usable':>8}{'mean':>9}{'95% CI':>20}")
    print("-" * 74)
    for cond, s in sorted(report["per_condition"].items()):
        ci = f"[{_fmt(s['ci_lo'], 6)}, {_fmt(s['ci_hi'], 6)}]".replace(" ", "")
        flag = "  <- no usable seed" if s["n_usable"] == 0 else ""
        print(f"{cond:<30}{s['n_seeds']:>7}{s['n_usable']:>8}{_fmt(s['mean'], 9)}{ci:>20}{flag}")
    missing = {c: s["n_missing"] for c, s in report["per_condition"].items() if s["n_missing"]}
    if missing:
        print("\n  Seeds with no organism in the late window (endpoint undefined, "
              "NOT zero):")
        for c, n in sorted(missing.items()):
            print(f"    {c:<28} {n}")

    print("\nPERSISTENCE")
    print(f"{'condition':<30}{'extinct':>9}{'survival':>10}{'late pop':>10}{'births':>9}")
    print("-" * 68)
    for cond, s in sorted(report["per_condition"].items()):
        p = s["persistence"]
        print(f"{cond:<30}{f'{s['extinctions']}/{s['n_seeds']}':>9}"
              f"{_fmt(p['survival_fraction'], 10)}{_fmt(p['late_population'], 10, 1)}"
              f"{_fmt(p['total_births'], 9, 0)}")

    if report.get("contrasts"):
        print("\nSEED-PAIRED CONTRASTS on the primary endpoint")
        print(f"{'contrast':<44}{'pairs':>7}{'diff':>9}{'95% CI':>20}{'dz':>7}")
        print("-" * 87)
        for name, c in sorted(report["contrasts"].items()):
            ci = f"[{_fmt(c['ci_lo'], 6)},{_fmt(c['ci_hi'], 6)}]".replace(" ", "")
            print(f"{name:<44}{int(c['n_pairs']):>7}{_fmt(c['mean_diff'], 9)}{ci:>20}{_fmt(c['dz'], 7, 2)}")

    if report.get("persistence_contrasts"):
        print("\nSEED-PAIRED CONTRASTS on survival fraction")
        print(f"{'contrast':<44}{'pairs':>7}{'diff':>9}{'95% CI':>20}{'dz':>7}")
        print("-" * 87)
        for name, c in sorted(report["persistence_contrasts"].items()):
            ci = f"[{_fmt(c['ci_lo'], 6)},{_fmt(c['ci_hi'], 6)}]".replace(" ", "")
            print(f"{name:<44}{int(c['n_pairs']):>7}{_fmt(c['mean_diff'], 9)}{ci:>20}{_fmt(c['dz'], 7, 2)}")

    inter = report.get("interaction")
    if inter:
        print("\nINTERACTION")
        if inter.get("description"):
            print(f"  {inter['description']}")
        ci = f"[{_fmt(inter['ci_lo'], 6)}, {_fmt(inter['ci_hi'], 6)}]".replace("  ", " ")
        print(f"  double difference = {_fmt(inter['interaction'], 7)}  95% CI {ci}  "
              f"dz={_fmt(inter['dz'], 5, 2)}  pairs={int(inter['n_pairs'])}")

    rule = prereg.get("decision_rule")
    if rule and report.get("contrasts"):
        print(f"\nDecision rule: {rule}\n")
        for name, c in sorted(report["contrasts"].items()):
            if not math.isfinite(c["mean_diff"]):
                print(f"  {name:<44} not evaluable (no paired seeds)")
                continue
            excludes_zero = (c["ci_lo"] > 0) == (c["ci_hi"] > 0)
            big = math.isfinite(c["dz"]) and abs(c["dz"]) >= 0.5
            print(f"  {name:<44} {'reject H0' if excludes_zero and big else 'fail to reject H0'}")
        if inter and math.isfinite(inter["interaction"]):
            ok = ((inter["ci_lo"] > 0) == (inter["ci_hi"] > 0)) and abs(inter["dz"]) >= 0.5
            print(f"  {'INTERACTION (H2 as stated)':<44} "
                  f"{'supported' if ok else 'not supported'}")

    if prereg.get("interpretation_limit"):
        print(f"\nInterpretation limit: {prereg['interpretation_limit']}")


if __name__ == "__main__":
    main()
