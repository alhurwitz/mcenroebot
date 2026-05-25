"""Tests for SwingController open-loop swing execution."""

from __future__ import annotations

import pytest

from mcenroebot.clock import FakeClock
from mcenroebot.drivers import MockBLDCDriver
from mcenroebot.swing.controller import SwingController, _TICK_MS
from mcenroebot.swing.profile import SwingProfile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STANDARD_PROFILE = SwingProfile(
    ramp_up_ms=50.0,
    hold_ms=100.0,
    ramp_down_ms=50.0,
    peak_throttle=0.5,
)

_TRIANGLE_PROFILE = SwingProfile(
    ramp_up_ms=50.0,
    hold_ms=0.0,
    ramp_down_ms=50.0,
    peak_throttle=0.6,
)


def _make_controller() -> tuple[MockBLDCDriver, FakeClock, SwingController]:
    driver = MockBLDCDriver()
    clock = FakeClock()
    ctl = SwingController(driver=driver, clock=clock)
    return driver, clock, ctl


# ---------------------------------------------------------------------------
# Test 1: fire() without arm raises RuntimeError
# ---------------------------------------------------------------------------


class TestFireWithoutArm:
    async def test_fire_without_arm_raises(self) -> None:
        _, _, ctl = _make_controller()
        with pytest.raises(RuntimeError, match="armed"):
            await ctl.fire(_STANDARD_PROFILE)


# ---------------------------------------------------------------------------
# Test 2: Throttle history matches profile shape
# ---------------------------------------------------------------------------


class TestThrottleShape:
    async def test_shape_ramp_hold_ramp_ends_at_zero(self) -> None:
        driver, _, ctl = _make_controller()
        ctl.arm()
        await ctl.fire(_STANDARD_PROFILE)

        # Exclude the final 0.0 (set by fire) and the disarm 0.0 (not appended
        # until disarm() is called — arm() was used, not context manager here).
        # The fire() always ends with set_throttle(0.0).
        history = driver.throttle_history
        # Last value must be 0.0 (the fire-end zero).
        assert history[-1] == 0.0

        # Identify the non-zero envelope portion (all but the trailing 0).
        envelope = history[:-1]
        assert len(envelope) > 0

        # Compute phase tick counts.
        ramp_up_ticks = max(1, round(_STANDARD_PROFILE.ramp_up_ms / _TICK_MS))
        hold_ticks = max(0, round(_STANDARD_PROFILE.hold_ms / _TICK_MS))
        ramp_down_ticks = max(1, round(_STANDARD_PROFILE.ramp_down_ms / _TICK_MS))

        ramp_up_part = envelope[:ramp_up_ticks]
        hold_part = envelope[ramp_up_ticks : ramp_up_ticks + hold_ticks]
        ramp_down_part = envelope[ramp_up_ticks + hold_ticks :]

        # Ramp-up: monotonically non-decreasing.
        for i in range(1, len(ramp_up_part)):
            assert ramp_up_part[i] >= ramp_up_part[i - 1], (
                f"ramp-up not monotone at tick {i}: {ramp_up_part}"
            )

        # Hold: all values at peak_throttle.
        peak = _STANDARD_PROFILE.peak_throttle
        for v in hold_part:
            assert v == pytest.approx(peak, abs=1e-9), f"hold not at peak: {v}"

        # Ramp-down: monotonically non-increasing.
        for i in range(1, len(ramp_down_part)):
            assert ramp_down_part[i] <= ramp_down_part[i - 1], (
                f"ramp-down not monotone at tick {i}: {ramp_down_part}"
            )


# ---------------------------------------------------------------------------
# Test 3: Total FakeClock elapsed matches profile.total_ms
# ---------------------------------------------------------------------------


class TestElapsedTime:
    async def test_elapsed_matches_total_ms(self) -> None:
        _, clock, ctl = _make_controller()
        ctl.arm()
        await ctl.fire(_STANDARD_PROFILE)

        expected_s = _STANDARD_PROFILE.total_ms / 1000.0
        assert clock.elapsed == pytest.approx(expected_s, abs=_TICK_MS / 1000.0)


# ---------------------------------------------------------------------------
# Test 4: Final throttle is 0
# ---------------------------------------------------------------------------


class TestFinalThrottleIsZero:
    async def test_final_throttle_is_zero(self) -> None:
        driver, _, ctl = _make_controller()
        ctl.arm()
        await ctl.fire(_STANDARD_PROFILE)

        history = driver.throttle_history
        assert history[-1] == 0.0


# ---------------------------------------------------------------------------
# Test 5: Context manager disarms on normal exit
# ---------------------------------------------------------------------------


class TestContextManagerDisarmsOnExit:
    async def test_driver_disarmed_after_context(self) -> None:
        driver, _, ctl = _make_controller()

        async with SwingController(driver=driver, clock=FakeClock()) as swing:
            assert driver.armed is True
            await swing.fire(_STANDARD_PROFILE)

        assert driver.armed is False


# ---------------------------------------------------------------------------
# Test 6: Context manager disarms even when fire raises
# ---------------------------------------------------------------------------


class _BoomError(Exception):
    """Sentinel exception raised at the 5th set_throttle call."""


