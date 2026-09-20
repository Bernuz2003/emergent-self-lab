# Roadmap status

Implementation state against `IMPLEMENTATION_ROADMAP.md`. Tracks what exists in
code, not what is planned. `GRAND_VISION.md` and the roadmap are the direction;
this file is the odometer.

Section numbers refer to the roadmap.

---

## Near term (roadmap §26): causal body-state use

| § | Requirement | State |
|---|---|---|
| 1 | Interventions on individual interoceptive channels | **done** — `sensors.interoception_channels`; temperature-only, energy-only, any subset |
| 1 | Standardized frozen tests: identical controller, world, position, physical state | **done** — `assays/runner.py`, one organism, reproduction denied by physics |
| 1 | Perceived body state manipulable independently of real body state | **done** — `FalsifySensor` changes the reading, `SetBody` changes the body |
| 1 | Compare action distributions, not realized actions | **done** — `Controller.action_probs`, `measures.policy_divergence` |
| 1 | Post-intervention rollouts measuring subsequent viability | **done** — `measures.viability_outcome`, `library.viability_after_falsification` |
| 2 | Separate decoupling / microenvironment / passive inertia / recovery | **done** — `measures.homeostasis` decomposes exactly; `vs_passive`; `recovery_time` and `time_to_band` |
| 3 | General assay framework, not experiment-specific utilities | **done** — `assays/` package: spec, runner, measures, library |
| 4 | One manipulation must not shift any unrelated random sequence | **done** — ten streams; a test parametrises over every one |
| 5 | Permanent provenance on every result | **done** — `provenance.py`; git commit, dirty flag, versions; result and recording schema versions |
| 6 | Visualizer v2: sensed vs true, action distribution, events, paired mode | **done** — `viz/paired.py`; the causal microscope |

The near-term block is implemented. What it has **not** yet produced is a
multi-seed recorded result: see "What to run next".

---

## What each assay establishes

Written as the claim it can support, not as the claim one might want.

| Assay | Supports |
|---|---|
| `body_contingency` | the temperature channel is *read* — and more than a magnitude-matched change to a channel with no thermal meaning |
| `sensor_dissociation` | actions follow the *reading* rather than the body |
| `viability_after_falsification` | reading it truthfully *helps* — the step from "used" to "useful" |
| `memory_necessity` | persistent state is load-bearing (a no-op for a reactive controller, which is its own control) |
| `actuator_remap` | how much control a body-schema change costs; the intact baseline for later plasticity work |

Roadmap §28's ladder puts it this way. "The controller reacts to temperature" is
weaker than "manipulating sensed internal temperature causally changes the
action distribution under identical external observations". The three assays
above are what separate those two sentences, plus a third the roadmap implies
but does not name: whether the causal use is *adaptive*.

---

## Next (roadmap §7): memory under partial observability

Blocked on the environment, not the machinery. `memory_necessity` and
capacity-matched controllers already exist; what does not exist is a world where
the current observation is insufficient. Roadmap §7 lists the four shapes:
a cue preceding a decision point, a hazard identifiable only from a past event,
an internal perturbation whose sensory evidence disappears, ambiguous junctions.

The internal-perturbation variant is the cheapest and already half-built:
`interventions.hidden_perturbation_*` displaces body temperature with no external
cue. Making its *evidence* fade — perturbing a variable the organism senses only
intermittently — turns it into a memory task.

## Then (roadmap §9): prediction before a self-model

`analysis/probes.py` already enforces the four evidential requirements §9 lists:
generalize across lineages, predict in held-out contexts, intervene on the
representation, and beat norm-matched random directions. Every claim so far has
failed at least one of them, which is the machinery working.

What is missing is a controller with a predictive head to probe.

## Later stages

§10 body-schema perturbations: partly available now (`RemapActuator`,
`DisableAction`, `AddSensorNoise`). §11 onward — modular bodies, morphology,
development, lifetime plasticity, persistent ecology, communication, culture —
are untouched, correctly, per roadmap §27 and §25: complexity should be earned.

---

## What to run next

Nothing in the near-term block has a recorded multi-seed result yet. In order:

```bash
# 1. calibrate E1c's perturbation: extinction 1-2/12 in the perturbed arms
python scripts/calibrate.py --perturb-prob 0.0 0.01 0.015 0.02 \
    --perturb-mag 0.15 0.20 --steps 4000 --seeds 12
python scripts/diagnose_redundancy.py --seeds 4

# 2. the milestone: does an evolved controller use its own body state?
python scripts/run_contingency.py --n-seeds 8 --steps 6000 --controllers 6 \
    --interoception-channels temperature --out runs/contingency.json

# 3. E1 under the fixed metrics and the closed decoy leak
python scripts/run_experiment.py configs/e1_interoception.json
python scripts/analyze.py runs/E1_interoception

# 4. E1c once calibrated
python scripts/run_experiment.py configs/e1c_temperature_only.json
python scripts/analyze.py runs/E1c_temperature_only
```

Step 2 is the roadmap's §30 horizon. The claim it can support, if
`tv_ratio` rises above 1 from ancestral to evolved with a seed-paired CI
excluding zero, `follows_sensed_margin` stays negative, and `in_band_benefit`
is positive:

> An evolved controller reads a representation of its own internal temperature,
> acts on that representation rather than on the physical value, and is better
> off for doing so.

That is one sentence, it is falsifiable, and none of its terms were programmed
in. It is not self-awareness.
