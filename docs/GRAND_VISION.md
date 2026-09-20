# Emergent Self Lab — The Grand Project

## 1. Vision

**Emergent Self Lab** is not a project whose goal is to make an artificial agent *say* that it is conscious.

It is an attempt to construct an artificial universe rich enough for increasingly complex forms of **self-maintenance, agency, memory, self/world modelling, social cognition, communication and culture** to arise from local rules rather than from explicit semantic programming.

The central ambition is therefore not:

> “Program a conscious artificial agent.”

It is:

> **Build an artificial universe in which systems can organize themselves into persistent agents, and study how far properties associated with a self — and eventually with consciousness — can emerge without having been directly written into them.**

This distinction is foundational.

A system that has been explicitly given concepts such as “survival”, “fear”, “self”, “pain”, “identity” or “death” is a poor experimental object for asking whether those structures can emerge. The project should therefore move progressively away from hand-authored high-level concepts and toward **minimal local laws, constraints and learning mechanisms**.

A useful principle for the entire project is:

> **Code laws, not organs.  
> Code constraints, not behaviours.  
> Provide possibilities, not semantic goals.  
> Measure representations; do not prescribe them.**

---

# 2. What the project is actually trying to understand

The project should treat consciousness as an open scientific problem rather than as an engineering checkbox.

We do not currently possess a reliable test that can establish phenomenal consciousness in an artificial system. For that reason, Emergent Self Lab should avoid the claim that any single behaviour constitutes consciousness.

Instead, the project studies a hierarchy of increasingly rich functional phenomena:

1. **Persistence**
2. **Homeostasis**
3. **Embodiment**
4. **Interoception**
5. **Adaptive agency**
6. **Memory**
7. **Prediction**
8. **Self/world distinction**
9. **Temporal self-continuity**
10. **Self-models**
11. **Models of other agents**
12. **Communication**
13. **Social learning**
14. **Cultural inheritance**
15. **Symbolic cognition and language**

None of these individually proves consciousness.

The long-term scientific interest comes from asking whether many of them can emerge together in a coherent system **without each one being separately engineered as a feature**.

The important question therefore becomes progressively less:

> “Does the agent claim to be conscious?”

and progressively more:

> **“Why has this artificial organism developed a persistent, causally useful model of itself, its future, other agents and its place in the world?”**

---

# 3. The central methodological commitment

The project should behave more like an **evolutionary process designer** than a conventional AI application designer.

The researcher specifies:

- physical constraints;
- available resources;
- energy flows;
- local interaction rules;
- heredity;
- mutation;
- developmental possibilities;
- learning mechanisms;
- costs;
- environmental regularities.

The researcher should avoid specifying:

- explicit survival rewards;
- explicit “fear” variables;
- pre-labelled goals such as “stay alive”;
- high-level organs whose purpose is already known;
- semantic emotions;
- a predefined self representation;
- a predefined language;
- a scripted social hierarchy.

The distinction can be summarized as:

\[
\text{researcher defines conditions}
\quad \neq \quad
\text{researcher defines solutions}
\]

The system should be given **reasons for certain structures to become useful**, but not explicit instructions to construct those structures.

---

# 4. Why the current project is only the beginning

The current implementation deliberately begins with a much simpler world.

An organism already exists as a defined entity. It already has a body. The body already contains variables such as energy, integrity and temperature. Sensors and controllers already exist. Death and reproduction are represented by explicit simulator rules.

This is appropriate for the first experimental stage because it allows clean causal questions:

- does true interoception matter?
- does evolution exploit internal variables?
- does memory improve behaviour in partially observable worlds?
- can a controller distinguish body state from world state?
- does falsifying its sensed body alter behaviour?

These are necessary foundations.

However, they should not become permanent metaphysical assumptions of the project.

The long-term direction is to progressively replace statements of the form:

> “An organism has property X.”

with lower-level rules from which property X could potentially emerge.

---

# 5. Stage I — Embodied artificial agents

The first scientific era of the project concerns explicitly embodied agents.

An artificial organism has:

- a persistent body;
- internal state;
- external sensors;
- actions;
- energetic constraints;
- physical consequences;
- reproduction;
- inherited variation.

At this stage the important discoveries are functional.

