"""Paired counterfactual view: the same controller, the same world, one change.

Roadmap section 6 calls this the step that turns the viewer from an animation
into a causal microscope. Two arms run in lockstep from an identical starting
condition and differ only in what the assay spec declares, so a divergence on
screen is attributable to that one thing.

The two arms are driven by `assays.runner.SpecSession`, the same object the
batch assays use. The viewer does not build its own experiment and cannot drift
from the one that produces the numbers.
"""
from __future__ import annotations

import collections
from dataclasses import dataclass

import numpy as np

from emergent_self.assays.runner import SpecSession
from emergent_self.assays.spec import AssaySpec
from emergent_self.config import RunConfig
from emergent_self.viz import palette
from emergent_self.viz.renderer import ACCENT, BG, DIM, FG, _load_fonts

PANEL_W = 300


@dataclass
class ArmView:
    label: str
    session: SpecSession
    trail: collections.deque


class PairedRenderer:
    """Two worlds side by side, with the divergence between them measured live."""

    def __init__(self, controller, base: RunConfig, spec_a: AssaySpec, spec_b: AssaySpec,
                 world_seed: int, cell: int = 12):
        import pygame

        if spec_a.world_seeds != spec_b.world_seeds:
            raise ValueError("a paired view must use the same worlds in both arms")
        self.pygame = pygame
        self.base = base
        self.differs_in = spec_b.differs_from(spec_a)

        self.arms = [
            ArmView(spec_a.name, SpecSession(controller, base, spec_a, world_seed),
                    collections.deque(maxlen=48)),
            ArmView(spec_b.name, SpecSession(controller, base, spec_b, world_seed),
                    collections.deque(maxlen=48)),
        ]
        self.size = self.arms[0].session.sim.world.size
        self.cell = cell
        self.grid_px = self.size * cell

        pygame.init()
        pygame.display.set_caption("Emergent Self Lab — paired counterfactual")
        self.screen = pygame.display.set_mode(
            (self.grid_px * 2 + 30 + PANEL_W, max(self.grid_px + 40, 520)))
        self.font, self.font_small, self.font_big = _load_fonts(pygame)
        self.clock = pygame.time.Clock()

        arr = palette.ambient_surface_array(self.arms[0].session.sim.world.ambient)
        surf = pygame.surfarray.make_surface(arr)
        self.background = pygame.transform.scale(surf, (self.grid_px, self.grid_px))

        self.paused = False
        self.speed = 6
        self.step_once = False
        self.quit = False
        self.tv_history: collections.deque = collections.deque(maxlen=PANEL_W - 40)
        self.step = 0

    # ------------------------------------------------------------------ input

    def handle_input(self) -> None:
        pg = self.pygame
        self.step_once = False
        for e in pg.event.get():
            if e.type == pg.QUIT:
                self.quit = True
            elif e.type == pg.KEYDOWN:
                if e.key in (pg.K_ESCAPE, pg.K_q):
                    self.quit = True
                elif e.key == pg.K_SPACE:
                    self.paused = not self.paused
                elif e.key == pg.K_RIGHT:
                    self.step_once = True
                elif e.key in (pg.K_PLUS, pg.K_EQUALS):
                    self.speed = min(120, self.speed * 2)
                elif e.key == pg.K_MINUS:
                    self.speed = max(1, self.speed // 2)

    # ------------------------------------------------------------------- tick

    def advance(self) -> bool:
        alive = False
        for arm in self.arms:
            alive |= arm.session.step()
            org = arm.session.org
            if not arm.session.dead:
                arm.trail.append((org.x, org.y))
        self.step += 1
        self.tv_history.append(self._tv())
        return alive

    def _probs(self, arm: ArmView):
        steps = arm.session.traj.steps
        return np.array(steps[-1]["probs"]) if steps else None

    def _tv(self) -> float:
        pa, pb = self._probs(self.arms[0]), self._probs(self.arms[1])
        if pa is None or pb is None:
            return float("nan")
        return float(0.5 * np.abs(pa - pb).sum())

    # ------------------------------------------------------------------- draw

    def draw(self) -> None:
        pg = self.pygame
        self.screen.fill(BG)
        for i, arm in enumerate(self.arms):
            ox = i * (self.grid_px + 15)
            self._draw_arm(arm, ox)
            self._text(arm.label, ox + 4, self.grid_px + 6, ACCENT, self.font_small)
        self._draw_panel()
        pg.display.flip()

    def _draw_arm(self, arm: ArmView, ox: int) -> None:
        pg = self.pygame
        c = self.cell
        self.screen.blit(self.background, (ox, 0))
        sim = arm.session.sim
        for x, y in zip(*np.nonzero(sim.world.resources)):
            pg.draw.circle(self.screen, (150, 196, 128),
                           (ox + x * c + c // 2, y * c + c // 2), max(2, c // 6))
        if len(arm.trail) > 1:
            surf = pg.Surface((self.grid_px, self.grid_px), pg.SRCALPHA)
            for i, (x, y) in enumerate(arm.trail):
                a = int(120 * (i + 1) / len(arm.trail))
                pg.draw.circle(surf, (232, 176, 84, a), (x * c + c // 2, y * c + c // 2),
                               max(1, c // 6))
            self.screen.blit(surf, (ox, 0))
        if arm.session.dead:
            self._text("TERMINATED", ox + 6, 6, (240, 120, 100), self.font_small)
            return
        org = arm.session.org
        col = palette.thermal(org.body.temperature)
        cx, cy = ox + org.x * c + c // 2, org.y * c + c // 2
        pg.draw.circle(self.screen, col, (cx, cy), max(3, c // 2))
        lo, hi = self.base.body.viable_temp_lo, self.base.body.viable_temp_hi
        if not (lo <= org.body.temperature <= hi):
            pg.draw.circle(self.screen, (240, 120, 100), (cx, cy), max(3, c // 2) + 3, 1)

    def _text(self, s, x, y, col=FG, font=None) -> int:
        f = font or self.font
        if f is None:
            return y + 14
        self.screen.blit(f.render(s, True, col), (x, y))
        return y + f.get_linesize() + 1

    def _draw_panel(self) -> None:
        x = self.grid_px * 2 + 30 + 10
        y = self._text(f"step {self.step}", x, 12, font=self.font_big)
        y = self._text(f"differs in: {', '.join(self.differs_in) or 'nothing'}",
                       x, y, ACCENT, self.font_small)
        y = self._text("everything else is shared", x, y, DIM, self.font_small)
        y += 8

        tv = self._tv()
        y = self._text(f"action-distribution TV  {tv:6.3f}"
                       if np.isfinite(tv) else "action-distribution TV     --", x, y)
        y = self._draw_sparkline(x, y + 2, PANEL_W - 30, 36)
        y += 8

        for arm in self.arms:
            y = self._text(f"- {arm.label} -", x, y, ACCENT, self.font_small)
            if arm.session.dead:
                y = self._text("  terminated", x, y, (240, 120, 100), self.font_small)
                y += 4
                continue
            org = arm.session.org
            sensed = org.sensed_intero
            y = self._text(f"  pos {org.x:>3},{org.y:<3}  age {org.body.age}",
                           x, y, DIM, self.font_small)
            y = self._text(f"  energy    {org.body.energy:6.2f}", x, y, font=self.font_small)
            y = self._text(f"  integrity {org.body.integrity:6.3f}", x, y, font=self.font_small)
            t_line = f"  temp      {org.body.temperature:6.3f}"
            if len(sensed) == 4 and abs(sensed[2] - org.body.temperature) > 1e-3:
                # The whole point of a dissociation arm: what it feels is not
                # what it is.
                t_line += f"   sensed {sensed[2]:.3f}"
                y = self._text(t_line, x, y, (240, 176, 96), self.font_small)
            else:
                y = self._text(t_line, x, y, font=self.font_small)
            y = self._draw_policy(arm, x + 4, y + 2)
            y += 6

        y = max(y + 10, self.screen.get_height() - 5 * 14 - 10)
        for line in ("space  pause", "->     step", "+ -    speed", "esc    quit"):
            y = self._text(line, x, y, DIM, self.font_small)

    def _draw_policy(self, arm: ArmView, x: int, y: int) -> int:
        """The action distribution itself, not the sampled action."""
        pg = self.pygame
        probs = self._probs(arm)
        if probs is None:
            return y
        labels = "·NESW"
        w, h = 20, 26
        for i, p in enumerate(probs):
            bx = x + i * (w + 3)
            pg.draw.rect(self.screen, (44, 46, 52), (bx, y, w, h))
            fill = int(h * float(p))
            pg.draw.rect(self.screen, (128, 188, 132), (bx, y + h - fill, w, fill))
            if self.font_small:
                self.screen.blit(self.font_small.render(labels[i], True, DIM),
                                 (bx + 6, y + h + 1))
        return y + h + 16

    def _draw_sparkline(self, x, y, w, h) -> int:
        pg = self.pygame
        pg.draw.rect(self.screen, (28, 30, 35), (x, y, w, h))
        pts = [p for p in self.tv_history if np.isfinite(p)]
        if len(pts) > 1:
            step = w / max(1, len(pts) - 1)
            coords = [(x + i * step, y + h - 2 - v * (h - 4)) for i, v in enumerate(pts)]
            pg.draw.lines(self.screen, (232, 176, 84), False, coords, 1)
        if self.font_small:
            # Below the box, not inside it: the trace runs the full height and a
            # label drawn over it is unreadable exactly when the divergence is
            # largest.
            self.screen.blit(self.font_small.render("policy divergence", True, DIM),
                             (x + 2, y + h + 2))
        return y + h + 15

    def tick(self) -> None:
        self.clock.tick(self.speed if not self.paused else 30)

    def close(self) -> None:
        self.pygame.quit()
