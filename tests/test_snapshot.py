"""The snapshot layer is the only thing the visualiser sees, so a recording must
round-trip exactly and the simulator must stay unaware of it."""
from __future__ import annotations

import json

import numpy as np

from emergent_self.config import RunConfig
from emergent_self.sim import Simulation
from emergent_self.snapshot import Recorder, iter_recording, load_recording


def _run(tmp_path, steps=40, every=1):
    sim = Simulation(RunConfig(steps=steps, seed=2, log_every=0, initial_agents=20))
    path = tmp_path / "rec.jsonl"
    with Recorder(path, sim.recording_header(), every=every) as rec:
        for _ in range(steps):
            sim.step()
            rec.write(sim.snapshot())
    return sim, path


def test_recording_round_trips(tmp_path):
    sim, path = _run(tmp_path)
    header, frames = load_recording(path)
    assert header.size == sim.world.size
    assert np.allclose(header.ambient_array, sim.world.ambient, atol=1e-4)
    assert len(frames) == 40
    assert frames[-1].step == sim.step_index


def test_snapshot_agrees_with_live_state(tmp_path):
    sim = Simulation(RunConfig(steps=10, seed=7, log_every=0, initial_agents=15))
    for _ in range(10):
        sim.step()
    snap = sim.snapshot()
    assert snap.population == len(sim.agents)
    assert {a.ident for a in snap.agents} == {a.ident for a in sim.agents}
    live = {a.ident: a for a in sim.agents}
    for view in snap.agents:
        a = live[view.ident]
        assert (view.x, view.y) == (a.x, a.y)
        assert view.temperature == round(a.body.temperature, 4)
    assert sorted(snap.resources) == sorted(
        (int(x), int(y)) for x, y in zip(*np.nonzero(sim.world.resources))
    )


def test_record_every_thins_frames(tmp_path):
    _, path = _run(tmp_path, steps=40, every=4)
    _, frames = load_recording(path)
    assert len(frames) == 10
    assert all(f.step % 4 == 0 for f in frames)


def test_streaming_matches_eager_load(tmp_path):
    _, path = _run(tmp_path, steps=20)
    _, frames = load_recording(path)
    assert [f.step for f in iter_recording(path)] == [f.step for f in frames]


def test_events_are_emitted_and_cleared_each_step(tmp_path):
    sim = Simulation(RunConfig(steps=200, seed=1, log_every=0, initial_agents=40))
    kinds, saw_nonempty = set(), False
    for _ in range(200):
        sim.step()
        snap = sim.snapshot()
        kinds |= {e[0] for e in snap.events}
        saw_nonempty |= bool(snap.events)
        # events belong to the step just taken, never accumulate
        assert snap.events == sim.events
    assert saw_nonempty
    assert "consume" in kinds


def test_snapshot_is_json_serialisable(tmp_path):
    sim = Simulation(RunConfig(steps=5, seed=3, log_every=0, initial_agents=10))
    for _ in range(5):
        sim.step()
    json.dumps(sim.snapshot().to_json())


def test_taking_snapshots_does_not_change_the_simulation():
    """The viewer must be a pure observer."""
    cfg = RunConfig(steps=80, seed=6, log_every=10, initial_agents=25)
    plain = Simulation(cfg)
    for _ in range(80):
        plain.step()

    watched = Simulation(cfg)
    for _ in range(80):
        watched.step()
        watched.snapshot()

    assert [a.ident for a in plain.agents] == [a.ident for a in watched.agents]
    assert np.allclose([a.body.energy for a in plain.agents],
                       [a.body.energy for a in watched.agents])
