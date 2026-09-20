#!/usr/bin/env python3
"""Textual dashboard for gravity-feeding directly into three launcher wheels.

Run: uv run python scripts/launcher_test.py [--dry-run]
Defaults match the current bench: ESC channels 2/3/4, 5% throttle, 8% cap.
Channel 2 is a bench wiring override, normally the head-roll servo. Check wiring
before arming. For the canonical tri-wheel wiring use --channels 3 4 6.
Use --max-throttle 70 --throttle 25 to reproduce the original chat's settings.

Start with LiPo disconnected, an empty guarded launcher, and no other hardware
control program running. Connect the LiPo, then click ARM (or press Enter) to arm for 3 seconds.
1/2/3 toggle wheels; A/S/D pulse individual wheels; Space pulses all wheels.
+/- adjust throttle by 1%; brackets adjust the next pulse by 25 ms (25-5000 ms).
G/B/J/N record single/double/jam/no-launch outcomes. X cuts wheel PWM and requires
Enter to re-arm; Q exits. Minimum throttle is restored after ordinary pulses.
Confirm motors actually stop before touching them; signal-off is not a brake.

Pulse timing is approximate: a 20 ms dashboard timer checks deadlines; PWM is 50 Hz.
Edit throttle/pulse fields and click APPLY. Keyboard shortcuts work outside fields.
Counters describe this session and are printed on exit; they are manual records.
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from collections.abc import Callable
from typing import Any, ClassVar

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Input, Label, Static

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
        max_throttle: int = 100,
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
        if key in (10, 13) and not self.armed:
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


class BenchInput(Input):
    """Keep stop and quit shortcuts available while editing numeric settings."""

    def check_consume_key(self, key: str, character: str | None) -> bool:
        if key.lower() in ("x", "q", "ctrl+c"):
            return False
        return super().check_consume_key(key, character)


class LauncherApp(App[int]):
    """The wheel-bench dashboard style with no-queue launcher controls."""

    TITLE = "McEnroeBot Launcher Bench"
    CSS = """
    Screen { align: center middle; }
    #viewport { height: 1fr; align: center middle; }
    #panel { width: 72; max-width: 100%; height: auto;
             border: round $primary; padding: 1 2; }
    #title { text-align: center; text-style: bold; background: $primary; color: $text; }
    #state { text-align: center; text-style: bold; margin: 1 0; color: $warning; }
    .field { width: 1fr; height: auto; margin: 0 1; }
    .field Label { color: $text-muted; }
    #controls { height: auto; margin: 0 0 1 0; }
    .buttons { height: auto; align-horizontal: center; }
    Button { margin: 0 1; min-width: 12; }
    .wheel { height: 3; align: center middle; }
    .wheel Static { width: 1fr; content-align: left middle; }
    #results { height: 2; text-align: center; margin-top: 1; }
    #status { height: 3; margin-top: 1; text-align: center; color: $accent; }
    #safety { color: $error; text-style: bold; text-align: center; }
    """
    BINDINGS: ClassVar = [
        Binding("x,X", "stop_test", "STOP", priority=True),
        Binding("q,Q", "quit_safe", "Quit", priority=True),
        Binding("ctrl+c", "quit_safe", "Quit", priority=True, show=False),
        Binding("space", "pulse_all", "Pulse all", priority=True),
    ]

    def __init__(self, bench: LauncherBench) -> None:
        super().__init__()
        self.bench = bench
        self.failed = False

    def compose(self) -> ComposeResult:
        dry = " — DRY RUN" if self.bench.rig.dry_run else ""
        with VerticalScroll(id="viewport"), Vertical(id="panel"):
            yield Static(f"McENROEBOT LAUNCHER BENCH{dry}", id="title")
            yield Static("DISARMED — PWM OFF", id="state")
            with Horizontal(id="controls"):
                with Vertical(classes="field"):
                    yield Label(f"THROTTLE % (0-{self.bench.max_throttle})")
                    yield BenchInput(str(self.bench.throttle), type="integer", id="percent")
                with Vertical(classes="field"):
                    yield Label("PULSE MS (25-5000)")
                    yield BenchInput(str(self.bench.pulse_ms), type="integer", id="pulse-ms")
                yield Button("APPLY", id="apply", variant="primary")
            with Horizontal(classes="buttons"):
                yield Button("LiPo connected — ARM", id="arm", variant="warning")
                yield Button("PULSE ALL", id="all", variant="success", disabled=True)
                yield Button("STOP", id="stop", variant="error")
            for index, channel in enumerate(self.bench.rig.channels):
                with Horizontal(classes="wheel"):
                    yield Static(f"Wheel {index + 1} / ch{channel}: OFF", id=f"wheel-{index}")
                    yield Button("TURN ON", id=f"toggle-{index}", disabled=True)
                    yield Button("PULSE", id=f"pulse-{index}", disabled=True)
            with Horizontal(classes="buttons"):
                for label, key in [
                    ("SINGLE", "good"),
                    ("DOUBLE", "double"),
                    ("JAM", "jam"),
                    ("NONE", "none"),
                ]:
                    yield Button(label, id=key)
            yield Static(id="results")
            yield Static(self.bench.last_action, id="status")
            yield Static("X = STOP   •   Q = safe quit   •   SPACE = pulse all", id="safety")
        yield Footer()

    def on_mount(self) -> None:
        self.set_focus(None)
        self.set_interval(0.02, self.advance)
        self.update_dashboard()

    def advance(self) -> None:
        if self.failed:
            return
        try:
            self.bench.tick()
        except Exception as exc:
            self.fault(exc)
        self.update_dashboard()

    def fault(self, exc: Exception) -> None:
        self.failed = True
        try:
            self.bench.stop()
        except Exception as stop_error:
            self.bench.last_action = f"FAULT: {exc}; stop failed: {stop_error}. Disconnect LiPo."
        else:
            self.bench.last_action = f"FAULT: {exc}. PWM off; quit and inspect the rig."

    def send_key(self, char: str) -> None:
        if self.failed and char not in ("x", "q"):
            return
        try:
            self.bench.handle_key(ord(char))
        except Exception as exc:
            self.fault(exc)
        self.update_dashboard()

    def update_dashboard(self) -> None:
        bench = self.bench
        state = (
            "ARMED"
            if bench.armed
            else "ARMING — wait 3 seconds"
            if bench.arm_deadline
            else "DISARMED — PWM OFF"
        )
        self.query_one("#state", Static).update("FAULT — disconnect LiPo" if self.failed else state)
        self.query_one("#arm", Button).disabled = (
            self.failed or bench.armed or bench.arm_deadline is not None
        )
        self.query_one("#all", Button).disabled = not bench.armed or self.failed
        for index, channel in enumerate(bench.rig.channels):
            state = "ON" if bench.running[index] else "MIN" if bench.armed else "OFF"
            if bench.deadlines[index]:
                state += " + PULSE"
            self.query_one(f"#wheel-{index}", Static).update(
                f"Wheel {index + 1} / ch{channel}: {state}"
            )
            toggle = self.query_one(f"#toggle-{index}", Button)
            toggle.label = "TURN OFF" if bench.running[index] else "TURN ON"
            toggle.variant = "success" if bench.running[index] else "default"
            toggle.disabled = not bench.armed or self.failed
            self.query_one(f"#pulse-{index}", Button).disabled = not bench.armed or self.failed
        total = sum(bench.stats.values())
        success = 100 * bench.stats["good"] / total if total else 0
        self.query_one("#results", Static).update(
            f"Single {bench.stats['good']}   Double {bench.stats['double']}   "
            f"Jam {bench.stats['jam']}   None {bench.stats['none']}\n"
            f"Total {total}   •   Single-ball success {success:.1f}%"
        )
        self.query_one("#status", Static).update(bench.last_action)

    def apply_settings(self) -> None:
        try:
            throttle = int(self.query_one("#percent", Input).value)
            pulse_ms = int(self.query_one("#pulse-ms", Input).value)
            if not 0 <= throttle <= self.bench.max_throttle or not 25 <= pulse_ms <= 5000:
                raise ValueError("settings outside the displayed limits")
        except ValueError as exc:
            self.bench.last_action = f"INVALID: {exc}"
        else:
            self.bench.throttle, self.bench.pulse_ms = throttle, pulse_ms
            try:
                self.bench.apply()
                self.bench.last_action = f"Applied {throttle}% throttle; next pulse {pulse_ms} ms."
            except Exception as exc:
                self.fault(exc)
        self.update_dashboard()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        key = event.button.id or ""
        if key == "apply":
            self.apply_settings()
        elif key == "arm":
            self.send_key("\n")
        elif key == "stop":
            self.action_stop_test()
        elif key == "all":
            self.send_key(" ")
        elif key.startswith("toggle-"):
            self.send_key(str(int(key[-1]) + 1))
        elif key.startswith("pulse-"):
            self.send_key("asd"[int(key[-1])])
        elif key in ("good", "double", "jam", "none"):
            self.send_key({"good": "g", "double": "b", "jam": "j", "none": "n"}[key])
        self.set_focus(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.apply_settings()
        self.set_focus(None)

    def on_key(self, event: events.Key) -> None:
        if isinstance(self.focused, Input):
            return
        char = event.character or ("\n" if event.key == "enter" else "")
        if char and char.lower() in "123asdgbjn+-=[]\n":
            event.stop()
            event.prevent_default()
            self.send_key(char.lower())
            if char in "+-=[]":
                self.query_one("#percent", Input).value = str(self.bench.throttle)
                self.query_one("#pulse-ms", Input).value = str(self.bench.pulse_ms)

    def action_pulse_all(self) -> None:
        if not isinstance(self.focused, Input):
            self.send_key(" ")

    def action_stop_test(self) -> None:
        self.send_key("x")

    def action_quit_safe(self) -> None:
        self.send_key("q")
        self.exit(1 if self.failed else 0)

    def on_unmount(self) -> None:
        self.bench.stop()


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
        status = int(LauncherApp(bench).run() or 0)
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
