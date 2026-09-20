# Results log

One entry per completed experiment, written whether the result is positive, null
or retracted. Failed evolutionary histories and withdrawn claims are kept on
purpose (`docs/METHODOLOGY.md`, "Statistics").

---

## E1 — Interoception and homeostasis

### First run: result retracted

The v0.2 write-up claimed *"H1 supported: thermoregulation evolved"* from a
contrast against a random controller at Hedges g = -0.92. **That contrast was an
artifact.** `exposure_weighted_index` returned `0.0` when the late window held no
organism; random populations die before reaching it, so **11 of 12 random runs
contributed an invented zero**. Two further defects compounded it:
`population_persisted` was read from the last logged row rather than `extinct_at`
and disagreed with the extinction record in **15 of 60 runs**; and windows were
relative to the surviving log, covering steps 900-1200 for a run that died early
and 4500-6000 for one that did not. All three are fixed, and regulation and
persistence are now separate endpoint families.

### Second run, under the fixed metrics

| condition | thermal decoupling advantage |
|---|---|
| A — ambient + true interoception | 0.0356 |
| B — ambient + shuffled interoception | **0.0827** |
| C — shuffled ambient + true interoception | 0.0508 |
| D — shuffled ambient + shuffled interoception | 0.0485 |

The preregistered interaction `(C-D) - (A-B)` is **+0.0579**, 95% CI
`[0.024, 0.086]`, dz = 1.27, positive in 6 of 7 fully usable seeds. **By the
preregistered decision rule it passes.**

It should not be reported as support for H2, for two reasons.

**The mechanism is the wrong way round.** The interaction is carried almost
entirely by its first term:

- with ambient available, `A - B = -0.0389`, CI `[-0.067, -0.016]`, dz = -0.90 —
  true interoception performs **worse** than shuffled;
- with ambient removed, `C - D = +0.0076`, CI comfortably spanning zero.

So the finding is not "interoception helps when the world stops broadcasting".
It is "true interoception hurts when the world does broadcast". The same
signature appears in E1b's stable arm at nearly the same magnitude
(`-0.0384` vs E1's `-0.0367`, 11 of 12 seeds in the same direction), so it is
systematic rather than noise — but it is not the claimed mechanism.

**One arm of the interaction was contaminated.** This run predates the split of
the sensor RNG. `shuffled` interoception consumes draws building its derangement
and the exteroceptive decoy locations were drawn from the same stream, so
C (interoception true) and D (interoception shuffled) — both with
`ambient: shuffled` — received **completely different decoy sequences**. The
`C - D` term is exactly the one this contaminates. Verified directly: the first
six decoy coordinates differ entirely between the two conditions on a fixed seed.

The correct statement, pending a re-run:

> The preregistered interaction criterion is met, but the interaction is driven
> primarily by a negative effect of true interoception when ambient information
> is available, rather than by a positive interoceptive benefit when it is
> absent. One of its two terms was additionally contaminated by a shared RNG
> stream. The intended mechanistic interpretation is not established.

### What replaces it

E1c (`configs/e1c_temperature_only.json`) removes both confounds: it ablates the
**temperature channel alone**, leaving energy, integrity and age veridical
everywhere, and its decision rule requires the simple effect `A - B` to be
positive so a negative stable-arm effect cannot carry the interaction by itself.

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

### Intake is not merely a by-product of living longer

Evolved organisms survive longer, so they have more steps in which to eat.
Normalising intake by steps survived removes that:

| | ancestral | evolved |
|---|---|---|
| resources per step | 0.067 | **0.132** |

Paired difference **+0.0655**, bootstrap CI `[0.045, 0.088]`, dz = 1.72, positive
in **11/11 seeds**. Acquisition roughly doubled per unit of time lived. The
selection signal is foraging itself, not longevity.

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

### The intervention was also uninterpretable, and is now scored against a null

Pushing the latent along the decoded energy direction moves the action
distribution by TV = 0.235. Along **12 norm-matched random directions** the mean
is **0.265** — z = **-0.31**. The decoded direction is indistinguishable from a
random one.

That figure therefore carried no information about the direction; it reflected
the size of the push. Which is what should have been expected once the grouped
probe showed the decoded axis does not generalise across lineages: there was no
reason for it to be a meaningful direction in the first place.

This is the third correction to a number reported in this file. The earlier
values were 0.047 (comparing single sampled actions, which at a softmax
temperature of 0.35 is mostly sampling noise), then 0.292 (comparing
distributions, but against no null). `intervention_with_null` now reports the
null distribution and the z-score alongside every intervention.

The standing conclusion is unchanged and better supported at each correction:
**information present is not information used** — and before that, *decodable*
must mean decodable across lineages, and *moved by a direction* must mean moved
more than by a random one.


---

## Instruments added since the last review

Three measurements that did not previously exist, all verified to run but none
yet producing a recorded multi-seed result.

### Body contingency (`scripts/run_contingency.py`)

Same world, same position, same everything — except the organism's sensed body
temperature, cold versus hot. If the channel is used, the two action
distributions must differ. Reported as `tv_body` against `tv_null`, a
magnitude-matched displacement of the *age* channel, because any large enough
input change moves a softmax policy and a bare TV means nothing.

### Sensor dissociation

Three arms sharing a world, a start position and a frozen controller:
veridical-cold, veridical-hot, and dissociated (physically hot, sensed cold).

A structural note that shapes the design: sensed temperature is the only route
body temperature takes into an observation, so on the first step the dissociated
arm's observation is *identical* to veridical-cold's. The separation is entirely
dynamic. And the dissociated arm is a **third trajectory, not a hybrid** — its
physics are the hot arm's and its actions are the cold arm's, so it visits cells
neither of the others visits and in smoke tests ended in better condition than
both. `follows_sensed_margin` is the endpoint; the integrity figures are context.

### Homeostasis decomposed

`thermoregulation_index` was renamed to `thermal_decoupling_advantage`, because
it scored **zero** for an organism that senses it is too hot, walks to a mild
cell and stays there — body and ambient both in band, difference zero — which is
textbook behavioural thermoregulation. The missing half is now measured:

```
thermal_decoupling_advantage = P(body in band)     - P(ambient occupied in band)
microenvironment_selection   = P(ambient occupied) - P(field in band)
------------------------------------------------------------------------------
homeostatic_advantage        = P(body in band)     - P(field in band)
```

The field baseline is the fraction of the whole world in band, which is what a
walker that does not select its microenvironment experiences on a torus.

First reading, seed 3: field 0.700, occupied 0.580, so
`microenvironment_selection = -0.121`. Organisms occupy cells **worse** than the
world average. That is an independent confirmation of the frozen assay: they go
where the food is, and the food is in the thermally hostile zones.
