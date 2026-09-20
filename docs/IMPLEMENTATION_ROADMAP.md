# Emergent Self Lab — Concrete Evolution Roadmap

## Purpose of this document

This document translates the long-term vision of Emergent Self Lab into a sequence of **concrete implementation directions**.

It is deliberately not a low-level code plan.

The implementation agent working on the repository should decide the exact module structure, APIs, classes and internal abstractions. This document defines instead:

- what the simulator should progressively be capable of representing;
- what should be changed or removed from the current conceptual model;
- what scientific capabilities should be added;
- what should remain measurable and controllable;
- how the visualizer should evolve;
- which milestones must be reached before moving to more ambitious stages.

The most important principle is:

> **Do not add complexity because it looks biologically interesting. Add it when it enables a new falsifiable question.**

---

# 1. Immediate objective: establish causal use of internal state

The current project already supports an explicit body, interoception, evolution, perturbations and frozen assays.

The next milestone should be narrow and decisive:

> **Show that an evolved controller causally uses information about its own internal state to select different actions under the same external conditions.**

This must be established before adding memory, complex bodies or self-models.

The clean conceptual assay is:

\[
same\ external\ world
+
different\ internal\ state
\Rightarrow
different\ action\ distribution
\]

Then:

\[
same\ physical\ body
+
different\ sensed\ internal\ state
\Rightarrow
different\ action\ distribution.
\]

The second intervention is especially important because it distinguishes physical consequence from **represented internal state**.

### Near-term requirements

The next experimental generation should therefore support:

- interventions targeting individual interoceptive channels rather than the entire body vector;
- especially **temperature-only**, **energy-only**, and later integrity-only ablations;
- standardized frozen tests using identical controller, environment, position and physical state;
- manipulation of perceived body state independently from real body state;
- direct comparison of action distributions rather than only realized actions;
- short post-intervention rollouts measuring whether the induced choice improves or worsens subsequent viability.

### Interpretation target

A positive result should support a statement such as:

> “The evolved controller uses a representation coupled to its own internal variable when choosing behaviour.”

It should **not** yet be described as self-awareness.

---

# 2. Improve the representation of homeostasis

The project should stop treating homeostasis as one scalar metric.

Two different strategies must be distinguished.

## Internal compensation

The organism remains viable despite occupying an externally hostile environment.

Example:

\[
T_{ambient}\notin viable
\quad \land \quad
T_{body}\in viable.
\]

## Environmental selection

The organism changes its location or behaviour so that the environment itself becomes compatible with its body.

Example:

\[
T_{body}\text{ too high}
\rightarrow
move
\rightarrow
cooler\ region.
\]

Both are legitimate forms of regulation.

Future analysis should explicitly separate:

- regulation produced by body/environment decoupling;
- regulation produced by choosing a suitable microenvironment;
- passive persistence due to thermal inertia;
- regulation induced by movement-generated heat;
- recovery after controlled perturbations.

This will prevent a successful thermoregulatory behaviour from being scored as neutral simply because the organism successfully moved into a thermally safe region.

---

# 3. Build a standardized causal assay framework

Frozen assays should become a general research primitive rather than an experiment-specific utility.

The framework should eventually allow:

> **Evolve once, then ask many controlled questions of the frozen controller.**

A general assay should make it possible to define:

- initial body state;
- initial world state;
- initial position;
- sensor mapping;
- actuator mapping;
- memory reset or preservation;
- perturbation;
- rollout horizon;
- measured outcomes.

The same controller should be evaluated across matched counterfactual conditions.

Conceptually:

\[
Controller
+
InitialState
+
Intervention
\rightarrow
Trajectory.
\]

The framework should make paired counterfactual experiments easy to express.

This capability will later support:

- false-body experiments;
- memory ablations;
- body remapping;
- tool incorporation;
- self/world causal tests;
- novel-threat experiments.

The assay system will become one of the most important scientific components of the repository.

---

# 4. Make every stochastic manipulation causally clean

The simulator should continue moving toward a strict rule:

> **Changing one experimental variable must not silently change any unrelated random sequence.**

Independent randomness should exist for conceptually independent processes.

Examples include:

- world generation;
- resource dynamics;
- reproduction placement;
- mutation;
- action sampling;
- interoceptive shuffling;
- exteroceptive decoys;
- sensor noise;
- external interventions.

