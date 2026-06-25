"""Async open-loop swing controller — drives a BLDC through a throttle envelope."""

from __future__ import annotations

import asyncio
from types import TracebackType

from mcenroebot._shelved.swing.profile import SwingProfile
from mcenroebot.clock import Clock, SystemClock
from mcenroebot.drivers import BLDCDriver, MockBLDCDriver

__all__ = ["SwingController", "_demo"]

# Tick cadence for sampling the throttle envelope (~200 Hz update rate).
# This is fast enough for the 50 Hz PWM update rate on the PCA9685 and
# small compared to a typical 100-200 ms swing, giving smooth ramps while
# keeping CPU overhead negligible.
_TICK_MS: float = 5.0


class SwingController:
    """Drives a BLDC through a SwingProfile, open-loop, with FakeClock-testable
    timing.  Implements the async context-manager protocol so callers can
    ``async with SwingController(driver, clock) as swing:`` and be guaranteed
    the driver is disarmed on exit even if ``fire()`` raises mid-swing.

    Safety:
      - ``fire()`` raises RuntimeError if the controller is not armed.
      - Context-manager exit always disarms the underlying driver.
      - The driver's own ``set_throttle`` validation (range, armed-state) is
        the source of truth — this controller never bypasses it.
    """

    def __init__(self, driver: BLDCDriver, clock: Clock) -> None:
        self._driver = driver
        self._clock = clock
        self._armed: bool = False

    async def __aenter__(self) -> SwingController:
        """Arm the controller and return self for use in ``async with`` blocks."""
        self.arm()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Disarm the driver unconditionally.  Re-raises any in-flight exception."""
        self._disarm()

    def arm(self) -> None:
        """Arm the underlying driver and mark this controller as armed."""
        self._driver.arm()
        self._armed = True

    def _disarm(self) -> None:
        """Disarm the underlying driver and clear the armed flag."""
        self._driver.disarm()
        self._armed = False

    async def fire(self, profile: SwingProfile) -> None:
        """Execute one swing envelope.

        Samples the profile at ``_TICK_MS`` cadence (~200 Hz) and calls
        ``driver.set_throttle`` for each tick.

        Total elapsed ``clock.now()`` time across the call equals
        ``profile.total_ms / 1000`` (within one tick).  At the end, throttle
        is set to 0.

        Raises
        ------
        RuntimeError
            If ``arm()`` has not been called first.
        """
        if not self._armed:
            raise RuntimeError("SwingController must be armed before calling fire().")

        total_ms = profile.total_ms
        ramp_up_end = profile.ramp_up_ms
        hold_end = profile.ramp_up_ms + profile.hold_ms
        peak = profile.peak_throttle

        elapsed_ms: float = 0.0

        while elapsed_ms < total_ms:
            # Clamp the tick so we never overshoot total_ms.
            tick_ms = min(_TICK_MS, total_ms - elapsed_ms)
            await self._clock.sleep(tick_ms / 1000.0)
            elapsed_ms += tick_ms

            # Compute throttle at this point in the envelope.
            t = elapsed_ms  # ms into the swing
            if t <= ramp_up_end:
                throttle = peak * (t / profile.ramp_up_ms)
            elif t <= hold_end:
                throttle = peak
            else:
                # ramp-down phase
                dt = t - hold_end
                throttle = peak * (1.0 - dt / profile.ramp_down_ms)

            # Clamp to [0, 1] to absorb floating-point rounding at boundaries.
            throttle = max(0.0, min(1.0, throttle))
            self._driver.set_throttle(throttle)

        # Final safety zero — guarantees BLDC is at rest regardless of how
        # the envelope sampled out.
        self._driver.set_throttle(0.0)


def _demo() -> None:
    """Fire two sample swing profiles against a MockBLDCDriver and print results.

    Run with ``python -m mcenroebot._shelved.swing``.
    """
    clock = SystemClock()
    driver = MockBLDCDriver()

    profiles = [
        (
            "Standard swing (50/100/50 ms, peak=0.8)",
            SwingProfile(ramp_up_ms=50.0, hold_ms=100.0, ramp_down_ms=50.0, peak_throttle=0.8),
        ),
        (
            "Triangle swing (hold_ms=0, peak=0.6)",
            SwingProfile(ramp_up_ms=75.0, hold_ms=0.0, ramp_down_ms=75.0, peak_throttle=0.6),
        ),
    ]

    async def _run() -> None:
        for label, profile in profiles:
            print(f"=== {label} ===")
            print(f"  total_ms={profile.total_ms:.0f}  peak={profile.peak_throttle}")
            async with SwingController(driver, clock) as ctl:
                await ctl.fire(profile)
            history = driver.throttle_history
            # history includes the disarm 0.0 appended by disarm() plus the
            # fire() final 0.0 — peak is the max of set_throttle calls.
            peak_seen = max(history) if history else 0.0
            print(f"  ticks={len(history)}  peak_seen={peak_seen:.3f}  final={history[-1]}")
            print()

    asyncio.run(_run())
