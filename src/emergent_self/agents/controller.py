"""Controllers.

Common interface: reset(), act(obs, rng) -> int, clone_mutated(rng, sigma),
param_count(), latent() -> np.ndarray.

Controllers carry no reward signal, no value function and no survival term. They
are a mapping from observation to an action distribution; everything else is
physics. Actions are sampled from a softmax rather than taken by argmax: a
deterministic argmax over a randomly initialised network collapses the founding
population onto a handful of constant policies, leaving evolution almost nothing
to select between.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from emergent_self.config import ControllerConfig


def _softmax(logits: np.ndarray, temperature: float) -> np.ndarray:
    z = logits / max(1e-6, temperature)
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


class Controller(ABC):
    n_actions: int

    @abstractmethod
    def reset(self) -> None: ...

    @abstractmethod
    def act(self, obs: np.ndarray, rng: np.random.Generator) -> int: ...

    @abstractmethod
    def clone_mutated(self, rng: np.random.Generator, sigma: float) -> "Controller": ...

    @abstractmethod
    def param_count(self) -> int: ...

    def action_probs(self, obs: np.ndarray) -> np.ndarray:
        """The action distribution for `obs`, without sampling from it.

        Interventions compare distributions. Sampling one action from each of
        two distributions and comparing the draws measures mostly sampling
        noise: with a softmax temperature of 0.35 two identical distributions
        disagree on a large fraction of single draws.
        """
        raise NotImplementedError

    def latent(self) -> np.ndarray:
        """Internal state exposed to post-hoc probes. Never read by the simulator."""
        return np.zeros(0)

    def genome(self) -> np.ndarray:
        """Flat parameter vector, used for lineage-distance metrics."""
        return np.zeros(0)


class RandomController(Controller):
    """Neutral baseline: uniform over actions, ignores every observation."""

    def __init__(self, n_actions: int = 5):
        self.n_actions = n_actions

    def reset(self) -> None:
        pass

    def act(self, obs: np.ndarray, rng: np.random.Generator) -> int:
        return int(rng.integers(self.n_actions))

    def clone_mutated(self, rng: np.random.Generator, sigma: float) -> "RandomController":
        return RandomController(self.n_actions)

    def action_probs(self, obs: np.ndarray) -> np.ndarray:
        return np.full(self.n_actions, 1.0 / self.n_actions)

    def param_count(self) -> int:
        return 0


class MLPController(Controller):
    """Reactive baseline. No persistent state between steps."""

    def __init__(self, input_dim: int, hidden_dim: int, n_actions: int, temperature: float):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.n_actions = n_actions
        self.temperature = temperature
        self.w1 = np.zeros((input_dim, hidden_dim))
        self.b1 = np.zeros(hidden_dim)
        self.w2 = np.zeros((hidden_dim, n_actions))
        self.b2 = np.zeros(n_actions)
        self._h = np.zeros(hidden_dim)

    @classmethod
    def initialised(cls, input_dim, hidden_dim, n_actions, temperature, scale, rng):
        c = cls(input_dim, hidden_dim, n_actions, temperature)
        c.w1 = rng.normal(0.0, scale, c.w1.shape)
        c.w2 = rng.normal(0.0, scale, c.w2.shape)
        return c

    def reset(self) -> None:
        self._h = np.zeros(self.hidden_dim)

    def act(self, obs: np.ndarray, rng: np.random.Generator) -> int:
        probs = self.action_probs(obs)
        return int(rng.choice(self.n_actions, p=probs))

    def action_probs(self, obs: np.ndarray) -> np.ndarray:
        self._h = np.tanh(obs @ self.w1 + self.b1)
        return _softmax(self._h @ self.w2 + self.b2, self.temperature)

    def probs_from_latent(self, h: np.ndarray) -> np.ndarray:
        """Read out an action distribution from a supplied hidden state, leaving
        the controller's own state untouched. This is what a latent intervention
        needs: the effect of h, not the effect of re-running the encoder."""
        return _softmax(h @ self.w2 + self.b2, self.temperature)

    def _arrays(self):
        return ("w1", "b1", "w2", "b2")

    def clone_mutated(self, rng: np.random.Generator, sigma: float) -> "MLPController":
        child = type(self)(self.input_dim, self.hidden_dim, self.n_actions, self.temperature)
        for name in self._arrays():
            parent = getattr(self, name)
            setattr(child, name, parent + rng.normal(0.0, sigma, parent.shape))
        return child

    def param_count(self) -> int:
        return sum(getattr(self, n).size for n in self._arrays())

    def latent(self) -> np.ndarray:
        return self._h.copy()

    def genome(self) -> np.ndarray:
        return np.concatenate([getattr(self, n).ravel() for n in self._arrays()])


class GRUController(MLPController):
    """Persistent-state controller for E2. Hidden state survives across steps and
    is cleared only by reset(), so behaviour can depend on the organism's history."""

    def __init__(self, input_dim: int, hidden_dim: int, n_actions: int, temperature: float):
        super().__init__(input_dim, hidden_dim, n_actions, temperature)
        h = hidden_dim
        self.wz = np.zeros((input_dim, h)); self.uz = np.zeros((h, h)); self.bz = np.zeros(h)
        self.wr = np.zeros((input_dim, h)); self.ur = np.zeros((h, h)); self.br = np.zeros(h)
        self.wh = np.zeros((input_dim, h)); self.uh = np.zeros((h, h)); self.bh = np.zeros(h)

    @classmethod
    def initialised(cls, input_dim, hidden_dim, n_actions, temperature, scale, rng):
        c = cls(input_dim, hidden_dim, n_actions, temperature)
        for name in ("wz", "uz", "wr", "ur", "wh", "uh", "w2"):
            arr = getattr(c, name)
            setattr(c, name, rng.normal(0.0, scale / np.sqrt(max(1, arr.shape[0])) * 2.0, arr.shape))
        return c

    def _arrays(self):
        return ("wz", "uz", "bz", "wr", "ur", "br", "wh", "uh", "bh", "w2", "b2")

    def action_probs(self, obs: np.ndarray) -> np.ndarray:
        h = self._h
        z = 1.0 / (1.0 + np.exp(-(obs @ self.wz + h @ self.uz + self.bz)))
        r = 1.0 / (1.0 + np.exp(-(obs @ self.wr + h @ self.ur + self.br)))
        n = np.tanh(obs @ self.wh + (r * h) @ self.uh + self.bh)
        self._h = (1.0 - z) * h + z * n
        return _softmax(self._h @ self.w2 + self.b2, self.temperature)


def _mlp_params(i, h, a):
    return i * h + h + h * a + a


def _gru_params(i, h, a):
    return 3 * (i * h + h * h + h) + h * a + a


def match_hidden_dim(kind: str, input_dim: int, n_actions: int, target_params: int) -> int:
    """Smallest hidden width whose parameter count is closest to `target_params`.

    Use this to capacity-match a recurrent controller against a reactive one
    before attributing any difference to memory rather than to size.
    """
    counter = _gru_params if kind == "gru" else _mlp_params
    best, best_gap = 1, None
    for h in range(1, 512):
        gap = abs(counter(input_dim, h, n_actions) - target_params)
        if best_gap is None or gap < best_gap:
            best, best_gap = h, gap
    return best


def build_controller(cfg: ControllerConfig, input_dim: int, n_actions: int, rng) -> Controller:
    if cfg.kind == "random":
        return RandomController(n_actions)
    cls = {"mlp": MLPController, "gru": GRUController}.get(cfg.kind)
    if cls is None:
        raise ValueError(f"unknown controller kind '{cfg.kind}'")
    return cls.initialised(input_dim, cfg.hidden_dim, n_actions, cfg.policy_temperature, cfg.init_scale, rng)