The exact implementation is secondary.

The conceptual requirement is that a paired experiment should differ **only in the declared manipulation whenever possible**.

This is critical because the project will rely increasingly on counterfactual comparisons.

---

# 5. Make experiment provenance permanent

Every future result should be self-identifying.

A run should carry enough metadata to answer:

> “Exactly which universe and which implementation produced this trajectory?”

At minimum, the result format should preserve:

- experiment configuration;
- configuration digest;
- source revision / Git commit;
- whether the working tree contained uncommitted modifications;
- package version;
- Python/runtime version;
- seed(s);
- experiment name;
- condition name;
- schema version for stored results.

This becomes increasingly important as the world, visualizer and assay system evolve.

---

# 6. Visualizer v2 — show causes, not just motion

The current live viewer is a good first step.

The next version should focus on **scientific observability** rather than graphical decoration.

## Agent inspection

Selecting an organism should eventually expose:

- true body variables;
- sensed body variables;
- local external observations;
- selected action;
- full action probability distribution;
- recent actions;
- short history of energy, temperature and integrity.

The visualizer must display observations that were actually consumed by the controller during simulation. It should not independently re-query stochastic sensors and thereby change or misrepresent the run.

## Event visualization

Important causal events should remain visible:

- resource consumption;
- birth;
- death;
- perturbation;
- thermal shock;
- later, damage and repair.

## Paired counterfactual mode

This should become a major feature.

Two instances of the same controller are shown side by side with the same initial world and state.

Only one variable differs.

Examples:

- true versus shuffled temperature;
- real versus false sensed temperature;
- memory preserved versus erased;
- intact versus remapped actuator;
- normal versus damaged appendage.

The visualizer should display how the trajectories diverge.

This transforms it from an animation into a **causal microscope**.

---

# 7. E2 should introduce real temporal necessity

Memory should not be added because recurrence is biologically appealing.

It should be introduced only when the environment contains tasks that **cannot be solved from the current observation alone**.

The world should create partial observability deliberately.

Examples:

- a resource cue appears before a later decision point;
- a dangerous region can only be identified from a previous event;
- an internal perturbation must be remembered after its direct sensory evidence disappears;
- routes contain ambiguous junctions whose correct choice depends on prior experience.

The experimental comparison should distinguish:

- reactive controllers;
- capacity-matched recurrent controllers;
- recurrent controllers with memory reset;
- recurrent controllers with memory-state permutation.

The key question:

> **Does persistent internal state become causally necessary for behaviour?**

Only after this should the project claim functional memory.

---

# 8. From memory to personal temporal continuity

Once memory is demonstrably useful, the project should begin distinguishing two kinds of information:

### Generic world memory

> “There was food to the east.”

### Self-related memory

> “When this body was in this state, taking this action caused this future consequence.”

Future tasks should require integrating:

\[
past\ internal\ state
+
past\ action
+
later\ consequence.
\]

This is the beginning of **temporal self-continuity**.

The system should eventually be able to use its own history as a predictive resource.

Again, the project should avoid hard-coding an autobiographical memory object. The environment should make personal history useful and then test what representation emerges.

---

# 9. Prediction should emerge before a self-model

The next architectural step should not be `SelfModel`.

The system should instead be given or evolve a general predictive capability.

It may attempt to predict:

- future observations;
- future internal state;
- effects of actions;
- resource changes;
- other agents.

The project should then ask whether the learned predictive state naturally factorizes into representations corresponding to:

- body;
- world;
- controllable variables;
- uncontrollable variables.

The most important evidence will be causal.

If a latent direction is claimed to encode some variable, the project should test:

1. whether it generalizes across lineages;
2. whether it predicts the variable in held-out contexts;
3. whether intervening on that representation changes the predicted or actual behaviour;
4. whether random norm-matched latent directions produce smaller effects.

Representation analysis must continue to distinguish:

\[
information\ present
\neq
information\ used.
\]

---

# 10. Introduce body-schema perturbations

Before moving to truly evolvable bodies, the existing explicit body can be used for strong self/world experiments.

Useful future manipulations include:

- reverse an actuator;
- rotate directional control;
- change the relationship between motion and heat;
- attach a new controllable effector;
- disable one action channel;
- introduce a controllable external object;
- remap one sensor.

