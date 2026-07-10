#!/usr/bin/env python3
"""TRI-WHEEL SPIN TEST — first all-three-wheels bring-up (2026-07-10).

Arms all three launcher ESCs (upper pair ch 3/4 + NEW bottom ch 6), then
lets you flip between spin presets and fire balls to see the spin for real.

Spin convention (contact surfaces all move in the launch direction):
    TOPSPIN  = upper pair FASTER than bottom  (top of ball driven forward)
    BACKSPIN = bottom FASTER than upper pair
    SIDESPIN = the two upper wheels differ (A vs B) — direction TBD on bench,
               note which way preset 4 curves and label it in this docstring.

Run ON THE PI (needs the ``pi`` extra: ``uv sync --extra pi``):

    uv run python scripts/triwheel_spin_test.py --throttle 0.12 --diff 0.03

Live keys:
    1 / 2 / 3     preset: FLAT / TOPSPIN / BACKSPIN
    4 / 5         preset: SIDESPIN A-fast / B-fast (upper pair differential)
    + / -         base throttle +-0.01 (all wheels rescale)
    ] / [         spin differential +-0.01
    f             fire one ball (feed servo LOAD->DISCH->LOAD)
    d             FLOOR HUNT: ramp each wheel alone from zero; press any
                  key the moment it spins (x = skip wheel). Prints each
                  wheel's spin-up floor AT TODAY'S BATTERY CHARGE.
    space         E-STOP: all wheels to zero, feed to LOAD, exit
    q             quit gracefully

Channel map (src/mcenroebot/channel_map.py is SSOT): pan=0, tilt=1,
head-roll=2, upper-pair ESCs 3/4 (SSOT names WHEEL_TOP/WHEEL_BOTTOM —
the v3 stacked-pair names, kept per the 2026-07-04 no-rename decision;
in the v4 tri bracket those two channels drive the UPPER PAIR), tri
bottom ESC = WHEEL_TRI_BOTTOM = 6, feed servo = 5.

NEW-ESC NOTE: if the fresh bottom ESC won't arm (endless beeping), it may
need one-time throttle-range calibration — do that per its manual before
this test, or it will sit silent while the pair spins.

DEADBAND NOTE (bench, 2026-07-10): these ESCs are open-loop — throttle is
just duty cycle, so the spin-up floor AND rpm-per-throttle scale with pack
voltage. The floor drifts with battery charge (and creeps up as the pack
sags mid-session). Re-run the 'd' floor hunt whenever the battery changes,
and feed the numbers into ThrottleMap's per-wheel floors.

SPEED NOTE (bench, 2026-07): even ONE wheel at 20% throttle fired "really
fast" — with three wheels gripping, the useful window is roughly 0.10-0.20,
just above the ~9% ESC deadband. Below ~0.09 a wheel stops entirely, so at
low base keep diff small or the slow wheel of a spin preset will stall.

SAFETY: all three wheels spin the whole session; keep hands out of the nip.
Pass --dry-run to rehearse off-hardware.
"""

from __future__ import annotations

import argparse
import select
import sys
import termios
import time
import tty
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
STEP: Final[float] = 0.01  # fine steps — the whole useful range is ~0.09-0.20
FLOOR_START: Final[float] = 0.04  # floor hunt: ramp start
FLOOR_STEP: Final[float] = 0.005
FLOOR_DWELL: Final[float] = 0.6  # s per step, waiting for your keypress
FLOOR_MAX: Final[float] = 0.25

