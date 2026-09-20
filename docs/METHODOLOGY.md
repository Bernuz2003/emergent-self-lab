# Methodology and Measurement

## Primary rule

Never infer consciousness directly from task success. State exactly what was measured.

## Choosing an endpoint

An endpoint conditioned on survival measures survival. This is not a hypothetical
failure: the first version of this package used "fraction of living organisms
currently inside the viable temperature band", and a uniformly random controller
scored as high as evolved populations on it, because organisms that leave the
band die and whoever is left is in band by construction.

The replacement compares an organism against its own circumstances:

    thermoregulation_index = P(body in band) - P(ambient at the occupied cell in band)

pooled over *every agent-step that ever occurred*, including the steps of
organisms that later died, and weighted by exposure so a long-lived organism does
not count the same as a one-step one.

**Missing data is NaN, never zero.** A late window that contains no organism is
an absence of measurement, not a measurement of zero. Coercing it to zero once
manufactured this project's headline result: 11 of 12 random-controller runs
reported an invented `0.0000` and produced a spurious Hedges g of -0.92. Every
statistic drops non-finite values and reports how many seeds actually
contributed.

**Persistence and regulation are separate endpoint families.** "This population
continued to exist" and "this population regulated its body temperature" are
different claims. Merging them is how an ecological result gets reported as a
homeostatic one.

**Windows are absolute.** "The last 25% of logged rows" covers a different
stretch of time for a run that died at step 1200 than for one that reached 6000.
Windows are defined against the preregistered run length.

**Name an endpoint for what it measures.** `thermoregulation_index` scored zero
for an organism that senses it is too hot, walks to a mild cell and stays there —
body and ambient both in band — which is textbook behavioural thermoregulation.
It measured thermal *decoupling* from the occupied cell, and is now named that.
The complementary half, choosing where to stand, is `microenvironment_selection`,
and the two sum to `homeostatic_advantage`.

**Every intervention needs a magnitude-matched null.** Any large enough push to a
hidden state moves a softmax policy, and any change to an input moves it too. A
total variation of 0.29 along a decoded direction looked like evidence until it
was compared with norm-matched random directions, which gave 0.27 — z = -0.31.
Report the null alongside the effect or do not report the effect.

**Ablate the channel the hypothesis is about.** Replacing the whole interoceptive
vector answers "do you know your own body", not "do you know your own
temperature". With energy acquisition the dominant selection pressure here, the
two are materially different experiments. `sensors.interoception_channels` names
which channels an ablation touches.

**Read the simple effects before believing an interaction.** E1's preregistered
interaction passed while being carried by true interoception performing *worse*
than shuffled when ambient was available — the opposite of the claimed mechanism.
A decision rule should require the simple effect to point the right way too.

**No endpoint here has a meaningful absolute zero.** Thermal inertia lets any body
linger in band after entering a hostile cell, and in cold regions the metabolic
heat of motion warms a body toward the band for free. Both give a random
controller a non-zero score. Every experiment config therefore declares a
`floor_condition`, and conditions are read against that floor measured in the
same worlds under the same calibration — never against zero.

Before interpreting a null, rule out two things that produce one for reasons
unrelated to the hypothesis:

- **Redundancy.** If the exteroceptive channel already predicts the body variable
  being ablated, no ablation can have an effect. `scripts/diagnose_redundancy.py`.
- **Extinction.** Extinct runs carry no information about the manipulated
  variable and simply destroy power. `scripts/calibrate.py`.

## Core metrics

### Viability
- lifespan distribution;
- fraction of time internal variables remain inside viable ranges;
- recovery time after perturbation;
- population persistence.

### Evolution
- reproductive events per lineage;
- lineage diversity;
- mutation distance;
- population turnover.

### Anticipation
- delayed-cost avoidance;
- immediate-resource sacrifice for future viability;
- calibration of predicted future body state.

### Self/world representation
- post-hoc probe accuracy for body vs world variables, **held out across
  lineages**: samples within an organism are autocorrelated and a lineage shares
  a controller up to mutation, so a split over observations reports lineage
  identity rather than a shared code. Every apparent decode in this project
  collapsed below chance once lineages were held out;
- invariance across visual changes;
- sensitivity to causal body mapping;
- causal effect of latent intervention on behavior.

## Measure frozen, not mid-flight

Any endpoint taken *during* evolution is taken on a moving population. Organisms
are being born, dying, mutating and competing while the measurement happens, so
the number mixes the controller's behaviour with the density it lived at, the
lineage that happened to win, and survivorship. "Did the controller get better?"
is not really answerable from it.

Separate the phases:

    EVOLUTION  ->  snapshot controllers at checkpoints  ->  FROZEN ASSAY

In the assay there is no mutation, no reproduction and no selection. One
controller at a time is placed alone in a standardised world, across a fixed set
of assay seeds identical for every controller. Differences between controllers
are then differences between controllers, and the ancestral cohort at step 0 is
the comparison that gives any later number meaning.

`src/emergent_self/assay.py`, driven by `scripts/run_assay.py`. Contrasts are
paired within evolution seed, since a seed fixes the world the lineage evolved in.

This is not optional polish. Run live, E1 suggested that thermoregulation had
evolved. Run frozen against its own ancestors, the same evolution turned out to
have selected for foraging while thermoregulation got slightly *worse* and
integrity got significantly worse.

## Required controls

For each major experiment use: random controller; reactive capacity-matched
controller; shuffled interoception; true interoception; and, where applicable,
memory-state permutation or predictive-head ablation.

`shuffled` interoception is not a fully neutral control and should not be the
only one. It borrows a reading from a *currently living* organism, so it removes
the self signal but introduces a **population signal**: another body encodes the
present density, ecological phase and ambient regime. That is a live candidate
explanation for shuffled outperforming true interoception in E1 and E1b. The
`independent` mode draws each channel from an empirical marginal accumulated over
the run, decoupling it from the current population state as well, at the cost of
no longer preserving the joint distribution across channels. Run both.

Shuffled interoception must be a **derangement** of body readings across the
living population, not an independently drawn donor per organism. An independent
draw leaves each organism a 1/n chance of receiving its own reading, which
restores true interoception for part of the population and becomes the typical
case exactly as a population dies back. A derangement preserves the marginal
distribution exactly and guarantees no organism sees itself.

Do not compare a larger recurrent network against a smaller feed-forward network and attribute differences solely to memory.

## Statistics

Predefine primary endpoints before large sweeps. Every experiment config carries
a `preregistration` block naming the hypothesis, the null, the manipulated
variable, the primary endpoint, the capacity control, and the decision rule —
written before the sweep runs, and shipped in the same file that runs it.

`scripts/analyze.py` applies the recorded decision rule mechanically and prints
its verdict, so the rule cannot be adjusted after seeing the numbers. Report distributions across seeds, effect sizes and uncertainty, not only best runs. Preserve failed evolutionary histories. `docs/RESULTS.md` records every
completed experiment, nulls included, with the config digest and seed list
needed to reproduce it.

## Interpretation vocabulary

Preferred: `homeostatic behavior`, `anticipatory regulation`, `termination avoidance`, `self-related representation`, `causal self/world distinction`.

Avoid without extraordinary evidence: `wants`, `feels`, `fears`, `is conscious`, `knows it exists`.