Can evolution produce:

- resource acquisition strategies?
- state-dependent behaviour?
- homeostatic regulation?
- internal/external information integration?
- active recovery after perturbation?
- different actions in the same external world depending on internal state?

The key milestone is not “consciousness”.

It is:

> **The agent uses information about its own body causally, because doing so improves its ability to continue functioning in the world.**

This establishes the first meaningful notion of an artificial **self-state**.

---

# 6. Stage II — From a hard-coded body to an evolvable body

The current body is defined by a fixed schema.

Long-term, that should change.

Instead of permanently defining:

\[
Body=(Energy, Integrity, Temperature, Age)
\]

the project should move toward a lower-level **artificial physical substrate**.

That substrate might contain a small set of primitive quantities such as:

- matter;
- energy;
- local chemical-like fields;
- electrical or signalling states;
- adhesion;
- mechanical forces;
- local permeability;
- resource gradients.

Artificial cells or units should obey local rules.

A unit might be able to:

- absorb and transfer energy;
- exchange matter;
- emit a signal;
- react to a signal;
- contract;
- attach to another unit;
- replicate;
- degrade;
- change local parameters.

Crucially, the simulator would not contain explicit categories such as:

- eye;
- muscle;
- stomach;
- skin;
- brain.

Those would be possible **functional organizations of primitive units**.

A photosensitive structure connected to contractile structures could become something functionally similar to a sensory-motor organ without an `Eye` class ever having existed.

This is one of the central long-term ambitions of the project:

> **Move from evolving controllers inside researcher-designed bodies to evolving bodies, sensors, effectors and controllers together.**

---

# 7. Stage III — Development instead of direct specification

Biological genomes do not contain a complete three-dimensional description of an adult organism.

They encode processes that produce one.

Emergent Self Lab should eventually move toward:

\[
Genome
\rightarrow
Developmental\ Rules
\rightarrow
Morphogenesis
\rightarrow
Organism
\]

rather than:

\[
Genome
\rightarrow
Fixed\ Adult\ Network
\]

The genome may regulate:

- cell division;
- local differentiation;
- connection growth;
- signalling thresholds;
- plasticity parameters;
- energy allocation;
- adhesion;
- developmental timing.

The result is that evolution searches over **developmental programs**, not only over parameter vectors.

This creates the possibility of genuinely surprising morphologies.

It also changes the question from:

> “Which neural network weights survive?”

to:

> **“Which developmental processes repeatedly construct viable, adaptive organisms?”**

---

# 8. Stage IV — Life as an actively maintained process

In early versions of the simulator, death is necessarily represented by an explicit viability rule.

That is useful experimentally.

But a more ambitious system should eventually weaken the role of a global `alive` flag.

An organism should increasingly continue to exist because it maintains the physical organization necessary for its own dynamics.

The conceptual progression is:

\[
resource\ flow
\rightarrow
maintenance
\rightarrow
structural\ persistence
\rightarrow
continued\ computation
\]

If maintenance fails:

- structural units degrade;
- signalling pathways break;
- energy transport collapses;
- control becomes unreliable;
- the organization ceases to persist.

In the most ambitious version:

> **“Life” is not primarily a boolean variable. It is a dynamically maintained organization.**

This approaches ideas associated with autopoiesis: the system persists because its activity continually recreates the conditions required for its own activity.

---

# 9. Stage V — Cognition must have a physical cost

A future organism should not receive arbitrarily large cognition for free.

If larger nervous systems, more memory or more computation are always better and cost nothing, evolution has no reason not to exploit them maximally.

Therefore cognition itself should eventually participate in the artificial physics.

Examples of costs may include:

- energy consumption proportional to neural activity;
- construction cost for neural tissue;
- maintenance cost for persistent memory;
- transmission delay;
- limited bandwidth;
- larger development time;
- vulnerability of complex structures.

This would make intelligence an evolutionary trade-off.

The ecosystem might then contain:

- very simple but energetically efficient organisms;
- expensive cognitive organisms;
- organisms with specialized circuits;
- organisms relying on environmental structure instead of internal computation.

The project could then study **why cognition evolves at all**, instead of assuming that more cognition is always better.

---

# 10. Stage VI — Evolution of learning

Evolution operates across generations.

