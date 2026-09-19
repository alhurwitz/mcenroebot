#!/usr/bin/env python3
"""Safe Textual dashboard for McEnroeBot wheel tests on bench channels 2/3/4.

Start with the wheel LiPo disconnected and the launcher empty and guarded:

    uv run python scripts/wheel_bench_tui.py

Use ``--dry-run`` to rehearse the controls without PCA9685 hardware.
"""

from __future__ import annotations

import argparse
import asyncio
import math
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, NamedTuple, Protocol

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Input, Label, Select, Static

from mcenroebot.channel_map import ESC_MAX_US, ESC_MIN_US, PCA9685_ADDRESS, PCA9685_FREQ_HZ

CHANNELS = (2, 3, 4)
TARGETS = {"all", *(str(channel) for channel in CHANNELS)}


class RunRequest(NamedTuple):
    target: str
    percent: float
    seconds: float


class RunnableRig(Protocol):
    def spin(self, target: str, percent: float) -> None: ...

    def minimum_all(self) -> None: ...


class WheelRig:
    """Thin hardware boundary around the three bench-wired wheel ESCs."""

    def __init__(self, *, dry_run: bool = False, kit: Any | None = None) -> None:
        self.dry_run = dry_run
        if dry_run:
            self._escs: dict[int, Any] = {}
            return
        if kit is None:
            from adafruit_servokit import ServoKit

            kit = ServoKit(channels=16, address=PCA9685_ADDRESS, frequency=PCA9685_FREQ_HZ)
        self._escs = {channel: kit.continuous_servo[channel] for channel in CHANNELS}
        for esc in self._escs.values():
            esc.set_pulse_width_range(ESC_MIN_US, ESC_MAX_US)

    def minimum_all(self) -> None:
        if self.dry_run:
            return
        for esc in self._escs.values():
            esc.throttle = -1.0

    def spin(self, target: str, percent: float) -> None:
        if self.dry_run:
            return
        channels = CHANNELS if target == "all" else (int(target),)
        throttle = -1.0 + 2.0 * percent / 100.0
        for channel in channels:
            self._escs[channel].throttle = throttle

    def signal_off(self) -> list[str]:
        """Disable every wheel PWM output, continuing after individual failures."""
        if self.dry_run:
            return []
        failures = []
        for channel in CHANNELS:
            try:
                # Adafruit Motor 3.4.20 rejects throttle=None. The inherited
                # fraction setter accepts None and writes duty_cycle=0.
                self._escs[channel].fraction = None
            except Exception as exc:
                failures.append(f"ch{channel}: {exc}")
        return failures


def parse_run(target: str, percent_text: str, seconds_text: str) -> RunRequest:
    percent = float(percent_text)
    seconds = float(seconds_text)
    if (
        target not in TARGETS
        or not math.isfinite(percent)
        or not 1.0 <= percent <= 8.0
        or not math.isfinite(seconds)
        or not 1.0 <= seconds <= 30.0
    ):
        raise ValueError("target must be all/2/3/4, percent 1-8, and seconds 1-30")
    return RunRequest(target=target, percent=percent, seconds=seconds)


