"""Pygame renderer for SimulationSnapshot.

Consumes snapshots. Never touches a Simulation, so the same renderer drives a
live run and a recorded one, and the simulator cannot acquire a dependency on
whether anyone is watching.
"""
from __future__ import annotations

import collections
from dataclasses import dataclass

import numpy as np

from emergent_self.snapshot import RecordingHeader, SimulationSnapshot
from emergent_self.viz import palette

PANEL_W = 330
BG = (16, 17, 20)
FG = (226, 228, 232)
DIM = (128, 132, 140)
ACCENT = (232, 176, 84)

#: What the agent dot's colour encodes. Cycled with the TAB key.
OVERLAYS = ("temperature", "energy", "integrity", "lineage", "age", "in_band")

HELP = [
    "space  pause/resume",
    "<- ->  step while paused",
    "+ -    speed",
    "tab    colour overlay",
    "t      trails",
    "r      resources",
    "click  inspect an organism",
    "esc    quit",
]


def _load_fonts(pygame):
    """Return (normal, small, big), or (None, None, None) if text is unavailable.

    Some pygame builds ship a broken font module - pygame 2.6.1 on Python 3.14
    raises on import - and a visualiser that refuses to open at all is worse
    than one that draws the world without labels. Install the `viz` extra, which
    pins pygame-ce, to get text.
    """
    try:
        return (pygame.font.SysFont("monospace", 13),
                pygame.font.SysFont("monospace", 11),
                pygame.font.SysFont("monospace", 16, bold=True))
    except Exception as exc:  # pragma: no cover - depends on the local build
        print(f"warning: pygame font module unavailable ({exc}); drawing without text. "
              f"Install the viz extra (pygame-ce) for labels.")
        return None, None, None


@dataclass
class ViewState:
    paused: bool = False
    speed: int = 8           # target steps per second
    overlay: int = 0
    trails: bool = True
    show_resources: bool = True
    selected: int | None = None
    quit: bool = False
    step_once: bool = False
    #: Only a recording can step backwards; a live run ignores this.
    step_back: bool = False


