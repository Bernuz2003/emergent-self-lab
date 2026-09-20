# Results log

One entry per completed experiment, written whether the result is positive, null
or retracted. Failed evolutionary histories and withdrawn claims are kept on
purpose (`docs/METHODOLOGY.md`, "Statistics").

---

## E1 — Interoception and homeostasis — **result retracted, re-run required**

The v0.2 write-up claimed *"H1 supported: thermoregulation evolved"* on the
strength of a contrast between evolved conditions and a random controller
(Hedges g = -0.92). **That contrast was an artifact and the claim is withdrawn.**

Three defects, all since fixed, produced it:

1. **Missing data was scored as zero.** `exposure_weighted_index` returned `0.0`
   when the late window contained no organism. Random-controller populations die
   before reaching that window, so **11 of 12 random runs reported exactly
   `0.0000`** — not a measured zero, an empty measurement. Those invented zeros
   are what created the effect size. Missing data is now `NaN`, dropped from
   every statistic, and the number of contributing seeds is printed beside each
   contrast.
2. **`population_persisted` was read from the last logged row** rather than from
   `extinct_at`, so it disagreed with the extinction record in **15 of 60 runs**
   and reported 0.75 for a condition that went extinct 12 times out of 12.
3. **Windows were relative to the surviving log**, so "the last 25%" covered
   steps 900–1200 for a run that died early and 4500–6000 for one that did not.
   Windows are now absolute against the preregistered run length.

A fourth issue made the comparison unsound independently of the statistics: the
endpoint pooled *regulation* and *persistence*. Whether a population continued to
exist and whether it regulated its body temperature are different claims, and
they are now separate endpoint families.

The E1 numbers are also stale for a second reason: the RNG streams were split
finer (see below), which changes every trajectory. E1 must be re-run before
anything is claimed from it:

```bash
python scripts/run_experiment.py configs/e1_interoception.json
python scripts/analyze.py runs/E1_interoception
```

What survives from the original run is the **diagnosis**, which the frozen assay
has since confirmed independently: with the ambient channel intact, ambient
temperature at the occupied cell predicted body temperature well enough that
interoception was redundant, and organisms could regulate positionally.

---

## Frozen assay — what evolution actually selected for — *recorded*

- Command: `python scripts/run_assay.py --n-seeds 12 --steps 6000 --assay-steps 600 --assay-seeds 6 --controllers 8 --out runs/assay_e1.json`
- 12 evolution seeds, 11 usable (seed 0 went extinct at step 1442 before the final checkpoint)
- 8 controllers per checkpoint x 6 standardised worlds x 600 steps
- Contrast: final cohort minus ancestral cohort, **paired within evolution seed**

Controllers were snapshotted at step 0 and step 6000, then evaluated frozen —
alone, with no mutation, no reproduction and no competition, across the same six
standardised worlds. This is the comparison a live population cannot provide.

| metric | ancestral | evolved | diff | 95% CI | dz | seeds won |
|---|---|---|---|---|---|---|
| resources eaten | 13.37 | 29.91 | **+16.54** | [12.09, 21.43] | 1.99 | **11/11** |
| move fraction | 0.763 | 0.890 | **+0.127** | [0.070, 0.189] | 1.20 | 10/11 |
| steps survived | 199.6 | 228.0 | **+28.4** | [4.07, 53.10] | 0.64 | 9/11 |
| death rate | 0.966 | 0.941 | -0.025 | [-0.053, 0.000] | -0.51 | 2/11 |
| final integrity | 0.132 | 0.068 | **-0.064** | [-0.116, -0.013] | -0.69 | 2/11 |
| thermoregulation index | -0.127 | -0.143 | -0.016 | [-0.055, 0.028] | -0.21 | 3/11 |
| regulation vs passive | -0.223 | -0.271 | -0.048 | [-0.101, 0.008] | -0.50 | 3/11 |

### What this establishes

Selection is strong and unambiguous, and its target is **foraging**, not
thermoregulation. Evolved controllers move more, eat more than twice as much,
and survive longer, on identical ground, in 9–11 of 11 seeds.

Over the same evolution, thermoregulation did not improve. Both regulation
endpoints moved slightly *negative*, and final integrity got significantly
**worse**: the evolved strategy trades structural integrity for energy intake.

This is the correct form of the H1 claim, and it is narrower than the one that
was retracted:

