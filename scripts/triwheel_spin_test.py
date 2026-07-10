#!/usr/bin/env python3
"""TRI-WHEEL SPIN TEST — full-screen bench console (curses).

Arms all three launcher ESCs (upper pair ch 3/4 + bottom ch 6) and shows a
terminal dashboard readable from across the bench: per-wheel throttle bars
(with each wheel's measured floor marked ``|``), preset, base/diff, and a
message line. Same keys as before.

Run ON THE PI (needs the ``pi`` extra: ``uv sync --extra pi``):

    uv run python scripts/triwheel_spin_test.py --throttle 0.12 --diff 0.03

Live keys:
    1 / 2 / 3     preset: FLAT / TOPSPIN / BACKSPIN
    4 / 5         preset: SIDESPIN A-fast / B-fast (upper pair differential)
    + / -         base throttle +-0.01 (all wheels rescale)
    ] / [         spin differential +-0.01
    f             fire one ball (feed servo LOAD->DISCH->LOAD)
    d             FLOOR HUNT: ramp each wheel alone from zero; press any
                  key the moment it spins (x = skip wheel). Floors show as
                  ``|`` markers on the bars — AT TODAY'S BATTERY CHARGE.
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
wheel of a spin preset will stall.

SAFETY: all three wheels spin the whole session; keep hands out of the nip.
Pass --dry-run to rehearse off-hardware (still needs a real terminal).
"""

from __future__ import annotations

import argparse
import contextlib
import curses
import time
from typing import Any, Final

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
ARM_SECONDS: Final[float] = 3.0
SPINUP_SECONDS: Final[float] = 2.5
LOAD_ANGLE: Final[float] = 70.0  # v3 ring arm (2026-07-04)
DISCH_ANGLE: Final[float] = 175.0
FEED_DWELL: Final[float] = 0.65
SLICE: Final[float] = 0.05
STEP: Final[float] = 0.01  # fine steps — the whole useful range is ~0.05-0.20
FLOOR_START: Final[float] = 0.03  # floor hunt: ramp start
FLOOR_STEP: Final[float] = 0.005
FLOOR_DWELL: Final[float] = 0.6  # s per step, waiting for your keypress
FLOOR_MAX: Final[float] = 0.25
BAR_VMAX: Final[float] = 0.30  # bar full-scale (top of the useful band)
BAR_WIDTH: Final[int] = 44

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


def fire_one(rig: Rig) -> None:
    rig.feed(DISCH_ANGLE)
    time.sleep(FEED_DWELL)
    rig.feed(LOAD_ANGLE)
    time.sleep(FEED_DWELL)


def _bar(v: float, floor: float | None) -> str:
    """ASCII throttle bar with an optional ``|`` floor marker."""
    fill = round(_clamp(v / BAR_VMAX, 0.0, 1.0) * BAR_WIDTH)
    cells = ["#" if i < fill else "-" for i in range(BAR_WIDTH)]
    if floor is not None:
        pos = round(_clamp(floor / BAR_VMAX, 0.0, 1.0) * (BAR_WIDTH - 1))
        cells[pos] = "|"
    return "".join(cells)


class Console:
    """Curses dashboard: big per-wheel bars + status, non-blocking keys."""

    def __init__(self, scr: Any) -> None:
        self.scr = scr
        with contextlib.suppress(curses.error):  # some terminals can't hide the cursor
            curses.curs_set(0)
        scr.nodelay(True)
        self.msg_text = ""

    def key(self) -> str | None:
        ch = self.scr.getch()
        if ch == -1:
            return None
        if ch == ord(" "):
            return "space"
        if 0 <= ch < 256:
            return chr(ch)
        return None  # resize / function keys — ignore

    def drain_keys(self) -> None:
        while self.scr.getch() != -1:
            pass

    def msg(self, text: str) -> None:
        self.msg_text = text

    def draw(
        self,
        preset: str,
        base: float,
        diff: float,
        thr: tuple[float, float, float],
        fired: int,
        floors: dict[str, float],
        dry: bool,
    ) -> None:
        scr = self.scr

        def put(y: int, x: int, s: str, attr: int = 0) -> None:
            with contextlib.suppress(curses.error):  # tiny terminal — clip silently
                scr.addstr(y, x, s, attr)

        scr.erase()
        title = "TRI-WHEEL SPIN TEST" + ("  [DRY RUN]" if dry else "")
        put(0, 0, title, curses.A_BOLD)
        put(2, 0, f" {preset} ", curses.A_REVERSE | curses.A_BOLD)
        put(2, 16, f"base {base:.3f}   diff {diff:.3f}   balls {fired}")
        for i, name in enumerate(WHEEL_NAMES):
            floor = floors.get(name)
            row = f"{name:<3} {thr[i]:.3f} [{_bar(thr[i], floor)}]"
            put(4 + i, 0, row, curses.A_BOLD)
        if floors:
            floors_line = "floors: " + "  ".join(f"{k}={v:.3f}" for k, v in floors.items())
        else:
            floors_line = "floors: unknown — press d to hunt (they drift with battery charge)"
        put(8, 0, floors_line)
        put(10, 0, self.msg_text, curses.A_DIM)
        put(12, 0, "1 flat   2 topspin   3 backspin   4/5 sidespin   f fire   d floor hunt")
        put(13, 0, "+/- base   ]/[ diff   space E-STOP   q quit")
        scr.refresh()


