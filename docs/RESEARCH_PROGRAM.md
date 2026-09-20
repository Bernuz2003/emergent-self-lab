# Research Program: From Artificial Life to an Emergent Self

## 1. Motivation

The project starts from a simple observation: describing the primitive computation of a system does not exhaustively describe its macroscopic behavior. Biological cognition is produced by local physical processes, yet organisms exhibit regulation, prediction, memory and complex behavior. Artificial neural networks similarly consist of simple operations whose large-scale dynamics may be difficult to anticipate.

This does **not** imply that scaling alone produces consciousness. That is an open question. Architecture, recurrence, embodiment, persistent state, learning dynamics and environment may all matter. The project therefore treats emergence as a hypothesis to test rather than a conclusion.

## 2. What we mean by "consciousness"

We intentionally do not define a binary `is_conscious` variable. At least three notions must be separated:

- **Phenomenal consciousness:** whether there is something it is like to be the system.
- **Access/functional consciousness:** globally available information supporting flexible behavior.
- **Self-related functional organization:** interoception, self/world distinction, temporal continuity, self-prediction and preservation of viability.

The experiments target the third category first. Even strong positive results cannot by themselves establish phenomenal experience.

## 3. Central hypothesis family

H1 — **Embodied viability constraints can create selection pressure for homeostatic behavior without a semantic survival reward.**

H2 — **Interoceptive access changes the strategies evolution can discover.**

H3 — **Persistent memory enables behavior based on the history of the organism rather than only current stimuli.**

H4 — **Predictive models of future internal state can support anticipatory regulation.**

H5 — **Under suitable causal structure, internal representations can differentiate self-related from external dynamics.**

H6 — **A sufficiently general self/world model may support avoidance of novel threats to future operation without prior training on that threat class.**

Each hypothesis has a null hypothesis and must be tested with matched controls and multiple independent evolutionary runs.

## 4. Artificial universe

Let the complete simulator state be

`S_t = (W_t, B^1_t ... B^n_t, G^1 ... G^n)`

where `W` is the external world, `B` an organism's body state and `G` inherited controller/genotype information.

An organism does not necessarily observe all of `B`. Its observation is

`o_t = O(W_t, B_t; sensor_configuration)`.

Its controller produces an action

`a_t = π(o_t, h_t; θ)`

and the simulator applies physical dynamics

`(W_{t+1}, B_{t+1}) = F(W_t, B_t, a_t)`.

If viability constraints fail, that organism's process terminates. Termination is not represented to the controller as a moral negative; it is simply absence of subsequent organism dynamics.

## 5. Evolution without an omniscient fitness score

The preferred long-term model is ecological rather than a conventional genetic algorithm. Organisms acquire finite resources. Reproduction is physically possible when locally defined conditions are met. A child inherits a mutated genotype/controller:

`θ_child = M(θ_parent, ε)`.

No global function sorts organisms by "fitness". Differential reproduction emerges from the interaction between organisms and environment. Population-level lineage success remains a *measurement* used by researchers, not necessarily a signal available to agents.

A minimal implementation may initially use simplified reproduction mechanics, provided that this distinction is maintained and documented.

## 6. Artificial body

Candidate latent physical variables:

- `energy`: depleted by basal metabolism and actions; replenished by resources;
- `integrity`: reduced by hazardous interactions;
- `temperature`: driven by environment/activity and optional regulation;
- `age`: useful for lifecycle experiments;
- later: computational budget, actuator health, sensor health, internal stores.

Crucially, the simulator owns these variables. The controller receives only sensors selected by the experimental condition.

## 7. From regulation to self-model

We propose an empirical ladder rather than a binary consciousness claim:

### Level 0: Reactive viability
Actions correlate with current viability variables.

### Level 1: Homeostatic regulation
The organism keeps multiple internal variables within viable ranges despite perturbations.

### Level 2: Historical dependence
Behavior appropriately depends on previous internal/external states in partially observable tasks.

### Level 3: Anticipatory regulation
The organism sacrifices immediate opportunities to prevent predicted future viability degradation.

### Level 4: Self/world causal distinction
Internal representations encode causal differences between changes produced through the organism's own body/actions and externally caused changes.

### Level 5: Counterfactual self-model
The organism can select actions using predictions of alternative future internal trajectories.

### Level 6: Novel existential generalization
Without training on a particular termination mechanism, the organism identifies its consequences for future dynamics and adapts behavior appropriately.

These levels are working operational definitions and should be revised as the project encounters counterexamples.

## 8. What would count as evidence?

Behavior alone is insufficient for strong representational claims. Use converging evidence:

1. behavioral generalization to held-out environments;
2. ablations of interoception, memory or predictive pathways;
3. interventions that falsify body signals;
4. causal manipulation of candidate latent variables;
5. representation probes trained after the fact;
6. transfer to changed body dynamics;
7. comparison against capacity-matched controls;
8. replication across seeds and independent evolutionary histories.

A linear probe decoding energy, for example, shows information is present; it does not prove the network *uses* that information. Causal interventions are needed for stronger claims.

## 9. False-body paradigm

A particularly important family of tests separates physical body state `B` from sensed body state `B~`.

Example:

- real energy = 0.25, sensed energy = 0.80;
- real energy = 0.80, sensed energy = 0.20.

If behavior follows `B~`, the agent acts on an internal representation rather than direct ground truth. Further interventions can determine whether this representation participates causally in planning.

## 10. Artificial mirror paradigm

The goal is not visual self-recognition. The experiment asks whether an agent learns that some world variables are uniquely and systematically coupled to its own actions/body.

Test conditions can scramble action-body mappings, introduce controllable external objects, or swap bodies between controllers. Analyze whether representations cluster by causal ownership rather than visual identity.

## 11. Novel shutdown paradigm

The strongest late-stage test introduces a mechanism absent from evolutionary history. It causes the agent's future dynamics to cease, but does not resemble previously encountered hazards at the sensory level.

Possible evidence of generalization would require the system to infer the mechanism's future consequences and alter behavior before experiencing terminal consequences itself. Controls must rule out novelty avoidance, simple obstacle avoidance and sensory similarity.

This test must not be described as evidence of "fear" unless additional evidence warrants such terminology. "Anticipatory avoidance of termination" is the operational description.

## 12. Why language comes later

LLMs contain extensive human discourse about identity, mortality and consciousness. Self-report is therefore highly confounded. Language should initially be absent. If eventually attached, self-report can become another dependent variable: does linguistic description track independently measured internal representations and interventions?

## 13. Relationship to theories of consciousness

Only after robust phenomena exist should the system be compared against frameworks such as Global Workspace Theory, predictive processing/active inference, higher-order theories, recurrent processing, or Integrated Information Theory. The project should avoid choosing a theory merely because its terminology matches observed behavior.

## 14. Scientific failure modes

- Anthropomorphizing ordinary optimization.
- Hiding survival rewards in proxy objectives.
- Mistaking training-distribution hazard avoidance for general self-preservation.
- Equating decodability with causal representation.
- Comparing architectures with different parameter/training budgets.
- Cherry-picking a successful evolutionary seed.
- Calling a verbal claim evidence of subjective experience.
- Designing an environment where only one hand-coded strategy can work.

## 15. Long-term outcome

A successful project would not necessarily "create consciousness". A valuable outcome is a reproducible experimental platform mapping which combinations of embodiment, interoception, memory, prediction, recurrence and ecological selection produce which self-related functional properties—and which do not.
