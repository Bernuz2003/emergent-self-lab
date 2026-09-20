# Emergent Self Lab

**An experimental artificial-life framework for studying the emergence of homeostasis, self-preservation, self/world models, temporal continuity, and other functional precursors associated with consciousness.**

> This project does **not** assume that consciousness is equivalent to intelligence, language, self-report, or survival behavior. Its goal is narrower and experimentally testable: construct minimal artificial worlds in which candidate functional prerequisites can emerge without being directly scripted, then measure and perturb them.

## Core research question

**Under what environmental and architectural conditions do homeostasis, anticipatory self-preservation, self/world distinction, temporal self-continuity, and self-modeling emerge when they are not explicitly programmed as semantic goals?**

The central methodological principle is to behave less like a chatbot designer and more like an evolutionary mechanism: specify local physics, heredity, variation, resource constraints, embodiment and causal consequences; avoid telling agents that they should "survive", "fear death", or "have a self".

## Why this repository exists

A language model can easily produce sentences such as *"I do not want to die"*. Such reports are deeply confounded by linguistic training data. This project therefore begins with **non-linguistic agents**, simple neural controllers and artificial bodies. Language is deliberately postponed.

The initial research ladder is:

`physics → embodiment → interoception → homeostasis → memory → prediction → self-model → novel-threat generalization`

None of these steps, individually or jointly, establishes phenomenal consciousness. They provide operational phenomena that can be measured scientifically.

## Design principles

1. **No consciousness labels during training.** Agents are never trained to claim consciousness.
2. **No direct survival reward.** There is no reward function at all. A controller emits an action distribution; physics does the rest. Death is the absence of subsequent dynamics, not `reward = -100`.
3. **Ecological selection rather than global ranking.** Reproduction happens locally when physical conditions permit. No omniscient fitness selector exists anywhere in the code.
4. **Body state is real simulator state.** Energy, integrity and temperature exist whether or not an agent can sense them.
5. **Interoception is experimental.** Access to body state is a manipulable variable, not an assumption.
6. **Ablations before interpretation.** Every claimed capability must survive matched controls.
7. **Novel threats matter.** Avoiding a hard-coded hazard is less informative than generalizing to a causally novel termination mechanism.
8. **Behavior is not phenomenology.** Results are functional properties, not proof of subjective experience.

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate          # fish: source .venv/bin/activate.fish
pip install -e ".[dev,viz]"

pytest                                            # 92 invariant tests
python scripts/validate_e0.py                     # simulator validity gate
python scripts/visualize.py --seed 4              # watch a run
python scripts/run_assay.py --n-seeds 12          # what did evolution select for?
```

`validate_e0.py` is a gate, not a demo. Nothing downstream is interpretable until
it passes. See [Workflow](#workflow) for the full loop.

## What the simulator actually does

A torus grid carries a static ambient temperature field of hot and cold blobs.
Resource density is deliberately highest where ambient temperature is most
hostile, so the richest foraging is the most dangerous and "eat as much as
possible" is not a winning strategy.

Each organism has a body the simulator owns:

- **energy** — drained by basal metabolism and by motion, restored by resources;
- **temperature** — relaxes toward the ambient of the occupied cell, and rises with the metabolic heat of motion;
- **integrity** — damaged while temperature sits outside the viable band, repaired metabolically at an energy cost, eroded by senescence;
- **age**.

An organism ends when energy or integrity reaches zero. It reproduces when local
physical conditions allow: enough energy, enough integrity to gestate, maturity,
a refractory period, and room nearby. Nothing ranks organisms against each other.

Observations are assembled declaratively from channels — a local resource patch,
a local ambient-temperature patch, proprioception, and interoception — and
**every channel can be ablated without changing the observation's width**, so
controller input capacity is matched across conditions by construction.

## Two phases

Any endpoint measured *during* evolution is measured on a moving population:
organisms are being born, dying, mutating and competing while the measurement
happens. "Did the controller get better?" is not answerable from such a number.

```
EVOLUTION  ->  snapshot controllers at checkpoints  ->  FROZEN ASSAY
```

In the assay there is no mutation, no reproduction and no selection. One
controller at a time, alone, in standardised worlds identical for every
controller, with the ancestral cohort at step 0 as the baseline.

This is not polish. Measured live, E1 suggested thermoregulation had evolved.
Measured frozen against its own ancestors, the same evolution had selected for
foraging, while thermoregulation got slightly worse and bodily integrity got
significantly worse.

## Workflow

```
scripts/validate_e0.py         gate: determinism, energy accounting, stream
                               separation, neutral baseline, ablation leakage

scripts/diagnose_redundancy.py is interoception even informative here? a null
                               under high redundancy says nothing about
                               interoception

scripts/calibrate.py           sweep world constants for extinction rate before
                               spending seeds on an experiment

scripts/capacity_match.py      pick a hidden width so two architectures have
                               equal parameter counts

scripts/run_experiment.py      run a preregistered multi-condition sweep
scripts/analyze.py             distributions, bootstrap CIs, effect sizes,
                               and the preregistered decision rule

scripts/run_assay.py           evolve, snapshot, then evaluate frozen against
                               the ancestral cohort, paired within seed
scripts/run_contingency.py     does an evolved controller act on its own body?
                               same world, different body; then falsify the
                               sensor and see which one the actions follow
