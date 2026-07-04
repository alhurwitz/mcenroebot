#!/usr/bin/env python3
"""Positional feed-unit metering bench tool (MG996R).

The feed airlock now uses a POSITIONAL MG996R (swapped in for the continuous
HD3512MG). A positional servo *holds* a commanded angle, so metering is just two
angles about 70 deg apart — LOAD and DISCHARGE — with **no hard end-stops** and
no stall. (``scoop_endstops_v1`` is therefore no longer required.)

Workflow:
  1. Press the scoop arm onto the servo spline, bolt the servo into the mount.
  2. JOG (this tool, or ``calibrate_servo.py``) until the arm sits at the LOAD
     stop; press 'L' to mark it. Jog to DISCHARGE; press 'D'.
  3. --cycle to rock LOAD<->DISCHARGE at speed: confirm exactly-one-ball
     metering and clean cup-26 release, and watch the chute mouth for the
     LIP_THETA pinch (arm must fully clear or fully block).
  4. 'p' prints the two angles + pulse range — paste into your feed config.

Run ON THE PI (needs the ``pi`` extra: ``uv sync --extra pi``):

    uv run python scripts/feed_meter.py

Channel: FEED_SERVO = ch5 (src/mcenroebot/channel_map.py is the single source
of truth: pan=0, tilt=1, head-roll=2, wheel ESCs 3/4, feed servo=5). The
constants are imported from the package when it is on the path; the literal
fallbacks below mirror channel_map.py for standalone copies of this script.

MG996R: 180 deg range, 25T spline, ~500-2500 us. Balls are ~3g and the hopper
neck-down carries the pile weight off the scoop, so torque has ample margin.
Pass --dry-run to rehearse the controls off-hardware.
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
    from mcenroebot.channel_map import FEED_MAX_US, FEED_MIN_US, FEED_SERVO
except ImportError:  # standalone copy — literals mirror channel_map.py
    FEED_SERVO = 5
    FEED_MIN_US = 500
    FEED_MAX_US = 2500

DEFAULT_CHANNEL: Final[int] = FEED_SERVO
DEFAULT_LOAD_ANGLE: Final[float] = 125.0  # arm at LOAD stop  (found on the bench)
DEFAULT_DISCH_ANGLE: Final[float] = 55.0  # arm at DISCHARGE  (~70 deg rock apart)
DEFAULT_DWELL: Final[float] = 0.60  # s held at each stop
DEFAULT_STEP_DEG: Final[float] = 0.0  # 0 = snap; >0 = stepped move (deg/tick)
DEFAULT_STEP_DELAY: Final[float] = 0.01  # s between steps when stepping
DEFAULT_MIN_PULSE: Final[int] = FEED_MIN_US  # MG996R full-sweep pulse range
DEFAULT_MAX_PULSE: Final[int] = FEED_MAX_US
ANGLE_MIN: Final[float] = 0.0
ANGLE_MAX: Final[float] = 180.0
FINE_NUDGE: Final[float] = 1.0
BIG_NUDGE: Final[float] = 5.0
DWELL_STEP: Final[float] = 0.05
SLICE: Final[float] = 0.02
_ARROWS: Final[dict[str, str]] = {"[C": "right", "[D": "left", "[A": "up", "[B": "down"}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# ---------------------------------------------------------------------------
# Terminal input (blocking + non-blocking single keypress, raw mode)
# ---------------------------------------------------------------------------


def read_key() -> str:
    fd = sys.stdin.fileno()
    is_tty = sys.stdin.isatty()
    old = termios.tcgetattr(fd) if is_tty else None
    try:
        if is_tty:
            tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "":  # EOF (stdin closed, e.g. piped dry-run) — quit cleanly
            return "q"
        if ch == "\x1b":
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if ready:
                return _ARROWS.get(sys.stdin.read(2), "esc")
            return "esc"
        return "space" if ch == " " else ch
    finally:
        if old is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def poll_key() -> str | None:
    """Non-blocking keypress; caller must already be in raw mode."""
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return None
    ch = sys.stdin.read(1)
    if ch == "":  # EOF (stdin closed, e.g. piped dry-run) — quit cleanly
        return "q"
    if ch == "\x1b":
        ready, _, _ = select.select([sys.stdin], [], [], 0.05)
        if ready:
            return _ARROWS.get(sys.stdin.read(2), "esc")
        return "esc"
    return "space" if ch == " " else ch


# ---------------------------------------------------------------------------
# Positional servo wrapper (Adafruit ServoKit, lazy import)
# ---------------------------------------------------------------------------


class Servo:
    def __init__(self, channel: int, min_pulse: int, max_pulse: int, dry_run: bool = False) -> None:
        self.channel = channel
        self.dry_run = dry_run
        self.angle = ANGLE_MAX / 2  # assume centered until first write
        if dry_run:
            self._servo: Any = None
            return
        try:
            from adafruit_servokit import ServoKit  # lazy: Pi-only extra
        except ImportError as exc:  # pragma: no cover - hardware path
            raise ImportError(
                f"{exc}\nRun on the Pi after `uv sync --extra pi`, "
                "or pass --dry-run to rehearse the controls off-hardware."
            ) from exc
        kit = ServoKit(channels=16)
        self._servo = kit.servo[channel]
        self._servo.set_pulse_width_range(min_pulse, max_pulse)
        self.write(self.angle)

    def write(self, angle: float) -> None:
        angle = _clamp(angle, ANGLE_MIN, ANGLE_MAX)
        self.angle = angle
        if self.dry_run:
            sys.stdout.write(f"\r  [dry-run] ch{self.channel} angle={angle:6.1f}     ")
            sys.stdout.flush()
        else:
            self._servo.angle = angle

    def move_to(
        self,
        target: float,
        step_deg: float,
        step_delay: float,
        interruptible: bool = False,
    ) -> str | None:
        """Snap (step_deg<=0) or step smoothly to ``target``.

        In stepped mode a 'space'/'q'/'esc' keypress aborts if interruptible.
        """
        target = _clamp(target, ANGLE_MIN, ANGLE_MAX)
        if step_deg <= 0:
            self.write(target)
            return None
        while abs(self.angle - target) > 1e-6:
            nxt = self.angle + max(-step_deg, min(step_deg, target - self.angle))
            self.write(nxt)
            if interruptible and (k := poll_key()) in ("space", "q", "esc"):
                return k
            time.sleep(step_delay)
        return None


# ---------------------------------------------------------------------------
# Params + display
# ---------------------------------------------------------------------------


class Params:
    def __init__(self, args: argparse.Namespace) -> None:
        self.load_angle = args.load_angle
        self.disch_angle = args.disch_angle
        self.dwell = args.dwell
        self.step_deg = args.step_deg
        self.step_delay = args.step_delay
        self.min_pulse = args.min_pulse
        self.max_pulse = args.max_pulse

    def summary(self, channel: int) -> str:
        return (
            "\n--- feed metering summary ---\n"
            f"  channel      : {channel}\n"
            f"  LOAD angle   : {self.load_angle:.1f} deg\n"
            f"  DISCH angle  : {self.disch_angle:.1f} deg\n"
            f"  rock         : {abs(self.load_angle - self.disch_angle):.1f} deg\n"
            f"  dwell        : {self.dwell:.2f} s\n"
            f"  pulse range  : ({self.min_pulse}, {self.max_pulse}) us\n"
            "  paste LOAD/DISCH into the feed config once metering is clean.\n"
        )


def _status(servo: Servo, p: Params) -> None:
    sys.stdout.write(
        f"\r  angle={servo.angle:6.1f}  LOAD={p.load_angle:.1f}"
        f"  DISCH={p.disch_angle:.1f}  dwell={p.dwell:.2f}s     "
    )
    sys.stdout.flush()


JOG_HELP = """
jog controls (single keypress):
  left / right ... nudge angle -/+ 1 deg
  j / k .......... nudge angle -/+ 5 deg
  L .............. mark CURRENT angle as LOAD
  D .............. mark CURRENT angle as DISCHARGE
  l .............. go to LOAD        d ... go to DISCHARGE
  c .............. run ONE cycle: LOAD -> DISCHARGE -> LOAD
  [ / ] .......... dwell -/+ 0.05 s
  p .............. print summary (paste into config)
  ? .............. this help          q / esc ... quit