> Embodied viability constraints produce strong selection for an energetic and
> ecological strategy, with no survival term anywhere in the system. In this
> environment that strategy does not include improved thermoregulation, and it
> is purchased partly at the cost of bodily integrity.

### Interpretation limit

This says what selection did in this environment. It is not evidence about felt
states, and the absence of evolved thermoregulation here is a fact about this
world, not a general claim about embodied agents.

---

## E1b — State-contingent homeostasis — *run, underpowered, needs recalibration*

- Config: `configs/e1b_state_contingent.json`
- Design: 2x2 (hidden body perturbation on | off) x (interoception true | shuffled), plus a random floor
- Seeds: 0–11, 6000 steps

E1b injects hidden internal perturbations — body temperature displaced by ±0.30
with probability 0.06 per organism per step — while leaving the ambient field,
the resource layout and the organism's position untouched. Two organisms on the
same cell can then require opposite actions, which is exactly what E1 lacked.
Measured effect on redundancy: R²(ambient → body) falls from 0.32 to 0.18.

### Outcome: not evaluable at this calibration

| condition | index | usable seeds | extinct |
|---|---|---|---|
| A perturbed + interoception | -0.122 | 5/12 | 7/12 |
| B perturbed + shuffled | -0.107 | 7/12 | 6/12 |
| C stable + interoception | 0.041 | 10/12 | 2/12 |
| D stable + shuffled | 0.104 | 11/12 | 1/12 |
| E random floor | — | **0/12** | 12/12 |

The perturbation is too lethal. The key contrast (A vs B) rests on **4 paired
seeds**, and the random floor produced no usable seed at all, so the interaction
that H2 now has to take cannot be estimated.

This is the infrastructure working as intended rather than a wasted run: the
same experiment under the old metrics would have filled the empty cells with
zeros and reported a confident result. The report instead refuses, prints
`usable 5/12`, `0/12` and `pairs 4`, and leaves the contrast blank.

### Before re-running

Recalibrate the perturbation down until extinction in the perturbed arms matches
the stable arms (roughly 1–2 of 12), then re-run:

```bash
python scripts/calibrate.py --steps 4000 --seeds 12          # extinction rate
python scripts/diagnose_redundancy.py                         # is intero informative
python scripts/run_experiment.py configs/e1b_state_contingent.json
python scripts/analyze.py runs/E1b_state_contingent
```

Candidate settings to sweep: `hidden_perturbation_prob` 0.02–0.04 with
`hidden_perturbation_magnitude` 0.20–0.25, or the current perturbation with
`body.thermal_damage` reduced to keep the excursions survivable. The requirement
is that the perturbed arms lose no more seeds than the stable ones, so the
interaction is estimated on twelve pairs rather than four.

---

## Representation probes — *recorded, methodological*

- Command: `python scripts/run_probes.py --controller gru --hidden 16 --evolve-steps 1500 --probe-steps 400`

| variable | grouped R² | pooled R² | chance | reading |
|---|---|---|---|---|
| energy | -5.693 | +0.312 | -0.021 | lineage identity |
| integrity | -2.398 | +0.407 | -0.077 | lineage identity |
| temperature | -1.085 | +0.441 | -0.020 | lineage identity |
| age | -9.553 | +0.410 | +0.002 | lineage identity |
| ambient | -1.322 | +0.563 | -0.020 | lineage identity |
| resource here | -0.017 | -0.005 | -0.041 | not decodable |

`pooled` holds out random observations; `grouped` holds out whole lineages.

An earlier version of the probe reported temperature at R² ≈ 0.59 and treated it
as evidence that body state was represented. It was not. Consecutive samples of
one organism are strongly autocorrelated and a whole lineage shares a controller
up to mutation, so a split taken over observations trains and tests on the same
lineages. Holding out lineages instead, every apparent decode collapses below
chance: the linear code is **lineage-specific**, and a decoder fit on some
organisms actively mispredicts in others.

Pushing the latent along the decoded energy direction moves the action
distribution by a total variation of 0.292 (sd 0.109). Note this is measured on
distributions now; the earlier figure of 0.047 came from comparing single
sampled actions, which at a softmax temperature of 0.35 is mostly sampling noise.

The standing conclusion is unchanged and now better supported: **information
present is not information used**, and *decodable* has to mean decodable across
lineages before it means anything at all.
