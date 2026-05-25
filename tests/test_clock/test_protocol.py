"""Protocol-level tests that apply to both Clock implementations."""

from __future__ import annotations

import pytest

from mcenroebot.clock import Clock, FakeClock, SystemClock


class TestProtocolCompliance:
    """Both concrete classes must satisfy the Clock protocol."""

    def test_system_clock_is_clock(self) -> None:
        clock: Clock = SystemClock()
        # If isinstance passes, the runtime_checkable protocol is satisfied.
        assert isinstance(clock, Clock)

    def test_fake_clock_is_clock(self) -> None:
        clock: Clock = FakeClock()
        assert isinstance(clock, Clock)

    async def test_system_clock_callable_through_protocol(self) -> None:
        """Call both methods on a Clock-typed variable — no type errors."""
        clock: Clock = SystemClock()
        t = clock.now()
        assert isinstance(t, float)
        # sleep(0) is effectively a no-op but still exercises the code path.
        await clock.sleep(0.0)

    async def test_fake_clock_callable_through_protocol(self) -> None:
        clock: Clock = FakeClock()
        t = clock.now()
        assert isinstance(t, float)
        await clock.sleep(0.0)


class TestMonotonicity:
    """now() must be non-decreasing across successive calls for both clocks."""

    def test_system_clock_now_is_non_decreasing(self) -> None:
        sc = SystemClock()
        readings = [sc.now() for _ in range(20)]
        for a, b in zip(readings, readings[1:]):
            assert b >= a, f"now() went backwards: {a} -> {b}"

    def test_fake_clock_now_is_non_decreasing_without_advance(self) -> None:
        fc = FakeClock()
        readings = [fc.now() for _ in range(20)]
        for a, b in zip(readings, readings[1:]):
            assert b >= a

    def test_fake_clock_now_is_non_decreasing_with_advance(self) -> None:
        fc = FakeClock()
        t0 = fc.now()
        fc.advance(1.0)
        t1 = fc.now()
        fc.advance(0.5)
        t2 = fc.now()
        assert t1 >= t0
        assert t2 >= t1

    async def test_fake_clock_now_is_non_decreasing_after_sleep(self) -> None:
        fc = FakeClock()
        t0 = fc.now()
        await fc.sleep(3.0)
        t1 = fc.now()
        await fc.sleep(0.0)
        t2 = fc.now()
        assert t1 >= t0
        assert t2 >= t1


class TestNegativeSleep:
    """Both clocks must raise ValueError for negative durations."""

    @pytest.mark.parametrize("seconds", [-0.001, -1.0, -1_000.0])
    async def test_fake_clock_sleep_negative_raises(self, seconds: float) -> None:
        fc = FakeClock()
        with pytest.raises(ValueError, match="non-negative"):
            await fc.sleep(seconds)

    @pytest.mark.parametrize("seconds", [-0.001, -1.0, -1_000.0])
    async def test_system_clock_sleep_negative_raises(self, seconds: float) -> None:
        sc = SystemClock()
        with pytest.raises(ValueError, match="non-negative"):
            await sc.sleep(seconds)

    @pytest.mark.parametrize("seconds", [-0.001, -1.0, -1_000.0])
    def test_fake_clock_advance_negative_raises(self, seconds: float) -> None:
        fc = FakeClock()
        with pytest.raises(ValueError, match="non-negative"):
            fc.advance(seconds)

    async def test_negative_sleep_does_not_advance_fake_clock(self) -> None:
        """Even if the exception is caught, time must not have moved."""
        fc = FakeClock()
        before = fc.now()
        try:
            await fc.sleep(-5.0)
        except ValueError:
            pass
        assert fc.now() == before
