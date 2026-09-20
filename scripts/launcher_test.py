#!/usr/bin/env python3
"""Keyboard bench test for gravity-feeding directly into three launcher wheels.

Run: uv run python scripts/launcher_test.py [--dry-run]
Defaults match the current bench: ESC channels 2/3/4, 5% throttle, 8% cap.
Channel 2 is a bench wiring override, normally the head-roll servo. Check wiring
before arming. For the canonical tri-wheel wiring use --channels 3 4 6.
Use --max-throttle 70 --throttle 25 to reproduce the original chat's settings.

Start with LiPo disconnected, an empty guarded launcher, and no other hardware
control program running. Connect the LiPo, then press Enter to arm for 3 seconds.
1/2/3 toggle wheels; A/S/D pulse individual wheels; Space pulses all wheels.
+/- adjust throttle by 1%; brackets adjust the next pulse by 25 ms (25-5000 ms).
G/B/J/N record single/double/jam/no-launch outcomes. X cuts wheel PWM and requires
Enter to re-arm; Q exits. Minimum throttle is restored after ordinary pulses.
Confirm motors actually stop before touching them; signal-off is not a brake.

Pulse timing is approximate: the input loop polls every 20 ms and PWM is 50 Hz.
Counters describe this session and are printed on exit; they are manual records.
"""

from __future__ import annotations

import argparse
import curses
import signal
import sys
import time
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from mcenroebot.channel_map import (
    ESC_MAX_US,
    ESC_MIN_US,
    PCA9685_ADDRESS,
    PCA9685_FREQ_HZ,
)


class WheelRig:
    """Own the PCA9685 connection; import Pi libraries only on connection."""

    def __init__(self, channels: tuple[int, ...], *, dry_run: bool = False) -> None:
        self.channels = channels
        self.dry_run = dry_run
        self.pca: Any = None
        self.bus: Any = None

    def connect(self) -> None:
        if self.dry_run:
            return
        import board
        import busio
        from adafruit_pca9685 import PCA9685

        self.bus = busio.I2C(board.SCL, board.SDA)
        self.pca = PCA9685(self.bus, address=PCA9685_ADDRESS)
        self.pca.frequency = PCA9685_FREQ_HZ
        errors = self.signal_off()
        if errors:
            raise OSError("; ".join(errors))

    def set_percent(self, index: int, percent: int) -> None:
        if not 0 <= percent <= 70:
            raise ValueError("Bench throttle must be between 0 and 70 percent")
        if not self.dry_run:
            pulse_us = ESC_MIN_US + (ESC_MAX_US - ESC_MIN_US) * percent / 100
            duty = int(pulse_us * self.pca.frequency * 65535 / 1_000_000)
            self.pca.channels[self.channels[index]].duty_cycle = duty

    def minimum_all(self) -> list[str]:
        errors = []
        if self.pca is not None:
            for index, channel in enumerate(self.channels):
                try:
                    self.set_percent(index, 0)
                except Exception as exc:
                    errors.append(f"ch{channel}: minimum failed: {exc}")
        return errors

    def signal_off(self) -> list[str]:
        errors = []
        if self.pca is not None:
            for channel in self.channels:
                try:
                    self.pca.channels[channel].duty_cycle = 0
                except Exception as exc:
                    errors.append(f"ch{channel}: PWM-off failed: {exc}")
        return errors

    def stop(self) -> list[str]:
        errors = self.minimum_all()
        errors.extend(self.signal_off())
        return errors

    def close(self) -> list[str]:
        errors = self.stop()
        for name in ("pca", "bus"):
            resource = getattr(self, name)
            if resource is not None:
                try:
                    resource.deinit()
                except Exception as exc:
                    errors.append(f"{name}: release failed: {exc}")
                finally:
                    setattr(self, name, None)
        return errors