scripts/run_probes.py          decode body and world variables from latent
                               state across held-out lineages, then intervene
scripts/visualize.py           watch a run live, record it, or replay it
```

## Watching a run

The visualiser is an instrument, not decoration: strategies that are opaque in
the aggregate numbers — patrolling a thermal margin, camping a resource patch,
exploiting metabolic heat in the cold, sitting still — are usually obvious within
seconds.

```bash
python scripts/visualize.py --seed 4                        # live
python scripts/visualize.py --experiment configs/e1_interoception.json \
    --condition A_ambient_and_intero --seed 4               # a specific condition
python scripts/visualize.py --seed 4 --headless --record runs/run.jsonl
python scripts/visualize.py --replay runs/run.jsonl         # no simulator needed
```

Background is the ambient thermal field; agent colour cycles through
temperature, energy, integrity, lineage, age and in-band with `tab`; click an
organism for its body monitor. `space` pauses, arrows step, `+/-` change speed.

`Simulation` knows nothing about any of this. It emits a `SimulationSnapshot`;
renderers and recorders consume one.

## Results so far

`docs/RESULTS.md` records every completed experiment — null results, and
retractions, included.

**What evolution selected for** (frozen assay, 11 usable seeds, paired within
seed). Evolved controllers versus their own ancestors, alone, on identical
ground:

| | diff | 95% CI | seeds won |
|---|---|---|---|
| resources eaten | **+16.5** | [12.1, 21.4] | 11/11 |
| move fraction | **+0.127** | [0.070, 0.189] | 10/11 |
| steps survived | **+28.4** | [4.1, 53.1] | 9/11 |
| final integrity | **-0.064** | [-0.116, -0.013] | 2/11 |
| thermoregulation index | -0.016 | [-0.055, 0.028] | 3/11 |

Selection is strong and its target is **foraging**, not thermoregulation — which
did not improve, and was purchased partly at the cost of bodily integrity.

**The E1 interaction passes its rule but not its mechanism.** A re-run under the
fixed metrics gives interaction `(C-D) - (A-B) = +0.058`, CI `[0.024, 0.086]`,
dz = 1.27 — which the preregistered rule accepts. It should not be read as
support for H2: the interaction is carried by `A - B = -0.039` (true
interoception performing *worse* than shuffled when ambient is available), not by
any benefit when ambient is removed, and the `C - D` term was contaminated by a
since-fixed shared RNG stream. `configs/e1c_temperature_only.json` removes both
problems.

**A retracted claim.** An earlier write-up reported "H1 supported:
thermoregulation evolved", from a random-vs-evolved contrast at Hedges g = -0.92.
That contrast was an artifact: the endpoint scored a *missing* late window as
`0.0`, and random populations die before reaching it, so 11 of 12 random runs
contributed an invented zero. Missing data is now `NaN` and the seed count is
printed beside every contrast. `docs/RESULTS.md` has the full post-mortem.

**Two probe claims, both withdrawn.** Body temperature appeared decodable from a
GRU hidden state at R² ≈ 0.44. Holding out whole *lineages* instead of random
observations, every decode collapses below chance: the code is lineage-specific,
not a shared representation. And pushing the latent along the decoded energy
direction gives TV = 0.235 against **0.265 for norm-matched random directions**,
z = -0.31 — indistinguishable from a random push. Every intervention is now
reported with its null.

## Repository map

- `docs/RESEARCH_PROGRAM.md` — scientific vision, hypotheses H1–H6, roadmap.
- `docs/ARCHITECTURE.md` — layer separation and module responsibilities.
- `docs/METHODOLOGY.md` — controls, endpoints, statistics, interpretation rules.
- `docs/RESULTS.md` — log of completed experiments, nulls included.
- `docs/experiments/E0_E5.md` — staged experiment specifications.
- `src/emergent_self/` — the simulator, controllers, evolution and analysis.
- `configs/` — preregistered experiment definitions.
- `scripts/` — the workflow above.
- `tests/` — physical invariants, sensor invariants, reproducibility guarantees.

## Measuring homeostasis

Homeostasis here has two halves, measured separately and summing exactly:

```
thermal_decoupling_advantage = P(body in band)     - P(ambient occupied in band)
microenvironment_selection   = P(ambient occupied) - P(field in band)
------------------------------------------------------------------------------
homeostatic_advantage        = P(body in band)     - P(field in band)
```

The first is the body resisting the cell it stands in; the second is choosing
which cell to stand in. An organism that walks to a mild spot and stays there
scores zero on the first and high on the second, which is why the first was
renamed from `thermoregulation_index`.

First reading: organisms occupy cells **worse** than the world average
(`microenvironment_selection = -0.12`). They go where the food is, and the food
is in the hostile zones — an independent confirmation of the assay result above.

## Status

`v0.3`. E0 passes (92 tests, 5 validity checks) and every result records the git
commit and dirty flag of the code that produced it.

| | state |
|---|---|
| Frozen assay | recorded result |
| E1 | first result retracted; re-run passes its rule but not its mechanism |
| E1b | runs, underpowered, superseded by E1c |
| E1c | specified, needs calibration then running |
| Body contingency / sensor dissociation | implemented, not yet recorded |
| E2, E4 | configs exist; both blocked on design faults documented in `docs/experiments/E0_E5.md` |
| E3, E5 | specified only |

## License

MIT. See `LICENSE`.