PRESETS: Final[dict[str, str]] = {
    "1": "FLAT",
    "2": "TOPSPIN",
    "3": "BACKSPIN",
    "4": "SIDE A-fast",
    "5": "SIDE B-fast",
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def poll_key() -> str | None:
    """Non-blocking single keypress; caller must already be in raw mode."""
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return None
    ch = sys.stdin.read(1)
    if ch == "":  # EOF (piped dry-run) — quit cleanly
        return "q"
    return "space" if ch == " " else ch


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
        vals = [_clamp(v, 0.0, 1.0) for v in (a, b, bot)]
        if self.dry_run:
            print(
                f"\r[dry] A {vals[0]:.2f}  B {vals[1]:.2f}  BOT {vals[2]:.2f}   ",
                end="",
                flush=True,
            )
            return
        for esc, v in zip(self._escs, vals, strict=True):
            esc.throttle = -1.0 + 2.0 * v

    def feed(self, angle: float) -> None:
        if self.dry_run:
            print(f"\r[dry] feed -> {angle:.0f} deg   ", end="", flush=True)
            return
        self._feed.angle = _clamp(angle, 0.0, 180.0)


def fire_one(rig: Rig) -> None:
    rig.feed(DISCH_ANGLE)
    time.sleep(FEED_DWELL)
    rig.feed(LOAD_ANGLE)
    time.sleep(FEED_DWELL)


def floor_hunt(rig: Rig) -> dict[str, float]:
    """Find each wheel's spin-up throttle floor at the current battery charge.

    Ramps ONE wheel at a time (others stopped) from FLOOR_START in FLOOR_STEP
    increments, dwelling FLOOR_DWELL at each. Press any key the moment the
    wheel starts to spin; x skips that wheel. Caller is already in raw mode,
    hence the explicit \r\n line endings.
    """
    names = ("A", "B", "BOT")
    floors: dict[str, float] = {}
    print("\r\nFLOOR HUNT — watch each wheel: any key = spinning, x = skip", end="\r\n")
    for i, name in enumerate(names):
        if rig.dry_run:
            floors[name] = FLOOR_START + 10 * FLOOR_STEP  # simulated
            print(f"[dry] {name} floor {floors[name]:.3f}", end="\r\n")
            continue
        vals = [0.0, 0.0, 0.0]
        rig.wheels(*vals)
        time.sleep(1.0)  # let it fully stop
        throttle = FLOOR_START
        while throttle <= FLOOR_MAX:
            vals[i] = throttle
            rig.wheels(*vals)
            print(f"\r{name}: {throttle:.3f}  ", end="", flush=True)
            deadline = time.monotonic() + FLOOR_DWELL
            key = None
            while time.monotonic() < deadline:
                key = poll_key()
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
        rig.wheels(*vals)
        note = f"{name} floor {floors[name]:.3f}" if name in floors else f"{name} skipped"
        print(f"\r{note}            ", end="\r\n")
        time.sleep(0.5)
    if floors:
        summary = "  ".join(f"{k}={v:.3f}" for k, v in floors.items())
        print(f"floors @ today's charge: {summary}", end="\r\n")
        print("(feed these into ThrottleMap per-wheel floors)", end="\r\n")
    return floors


def status(
    preset: str, base: float, diff: float, thr: tuple[float, float, float], fired: int
) -> None:
    print(
        f"\r{preset:<11} base {base:.2f} diff {diff:.2f} | "
        f"A {thr[0]:.2f} B {thr[1]:.2f} BOT {thr[2]:.2f} | balls {fired}   ",
        end="",
        flush=True,
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--throttle", type=float, default=0.12, help="base wheel power 0..1")
    p.add_argument("--diff", type=float, default=0.03, help="spin differential 0..0.3")
    p.add_argument("--dry-run", action="store_true", help="rehearse off-hardware")
    args = p.parse_args()

    rig = Rig(dry_run=args.dry_run)
    base = _clamp(args.throttle, 0.0, 1.0)
    diff = _clamp(args.diff, 0.0, 0.3)
    preset = "FLAT"

    print(
        f"Arming 3 ESCs on ch {UPPER_ESC_A}/{UPPER_ESC_B}/{BOTTOM_ESC} "
        f"({ARM_SECONDS:.0f}s at zero throttle)..."
    )
    rig.wheels(0.0, 0.0, 0.0)
    rig.feed(LOAD_ANGLE)
    time.sleep(ARM_SECONDS)

    thr = mix(preset, base, diff)
    print(f"Spinning up FLAT at {base:.2f}...")
    rig.wheels(*thr)
    time.sleep(SPINUP_SECONDS)
    print(
        "Keys: 1=flat 2=top 3=back 4/5=side +/-=throttle [/]=diff "
        "f=fire d=floorhunt space=E-STOP q=quit"
    )

    fired = 0
    fd = sys.stdin.fileno()
    is_tty = sys.stdin.isatty()
    old = termios.tcgetattr(fd) if is_tty else None
    try:
        if is_tty:
            tty.setraw(fd)
        status(preset, base, diff, thr, fired)
        while True:
            key = poll_key()
            if key in ("space", "q", "\x03"):
                break
            dirty = False
            if key in PRESETS:
                preset, dirty = PRESETS[key], True
            elif key in ("+", "="):
                base, dirty = _clamp(base + STEP, 0.0, 1.0), True
            elif key == "-":
                base, dirty = _clamp(base - STEP, 0.0, 1.0), True
            elif key == "]":
                diff, dirty = _clamp(diff + STEP, 0.0, 0.3), True
            elif key == "[":
                diff, dirty = _clamp(diff - STEP, 0.0, 0.3), True
            elif key == "f":
                fire_one(rig)
                fired += 1
                dirty = True
            elif key == "d":
                floor_hunt(rig)
                dirty = True  # dirty path spins the preset back up
            if dirty:
                thr = mix(preset, base, diff)
                rig.wheels(*thr)
                status(preset, base, diff, thr, fired)
            time.sleep(SLICE)
    finally:
        if old is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        rig.wheels(0.0, 0.0, 0.0)
        rig.feed(LOAD_ANGLE)
        print(f"\nDone — {fired} balls. All wheels stopped, feed at LOAD.")


if __name__ == "__main__":
    main()