class Renderer:
    def __init__(self, header: RecordingHeader, cell: int = 18, trail_len: int = 24):
        import pygame

        self.pygame = pygame
        self.header = header
        self.size = header.size
        self.cell = cell
        self.trail_len = trail_len
        self.grid_px = self.size * cell

        pygame.init()
        pygame.display.set_caption("Emergent Self Lab")
        self.screen = pygame.display.set_mode((self.grid_px + PANEL_W, max(self.grid_px, 560)))
        self.font, self.font_small, self.font_big = _load_fonts(pygame)
        self.clock = pygame.time.Clock()

        # The thermal field is static, so it is rasterised once.
        arr = palette.ambient_surface_array(header.ambient_array)
        surf = pygame.surfarray.make_surface(arr)
        self.background = pygame.transform.scale(surf, (self.grid_px, self.grid_px))

        self.state = ViewState()
        self.trails: dict[int, collections.deque] = {}
        self.flashes: list[tuple[int, int, int, tuple[int, int, int]]] = []
        self._band_history: collections.deque = collections.deque(maxlen=self.grid_px // 2)

    # ------------------------------------------------------------------ input

    def handle_input(self) -> ViewState:
        pg = self.pygame
        st = self.state
        st.step_once = False
        st.step_back = False
        for e in pg.event.get():
            if e.type == pg.QUIT:
                st.quit = True
            elif e.type == pg.KEYDOWN:
                if e.key in (pg.K_ESCAPE, pg.K_q):
                    st.quit = True
                elif e.key == pg.K_SPACE:
                    st.paused = not st.paused
                elif e.key in (pg.K_RIGHT, pg.K_LEFT):
                    st.step_once = True
                    st.step_back = e.key == pg.K_LEFT
                elif e.key in (pg.K_PLUS, pg.K_EQUALS):
                    st.speed = min(240, st.speed * 2)
                elif e.key == pg.K_MINUS:
                    st.speed = max(1, st.speed // 2)
                elif e.key == pg.K_TAB:
                    st.overlay = (st.overlay + 1) % len(OVERLAYS)
                elif e.key == pg.K_t:
                    st.trails = not st.trails
                elif e.key == pg.K_r:
                    st.show_resources = not st.show_resources
            elif e.type == pg.MOUSEBUTTONDOWN and e.pos[0] < self.grid_px:
                self._select_at(e.pos)
        return st

    def _select_at(self, pos) -> None:
        gx, gy = pos[0] // self.cell, pos[1] // self.cell
        best, best_d = None, 9
        for ident, (ax, ay) in self._positions.items():
            d = abs(ax - gx) + abs(ay - gy)
            if d < best_d:
                best, best_d = ident, d
        self.state.selected = best

    # ----------------------------------------------------------------- colour

    def _agent_color(self, a) -> tuple[int, int, int]:
        mode = OVERLAYS[self.state.overlay]
        if mode == "temperature":
            return palette.thermal(a.temperature)
        if mode == "energy":
            return palette.viability(min(1.0, a.energy / self.header.energy_max))
        if mode == "integrity":
            return palette.viability(a.integrity)
        if mode == "lineage":
            return palette.lineage(a.founder)
        if mode == "age":
            return palette.viability(1.0 - min(1.0, a.age / 400.0))
        return (128, 188, 132) if a.in_band else (196, 88, 72)

    # ------------------------------------------------------------------- draw

    def draw(self, snap: SimulationSnapshot) -> None:
        pg = self.pygame
        self.screen.fill(BG)
        self.screen.blit(self.background, (0, 0))
        self._positions = {a.ident: (a.x, a.y) for a in snap.agents}

        self._draw_band_outline()
        if self.state.show_resources:
            self._draw_resources(snap)
        self._update_flashes(snap)
        if self.state.trails:
            self._draw_trails(snap)
        self._draw_agents(snap)
        self._draw_panel(snap)
        pg.display.flip()

    def _draw_band_outline(self) -> None:
        """Mark the cells whose ambient temperature is itself inside the viable
        band. These are the places an organism can rest without paying."""
        amb = self.header.ambient_array
        mask = (amb >= self.header.viable_temp_lo) & (amb <= self.header.viable_temp_hi)
        overlay = self.pygame.Surface((self.grid_px, self.grid_px), self.pygame.SRCALPHA)
        for x, y in zip(*np.nonzero(mask)):
            self.pygame.draw.rect(
                overlay, (235, 238, 245, 16),
                (x * self.cell, y * self.cell, self.cell, self.cell))
        self.screen.blit(overlay, (0, 0))

    def _draw_resources(self, snap) -> None:
        c = self.cell
        for x, y in snap.resources:
            self.pygame.draw.circle(
                self.screen, (150, 196, 128),
                (x * c + c // 2, y * c + c // 2), max(2, c // 6))

    #: (ttl, colour) per event kind. A flash shrinks and fades as its ttl runs
    #: down, so events read as brief pulses. Growing rings that outlive several
    #: steps swamp the grid: with tens of ingestion events per step the screen
    #: fills with outlines and the organisms stop being visible.
    _FLASH = {
        "birth": (5, (150, 220, 160)),
        "death": (5, (222, 110, 96)),
        "consume": (3, (205, 225, 165)),
    }

    def _update_flashes(self, snap) -> None:
        self.flashes = [(x, y, t - 1, col) for x, y, t, col in self.flashes if t > 1]
        pos = self._positions
        for e in snap.events:
            kind = e[0]
            if kind not in self._FLASH:
                continue
            ttl, col = self._FLASH[kind]
            if kind == "birth":
                if e[1] in pos:
                    self.flashes.append((*pos[e[1]], ttl, col))
            elif kind == "death":
                # ("death", ident, x, y): the organism is already gone from the
                # snapshot, so the event carries its last position.
                self.flashes.append((e[2], e[3], ttl, col))
            else:
                self.flashes.append((e[1], e[2], ttl, col))

        c = self.cell
        surf = self.pygame.Surface((self.grid_px, self.grid_px), self.pygame.SRCALPHA)
        for x, y, t, col in self.flashes:
            radius = max(2, int(c * 0.30) + t)
            alpha = int(200 * t / 6)
            self.pygame.draw.circle(surf, (*col, alpha),
                                    (x * c + c // 2, y * c + c // 2), radius, 1)
        self.screen.blit(surf, (0, 0))

    def _draw_trails(self, snap) -> None:
        live = set(self._positions)
        for ident in list(self.trails):
            if ident not in live:
                del self.trails[ident]
        for a in snap.agents:
            self.trails.setdefault(a.ident, collections.deque(maxlen=self.trail_len)).append((a.x, a.y))

        c = self.cell
        founders = {a.ident: a.founder for a in snap.agents}
        surf = self.pygame.Surface((self.grid_px, self.grid_px), self.pygame.SRCALPHA)
        for ident, path in self.trails.items():
            if len(path) < 2:
                continue
            # Colour by lineage, matching the agent overlay. Colouring by ident
            # gave siblings of one lineage different trails.
            col = palette.lineage(founders.get(ident, ident))
            for i, (x, y) in enumerate(path):
                alpha = int(90 * (i + 1) / len(path))
                self.pygame.draw.circle(surf, (*col, alpha),
                                        (x * c + c // 2, y * c + c // 2), max(1, c // 7))
        self.screen.blit(surf, (0, 0))

    def _draw_agents(self, snap) -> None:
        c = self.cell
        r = max(3, c // 2 - 2)
        for a in snap.agents:
            cx, cy = a.x * c + c // 2, a.y * c + c // 2
            self.pygame.draw.circle(self.screen, self._agent_color(a), (cx, cy), r)
            # A ring marks an organism outside the viable band, so a thermal
            # problem is visible under every overlay, not only the thermal one.
            if not a.in_band:
                self.pygame.draw.circle(self.screen, (240, 120, 100), (cx, cy), r + 2, 1)
            if a.ident == self.state.selected:
                self.pygame.draw.circle(self.screen, ACCENT, (cx, cy), r + 5, 2)

    # ------------------------------------------------------------------ panel

    def _text(self, s, x, y, col=FG, font=None) -> int:
        f = font or self.font
        if f is None:
            return y + 14
        self.screen.blit(f.render(s, True, col), (x, y))
        return y + f.get_linesize() + 1

    def _bar(self, x, y, w, frac, col, label, value) -> int:
        pg = self.pygame
        frac = min(1.0, max(0.0, frac))
        pg.draw.rect(self.screen, (44, 46, 52), (x, y, w, 11))
        pg.draw.rect(self.screen, col, (x, y, int(w * frac), 11))
        if self.font_small is not None:
            self.screen.blit(self.font_small.render(f"{label} {value}", True, FG), (x + 4, y - 1))
        return y + 17

    def _draw_panel(self, snap) -> None:
        x = self.grid_px + 14
        y = 12
        y = self._text(f"step {snap.step}", x, y, font=self.font_big)
        y = self._text(f"population   {snap.population}", x, y)
        y = self._text(f"lineages     {int(snap.stats.get('n_founders', 0))}", x, y)
        y = self._text(f"births       {int(snap.stats.get('births', 0))}", x, y)
        y = self._text(f"deaths       {int(snap.stats.get('deaths', 0))}", x, y)
        y = self._text(f"resources    {len(snap.resources)}", x, y)
        y += 6

        band = snap.stats.get("band_occupancy", 0.0)
        self._band_history.append(band)
        y = self._bar(x, y + 6, PANEL_W - 30, band, (128, 188, 132),
                      "in viable band", f"{band:5.1%}")
        y = self._draw_sparkline(x, y + 2, PANEL_W - 30, 34)
        y += 8

        y = self._text(f"colour: {OVERLAYS[self.state.overlay]}", x, y, ACCENT)
        y = self._text(f"{'paused' if self.state.paused else 'running'}  "
                       f"{self.state.speed} steps/s", x, y, DIM)
        y += 8

        sel = next((a for a in snap.agents if a.ident == self.state.selected), None)
        y = self._text("- body monitor -", x, y, ACCENT)
        if sel is None:
            y = self._text("click an organism", x, y, DIM)
        else:
            y = self._text(f"id {sel.ident}  lineage {sel.founder}", x, y)
            y += 8
            y = self._bar(x, y, PANEL_W - 30, sel.energy / self.header.energy_max,
                          (206, 168, 82), "energy   ", f"{sel.energy:5.2f}")
            y = self._bar(x, y, PANEL_W - 30, sel.integrity,
                          (128, 188, 132), "integrity", f"{sel.integrity:5.2f}")
            y = self._bar(x, y, PANEL_W - 30, sel.temperature,
                          palette.thermal(sel.temperature), "temp     ", f"{sel.temperature:5.2f}")
            lo, hi = self.header.viable_temp_lo, self.header.viable_temp_hi
            y = self._text(f"band {lo:.2f}-{hi:.2f}  "
                           f"{'inside' if sel.in_band else 'OUTSIDE'}", x, y,
                           FG if sel.in_band else (240, 120, 100), self.font_small)
            y = self._text(f"age {sel.age}   action {sel.action}", x, y, DIM, self.font_small)

            # Sensed versus physical. Under an ablation or a false-body
            # intervention these diverge, and the divergence is the experiment.
            if len(sel.sensed_intero) == 4:
                se, si, st_, sa = sel.sensed_intero
                phys = (sel.energy / self.header.energy_max, sel.integrity,
                        sel.temperature, None)
                y += 6
                y = self._text("sensed body (as delivered)", x, y, ACCENT, self.font_small)
                for name, sv, pv in (("energy", se, phys[0]), ("integrity", si, phys[1]),
                                     ("temp", st_, phys[2])):
                    diverged = pv is not None and abs(sv - pv) > 1e-3
                    y = self._text(
                        f"  {name:<10}{sv:5.2f}" + (f"   true {pv:5.2f}" if diverged else ""),
                        x, y, (240, 176, 96) if diverged else DIM, self.font_small)

        y = max(y + 14, self.screen.get_height() - len(HELP) * 14 - 12)
        for line in HELP:
            y = self._text(line, x, y, DIM, self.font_small)

    def _draw_sparkline(self, x, y, w, h) -> int:
        pg = self.pygame
        pg.draw.rect(self.screen, (28, 30, 35), (x, y, w, h))
        pts = list(self._band_history)
        if len(pts) > 1:
            step = w / max(1, len(pts) - 1)
            coords = [(x + i * step, y + h - 2 - v * (h - 4)) for i, v in enumerate(pts)]
            pg.draw.lines(self.screen, (128, 188, 132), False, coords, 1)
        if self.font_small is not None:
            self.screen.blit(self.font_small.render("band occupancy", True, DIM), (x + 4, y + h - 13))
        return y + h

    def tick(self) -> None:
        self.clock.tick(self.state.speed if not self.state.paused else 30)

    def close(self) -> None:
        self.pygame.quit()