The key question becomes:

> **Does the agent update its behaviour when the causal structure of its own controllable system changes?**

Later, the project can ask whether an external tool becomes incorporated into the functional body schema.

This is one of the cleanest paths toward studying a learned boundary of self.

---

# 11. Introduce a primitive modular body

Only after the current causal foundations are reliable should the project begin replacing the monolithic body.

The first modular body does not need realistic biology.

It should instead consist of a small number of generic units with local properties.

Possible unit capabilities:

- store energy;
- exchange energy;
- sense a local field;
- emit a signal;
- generate movement;
- connect to neighbours;
- take damage;
- repair.

The important change is:

> **The simulator should no longer know that one unit is “an eye” or “a muscle”.**

Function should arise from connection and use.

At this stage the body may still have a predefined topology.

The first goal is simply to make the organism internally modular enough that:

- damage can be local;
- control can be distributed;
- different substructures can have different roles.

---

# 12. Evolve morphology and sensing

The next step is to allow evolution to modify not only controller weights but also the body configuration.

Possible evolutionary degrees of freedom include:

- number of units;
- unit types or continuous unit parameters;
- location of sensors;
- location of effectors;
- connection topology;
- signal pathways;
- energy allocation;
- body geometry.

The project should avoid maximizing morphological complexity directly.

Complex bodies should emerge only when useful.

A key experimental question becomes:

> **What morphology evolves when cognition, movement, sensing and maintenance all have costs?**

---

# 13. Replace direct morphology with development

Directly evolving a complete adult body will eventually become brittle and expensive.

The project should then move toward a developmental encoding.

A genome specifies **rules that construct an organism**.

Possible developmental primitives:

- divide;
- differentiate;
- connect;
- migrate;
- emit local growth signal;
- stop growing;
- alter local plasticity.

The result should be generated through a developmental process before or during early life.

This enables:

- scalable morphology;
- reuse of developmental motifs;
- repair and regrowth;
- developmental plasticity;
- evolutionary innovation through compact programs.

A major long-term goal is:

\[
Genome
\rightarrow
Development
\rightarrow
Body
+
NervousSystem.
\]

---

# 14. Make nervous systems physically expensive

When body and controller co-evolve, cognitive resources should carry costs.

The world should eventually make trade-offs possible between:

- computation;
- movement;
- reproduction;
- repair;
- sensing.

Neural activity may consume energy.

Larger neural structures may require maintenance.

Long-term memory may consume capacity or energy.

The exact physical model should remain simple enough to understand.

The purpose is not biological realism.

The purpose is to ensure that:

> **A larger brain must justify its existence.**

---

# 15. Introduce lifetime plasticity

When the environment becomes sufficiently variable, static inherited policies will become limiting.

The system should then allow controllers to change within one lifetime.

Possible mechanisms may include:

- local plasticity;
- Hebbian-like updates;
- predictive-error-driven updates;
- learned plasticity rules;
- differentiable recurrent adaptation;
- evolution-designed learning parameters.

The important distinction is:

\[
genome = learning\ machinery
\]

not:

\[
genome = complete\ lifetime\ knowledge.
\]

This will create individuals whose experiences matter independently of their lineage.

---

# 16. Persistent ecosystem architecture

Eventually the simulator should stop treating every experiment as an isolated finite episode.

A higher-level persistent-world mode should support:

- continuous time;
- long-lived environmental state;
- many simultaneous lineages;
- population expansion and collapse;
- ecological niches;
- environmental modification;
- long-term evolutionary records.

Experiments can still fork standardized snapshots from this world for controlled assays.

This creates a useful separation:

\[
Open\ World\ Evolution
\rightarrow
Controlled\ Scientific\ Assays.
\]

The evolving world remains messy and open-ended.

Scientific conclusions come from frozen causal tests.

---

# 17. Species and ecological interaction

When multiple lineages become sufficiently differentiated, the simulator should support meaningful interactions among organisms.

No high-level categories such as “predator” or “prey” need to be assigned.

Instead, agents should be able to affect one another through local physical rules.

Possible primitives include:

- transfer energy;
- obstruct movement;
- damage;
- share resources;
- exchange signals;
- attach;
- alter local environment.

Predation, cooperation or parasitism become interpretations of emergent patterns.

This continues the guiding principle:

