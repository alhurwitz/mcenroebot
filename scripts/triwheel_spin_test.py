#!/usr/bin/env python3
"""TRI-WHEEL SPIN TEST — Textual bench console.

Arms all three launcher ESCs (upper pair ch 3/4 + bottom ch 6) and shows a
full-screen dashboard readable from across a rattling bench: big digit
readouts for base/diff/balls, per-wheel throttle bars with each wheel's
measured floor marked in red, stall warnings, and footer key hints.

Needs the ``textual`` package: run ``uv add textual`` once, then on the Pi
(with the ``pi`` extra: ``uv sync --extra pi``):

    uv run python scripts/triwheel_spin_test.py --throttle 0.12 --diff 0.03

Live keys:
    1 / 2 / 3     preset: FLAT / TOPSPIN / BACKSPIN
    4 / 5         preset: SIDESPIN A-fast / B-fast (upper pair differential)
    + / -         base throttle +-0.01 (all wheels rescale)
    ] / [         spin differential +-0.01
    f             fire one ball (feed servo LOAD->DISCH->LOAD)
    d             FLOOR HUNT: ramp each wheel alone from zero; press any
                  key the moment it spins (x = skip wheel). Floors show as
                  red ticks on the bars — AT TODAY'S BATTERY CHARGE.
    space         E-STOP: all wheels to zero, feed to LOAD, exit
    q             quit gracefully

Channel map (src/mcenroebot/channel_map.py is SSOT): pan=0, tilt=1,
head-roll=2, upper-pair ESCs 3/4 (SSOT names WHEEL_TOP/WHEEL_BOTTOM —
the v3 stacked-pair names, kept per the 2026-07-04 no-rename decision;
in the v4 tri bracket those two channels drive the UPPER PAIR), tri
bottom ESC = WHEEL_TRI_BOTTOM = 6, feed servo = 5.

DEADBAND NOTE (bench, 2026-07-10): these ESCs are open-loop — throttle is
just duty cycle, so the spin-up floor AND rpm-per-throttle scale with pack
voltage. The floor drifts with battery charge (and creeps up as the pack
sags mid-session). Re-run the 'd' floor hunt whenever the battery changes.
First measured floors (2026-07-10): A=0.050 B=0.045 BOT=0.045.

SPEED NOTE (bench, 2026-07): even ONE wheel at 20% throttle fired "really
fast" — the useful window is roughly floor+0.02 to 0.20. A wheel commanded
below its floor stops entirely, so at low base keep diff small or the slow
wheel of a spin preset will stall (the bar turns red when that happens).

SAFETY: all three wheels spin the whole session; keep hands out of the nip.
Pass --dry-run to rehearse off-hardware (still needs a real terminal).
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any, ClassVar, Final

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Digits, Footer, Label, Static

try:  # single source of truth when running from the repo (uv run ...)
    from mcenroebot.channel_map import (
        FEED_MAX_US,
        FEED_MIN_US,
        FEED_SERVO,
        WHEEL_BOTTOM,
        WHEEL_TOP,
        WHEEL_TRI_BOTTOM,
    )
except ImportError:  # standalone copy — literals mirror channel_map.py
    FEED_SERVO = 5
    FEED_MIN_US = 500
    FEED_MAX_US = 2500
    WHEEL_TOP = 3
    WHEEL_BOTTOM = 4
    WHEEL_TRI_BOTTOM = 6

# Local roles for the v4 tri bracket: ch3/4 ESCs drive the upper pair,
# ch6 drives the wheel under the ball path.
UPPER_ESC_A: Final[int] = WHEEL_TOP
UPPER_ESC_B: Final[int] = WHEEL_BOTTOM
BOTTOM_ESC: Final[int] = WHEEL_TRI_BOTTOM

ESC_MIN_US: Final[int] = 1000  # standard airplane-ESC throttle range
ESC_MAX_US: Final[int] = 2000
ARM_SECONDS = 3.0  # not Final: tests shrink these
SPINUP_SECONDS = 2.5
FEED_DWELL = 0.65
LOAD_ANGLE: Final[float] = 70.0  # v3 ring arm (2026-07-04)
DISCH_ANGLE: Final[float] = 175.0
STEP: Final[float] = 0.01  # fine steps — the whole useful range is ~0.05-0.20
FLOOR_START: Final[float] = 0.03  # floor hunt: ramp start
FLOOR_STEP: Final[float] = 0.005
FLOOR_DWELL: Final[float] = 0.6  # s per step, waiting for your keypress
FLOOR_MAX: Final[float] = 0.25
BAR_VMAX: Final[float] = 0.30  # bar full-scale (top of the useful band)
BAR_WIDTH: Final[int] = 50

WHEEL_NAMES: Final[tuple[str, str, str]] = ("A", "B", "BOT")

PRESETS: Final[dict[str, str]] = {
    "1": "FLAT",
    "2": "TOPSPIN",
    "3": "BACKSPIN",
    "4": "SIDE A-fast",
    "5": "SIDE B-fast",
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def mix(preset: str, base: float, diff: float) -> tuple[float, float, float]:
    """Return (upper_A, upper_B, bottom) throttles for a preset."""
    a = b = bot = base
    if preset == "TOPSPIN":
        a = b = base + diff
        bot = base - diff
    elif preset == "BACKSPIN":
        a = b = base - diff
        bot = base + diff
    elif preset == "SIDE A-fast":
        a, b = base + diff, base - diff
    elif preset == "SIDE B-fast":
        a, b = base - diff, base + diff
    return tuple(_clamp(v, 0.0, 1.0) for v in (a, b, bot))  # type: ignore[return-value]


class Rig:
    """Three wheel ESCs + one positional feed servo on the PCA9685."""

    def __init__(self, dry_run: bool) -> None:
        self.dry_run = dry_run
        if dry_run:
            self._escs: Any = None
            self._feed: Any = None
            return
        try:
            from adafruit_servokit import ServoKit  # lazy: Pi-only extra
        except ImportError as exc:  # pragma: no cover - hardware path
            raise ImportError(
                f"{exc}\nRun on the Pi after `uv sync --extra pi`, "
                "or pass --dry-run to rehearse off-hardware."
            ) from exc
        kit = ServoKit(channels=16)
        chans = (UPPER_ESC_A, UPPER_ESC_B, BOTTOM_ESC)
        self._escs = [kit.continuous_servo[c] for c in chans]
        for esc in self._escs:
            esc.set_pulse_width_range(ESC_MIN_US, ESC_MAX_US)
        self._feed = kit.servo[FEED_SERVO]
        self._feed.set_pulse_width_range(FEED_MIN_US, FEED_MAX_US)

    def wheels(self, a: float, b: float, bot: float) -> None:
        """Per-wheel power 0..1 -> ESC throttle (-1 = 1000us = stopped)."""
        if self.dry_run:
            return
        vals = [_clamp(v, 0.0, 1.0) for v in (a, b, bot)]
        for esc, v in zip(self._escs, vals, strict=True):
            esc.throttle = -1.0 + 2.0 * v

    def feed(self, angle: float) -> None:
        if self.dry_run:
            return
        self._feed.angle = _clamp(angle, 0.0, 180.0)


def _bar_text(name: str, value: float, floor: float | None) -> Text:
    """One wheel row: name, value, bar with red floor tick; red if stalled."""
    stalled = floor is not None and 0.0 < value < floor
    fill = round(_clamp(value / BAR_VMAX, 0.0, 1.0) * BAR_WIDTH)
    floor_pos = None
    if floor is not None:
        floor_pos = round(_clamp(floor / BAR_VMAX, 0.0, 1.0) * (BAR_WIDTH - 1))
    fill_style = "bold red" if stalled else "bold green"
    text = Text(f"{name:<4}{value:.3f} ", style="bold")
    for i in range(BAR_WIDTH):
        if i == floor_pos:
            text.append("▎", "bold red")
        elif i < fill:
            text.append("█", fill_style)
        else:
            text.append("╌", "grey37")
    if stalled:
        text.append("  STALLED", "bold red blink")
    return text


class SpinTestApp(App[int]):
    """Bench console for the tri-wheel launcher."""

    TITLE = "TRI-WHEEL SPIN TEST"

    CSS = """
    #title { padding: 0 1; text-style: bold; background: $primary; color: $text; }
    #readouts { height: 5; padding: 0 1; }
    #readouts Vertical { width: 18; }
    #readouts Label { color: $text-muted; }
    #preset { text-style: bold reverse; padding: 0 1; width: auto; }
    .bar { height: 1; padding: 0 1; }
    #floors { padding: 0 1; color: $text-muted; }
    #message { padding: 1 1 0 1; color: $warning; text-style: bold; }
    """

    BINDINGS: ClassVar = [
        Binding("1", "preset('1')", "flat"),
        Binding("2", "preset('2')", "topspin"),
        Binding("3", "preset('3')", "backspin"),
        Binding("4", "preset('4')", "sideA", show=False),
        Binding("5", "preset('5')", "sideB", show=False),
        Binding("f", "fire", "fire"),
        Binding("d", "floor_hunt", "floor hunt"),
        Binding("space", "estop", "E-STOP"),
        Binding("q", "quit_app", "quit"),
    ]

    def __init__(self, dry_run: bool, base: float, diff: float) -> None:
        super().__init__()
        self.rig = Rig(dry_run=dry_run)
        self.base = _clamp(base, 0.0, 1.0)
        self.diff = _clamp(diff, 0.0, 0.3)
        self.preset = "FLAT"
        self.floors: dict[str, float] = {}
        self.fired = 0
        self.armed = False
        self.hunting = False
        self._hunt_keys: asyncio.Queue[str] = asyncio.Queue()
        self._thr: tuple[float, float, float] = (0.0, 0.0, 0.0)

    # --- layout -----------------------------------------------------------

    def compose(self) -> ComposeResult:
        dry = "  [DRY RUN]" if self.rig.dry_run else ""
        yield Static(f" {self.TITLE}{dry}", id="title")
        with Horizontal(id="readouts"):
            with Vertical():
                yield Label("BASE")
                yield Digits("0.000", id="base")
            with Vertical():
                yield Label("DIFF")
                yield Digits("0.000", id="diff")
            with Vertical():
                yield Label("BALLS")
                yield Digits("0", id="balls")
            with Vertical():
                yield Label("PRESET")
                yield Static("FLAT", id="preset")
        for name in WHEEL_NAMES:
            yield Static(id=f"bar-{name}", classes="bar")
        yield Static(id="floors")
        yield Static(id="message")
        yield Footer()

    # --- state -> screen ----------------------------------------------------

    def _refresh(self) -> None:
        self.query_one("#base", Digits).update(f"{self.base:.3f}")
        self.query_one("#diff", Digits).update(f"{self.diff:.3f}")
        self.query_one("#balls", Digits).update(str(self.fired))
        self.query_one("#preset", Static).update(self.preset)
        for i, name in enumerate(WHEEL_NAMES):
            bar = _bar_text(name, self._thr[i], self.floors.get(name))
            self.query_one(f"#bar-{name}", Static).update(bar)
        if self.floors:
            floors = "floors @ this charge:  " + "   ".join(
                f"{k}={v:.3f}" for k, v in self.floors.items()
            )
        else:
            floors = "floors unknown — press d to hunt (they drift with battery charge)"
        self.query_one("#floors", Static).update(floors)

    def _message(self, text: str) -> None:
        self.query_one("#message", Static).update(text)

    def _apply(self) -> None:
        """Recompute the mix, command the ESCs, redraw."""
        self._thr = mix(self.preset, self.base, self.diff)
        self.rig.wheels(*self._thr)
        self._refresh()

    def _rig_stop(self) -> None:
        self.rig.wheels(0.0, 0.0, 0.0)
        self.rig.feed(LOAD_ANGLE)

    # --- lifecycle ----------------------------------------------------------

    def on_mount(self) -> None:
        self._refresh()
        self.run_worker(self._arm(), exclusive=True)

    async def _arm(self) -> None:
        self._message(
            f"arming 3 ESCs on ch {UPPER_ESC_A}/{UPPER_ESC_B}/{BOTTOM_ESC} "
            f"({ARM_SECONDS:.0f}s at zero throttle)..."
        )
        self.rig.wheels(0.0, 0.0, 0.0)
        self.rig.feed(LOAD_ANGLE)
        await asyncio.sleep(ARM_SECONDS)
        self._message(f"spinning up {self.preset} at {self.base:.3f}...")
        self._apply()
        await asyncio.sleep(SPINUP_SECONDS)
        self.armed = True
        self._message("ready — keep hands out of the nip")

    # --- keys ---------------------------------------------------------------

    def on_key(self, event: Any) -> None:
        if self.hunting:  # any key marks spin-up (x skips) — see _hunt
            self._hunt_keys.put_nowait(event.key)
            event.stop()
            event.prevent_default()
            return
        # +/-/]/[ aren't clean binding names; match key name OR character
        ch = getattr(event, "character", None)
        if event.key in ("plus", "equals_sign") or ch in ("+", "="):
            self._bump(base=STEP)
        elif event.key == "minus" or ch == "-":
            self._bump(base=-STEP)
        elif event.key == "right_square_bracket" or ch == "]":
            self._bump(diff=STEP)
        elif event.key == "left_square_bracket" or ch == "[":
            self._bump(diff=-STEP)

    def _bump(self, base: float = 0.0, diff: float = 0.0) -> None:
        if not self.armed:
            return
        self.base = _clamp(self.base + base, 0.0, 1.0)
        self.diff = _clamp(self.diff + diff, 0.0, 0.3)
        self._apply()

    # --- actions --------------------------------------------------------------

    def action_preset(self, key: str) -> None:
        if not self.armed or self.hunting:
            return
        self.preset = PRESETS[key]
        self._apply()

    def action_fire(self) -> None:
        if not self.armed or self.hunting:
            return
        self.run_worker(self._fire(), exclusive=True)

    async def _fire(self) -> None:
        self.rig.feed(DISCH_ANGLE)
        await asyncio.sleep(FEED_DWELL)
        self.rig.feed(LOAD_ANGLE)
        await asyncio.sleep(FEED_DWELL)
        self.fired += 1
        self._message(f"ball {self.fired} fired ({self.preset})")
        self._refresh()

    def action_floor_hunt(self) -> None:
        if not self.armed or self.hunting:
            return
        self.run_worker(self._hunt(), exclusive=True)

    async def _hunt(self) -> None:
        self.hunting = True
        try:
            for i, name in enumerate(WHEEL_NAMES):
                if self.rig.dry_run:
                    self.floors[name] = FLOOR_START + 4 * FLOOR_STEP  # simulated
                    continue
                vals = [0.0, 0.0, 0.0]
                self.rig.wheels(vals[0], vals[1], vals[2])
                self._thr = (vals[0], vals[1], vals[2])
                self._message(f"FLOOR HUNT {name}: any key the moment it spins — x skips")
                self._refresh()
                await asyncio.sleep(1.0)  # let everything fully stop
                while not self._hunt_keys.empty():
                    self._hunt_keys.get_nowait()
                throttle = FLOOR_START
                while throttle <= FLOOR_MAX:
                    vals[i] = throttle
                    self.rig.wheels(vals[0], vals[1], vals[2])
                    self._thr = (vals[0], vals[1], vals[2])
                    self._refresh()
                    try:
                        key = await asyncio.wait_for(self._hunt_keys.get(), FLOOR_DWELL)
                    except TimeoutError:
                        throttle = round(throttle + FLOOR_STEP, 3)
                        continue
                    if key != "x":
                        self.floors[name] = throttle
                    break
                vals[i] = 0.0
                self.rig.wheels(vals[0], vals[1], vals[2])
                await asyncio.sleep(0.5)
            if self.floors:
                summary = "   ".join(f"{k}={v:.3f}" for k, v in self.floors.items())
                prefix = "[dry] simulated " if self.rig.dry_run else ""
                self._message(f"{prefix}floors @ today's charge:  {summary}")
            else:
                self._message("floor hunt: nothing recorded")
        finally:
            self.hunting = False
            self._apply()  # spin the preset back up

    def action_estop(self) -> None:
        self._rig_stop()
        self.exit(self.fired)

    def action_quit_app(self) -> None:
        self._rig_stop()
        self.exit(self.fired)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--throttle", type=float, default=0.12, help="base wheel power 0..1")
    p.add_argument("--diff", type=float, default=0.03, help="spin differential 0..0.3")
    p.add_argument("--dry-run", action="store_true", help="rehearse off-hardware")
    args = p.parse_args()

    app = SpinTestApp(dry_run=args.dry_run, base=args.throttle, diff=args.diff)
    try:
        fired = app.run()
    finally:
        app._rig_stop()  # belt and braces — idempotent
    print(f"Done — {fired or 0} balls. All wheels stopped, feed at LOAD.")


if __name__ == "__main__":
    main()