async def execute_run(
    rig: RunnableRig,
    request: RunRequest,
    status: Callable[[str], None],
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Run one bounded wheel test and always restore minimum throttle."""
    rig.spin(request.target, request.percent)
    try:
        percent = f"{request.percent:g}"
        if request.target == "all":
            status(f"All wheels spinning at {percent}%")
            spinup = min(2.0, request.seconds)
            await sleep(spinup)
            remaining = request.seconds - spinup
            if remaining > 0:
                status(f"FEED ONE BALL — stopping in {remaining:g} seconds")
                await sleep(remaining)
        else:
            status(f"Channel {request.target} spinning at {percent}%")
            await sleep(request.seconds)
    finally:
        rig.minimum_all()
    status("Stopped at minimum throttle — ready")


class WheelBenchApp(App[int]):
    """Keyboard-friendly wheel test dashboard."""

    TITLE = "McEnroeBot Wheel Bench"
    CSS = """
    Screen { align: center middle; }
    #panel { width: 72; height: auto; border: round $primary; padding: 1 2; }
    #title { text-align: center; text-style: bold; background: $primary; color: $text; }
    #state { text-align: center; text-style: bold; margin: 1 0; color: $warning; }
    .field { width: 1fr; height: auto; margin: 0 1; }
    .field Label { color: $text-muted; }
    #controls { height: auto; margin: 1 0; }
    #buttons { height: auto; align-horizontal: center; }
    Button { margin: 0 1; }
    #status { height: 3; margin-top: 1; text-align: center; color: $accent; }
    #safety { color: $error; text-style: bold; text-align: center; }
    """
    BINDINGS: ClassVar = [
        Binding("r", "run_test", "Run", priority=True),
        Binding("s", "stop_test", "Stop", priority=True),
        Binding("space", "estop", "E-STOP", priority=True),
        Binding("q", "quit_safe", "Quit", priority=True),
    ]

    def __init__(self, *, rig: WheelRig) -> None:
        super().__init__()
        self.rig = rig
        self.armed = False
        self._run_task: asyncio.Task[None] | None = None
        self._shutdown_done = False

    def compose(self) -> ComposeResult:
        dry = " — DRY RUN" if self.rig.dry_run else ""
        with Vertical(id="panel"):
            yield Static(f"McENROEBOT WHEEL BENCH{dry}", id="title")
            yield Static("DISARMED — start with LiPo disconnected", id="state")
            with Horizontal(id="controls"):
                with Vertical(classes="field"):
                    yield Label("TARGET")
                    yield Select(
                        [
                            ("All wheels", "all"),
                            ("Channel 2", "2"),
                            ("Channel 3", "3"),
                            ("Channel 4", "4"),
                        ],
                        value="all",
                        id="target",
                    )
                with Vertical(classes="field"):
                    yield Label("THROTTLE %  (1-8)")
                    yield Input(value="5", type="number", id="percent")
                with Vertical(classes="field"):
                    yield Label("SECONDS  (1-30)")
                    yield Input(value="10", type="number", id="seconds")
            with Horizontal(id="buttons"):
                yield Button("LiPo connected — ARM", id="arm", variant="warning")
                yield Button("START MOTORS", id="run", variant="success", disabled=True)
                yield Button("STOP MOTORS", id="stop", variant="warning")
                yield Button("E-STOP + EXIT", id="estop", variant="error")
            yield Static("Set values, arm, then START. STOP keeps the dashboard open.", id="status")
            yield Static("SPACE = E-STOP   •   Q = safe quit   •   keep hands clear", id="safety")
        yield Footer()

    def on_mount(self) -> None:
        self.rig.minimum_all()

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def _set_state(self, message: str) -> None:
        self.query_one("#state", Static).update(message)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "arm":
            self.armed = True
            self.query_one("#run", Button).disabled = False
            event.button.disabled = True
            self._set_state("ARMED — minimum throttle active")
            self._set_status("Ready. Verify all wheels are stopped before RUN.")
        elif button_id == "run":
            self.action_run_test()
        elif button_id == "stop":
            self.action_stop_test()
        elif button_id == "estop":
            self.action_estop()

    def _current_request(self) -> RunRequest:
        target = self.query_one("#target", Select).value
        if not isinstance(target, str):
            raise ValueError("select a wheel target")
        return parse_run(
            target,
            self.query_one("#percent", Input).value,
            self.query_one("#seconds", Input).value,
        )

    def action_run_test(self) -> None:
        if not self.armed or (self._run_task is not None and not self._run_task.done()):
            return
        try:
            request = self._current_request()
        except (TypeError, ValueError) as exc:
            self._set_status(f"INVALID: {exc}")
            return
        self._set_state("RUNNING")
        self.query_one("#run", Button).disabled = True
        self._run_task = asyncio.create_task(self._run(request))

    async def _run(self, request: RunRequest) -> None:
        try:
            await execute_run(self.rig, request, self._set_status)
            self._set_state("ARMED — minimum throttle active")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._set_state("FAULT — PWM disabled; disconnect LiPo")
            self._set_status(str(exc))
            self._safe_shutdown()
        finally:
            if self.is_mounted and self.armed and not self._shutdown_done:
                self.query_one("#run", Button).disabled = False

    def action_stop_test(self) -> None:
        if self._run_task is not None and not self._run_task.done():
            self._run_task.cancel()
        self.rig.minimum_all()
        if self.armed:
            self._set_state("ARMED — minimum throttle active")
        self._set_status("STOPPED — ready for another test")

    def _safe_shutdown(self) -> list[str]:
        if self._shutdown_done:
            return []
        self._shutdown_done = True
        if self._run_task is not None and not self._run_task.done():
            self._run_task.cancel()
        self.rig.minimum_all()
        return self.rig.signal_off()

    def action_estop(self) -> None:
        failures = self._safe_shutdown()
        self.exit(1 if failures else 0)

    def action_quit_safe(self) -> None:
        self.action_estop()

    def on_unmount(self) -> None:
        self._safe_shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="rehearse without hardware")
    args = parser.parse_args()
    rig = WheelRig(dry_run=args.dry_run)
    result: int | None = None
    failures: list[str] = []
    try:
        result = WheelBenchApp(rig=rig).run()
    finally:
        failures = rig.signal_off()
    if failures:
        print("PWM-off failed: " + "; ".join(failures))
        print("Disconnect LiPo immediately.")
        return 1
    print("All wheel PWM signals are off. Disconnect LiPo before touching the launcher.")
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
