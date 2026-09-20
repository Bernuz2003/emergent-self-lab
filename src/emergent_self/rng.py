"""Independent random streams.

Rationale (docs/RESEARCH_PROGRAM.md 14.5): if two concerns share one generator,
the number of draws one of them consumes shifts the sequence the other sees. Two
conditions given "the same seed" then experience different worlds, and the
comparison is confounded.

The split is finer than it first looks like it needs to be, because two real
leaks were found after the coarse version was already in place:

* `shuffled` interoception draws a donor every step while `true` interoception
  draws nothing. Sharing one stream between sensor bookkeeping and action
  sampling meant the two conditions received different *action* randomness for
  no reason connected to the manipulation.
* Child placement drew from the same stream as resource respawn, so a population
  that reproduced more shifted every subsequent resource position. Reproductive
  success silently altered the environment.

Each concern therefore owns a stream, and adding a draw to one can never move
another.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

STREAMS = (
    "world_init",              # ambient field, initial resource placement
    "resource_dynamics",       # respawn during the run
    "reproduction_placement",  # where a child is put
    "mutation",                # genome perturbation
    "action",                  # controller action sampling, and nothing else
    # The sensor stream is split three ways. A single sensor stream still leaked:
    # `shuffled` interoception consumes draws building its derangement, which
    # shifted the exteroceptive decoy locations drawn immediately afterwards. So
    # C (intero true, ambient shuffled) and D (intero shuffled, ambient shuffled)
    # received completely different decoy sequences, contaminating exactly the
    # contrast the E1 interaction rests on.
    "intero_donor",            # derangement of body readings across the population
    "extero_decoy",            # where an ablated exteroceptive channel reads from
    "sensor_noise",            # additive noise on a sensed channel
    "init",                    # founder placement and controller initialisation
    "intervention",            # researcher-applied perturbations
)


@dataclass(frozen=True)
class RngBundle:
    """One generator per concern, reproducibly derived from a single seed."""

    world_init: np.random.Generator
    resource_dynamics: np.random.Generator
    reproduction_placement: np.random.Generator
    mutation: np.random.Generator
    action: np.random.Generator
    intero_donor: np.random.Generator
    extero_decoy: np.random.Generator
    sensor_noise: np.random.Generator
    init: np.random.Generator
    intervention: np.random.Generator

    @classmethod
    def from_seed(cls, seed: int) -> "RngBundle":
        children = np.random.SeedSequence(seed).spawn(len(STREAMS))
        return cls(**{name: np.random.default_rng(s) for name, s in zip(STREAMS, children)})
