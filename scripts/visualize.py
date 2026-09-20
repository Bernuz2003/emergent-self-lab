"""Watch a simulation, live or from a recording.

This is a scientific instrument, not decoration: strategies that are opaque in
the aggregate numbers - patrolling a thermal margin, camping a resource patch,
exploiting metabolic heat in the cold, sitting still - are usually obvious
within seconds of watching.

  live:    python scripts/visualize.py --config configs/e0_validity.json --seed 4
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
            if not st.paused or st.step_once:
                # A finished recording loops rather than freezing on its last
                # frame, so a short run can be watched repeatedly.
                i = (i + 1) % len(frames)
    finally:
        renderer.close()


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
    args = ap.parse_args()

    if args.experiment and not args.condition:
        raise SystemExit("--experiment requires --condition")
    if args.replay:
        run_replay(args)
    else:
        run_live(args)


if __name__ == "__main__":
    main()