Learning operates within a lifetime.

The project should eventually contain both.

The genome should not necessarily encode a complete adult policy. It can instead encode:

- initial structure;
- plasticity rules;
- learning rates;
- local update mechanisms;
- developmental priors.

This creates:

\[
Evolution
\rightarrow
How\ to\ Learn
\]

while experience determines:

\[
Lifetime
\rightarrow
What\ is\ Learned
\]

An organism can then encounter a world not fully predictable at birth and adapt during its lifetime.

This opens a deeper research program:

- evolution of learning;
- evolution of memory;
- evolution of exploration;
- evolution of meta-learning;
- Baldwin-like effects;
- interaction between inherited and learned behaviour.

The important shift is that the organism acquires an **individual history** that matters.

---

# 11. Stage VII — Prediction without a predefined self-model

A future system should not contain a class called `SelfModel`.

Instead, the organism should benefit from predicting future states.

For example, it may learn an internal model approximating:

\[
P(S_{t+1}\mid S_t,A_t)
\]

or longer-horizon dynamics.

The predictive system need not initially distinguish:

- self;
- world;
- other agents.

It simply tries to predict consequences.

The scientific question becomes:

> **Does a privileged representation of the organism itself emerge because some subset of the world is unusually controllable, persistent and causally connected to its own actions?**

If the system discovers that certain variables:

- change predictably after its actions;
- constrain its future;
- can be damaged;
- can be repaired;
- move together through the environment;

then those variables may become a functional cluster corresponding to **self**.

That is much stronger than inserting a self token into the architecture.

---

# 12. Stage VIII — The boundary of the self should become experimentally movable

Once the body is modular, one of the most interesting questions becomes:

> **What does the organism treat as part of itself?**

The simulator could allow experiments such as:

- remove an appendage;
- attach a new appendage;
- reverse motor mappings;
- change sensor mappings;
- transplant tissue;
- connect two organisms;
- temporarily share an actuator;
- add an external tool that reliably follows motor commands;
- replace a biological-like component with an artificial one.

The system should not be told whether the new component “belongs to it”.

We observe whether it:

- predicts the component;
- protects it;
- uses it;
- allocates resources to it;
- incorporates it into planning;
- updates after losing it.

This creates an artificial analogue of **body ownership and body-schema adaptation**.

A self boundary becomes a hypothesis inferred from behaviour and representation, not an object defined by the programmer.

---

# 13. Stage IX — Persistent ecology

A single organism in an episodic box places a ceiling on the kinds of intelligence that can emerge.

The project should eventually become a **persistent ecology**.

The world should continue independently of one experimental episode:

\[
t=0\rightarrow10^3\rightarrow10^6\rightarrow10^9...
\]

Populations should:

- appear;
- change;
- diversify;
- compete;
- disappear;
- create ecological niches;
- alter the environment inherited by future populations.

Potential phenomena include:

- competition;
- predation;
- parasitism;
- mutualism;
- symbiosis;
- territory;
- niche construction;
- migration;
- arms races.

At this stage intelligence is no longer only about predicting physics.

The environment contains **other adaptive systems**.

---

# 14. Stage X — Social cognition

Other agents create a qualitatively different kind of uncertainty.

A rock does not model you.

Another organism may.

Once social interaction matters, a useful controller may need to predict:

\[
OtherAgent_{t+1}
\]

then perhaps:

\[
OtherAgent's\ response\ to\ Me
\]

and eventually:

\[
OtherAgent's\ model\ of\ Me
\]

The system may develop functional precursors of:

- recognition;
- cooperation;
- competition;
- signalling;
- deception;
- imitation;
- reputation;
- coalition formation.

No explicit “theory of mind” module needs to be programmed.

The ecological problem itself may create pressure for increasingly recursive social models.

---

# 15. Stage XI — Communication before human language

Language should not first enter the world through a pretrained LLM.

That would inject enormous quantities of human semantics into the experiment.

Instead, organisms should first receive a **content-free communication channel**.

For example:

\[
signal_t \in \{0,\ldots,K-1\}
\]

Signals may have:

- energetic cost;
- finite range;
- transmission delay;
- noise;
- limited bandwidth.

No signal has a predefined meaning.