"""


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------


def _one_cycle(servo: Servo, p: Params, interruptible: bool) -> str | None:
    for target in (p.disch_angle, p.load_angle):
        if (k := servo.move_to(target, p.step_deg, p.step_delay, interruptible)) is not None:
            return k
        if (k := _dwell(p.dwell, interruptible)) is not None:
            return k
    return None


def _dwell(seconds: float, interruptible: bool) -> str | None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if interruptible and (k := poll_key()) in ("space", "q", "esc"):
            return k
        time.sleep(min(SLICE, max(0.0, end - time.monotonic())))
    return None


def jog(servo: Servo, p: Params) -> int:
    print(f"JOG mode on channel {servo.channel}. '?' for help, 'q' to quit.")
    print(JOG_HELP)
    servo.write(servo.angle)
    _status(servo, p)
    while True:
        key = read_key()
        if key in ("q", "esc"):
            break
        if key == "right":
            servo.write(servo.angle + FINE_NUDGE)
        elif key == "left":
            servo.write(servo.angle - FINE_NUDGE)
        elif key == "k":
            servo.write(servo.angle + BIG_NUDGE)
        elif key == "j":
            servo.write(servo.angle - BIG_NUDGE)
        elif key == "L":
            p.load_angle = servo.angle
        elif key == "D":
            p.disch_angle = servo.angle
        elif key == "l":
            servo.move_to(p.load_angle, p.step_deg, p.step_delay)
        elif key == "d":
            servo.move_to(p.disch_angle, p.step_deg, p.step_delay)
        elif key == "c":
            _one_cycle(servo, p, interruptible=False)
        elif key == "]":
            p.dwell = _clamp(p.dwell + DWELL_STEP, 0.0, 5.0)
        elif key == "[":
            p.dwell = _clamp(p.dwell - DWELL_STEP, 0.0, 5.0)
        elif key == "p":
            print(p.summary(servo.channel))
        elif key == "?":
            print(JOG_HELP)
        else:
            continue
        _status(servo, p)
    return 0


def cycle(servo: Servo, p: Params, cycles: int) -> int:
    print(f"CYCLE mode on channel {servo.channel}. Space = e-stop, 'q' = quit.")
    print("Each LOAD->DISCHARGE rock should discharge exactly one ball.\n")
    fd = sys.stdin.fileno()
    is_tty = sys.stdin.isatty()
    old = termios.tcgetattr(fd) if is_tty else None
    n = 0
    try:
        if is_tty:
            tty.setraw(fd)
        servo.move_to(p.load_angle, p.step_deg, p.step_delay, interruptible=True)
        _dwell(p.dwell, interruptible=True)
        while cycles == 0 or n < cycles:
            if _one_cycle(servo, p, interruptible=True) in ("space", "q", "esc"):
                break
            n += 1
            sys.stdout.write(f"\r  rock {n}     ")
            sys.stdout.flush()
    finally:
        if old is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    print(f"\nstopped after {n} rock(s).")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument(
        "--channel",
        type=int,
        default=DEFAULT_CHANNEL,
        help=f"PCA9685 channel (default {DEFAULT_CHANNEL} = FEED_SERVO per channel_map.py)",
    )
    p.add_argument("--load-angle", type=float, default=DEFAULT_LOAD_ANGLE)
    p.add_argument("--disch-angle", type=float, default=DEFAULT_DISCH_ANGLE)
    p.add_argument("--dwell", type=float, default=DEFAULT_DWELL, help="s held at each stop")
    p.add_argument(
        "--step-deg",
        type=float,
        default=DEFAULT_STEP_DEG,
        help="0 = snap; >0 = stepped move for a gentler swing",
    )
    p.add_argument("--step-delay", type=float, default=DEFAULT_STEP_DELAY)
    p.add_argument("--min-pulse", type=int, default=DEFAULT_MIN_PULSE)
    p.add_argument("--max-pulse", type=int, default=DEFAULT_MAX_PULSE)
    p.add_argument("--cycle", action="store_true", help="auto-repeat (default: jog)")
    p.add_argument("--cycles", type=int, default=0, help="cycle count (0 = until keypress)")
    p.add_argument("--dry-run", action="store_true", help="print angles instead of driving")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not (0 <= args.channel <= 15):
        print(f"error: --channel {args.channel} out of range [0, 15]", file=sys.stderr)
        return 2
    try:
        servo = Servo(args.channel, args.min_pulse, args.max_pulse, dry_run=args.dry_run)
    except ImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    params = Params(args)
    try:
        return cycle(servo, params, args.cycles) if args.cycle else jog(servo, params)
    except KeyboardInterrupt:
        return 0
    finally:
        print("\ndone.")


if __name__ == "__main__":
    sys.exit(main())