class _FaultingBLDCDriver(MockBLDCDriver):
    """MockBLDCDriver that raises _BoomError on the N-th set_throttle call."""

    def __init__(self, fail_at_call: int = 5) -> None:
        super().__init__()
        self._fail_at = fail_at_call
        self._call_count = 0

    def set_throttle(self, throttle: float) -> None:
        self._call_count += 1
        if self._call_count == self._fail_at:
            raise _BoomError("Injected fault at set_throttle call #5")
        super().set_throttle(throttle)


class TestContextManagerDisarmsOnError:
    async def test_driver_disarmed_after_fire_raises(self) -> None:
        driver = _FaultingBLDCDriver(fail_at_call=5)
        clock = FakeClock()
        ctl = SwingController(driver=driver, clock=clock)

        with pytest.raises(_BoomError):
            async with ctl:
                await ctl.fire(_STANDARD_PROFILE)

        # Context manager must have called disarm() regardless of the exception.
        assert driver.armed is False


# ---------------------------------------------------------------------------
# Test 7: Triangle profile (hold_ms=0)
# ---------------------------------------------------------------------------


class TestTriangleProfile:
    async def test_triangle_elapsed_matches_total(self) -> None:
        _, clock, ctl = _make_controller()
        ctl.arm()
        await ctl.fire(_TRIANGLE_PROFILE)

        expected_s = _TRIANGLE_PROFILE.total_ms / 1000.0
        assert clock.elapsed == pytest.approx(expected_s, abs=_TICK_MS / 1000.0)

    async def test_triangle_throttle_rises_then_falls(self) -> None:
        driver, _, ctl = _make_controller()
        ctl.arm()
        await ctl.fire(_TRIANGLE_PROFILE)

        history = driver.throttle_history[:-1]  # exclude trailing 0 from fire()
        assert len(history) > 2

        # Find the peak value index.
        peak_idx = history.index(max(history))
        # Before peak: non-decreasing.
        for i in range(1, peak_idx + 1):
            assert history[i] >= history[i - 1]
        # After peak: non-increasing.
        for i in range(peak_idx + 1, len(history)):
            assert history[i] <= history[i - 1]


# ---------------------------------------------------------------------------
# Test 8: Tick cadence — number of set_throttle calls is ~total_ms / _TICK_MS + 1
# ---------------------------------------------------------------------------


class TestTickCadence:
    async def test_call_count_approximately_total_ms_over_tick_ms(self) -> None:
        driver, _, ctl = _make_controller()
        ctl.arm()
        await ctl.fire(_STANDARD_PROFILE)

        expected_ticks = _STANDARD_PROFILE.total_ms / _TICK_MS + 1  # +1 for final zero
        actual_calls = len(driver.throttle_history)
        # Allow ±2 for rounding / off-by-one — don't over-constrain.
        assert abs(actual_calls - expected_ticks) <= 2


# ---------------------------------------------------------------------------
# Test 9: Multiple sequential fires on the same armed controller
# ---------------------------------------------------------------------------


class TestMultipleSequentialFires:
    async def test_second_fire_appends_to_history(self) -> None:
        driver, _, ctl = _make_controller()
        ctl.arm()

        await ctl.fire(_STANDARD_PROFILE)
        after_first = len(driver.throttle_history)
        assert after_first > 0

        await ctl.fire(_TRIANGLE_PROFILE)
        after_second = len(driver.throttle_history)
        # Second fire must have added more entries.
        assert after_second > after_first

    async def test_both_envelopes_appear_in_order(self) -> None:
        driver, _, ctl = _make_controller()
        ctl.arm()

        # Use two distinct peaks so we can identify boundaries.
        profile_a = SwingProfile(
            ramp_up_ms=20.0, hold_ms=10.0, ramp_down_ms=20.0, peak_throttle=0.3
        )
        profile_b = SwingProfile(
            ramp_up_ms=20.0, hold_ms=10.0, ramp_down_ms=20.0, peak_throttle=0.7
        )

        await ctl.fire(profile_a)
        split = len(driver.throttle_history)
        await ctl.fire(profile_b)

        first_half = driver.throttle_history[:split]
        second_half = driver.throttle_history[split:]

        # Each half ends at 0 (fire-end zero).
        assert first_half[-1] == 0.0
        assert second_half[-1] == 0.0

        # Peak in first half should be near profile_a.peak_throttle.
        assert max(first_half) == pytest.approx(profile_a.peak_throttle, abs=0.02)
        # Peak in second half should be near profile_b.peak_throttle.
        assert max(second_half) == pytest.approx(profile_b.peak_throttle, abs=0.02)


# ---------------------------------------------------------------------------
# Test 10: Re-arming after disarm via context manager
# ---------------------------------------------------------------------------


class TestRearmingAfterDisarm:
    async def test_new_context_manager_fires_after_first_exits(self) -> None:
        driver = MockBLDCDriver()

        # First context manager — fires and disarms.
        async with SwingController(driver=driver, clock=FakeClock()) as ctl:
            await ctl.fire(_STANDARD_PROFILE)

        assert driver.armed is False

        # Second context manager on same driver — must work after re-arm.
        async with SwingController(driver=driver, clock=FakeClock()) as ctl2:
            await ctl2.fire(_TRIANGLE_PROFILE)

        assert driver.armed is False
        # Should have accumulated history from both runs (including disarm zeros).
        assert len(driver.throttle_history) > 0