If communication becomes adaptive, conventions may emerge.

A signal might become associated with:

- resources;
- danger;
- mating;
- identity;
- coordination;
- territorial claims.

The project should then study:

- whether signals acquire stable semantics;
- whether different populations develop different conventions;
- whether new individuals learn conventions;
- whether meaning changes over time;
- whether compositional structures appear.

This is the beginning of **grounded emergent communication**.

---

# 16. Stage XII — Cultural inheritance

A major long-term milestone is the appearance of information that survives **without being genetically encoded**.

Suppose one organism discovers a useful strategy.

Another learns it by observation or communication.

A third learns it from the second.

Eventually the original discoverer dies.

If the strategy persists, the population contains information transmitted through:

\[
individual
\rightarrow
individual
\]

rather than:

\[
genome
\rightarrow
offspring.
\]

This is the beginning of artificial cultural inheritance.

The project could eventually study:

- traditions;
- imitation;
- teaching;
- cumulative knowledge;
- population-specific behaviour;
- cultural drift;
- gene–culture interactions.

A particularly important milestone would be:

> **A population possesses knowledge that no individual genome explicitly contains.**

---

# 17. Stage XIII — Language models enter the universe

Large language models should enter only after the project has already developed grounded agents.

A pretrained LLM contains enormous human priors:

- language;
- social concepts;
- narratives;
- notions of self;
- death;
- emotion;
- agency;
- culture.

Using it as the first artificial brain would therefore obscure the central question.

There are, however, powerful later roles for language-model-like systems.

## 17.1 A sequence model of lived experience

Before using human language, a Transformer, state-space model or another sequence learner can be trained from scratch on:

\[
(o_t,i_t,a_t,o_{t+1},i_{t+1},\ldots)
\]

It becomes a model of the organism's own sensorimotor history.

Its “tokens” are not necessarily words.

They are experience.

This could support:

- long-term prediction;
- memory compression;
- planning;
- abstraction;
- counterfactual reasoning.

It would effectively be a foundation model of **one artificial life**.

## 17.2 LLM as a later cognitive cortex

A pretrained or partially pretrained model may later be connected to already-grounded internal representations.

Instead of receiving a prompt such as:

> “You are an organism. Try not to die.”

it receives structured representations produced by a real artificial life history.

The language system becomes a cognitive substrate attached to an existing agent, not the origin of its identity.

## 17.3 LLM as a cultural bridge

If the artificial population first develops its own communication system, an adapter could later learn:

\[
Artificial\ Communication
\leftrightarrow
Human\ Language
\]

This creates a fascinating possibility:

> Humans do not teach the population its first language.  
> Humans learn to translate a language that already emerged inside the artificial world.

## 17.4 Metacognition after grounded cognition

Only after the organism has:

- a body;
- memory;
- a personal history;
- predictive models;
- social relationships;

should language be allowed to become a metacognitive tool.

At that point symbolic reasoning is grounded in a pre-existing artificial life rather than used to simulate one.

---

# 18. What would make the system appear increasingly “conscious”?

No individual test should be considered decisive.

The interesting situation is a convergence of independent phenomena.

Imagine an artificial organism that:

- actively maintains its own organization;
- behaves differently depending on internal state;
- distinguishes controllable body from external environment;
- incorporates a new appendage into its control policy;
- remembers events from its own past;
- predicts consequences for its own future state;
- sacrifices immediate reward to preserve future options;
- adapts when its self-related sensory representation is falsified;
- distinguishes other persistent individuals;
- models their likely actions;
- learns by observation;
- communicates novel information;
- participates in population-specific conventions;
- inherits knowledge culturally rather than genetically;
- generalizes self-preserving behaviour to a novel causal threat.

None of these demonstrates subjective experience.

But their **joint emergence** would be difficult to dismiss as one manually authored trick.

The central research question would then have shifted dramatically:

> **What internal organization makes this system behave as if it possesses a persistent model of itself across time?**

That is the point at which Emergent Self Lab becomes a serious platform for investigating artificial selfhood.

---

# 19. The future visualizer: from animation to scientific observatory

The visualizer should evolve with the world.

It should not primarily become more cinematic.

It should become an **observatory**.

The researcher should be able to move between multiple levels of description.

