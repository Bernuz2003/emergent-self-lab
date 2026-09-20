"""Declarative observation assembly.

Two invariants this module exists to enforce:

1. Observation dimensionality is identical in every condition. Ablating a
   channel replaces its contents, never its width, so controller input capacity
   is matched by construction (methodology: "do not compare a larger network
   against a smaller one").

2. Ablation preserves marginal statistics. The default interoception control is
   `shuffled`: body values are borrowed from another living organism at the same
   step. The population-level distribution of the channel is therefore unchanged
   and only its coupling to *this* body is destroyed. Zeroing a channel would
   confound loss-of-self-information with a change in input statistics; that
   weaker control is available as `constant` and should be reported as such.
"""
from __future__ import annotations

import numpy as np

from emergent_self.config import BodyConfig, SensorConfig

INTEROCEPTION_MODES = ("true", "shuffled", "noisy", "constant", "false_body", "independent")
INTERO_CHANNELS = ("energy", "integrity", "temperature", "age")
EXTEROCEPTION_MODES = ("true", "shuffled", "constant")
N_ACTIONS = 5
N_INTERO = 4


def channel_layout(cfg: SensorConfig) -> dict[str, tuple[int, int]]:
    """Map channel name -> (start, stop) index into the observation vector."""
    patch = (2 * cfg.view_radius + 1) ** 2
    layout: dict[str, tuple[int, int]] = {}
    cursor = 0
    for name, width in (
        ("resources", patch),
        ("ambient", patch),
        ("proprioception", N_ACTIONS + 1),
        ("interoception", N_INTERO),
        ("bias", 1),
    ):
        layout[name] = (cursor, cursor + width)
        cursor += width
    return layout


def observation_dim(cfg: SensorConfig) -> int:
    return channel_layout(cfg)[ "bias" ][1]


def derangement(n: int, rng: np.random.Generator) -> np.ndarray:
    """A permutation of range(n) with no fixed point.

    Used to reassign body readings across the population for the `shuffled`
    interoception control. Drawing a donor independently per organism is not
    equivalent: it leaves each organism a 1/n chance of receiving its own
    reading, which quietly restores true interoception for part of the
    population and becomes the *typical* case as a population dies back.

    No derangement exists for n < 2; the caller must handle that.
    """
    if n < 2:
        raise ValueError("no derangement exists for n < 2")
    perm = rng.permutation(n)
    # Repair fixed points by swapping each with its successor. One pass suffices:
    # a swap can only create a fixed point at a position already passed if the
    # partner mapped back here, which the swap itself resolves.
    for i in range(n):
        if perm[i] == i:
            j = (i + 1) % n
            perm[i], perm[j] = perm[j], perm[i]
    if perm[n - 1] == n - 1:
        perm[n - 1], perm[0] = perm[0], perm[n - 1]
    return perm


def interoceptive_vector(body, body_cfg: BodyConfig) -> np.ndarray:
    """Ground-truth normalized body state, before any condition is applied."""
    return np.array(
        [
            body.energy / body_cfg.energy_max,
            body.integrity,
            body.temperature,
            min(1.0, body.age / max(1, body_cfg.senescence_onset)),
        ],
        dtype=float,
    )


def channel_mask(cfg: SensorConfig) -> np.ndarray:
    """Boolean mask over (energy, integrity, temperature, age): which channels
    the ablation touches. Everything else stays veridical."""
    names = cfg.interoception_channels
    if names is None:
        return np.ones(N_INTERO, dtype=bool)
    unknown = set(names) - set(INTERO_CHANNELS)
    if unknown:
        raise ValueError(f"unknown interoceptive channel(s): {sorted(unknown)}")
    return np.array([c in names for c in INTERO_CHANNELS])


def apply_interoception_mode(
    true_vec: np.ndarray,
    *,
    cfg: SensorConfig,
    rng: np.random.Generator,
    donor_vec: np.ndarray | None,
    false_body: tuple[int, float] | None,
    marginal_vec: np.ndarray | None = None,
) -> np.ndarray:
    """Transform ground-truth interoception according to the condition.

    The transform is applied only to the channels named by
    `cfg.interoception_channels`; the rest of the vector passes through
    untouched. This is what makes a temperature-only ablation possible.
    """
    mode = cfg.interoception
    if mode == "true":
        return true_vec

    if mode == "constant":
        ablated = np.full_like(true_vec, 0.5)
    elif mode == "noisy":
        ablated = np.clip(
            true_vec + rng.normal(0.0, cfg.interoception_noise, true_vec.shape), 0.0, 1.0)
    elif mode == "shuffled":
        # Another *currently living* organism's reading. Preserves the population
        # marginal exactly, but see `independent`: it also carries information
        # about the present state of the population.
        ablated = true_vec.copy() if donor_vec is None else donor_vec.copy()
    elif mode == "independent":
        # Drawn from an empirical marginal accumulated over the run, so it is
        # decoupled from the *current* population state as well as from this
        # body. `shuffled` removes the self signal but introduces a population
        # signal - global density, ecological phase, the ambient regime everyone
        # is currently in - which is a candidate explanation for shuffled
        # outperforming true interoception, and has to be controlled separately.
        ablated = true_vec.copy() if marginal_vec is None else marginal_vec.copy()
    elif mode == "false_body":
        ablated = true_vec.copy()
        if false_body is not None:
            index, value = false_body
            ablated[index] = value
    else:
        raise ValueError(f"unknown interoception mode '{mode}'")

    mask = channel_mask(cfg)
    return np.where(mask, ablated, true_vec)


def apply_extero_mode(patch: np.ndarray, mode: str, decoy: np.ndarray | None,
                      fill: float) -> np.ndarray:
    """Ablate an exteroceptive channel without changing its width.

    `shuffled` substitutes the same field read at an unrelated location, so the
    marginal distribution of the channel is preserved and only its coupling to
    the organism's actual position is destroyed. `constant` is the blunter
    control and changes the input statistics; report which one was used.
    """
    if mode == "true":
        return patch
    if mode == "shuffled":
        return patch if decoy is None else decoy
    if mode == "constant":
        return np.full_like(patch, fill)
    raise ValueError(f"unknown exteroception mode '{mode}'")


def assemble(
    *,
    resource_patch: np.ndarray,
    ambient_patch: np.ndarray,
    last_action: int,
    moved: bool,
    sensed_intero: np.ndarray,
    cfg: SensorConfig,
) -> np.ndarray:
    """Concatenate channels into the fixed-width observation vector."""
    layout = channel_layout(cfg)
    obs = np.zeros(layout["bias"][1])

    lo, hi = layout["resources"]
    obs[lo:hi] = resource_patch.ravel()
    lo, hi = layout["ambient"]
    obs[lo:hi] = ambient_patch.ravel()

    if cfg.proprioception:
        lo, _ = layout["proprioception"]
        obs[lo + last_action] = 1.0
        obs[lo + N_ACTIONS] = float(moved)

    lo, hi = layout["interoception"]
    obs[lo:hi] = sensed_intero

    obs[layout["bias"][0]] = 1.0
    return obs