def floor_hunt(
    rig: Rig,
    con: Console,
    fired: int,
    floors: dict[str, float],
) -> None:
    """Find each wheel's spin-up throttle floor at the current battery charge.

    Ramps ONE wheel at a time (others stopped) from FLOOR_START in FLOOR_STEP
    increments, dwelling FLOOR_DWELL at each. Press any key the moment the
    wheel starts to spin; x skips that wheel. Updates ``floors`` in place.
    """
    for i, name in enumerate(WHEEL_NAMES):
        if rig.dry_run:
            floors[name] = FLOOR_START + 4 * FLOOR_STEP  # simulated
            continue
        vals = [0.0, 0.0, 0.0]
        rig.wheels(vals[0], vals[1], vals[2])
        con.msg(f"FLOOR HUNT {name}: any key the moment it spins, x = skip")
        con.draw("HUNT", 0.0, 0.0, (vals[0], vals[1], vals[2]), fired, floors, rig.dry_run)
        time.sleep(1.0)  # let everything fully stop
        con.drain_keys()
        throttle = FLOOR_START
        while throttle <= FLOOR_MAX:
            vals[i] = throttle
            rig.wheels(vals[0], vals[1], vals[2])
            con.draw("HUNT", throttle, 0.0, (vals[0], vals[1], vals[2]), fired, floors, False)
            deadline = time.monotonic() + FLOOR_DWELL
            key = None
            while time.monotonic() < deadline:
                key = con.key()
                if key:
                    break
                time.sleep(0.02)
            if key == "x":
                break
            if key:
                floors[name] = throttle
                break
            throttle = round(throttle + FLOOR_STEP, 3)
        vals[i] = 0.0
        rig.wheels(vals[0], vals[1], vals[2])
        time.sleep(0.5)
    summary = "  ".join(f"{k}={v:.3f}" for k, v in floors.items()) if floors else "none found"
    prefix = "[dry] simulated " if rig.dry_run else ""
    con.msg(f"{prefix}floors @ today's charge: {summary}")


def run(scr: Any, args: argparse.Namespace) -> int:
    con = Console(scr)
    rig = Rig(dry_run=args.dry_run)
    base = _clamp(args.throttle, 0.0, 1.0)
    diff = _clamp(args.diff, 0.0, 0.3)
    preset = "FLAT"
    floors: dict[str, float] = {}
    fired = 0

    thr = (0.0, 0.0, 0.0)
    con.msg(
        f"arming 3 ESCs on ch {UPPER_ESC_A}/{UPPER_ESC_B}/{BOTTOM_ESC} "
        f"({ARM_SECONDS:.0f}s at zero throttle)..."
    )
    con.draw(preset, base, diff, thr, fired, floors, rig.dry_run)
    rig.wheels(*thr)
    rig.feed(LOAD_ANGLE)
    time.sleep(ARM_SECONDS)

    thr = mix(preset, base, diff)
    con.msg(f"spinning up {preset} at {base:.3f}...")
    con.draw(preset, base, diff, thr, fired, floors, rig.dry_run)
    rig.wheels(*thr)
    time.sleep(SPINUP_SECONDS)
    con.msg("ready")

    try:
        while True:
            key = con.key()
            if key in ("space", "q", "\x03"):
                break
            if key in PRESETS:
                preset = PRESETS[key]
            elif key in ("+", "="):
                base = _clamp(base + STEP, 0.0, 1.0)
            elif key == "-":
                base = _clamp(base - STEP, 0.0, 1.0)
            elif key == "]":
                diff = _clamp(diff + STEP, 0.0, 0.3)
            elif key == "[":
                diff = _clamp(diff - STEP, 0.0, 0.3)
            elif key == "f":
                fire_one(rig)
                fired += 1
                con.msg(f"ball {fired} fired ({preset})")
            elif key == "d":
                floor_hunt(rig, con, fired, floors)
                time.sleep(SPINUP_SECONDS)  # preset spins back up below
            thr = mix(preset, base, diff)
            rig.wheels(*thr)
            stalled = [
                name
                for name, t in zip(WHEEL_NAMES, thr, strict=True)
                if (fl := floors.get(name)) is not None and 0.0 < t < fl
            ]
            if stalled:
                con.msg(f"WARNING: {'/'.join(stalled)} below floor — stalled")
            con.draw(preset, base, diff, thr, fired, floors, rig.dry_run)
            time.sleep(SLICE)
    finally:
        rig.wheels(0.0, 0.0, 0.0)
        rig.feed(LOAD_ANGLE)
    return fired


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--throttle", type=float, default=0.12, help="base wheel power 0..1")
    p.add_argument("--diff", type=float, default=0.03, help="spin differential 0..0.3")
    p.add_argument("--dry-run", action="store_true", help="rehearse off-hardware")
    args = p.parse_args()

    try:
        fired = curses.wrapper(run, args)
    except KeyboardInterrupt:
        fired = -1
    if fired >= 0:
        print(f"Done — {fired} balls. All wheels stopped, feed at LOAD.")
    else:
        print("Interrupted — wheels stopped, feed at LOAD.")


if __name__ == "__main__":
    main()
