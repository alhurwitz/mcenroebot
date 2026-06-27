#!/usr/bin/env python3
"""Interactive servo calibration for McEnroe V2.

Jog one MG996R on a PCA9685 channel to find true center and the usable
end stops, and tune the pulse-width range so a commanded 0-180 maps to
real physical travel. Prints a summary block you can paste into config.

Run ON THE PI (needs the ``pi`` extra installed via ``uv sync --extra pi``):

    uv run python scripts/calibrate_servo.py --channel 0

Controls (single keypress, no Enter needed):

    left / right ... jog by the current step
    j / k .......... nudge angle down / up by 5 deg
    - / = .......... shrink / grow the jog step
    c .............. center (90 deg)
    z / x .......... jump to 0 / 180
    [ / ] .......... min pulse width  -25 / +25 us
    { / } .......... max pulse width  -25 / +25 us
    p .............. reprint the summary
    q / ESC ........ quit (prints summary)

Channel map (see CLAUDE.md): yaw=0, pitch=1, ESC=2 (do NOT drive the ESC
channel with this tool — it expects a throttle pulse, not a servo angle).

WARNING: if a servo buzzes/grinds at an end it is stalled against a
mechanical limit. Back off immediately — that is how MG996R gears strip.
"""

from __future__ import annotations

import argparse
import select
import sys
import termios
import tty
from typing import Any, Final

from mcenroebot.drivers.servo.pca9685 import PCA9685ServoDriver

ANGLE_MIN: Final[float] = 0.0
ANGLE_MAX: Final[float] = 180.0
ANGLE_CENTER: Final[float] = 90.0
DEFAULT_MIN_PULSE: Final[int] = 500
DEFAULT_MAX_PULSE: Final[int] = 2500
PULSE_NUDGE: Final[int] = 25
BIG_NUDGE: Final[float] = 5.0
STEP_MIN: Final[float] = 0.5
STEP_MAX: Final[float] = 45.0
DEFAULT_STEP: Final[float] = 1.0
_ESC_PEEK_TIMEOUT_S: Final[float] = 0.05
_ARROWS: Final[dict[str, str]] = {"[C": "right", "[D": "left", "[A": "up", "[B": "down"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def read_key() -> str:
    """Read one keypress in raw mode, decoding arrow escape sequences.

    Returns a single character, one of ``left/right/up/down``, or ``esc``.
    A bare ESC is distinguished from an arrow sequence by a short peek.
    """
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ready, _, _ = select.select([sys.stdin], [], [], _ESC_PEEK_TIMEOUT_S)
            if ready:
                return _ARROWS.get(sys.stdin.read(2), "esc")
            return "esc"
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


def apply_pulse_range(driver: PCA9685ServoDriver, channel: int, min_us: int, max_us: int) -> bool:
    """Tune the channel's pulse-width range on the underlying ServoKit.

    Pulse tuning is not part of the ServoDriver protocol, so this reaches
    into the real driver's private ``_kit`` — fine for a calibration tool.
    Returns False if the attribute is absent (e.g. a mock driver).
    """
    kit: Any = getattr(driver, "_kit", None)
    if kit is None:
        return False
    kit.servo[channel].set_pulse_width_range(min_us, max_us)
    return True


def _status(angle: float, step: float, min_us: int, max_us: int) -> None:
    sys.stdout.write(
        f"\r  angle={angle:6.1f} deg   step={step:4.1f}   pulse=[{min_us}, {max_us}] us     "
    )
    sys.stdout.flush()


def _print_summary(channel: int, angle: float, min_us: int, max_us: int) -> None:
    print("\n\n--- calibration summary ---")
    print(f"  channel        : {channel}")
    print(f"  last angle     : {angle:.1f} deg")
    print(f"  pulse range    : ({min_us}, {max_us})  # microseconds for set_pulse_width_range")
    print("  paste into your servo config / AimGeometry once you've confirmed")
    print("  the ends reach the mechanical limits without buzzing.\n")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def calibrate(channel: int, min_pulse: int, max_pulse: int, start_angle: float) -> int:
    try:
        driver = PCA9685ServoDriver()
    except ImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("Run this on the Pi after `uv sync --extra pi`.", file=sys.stderr)
        return 1

    angle = _clamp(start_angle, ANGLE_MIN, ANGLE_MAX)
    step = DEFAULT_STEP
    min_us, max_us = min_pulse, max_pulse
    if not apply_pulse_range(driver, channel, min_us, max_us):
        print("note: driver has no tunable pulse range; angles only.", file=sys.stderr)
    driver.write_angle(channel, angle)

    print(f"calibrating channel {channel}.  press 'p' for help/summary, 'q' to quit.")
    _status(angle, step, min_us, max_us)

    while True:
        key = read_key()
        if key in ("q", "esc"):
            break
        if key in ("right",):
            angle = _clamp(angle + step, ANGLE_MIN, ANGLE_MAX)
        elif key in ("left",):
            angle = _clamp(angle - step, ANGLE_MIN, ANGLE_MAX)
        elif key in ("up", "k"):
            angle = _clamp(angle + BIG_NUDGE, ANGLE_MIN, ANGLE_MAX)
        elif key in ("down", "j"):
            angle = _clamp(angle - BIG_NUDGE, ANGLE_MIN, ANGLE_MAX)
        elif key == "-":
            step = _clamp(step / 2.0, STEP_MIN, STEP_MAX)
        elif key == "=":
            step = _clamp(step * 2.0, STEP_MIN, STEP_MAX)
        elif key == "c":
            angle = ANGLE_CENTER
        elif key == "z":
            angle = ANGLE_MIN
        elif key == "x":
            angle = ANGLE_MAX
        elif key == "[":
            min_us -= PULSE_NUDGE
            apply_pulse_range(driver, channel, min_us, max_us)
        elif key == "]":
            min_us += PULSE_NUDGE
            apply_pulse_range(driver, channel, min_us, max_us)
        elif key == "{":
            max_us -= PULSE_NUDGE
            apply_pulse_range(driver, channel, min_us, max_us)
        elif key == "}":
            max_us += PULSE_NUDGE
            apply_pulse_range(driver, channel, min_us, max_us)
        elif key == "p":
            _print_summary(channel, angle, min_us, max_us)
            _status(angle, step, min_us, max_us)
            continue
        else:
            continue
        driver.write_angle(channel, angle)
        _status(angle, step, min_us, max_us)

    _print_summary(channel, angle, min_us, max_us)
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    description = (__doc__ or "").splitlines()[0]
    p = argparse.ArgumentParser(description=description)
    p.add_argument(
        "--channel", type=int, default=0, help="PCA9685 channel: yaw=0, pitch=1 (default 0)"
    )
    p.add_argument(
        "--min-pulse",
        type=int,
        default=DEFAULT_MIN_PULSE,
        help="starting min pulse us (default 500)",
    )
    p.add_argument(
        "--max-pulse",
        type=int,
        default=DEFAULT_MAX_PULSE,
        help="starting max pulse us (default 2500)",
    )
    p.add_argument(
        "--start", type=float, default=ANGLE_CENTER, help="starting angle in deg (default 90)"
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not (0 <= args.channel <= 15):
        print(f"error: --channel {args.channel} out of range [0, 15]", file=sys.stderr)
        return 2
    return calibrate(args.channel, args.min_pulse, args.max_pulse, args.start)


if __name__ == "__main__":
    sys.exit(main())