class LauncherBench:
    """Nonblocking control state: pulse deadlines never delay stop input."""

    def __init__(
        self,
        rig: WheelRig,
        *,
        throttle: int = 5,
        max_throttle: int = 8,
        pulse_ms: int = 250,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.rig = rig
        self.throttle = throttle
        self.max_throttle = max_throttle
        self.pulse_ms = pulse_ms
        self.clock = clock
        self.running = [False] * 3
        self.deadlines = [0.0] * 3
        self.armed = False
        self.arm_deadline: float | None = None
        self.stats = {"good": 0, "double": 0, "jam": 0, "none": 0}
        self.last_action = "Connect LiPo, then Enter to arm (3 seconds)."

    def apply(self) -> None:
        if self.armed:
            for index in range(3):
                active = self.running[index] or self.deadlines[index] > 0
                self.rig.set_percent(index, self.throttle if active else 0)

    def stop(self) -> None:
        self.armed = False
        self.arm_deadline = None
        self.running = [False] * 3
        self.deadlines = [0.0] * 3
        errors = self.rig.stop()
        self.last_action = "STOP: PWM off. Enter to re-arm."
        if errors:
            raise OSError("; ".join(errors))

    def tick(self) -> None:
        now = self.clock()
        if self.arm_deadline is not None and now >= self.arm_deadline:
            self.arm_deadline = None
            self.armed = True
            self.last_action = "ESCs armed. Verify wheels stay stopped at minimum."
        expired = False
        for index, deadline in enumerate(self.deadlines):
            if deadline and now >= deadline:
                self.deadlines[index] = 0.0
                expired = True
        if expired:
            self.apply()
            self.last_action = "Pulse complete; continuous wheel settings restored."

    def handle_key(self, key: int) -> bool:
        char = chr(key).lower() if 0 <= key < 256 else ""
        if char in ("q", "x", "\x03"):
            self.stop()
            return char == "x"
        if key in (10, 13, curses.KEY_ENTER) and not self.armed:
            if self.arm_deadline is None:
                errors = self.rig.minimum_all()
                if errors:
                    raise OSError("; ".join(errors))
                self.arm_deadline = self.clock() + 3.0
                self.last_action = "Arming at minimum throttle... X cancels."
        elif char in ("+", "=", "-"):
            step = -1 if char == "-" else 1
            self.throttle = max(0, min(self.max_throttle, self.throttle + step))
            self.apply()
        elif char in ("[", "]"):
            step = 25 if char == "]" else -25
            self.pulse_ms = max(25, min(5000, self.pulse_ms + step))
        elif char in ("g", "b", "j", "n"):
            outcome = {"g": "good", "b": "double", "j": "jam", "n": "none"}[char]
            self.stats[outcome] += 1
            self.last_action = f"Recorded: {outcome}"
        elif self.armed and char in ("1", "2", "3"):
            index = int(char) - 1
            self.running[index] = not self.running[index]
            if not self.running[index]:
                self.deadlines[index] = 0.0
            self.apply()
        elif self.armed and char in ("a", "s", "d", " "):
            indices = range(3) if char == " " else ("asd".index(char),)
            for index in indices:
                # Key repeat must not stretch an in-progress pulse indefinitely.
                if not self.deadlines[index]:
                    self.deadlines[index] = self.clock() + self.pulse_ms / 1000
            self.apply()
            self.last_action = f"Pulse requested: {self.pulse_ms} ms at {self.throttle}%"
        return True


def draw_screen(screen: Any, bench: LauncherBench) -> None:
    total = sum(bench.stats.values())
    success = 100 * bench.stats["good"] / total if total else 0.0
    mode = "DRY RUN" if bench.rig.dry_run else "LIVE HARDWARE"
    state = "ARMED" if bench.armed else "ARMING" if bench.arm_deadline else "PWM OFF"
    lines = [
        "McEnroeBot - Launcher Bench Test       X: STOP    Q: QUIT",
        f"{mode} | {state} | Enter: arm/re-arm (3 seconds)",
        f"Throttle: {bench.throttle}% (cap {bench.max_throttle}%)  Next pulse: {bench.pulse_ms} ms",
        "",
    ]
    for index, channel in enumerate(bench.rig.channels):
        status = "CONTINUOUS" if bench.running[index] else "MINIMUM" if bench.armed else state
        if bench.deadlines[index]:
            status += " + PULSE" if bench.running[index] else " / PULSE"
        lines.append(f"Wheel {index + 1} / ch{channel}: {status}")
    lines.extend(
        [
            "",
            "1 / 2 / 3  Toggle continuous wheel",
            "A / S / D  Pulse wheel 1 / 2 / 3    SPACE: pulse ALL",
            "+ / -      Throttle +/-1%     ] / [: next pulse +/-25 ms",
            "X          Cut wheel signals, cancel pulses, require re-arm",
            "G / B / J / N: record single / double / jam / no launch",
            "",
            f"Single: {bench.stats['good']}  Double: {bench.stats['double']}  "
            f"Jam: {bench.stats['jam']}  None: {bench.stats['none']}",
            f"Total: {total}   Single-ball success: {success:.1f}%",
            "",
            bench.last_action,
            "Confirm motors stop physically. Disconnect LiPo before touching.",
        ]
    )
    screen.erase()
    height, width = screen.getmaxyx()
    for row, line in enumerate(lines[:height]):
        if width > 1:
            # Terminal resize may race the dimensions read above.
            with suppress(curses.error):
                screen.addnstr(row, 0, line, width - 1)
    screen.refresh()


def run_tui(screen: Any, bench: LauncherBench) -> None:
    with suppress(curses.error):
        curses.curs_set(0)
    screen.keypad(True)
    screen.timeout(20)
    while True:
        was_armed = bench.armed
        bench.tick()
        if bench.armed and not was_armed:
            curses.flushinp()  # Discard motion keys queued during arming.
        draw_screen(screen, bench)
        key = screen.getch()
        if not bench.handle_key(key):
            return
        if key in (ord("x"), ord("X"), 10, 13, curses.KEY_ENTER):
            curses.flushinp()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dry-run", action="store_true", help="rehearse without hardware")
    parser.add_argument("--channels", nargs=3, type=int, default=(2, 3, 4), metavar="CH")
    parser.add_argument("--throttle", type=int, default=5, help="starting percent (default: 5)")
    parser.add_argument("--max-throttle", type=int, default=8, help="cap, 1-70%% (default: 8)")
    parser.add_argument("--pulse-ms", type=int, default=250, help="pulse, 25-5000 ms")
    args = parser.parse_args(argv)
    if len(set(args.channels)) != 3 or any(not 0 <= ch <= 15 for ch in args.channels):
        parser.error("--channels must be three distinct PCA9685 channels from 0 to 15")
    if not 1 <= args.max_throttle <= 70 or not 0 <= args.throttle <= args.max_throttle:
        parser.error("require 0 <= throttle <= max-throttle and 1 <= max-throttle <= 70")
    if not 25 <= args.pulse_ms <= 5000:
        parser.error("--pulse-ms must be between 25 and 5000")
    rig = WheelRig(tuple(args.channels), dry_run=args.dry_run)
    bench = LauncherBench(
        rig, throttle=args.throttle, max_throttle=args.max_throttle, pulse_ms=args.pulse_ms
    )
    status = 0
    previous = {}

    def interrupt(signum: int, frame: Any) -> None:
        raise KeyboardInterrupt

    try:
        for signum in (signal.SIGTERM, signal.SIGHUP):
            previous[signum] = signal.signal(signum, interrupt)
        rig.connect()
        curses.wrapper(run_tui, bench)
    except KeyboardInterrupt:
        status = 130
    except Exception as exc:
        print(f"Launcher test failed: {exc}", file=sys.stderr)
        status = 1
    finally:
        errors = rig.close()
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        if errors:
            status = 1
            print("Cleanup errors; disconnect LiPo: " + "; ".join(errors), file=sys.stderr)
        print(f"Session results: {bench.stats}")
        if not args.dry_run:
            print("Disconnect LiPo. Confirm wheels have physically stopped.")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
