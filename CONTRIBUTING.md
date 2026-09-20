# Contributing

Keep world physics, body physics, sensors, controllers, evolution and analysis
separate. Analysis must never influence a scored run; an intervention is the
exception and must be declared in the config's `interventions` block.

## Before you run an experiment

1. `pytest` — invariants must pass.
2. `python scripts/validate_e0.py` — the validity gate. Nothing downstream is
   interpretable until all five checks pass.
3. If you changed any body or world constant, `python scripts/calibrate.py` and
   `python scripts/diagnose_redundancy.py`. A configuration where many seeds go
   extinct early, or where the exteroceptive channel already predicts the
   variable you are ablating, will produce an uninformative null.
4. If you are comparing architectures, `python scripts/capacity_match.py`.
5. Watch one run before trusting any number: `python scripts/visualize.py --seed 4`.
   Degenerate strategies are obvious on screen and invisible in a mean.

## Measure frozen wherever you can

Anything measured during evolution is measured on a moving population and mixes
the controller's behaviour with density, lineage luck and survivorship. Prefer
`scripts/run_assay.py`: snapshot controllers at checkpoints, then evaluate them
alone in standardised worlds against the ancestral cohort. This has already
overturned one result.

## Statistics rules that are not negotiable

- **Missing data is NaN.** Never let an empty window score as zero; report how
  many seeds contributed to every contrast.
- **Windows are absolute**, defined against the preregistered run length, not
  against however many rows a dying run happened to log.
- **Persistence and regulation are separate endpoints.** Do not merge them.
- **Pair contrasts by seed** where the design allows it; a seed fixes the world.
- **Probes hold out lineages**, not observations.
- **Interventions are scored against a magnitude-matched null.** Any big enough
  push moves a softmax policy; report the null or report nothing.
- **Ablate the channel the hypothesis names**, via
  `sensors.interoception_channels`, not the whole body vector.
- **Check the simple effects before believing an interaction.** One has already
  passed its rule while running the opposite way to its claimed mechanism.
- **Commit before running.** Results record the commit and a `dirty_worktree`
  flag; a dirty result cannot be traced to any revision.

## A new experiment needs

A config under `configs/` with a `preregistration` block written *before* the
sweep runs, naming: hypothesis, null hypothesis, manipulated variable, primary
endpoint and its definition, reference condition, floor condition, capacity
control, decision rule, required seeds, and the explicit limit on
interpretation. `scripts/analyze.py` applies the decision rule mechanically, so
it cannot be adjusted after seeing the numbers.

Write the outcome into `docs/RESULTS.md` whether it is positive or null.

## Naming

Prefer an operational term over an anthropomorphic one wherever one exists:
`homeostatic behavior`, `anticipatory regulation`, `termination avoidance`,
`self-related representation`, `causal self/world distinction`.

Avoid `wants`, `feels`, `fears`, `is conscious`, `knows it exists` — in code,
comments, commit messages and write-ups alike.
