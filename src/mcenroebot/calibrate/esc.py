"""EscCalibrator — one-shot ESC throttle calibration routine."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcenroebot.clock import Clock
from mcenroebot.drivers import BLDCDriver

__all__ = ["EscCalibrator", "_demo"]

# Small settle delay (seconds) injected between the two throttle steps so the
# operator has a brief pause before the next prompt.  Hardcoded per V2_PLAN §4.8;
# not exposed as a constructor argument because ESC calibration is a one-time
# hardware setup, not a performance-critical loop.
_SETTLE_S: float = 0.5


class EscCalibrator:
    """One-shot ESC calibration routine.

    Standard ESC throttle calibration sequence:
      1. Power off ESC.  Operator confirms via prompt.
      2. ``set_throttle(1.0)`` — send max-throttle PWM (2000 µs).
      3. Operator powers ON the ESC; ESC reads max-throttle and emits beeps.
         Operator confirms beeps via prompt.
      4. ``set_throttle(0.0)`` — send min-throttle PWM (1000 µs).
      5. Operator hears confirmation beeps; calibration is stored in the ESC.
         Operator confirms via prompt.
      6. ``disarm()``.

    The routine accepts a ``prompt_fn`` injection point so tests can record /
    drive prompts without touching stdin.  Defaults to the built-in ``input``
    for live use.

    ``prompt_fn`` is typed ``Callable[[str], Any]``.  The real ``input``
    builtin returns ``str``, but we never use the return value — we only want a
    blocking prompt.  Using ``Any`` keeps mypy strict-mode happy while still
    accepting ``input`` directly.

    Note on ``arm()``:
      The calibration sequence sends raw throttle values that do NOT go through
      the BLDCDriver's "must-be-armed" guard.  This calibrator arms the driver
      at the very start so ``set_throttle`` calls succeed, and disarms it at the
      end.  Calibration is a privileged operation run once before normal use.
    """

    def __init__(
        self,
        driver: BLDCDriver,
        clock: Clock,
        prompt_fn: Callable[[str], Any] = input,
    ) -> None:
        self._driver = driver
        self._clock = clock
        self._prompt_fn = prompt_fn

    async def run(self) -> None:
        """Execute the calibration sequence end-to-end.

        Sequence (in order):
          - prompt("Step 1: Power OFF the ESC. Press Enter when ready: ")
          - driver.arm()
          - driver.set_throttle(1.0)
          - prompt("Step 2: Power ON the ESC. Wait for max-throttle beeps. "
            "Press Enter when heard: ")
          - clock.sleep(0.5)   # small settle delay between prompts
          - driver.set_throttle(0.0)
          - prompt("Step 3: Wait for min-throttle beeps. Press Enter when heard: ")
          - clock.sleep(0.5)
          - driver.disarm()

        The driver is always disarmed on exit, even if a prompt raises
        (e.g. ``KeyboardInterrupt`` from Ctrl-C).  The ``try/finally`` block
        guarantees this.
        """
        self._prompt_fn("Step 1: Power OFF the ESC. Press Enter when ready: ")
        self._driver.arm()
        try:
            self._driver.set_throttle(1.0)
            self._prompt_fn(
                "Step 2: Power ON the ESC. Wait for max-throttle beeps. Press Enter when heard: "
            )
            await self._clock.sleep(_SETTLE_S)
            self._driver.set_throttle(0.0)
            self._prompt_fn("Step 3: Wait for min-throttle beeps. Press Enter when heard: ")
            await self._clock.sleep(_SETTLE_S)
        finally:
            self._driver.disarm()


def _demo() -> None:
    """Run a dry-run calibration against a MockBLDCDriver and FakeClock.

    Run with ``python -m mcenroebot.calibrate``.
    """
    import asyncio

    from mcenroebot.clock import FakeClock
    from mcenroebot.drivers import MockBLDCDriver

    driver = MockBLDCDriver()
    clock = FakeClock()
    prompts: list[str] = []

    def _silent_prompt(msg: str) -> None:
        prompts.append(msg)
        print(f"[prompt] {msg}")

    calibrator = EscCalibrator(driver=driver, clock=clock, prompt_fn=_silent_prompt)
    asyncio.run(calibrator.run())

    print(f"throttle_history={driver.throttle_history}")
    print(f"armed={driver.armed}")
    print(f"clock.elapsed={clock.elapsed:.3f}s")
    print(f"prompts ({len(prompts)}):")
    for i, p in enumerate(prompts, 1):
        print(f"  {i}. {p!r}")