> **Implement interaction primitives, not ecological roles.**

---

# 18. Emergent communication

Communication should first appear as an abstract, semantically empty channel.

A signal should have:

- finite bandwidth;
- spatial range;
- cost;
- optional noise.

No symbol receives a human-authored meaning.

The project should then test whether:

- signal usage becomes correlated with environmental state;
- receivers modify behaviour appropriately;
- conventions generalize;
- conventions differ among populations;
- new individuals learn them socially.

Later, the visualizer should provide tools for discovering signal semantics automatically by correlating signals with context and consequence.

---

# 19. Social learning and cultural memory

Once communication and observation exist, information should be allowed to pass between individuals without genetic inheritance.

The simulator should support situations where a behaviour can be learned from:

- imitation;
- observation;
- communicated signal;
- following another agent.

The key milestone is:

> **Behaviour survives the individuals that originally discovered it.**

The analytics layer should therefore eventually distinguish:

- genetic inheritance;
- individual learning;
- social learning;
- population-level persistence of information.

This is the beginning of artificial culture.

---

# 20. Sequence models and transformers — but grounded first

Only after grounded memory and prediction exist should larger sequence models be introduced.

The first use should not involve natural language.

A Transformer, state-space model or similar architecture can process the organism's lived sequence:

\[
observation,\ internal\ state,\ action,\ consequence,\ldots
\]

Its role may include:

- compressing long-term history;
- predicting future observations;
- retrieving relevant memories;
- planning;
- representing long-range dependencies.

The important principle is:

> **Train first on artificial experience, not on human stories about experience.**

A model trained this way becomes a cognitive system grounded in the world it actually inhabits.

---

# 21. Later integration of pretrained LLMs

A pretrained LLM should enter only when there is already an artificial organism worth attaching it to.

Possible integration modes:

## Cognitive adapter

The LLM receives a learned compressed representation of the organism's grounded experience rather than raw human prompts.

## Planning layer

The LLM proposes high-level hypotheses or plans that are translated into lower-level actions by grounded systems.

## Cultural interface

An adapter learns to translate between emergent artificial signals and human language.

## Metacognitive layer

The LLM is allowed to reason symbolically about memories and predictive representations that originated in the organism's own experience.

The key design rule:

> **The LLM should augment an existing artificial self, not manufacture one through role-play.**

---

# 22. Visualizer v3 — multi-scale scientific observatory

As the universe becomes richer, the viewer should support multiple scales.

## World scale

Display:

- populations;
- resource flows;
- environmental fields;
- territories;
- migrations;
- lineage clusters.

## Organism scale

Display:

- morphology;
- local damage;
- energetic flow;
- sensor activity;
- actuator activity;
- developmental state.

## Cognitive scale

Display:

- neural activation;
- memory state;
- predictions;
- uncertainty;
- causal latent interventions.

## Subjective scale

Display exactly what the agent currently perceives.

This should be explicitly contrasted with ground truth.

## Evolutionary scale

Display:

- phylogenetic tree;
- lineage birth and extinction;
- behavioural innovations;
- morphology transitions;
- communication conventions.

The user should be able to jump from a population-level event to the exact individuals and ancestors involved.

---

# 23. Replay and universe forking

Recorded simulations should eventually become first-class scientific artifacts.

A saved world state should allow:

- replay;
- pause;
- inspection;
- branch/fork;
- intervention;
- comparison.

A researcher should be able to select a historical point and create:

\[
World_A = original
\]

\[
World_B = same\ state + intervention.
\]

Then run both futures deterministically where possible.

This creates a general infrastructure for causal experimentation across every later stage of the project.

---

# 24. Emergence analytics

As simulations become too large for manual inspection, the project will need tools that search for behavioural change.

They should not label consciousness.

They should flag possible innovations.

Examples:

- sudden change in sensor/action mutual information;
- novel state-dependent policies;
- increased predictive horizon;
- new signal convention;
- appearance of social imitation;
- new morphology;
- rapid lineage expansion;
- new causal sensitivity to a body variable.

These events can create markers on the evolutionary timeline.

The researcher then investigates them using replay and counterfactual assays.

---

# 25. Avoiding the “feature accumulation” trap

At every stage, before adding a feature, ask:

### Is this a law or a solution?

Bad:

> Add a fear module.

Better:

