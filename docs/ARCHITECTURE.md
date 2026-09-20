# Architecture

## Separation of concerns

Five layers stay distinct, so semantic objectives cannot leak into controllers:

1. **World physics** — `world/` owns the grid, the ambient thermal field, and the resource process. It knows nothing about controllers or metrics.
2. **Body physics** — `agents/body.py` owns metabolism, thermal coupling, damage, repair and viability. Every variable here is simulator state; whether a controller can sense any of it is decided elsewhere.
3. **Sensors** — `agents/sensors.py` assembles observations declaratively and is where an experiment's manipulation lives.
4. **Controller** — `agents/controller.py`. A mapping from observation to an action distribution. No reward, no value function, no survival term.
5. **Evolution** — `evolution/` owns mutation, local reproduction rules and lineage metadata.
6. **Analysis** — `analysis/` never influences a scored run. Interventions are the exception and must be declared in the config's `interventions` block.

## Module responsibilities

| module | owns |
|---|---|
| `rng.py` | one generator per concern, spawned from the run seed |
| `config.py` | the dataclass config tree, JSON loading, config digest |
| `world/thermal.py` | ambient field construction and the resource density it induces |
| `world/grid.py` | torus topology, resource spawn/consume, egocentric patches |
| `agents/body.py` | body transition law and the energy ledger |
| `agents/sensors.py` | channel layout, ablation modes, observation assembly |
| `agents/controller.py` | MLP, GRU, random; capacity matching |
| `evolution/reproduction.py` | local reproduction conditions |
| `evolution/lineage.py` | per-organism life records, founder entropy |
| `sim.py` | the step loop that composes all of the above |
| `experiment.py` | condition x seed sweeps, parallel execution, reporting |
| `analysis/metrics.py` | endpoints, including the primary one |
| `analysis/stats.py` | bootstrap CIs, Hedges g, Cliff's delta |
| `analysis/probes.py` | post-hoc decoding and causal latent interventions |
| `analysis/validity.py` | the E0 gate |
| `assays/spec.py` | a controlled test declared as data |
| `assays/runner.py` | executes a spec against a frozen controller |
| `assays/measures.py` | outcomes computed from a trajectory |
| `assays/library.py` | the standard assays, each a pair of specs |
| `assays/cohorts.py` | evolve, snapshot at checkpoints, score each cohort |
| `snapshot.py` | serialisable view of one step; recording and replay |
| `viz/` | pygame renderer, optional (`pip install -e ".[viz]"`) |
| `provenance.py` | git commit, dirty flag and library versions on every result |

## Random number streams

`rng.py` spawns an independent generator per concern: `world_init`,
`resource_dynamics`, `reproduction_placement`, `mutation`, `action`, `sensor`,
`init`, `intervention`.

This is not tidiness. If two concerns share a generator, the draws one consumes
shift the sequence the other sees, and two conditions given "the same seed"
experience different worlds. Three such leaks have been found and closed:

- **mutation into world.** Draw count depended on parameter count, so controller
  size changed resource placement and every architecture comparison was
  confounded (failure mode 14.5).
- **sensor into action.** `shuffled` interoception draws a donor every step while
  `true` draws none, so the two conditions received different *action*
  randomness for a reason unrelated to the manipulation.
- **reproduction placement into resource dynamics.** A population that
  reproduced more shifted every subsequent resource position, so reproductive
  success silently altered the environment.
- **interoceptive donor draws into exteroceptive decoy draws.** `shuffled`
  interoception consumes draws building its derangement while `true` consumes
  none, so two conditions differing only in interoception received different
  *exteroceptive* decoy sequences. This contaminated exactly the `C - D` term of
  the E1 interaction. The sensor stream is now split into `intero_donor`,
  `extero_decoy` and `sensor_noise`.

`check_rng_independence` asserts a 4-unit and a 64-unit controller see
byte-identical resource placement, and `tests/test_reproducibility.py`
parametrises over every stream to assert that draining one never moves another.

## Observation channels

Channel layout is declarative and its **width is constant across every
condition**. Ablating a channel replaces its contents, never its size, so
controller input capacity is matched by construction.

Ablation preserves marginal statistics wherever possible:

- `shuffled` interoception substitutes another living organism's body reading;
- `shuffled` exteroception substitutes the same field read at an unrelated location;
- `constant` fills with a fixed value. This is the blunter control — it changes
  the channel's input statistics as well as its information content — and which
  one was used must be reported.

## Controllers

Common interface: `reset()`, `act(obs, rng)`, `clone_mutated(rng, sigma)`,
`param_count()`, `latent()`, `genome()`.

Actions are sampled from a softmax, not taken by argmax. A deterministic argmax
over randomly initialised networks collapses the founding population onto a
handful of constant policies and leaves evolution almost nothing to select
between.

Before comparing architectures, run `scripts/capacity_match.py` to choose a
hidden width with a matching parameter count, and re-run it after any change to
the sensor layout.

## Experiment hooks

`Simulation` exposes three hooks, all `None` during an ordinary run:

```
sensor_filter(organism, obs)           -> obs      before the controller acts
action_filter(organism, action, probs) -> action   after it acts
step_observer(organism, record)        -> None     after physics
```

The assay framework installs these rather than reimplementing the step loop, so
assay physics and evolution physics are the same code by construction. A test
asserts that installing an observer leaves the trajectory byte-identical.

## The assay framework

Roadmap §3: frozen assays are a general research primitive, not per-experiment
utilities. An `AssaySpec` is data — initial state, interventions, sensor wiring,
horizon — so two conditions can be written side by side and `differs_from` will
say what actually differs between them rather than the author asserting it.

Interventions compose: `SetBody` changes the body, `FalsifySensor` changes only
the reading, `ResetMemory`, `RemapActuator`, `DisableAction`, `AddSensorNoise`.
Everything the later stages need is expressible without new machinery: false
bodies, memory ablation, body remapping, tool incorporation, novel threats.

`SpecSession` runs a spec one step at a time. Both the batch runner and the
paired live viewer drive it, so the viewer cannot drift from the experiment that
produces the numbers.

## Two phases: evolution and assay

Endpoints measured during evolution are measured on a moving population.
`assay.py` snapshots controllers at checkpoints — deep copies, so the originals
keep evolving — and evaluates each one alone in a standardised world with
reproduction made physically impossible. The ancestral cohort at step 0 is the
baseline every later cohort is read against. See `docs/METHODOLOGY.md`,
"Measure frozen, not mid-flight".

## Observation without coupling

`Simulation.snapshot()` produces a `SimulationSnapshot`: a plain serialisable
picture of one step. Renderers, recorders and analysis consume snapshots and the
simulator knows nothing about them, so a recorded run replays with no simulator
running and the visualiser can never become a second divergent implementation of
simulation state. The static ambient field lives in a recording's header rather
than in every frame.

## Provenance

A config digest identifies the *settings*, not the *code*. Every result file
also records the git commit, whether the working tree was dirty, the package
version and the interpreter version. `dirty_worktree` is the field that matters:
a commit recorded alongside uncommitted edits does not identify what ran, and
scripts print a warning when it is set.

## Reproducibility

Every run records its full config, its seed and a config digest. Evolutionary
claims require many seeds; a single compelling trajectory is anecdotal.
`analysis/validity.py` asserts byte-identical replay before anything else runs.