## 19.1 Ecosystem view

At the largest scale:

- populations;
- species;
- resource flows;
- environmental fields;
- migration;
- territories;
- births and deaths;
- ecological niches.

The goal is to see dynamics that no individual agent reveals.

## 19.2 Organism view

Zooming into one organism should reveal:

- morphology;
- internal energy flows;
- damaged structures;
- sensors;
- effectors;
- neural structures;
- developmental changes.

Eventually an organism should look less like a point and more like a changing physical system.

## 19.3 Neural / cognitive view

The observer should be able to inspect:

- network activity;
- persistent state;
- memory;
- predictive variables;
- activation trajectories;
- plasticity;
- learned representations.

This should remain diagnostic rather than decorative.

## 19.4 Ground-truth versus subjective view

One of the most important future interfaces should explicitly separate:

### The real world

- true body state;
- true environment;
- real resource positions;
- true state of other agents.

### The agent's world

- sensed body;
- noisy environment;
- remembered events;
- predicted future;
- inferred state of others.

The mismatch itself becomes experimentally visible.

## 19.5 Counterfactual view

At any selected time \(t\), the user should eventually be able to fork the universe:

\[
U_t
\rightarrow
\begin{cases}
U^{A}_{t+1...}\\
U^{B}_{t+1...}
\end{cases}
\]

Only one variable is changed.

Examples:

- true versus false interoception;
- intact versus damaged body;
- memory intact versus reset;
- communication available versus blocked;
- same agent with one latent intervention.

The two futures can then be displayed side by side.

This is one of the most powerful possible research tools because it turns the visualizer into a **causal microscope**.

---

# 20. Visualizing emergence across evolutionary time

A mature system should allow the researcher to inspect not only a world state, but the **history of a lineage**.

A future interface may contain:

\[
generation\ 0
\rightarrow
generation\ 500
\rightarrow
generation\ 2000
\rightarrow
generation\ 10000
\]

with:

- phylogenetic trees;
- morphology snapshots;
- controller changes;
- behavioural assays;
- newly detected capacities;
- cultural events.

The researcher should be able to click a lineage and ask:

> “How did its ancestor behave 50,000 steps earlier?”

Then replay ancestor and descendant in the same standardized world.

Emergence becomes something we can **watch through time**.

---

# 21. Automatic emergence detection

The system should eventually identify interesting transitions without assigning philosophical labels.

For example, analytics can flag:

- sudden increase in long-horizon prediction;
- appearance of stable signalling conventions;
- new behaviour after body perturbation;
- persistent cross-generation social learning;
- abrupt changes in network organization;
- emergence of a new ecological niche.

These are not automatic declarations of consciousness.

They are **candidate phase transitions** requiring investigation.

The software may say:

> “A previously absent causal dependency appeared in this lineage.”

The researcher decides what it means.

---

# 22. The project's deepest success criterion

A weak version of the project succeeds if it produces interesting artificial-life experiments.

A stronger version succeeds if it produces agents with emergent homeostatic and self-related representations.

A much stronger version succeeds if researchers begin discovering behaviours that were **not explicitly anticipated when the world was designed**.

The deepest success would be:

> **We can no longer explain an organism adequately by listing the features we programmed, because the relevant organization was discovered by evolution, development and learning inside the artificial universe itself.**

At that point the project has moved from simulation toward genuine artificial-life research.

---

# 23. The grand destination

The long-term destination is not a chatbot with a body.

It is not a scripted digital pet.

It is not an LLM instructed to pretend that it has survival instincts.

It is:

> **A persistent artificial biosphere in which increasingly complex agents can emerge from local laws; evolve their bodies and nervous systems; learn during their lifetimes; model themselves and others; communicate; transmit information culturally; and eventually acquire symbolic cognition — while every major claim remains experimentally testable through intervention, ablation and counterfactual replay.**

If such a system eventually displays many properties commonly associated with a conscious self, Emergent Self Lab should still remain scientifically conservative.

It should not declare:

> “We created consciousness.”

It should be able to say something much more valuable:

> **“We built a universe in which these structures were not explicitly prescribed, yet they emerged. Here is the evolutionary history, here are the causal interventions, and here is the evidence for what each structure actually does.”**

That is the grand project.