> Create conditions where anticipating damaging future states can become useful.

Bad:

> Add an eye.

Better:

> Provide local photoreceptive sensitivity and allow morphology to exploit it.

Bad:

> Add a self-model.

Better:

> Make prediction of one's own controllable dynamics useful.

Bad:

> Add language.

Better:

> Provide costly signalling and allow conventions to emerge.

Bad:

> Add curiosity.

Better:

> Create environments where information acquisition has long-term adaptive value.

This test should become part of the project's design culture.

---

# 26. Suggested high-level sequence

The following ordering keeps the project scientifically interpretable.

### Near term

**Causal body-state use**

Interoception channel isolation, false-body counterfactuals, clean frozen assays, improved homeostasis metrics, paired visualization.

### Next

**Memory under partial observability**

Demonstrate that internal temporal state is useful and causally necessary.

### Then

**Prediction and temporal self-continuity**

Learn future consequences and identify whether self-related predictive representations emerge.

### Then

**Body-schema plasticity**

Alter sensors, actuators and body mappings; test adaptation and incorporation.

### Then

**Primitive modular embodiment**

Replace the monolithic body with composable local units.

### Then

**Morphological evolution and development**

Allow bodies and nervous systems to be generated rather than fixed.

### Then

**Lifetime plasticity**

Individuals become products of both ancestry and personal experience.

### Then

**Persistent ecology**

Open-ended populations, ecological interaction and niche formation.

### Then

**Social cognition and emergent communication**

Other agents become an important part of the prediction problem.

### Then

**Cultural inheritance**

Information persists outside genomes.

### Then

**Grounded large sequence models**

Transformers or related architectures operate on artificial experience.

### Finally

**Human-language bridge / LLM integration**

Natural language becomes a late cognitive and cultural interface, not the origin of the artificial agent.

---

# 27. What should *not* be prioritized yet

The following additions would currently risk making the project look more sophisticated while reducing interpretability:

- many new organs;
- realistic human physiology;
- emotions represented as named variables;
- pretrained LLM agents inside the current simple grid;
- explicit symbolic “self” tokens;
- hand-built personality;
- complex 3D graphics;
- high-fidelity physics;
- many simultaneous internal variables with no experiment requiring them.

The project should remain minimal enough that each new capacity has a reason to exist.

Complexity should be earned.

---

# 28. Definition of progress

Progress should not be measured by lines of code or number of biological features.

A stage is complete when the project can make a stronger experimentally grounded statement than before.

Examples:

> “The controller reacts to temperature.”

is weaker than:

> “Under identical external observations, manipulating sensed internal temperature causally changes the controller's action distribution.”

which is weaker than:

> “The controller updates a persistent body representation after the body mapping changes and subsequently restores effective control.”

which is weaker than:

> “A self/world distinction emerged in a predictive architecture not explicitly given one.”

The roadmap should always move toward **stronger causal claims with less semantic structure hard-coded by the researcher**.

---

# 29. Long-term implementation destination

The eventual system should contain four interacting layers:

\[
\boxed{
Artificial\ Physics
}
\]

Local energy, matter, signalling and interaction laws.

\[
\boxed{
Artificial\ Life
}
\]

Self-maintaining, evolving, developing bodies.

\[
\boxed{
Artificial\ Cognition
}
\]

Learning, prediction, memory and planning grounded in lived experience.

\[
\boxed{
Artificial\ Culture
}
\]

Communication, social learning and information that persists across individuals.

The visualizer and scientific tooling sit outside these layers as observers.

They provide:

\[
replay
+
intervention
+
counterfactuals
+
lineage\ history
+
representation\ analysis.
\]

That separation is essential.

The universe should run according to its own rules.

The researcher should be able to inspect it deeply without secretly becoming part of those rules.

---

# 30. The next concrete horizon

For the foreseeable implementation work, the project should remain focused on one transition:

\[
\text{embodied reactive organism}
\rightarrow
\text{organism with a causally useful internal self-state}.
\]

Only after this is demonstrated cleanly should the project move to:

\[
\text{self-state}
\rightarrow
\text{self-history}
\rightarrow
\text{self-prediction}.
\]

That sequence provides a disciplined bridge between the current simulator and the much larger long-term vision.

The project does not need to become grand immediately.

It needs to make every small step point toward something grand.
