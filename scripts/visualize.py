"""Watch a simulation, live or from a recording.

This is a scientific instrument, not decoration: strategies that are opaque in
the aggregate numbers - patrolling a thermal margin, camping a resource patch,
exploiting metabolic heat in the cold, sitting still - are usually obvious
within seconds of watching.

  live:    python scripts/visualize.py --config configs/e0_validity.json --seed 4
  paired:  python scripts/visualize.py --paired sensor_dissociation --evolve 4000
  record:  python scripts/visualize.py --config configs/e0_validity.json --record runs/run.jsonl --headless
  replay:  python scripts/visualize.py --replay runs/run.jsonl

A condition from an experiment config can be selected directly:

  python scripts/visualize.py --experiment configs/e1_interoception.json \
      --condition A_ambient_and_intero --seed 4
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path


def _build_config(args):
    from emergent_self.config import load_run_config, run_config_from_dict
    from emergent_self.experiment import deep_merge

    if args.experiment:
        spec = json.loads(Path(args.experiment).read_text())
        conditions = spec["conditions"]
        if args.condition not in conditions:
            raise SystemExit(f"condition must be one of: {', '.join(conditions)}")
        merged = deep_merge(spec.get("base", {}), conditions[args.condition])
        merged.update({"name": spec["name"], "condition": args.condition, "seed": args.seed})
        cfg = run_config_from_dict(merged)
    else:
        cfg = replace(load_run_config(args.config), seed=args.seed)
    return replace(cfg, steps=args.steps or cfg.steps, log_every=0)


def run_live(args) -> None:
    from emergent_self.sim import Simulation
    from emergent_self.snapshot import Recorder

    cfg = _build_config(args)
    sim = Simulation(cfg)
    print(f"live: seed={cfg.seed} steps={cfg.steps} condition={cfg.condition}")

    recorder = Recorder(args.record, sim.recording_header(), args.record_every) if args.record else None
    renderer = None
    if not args.headless:
        from emergent_self.viz.renderer import Renderer

        renderer = Renderer(sim.recording_header(), cell=args.cell)

    try:
        for _ in range(cfg.steps):
            if renderer:
                st = renderer.handle_input()
                if st.quit:
                    break
                if st.paused and not st.step_once:
                    renderer.draw(sim.snapshot())
                    renderer.tick()
                    continue
            sim.step()
            snap = sim.snapshot()
            if recorder:
                recorder.write(snap)
            if renderer:
                renderer.draw(snap)
                renderer.tick()
            if not sim.agents:
                print(f"population extinct at step {sim.step_index}")
                break
    finally:
        if recorder:
            recorder.close()
            print(f"wrote {args.record} ({recorder.frames} frames)")
        if renderer:
            renderer.close()


def run_replay(args) -> None:
    from emergent_self.snapshot import load_recording
    from emergent_self.viz.renderer import Renderer

    header, frames = load_recording(args.replay)
    print(f"replay: {args.replay} ({len(frames)} frames, grid {header.size})")
    renderer = Renderer(header, cell=args.cell)
    i = 0
    try:
        while True:
            st = renderer.handle_input()
            if st.quit:
                break
            renderer.draw(frames[min(i, len(frames) - 1)])
            renderer.tick()
            if st.step_once:
                # A recording can be stepped in either direction.
                i = (i - 1) % len(frames) if st.step_back else (i + 1) % len(frames)
            elif not st.paused:
                # A finished recording loops rather than freezing on its last
                # frame, so a short run can be watched repeatedly.
                i = (i + 1) % len(frames)
    finally:
        renderer.close()


PAIRED_SPECS = ("sensor_dissociation", "body_contingency", "memory_wipe", "actuator_remap")


def _paired_specs(kind: str, horizon: int, world_seed: int):
    """Two specs differing in exactly one declared field."""
    from emergent_self.assays.library import (
        body_contingency_specs,
        sensor_dissociation_specs,
    )
    from emergent_self.assays.spec import AssaySpec, InitialState, RemapActuator, ResetMemory

    worlds = (world_seed,)
    if kind == "sensor_dissociation":
        v_cold, _, dissoc = sensor_dissociation_specs(world_seeds=worlds, horizon=horizon)
        return v_cold, dissoc
    if kind == "body_contingency":
        return body_contingency_specs(world_seeds=worlds, horizon=horizon)
    intact = AssaySpec(name="intact", world_seeds=worlds, horizon=horizon,
                       initial=InitialState(warmup=20, reset_memory_before_start=False))
    if kind == "memory_wipe":
        return intact, intact.with_(name="memory_wiped",
                                    interventions=(ResetMemory(start=0),))
    return intact, intact.with_(name="actuator_remapped",
                                interventions=(RemapActuator(permutation=(0, 3, 4, 1, 2)),))


def run_paired_view(args) -> None:
    """Evolve briefly, take a controller, then run two arms in lockstep."""
    import numpy as np

    from emergent_self.sim import Simulation
    from emergent_self.viz.paired import PairedRenderer

    cfg = _build_config(args)
    sim = Simulation(cfg)
    for _ in range(args.evolve):
        sim.step()
        if not sim.agents:
            raise SystemExit(f"population went extinct at step {sim.step_index}; "
                             f"try a different --seed or a shorter --evolve")
    picks = sim.snapshot_controllers(1, np.random.default_rng(args.seed))
    if not picks:
        raise SystemExit("no controller available to assay")

    spec_a, spec_b = _paired_specs(args.paired, args.horizon, 1000 + args.seed)
    print(f"paired: {spec_a.name} vs {spec_b.name}")
    print(f"  {spec_a.describe()}")
    print(f"  {spec_b.describe()}")
    print(f"  differs in: {spec_b.differs_from(spec_a) or ['nothing']}")

    r = PairedRenderer(picks[0], cfg, spec_a, spec_b, 1000 + args.seed, cell=args.cell)
    try:
        for _ in range(args.horizon):
            r.handle_input()
            if r.quit:
                break
            if r.paused and not r.step_once:
                r.draw()
                r.tick()
                continue
            if not r.advance():
                r.draw()
                break
            r.draw()
            r.tick()
        while not r.quit:
            r.handle_input()
            r.draw()
            r.tick()
    finally:
        r.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="configs/e0_validity.json")
    ap.add_argument("--experiment", default=None, help="an experiment config; use with --condition")
    ap.add_argument("--condition", default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--cell", type=int, default=18, help="pixels per grid cell")
    ap.add_argument("--record", default=None, help="write a replayable recording here")
    ap.add_argument("--record-every", type=int, default=1)
    ap.add_argument("--headless", action="store_true", help="record without opening a window")
    ap.add_argument("--replay", default=None)
    ap.add_argument("--paired", default=None, choices=PAIRED_SPECS,
                    help="paired counterfactual view: two arms, one declared difference")
    ap.add_argument("--evolve", type=int, default=3000,
                    help="steps of evolution before snapshotting the controller to assay")
    ap.add_argument("--horizon", type=int, default=250, help="paired rollout length")
    args = ap.parse_args()

    if args.experiment and not args.condition:
        raise SystemExit("--experiment requires --condition")
    if args.paired:
        run_paired_view(args)
    elif args.replay:
        run_replay(args)
    else:
        run_live(args)


if __name__ == "__main__":
    main()
