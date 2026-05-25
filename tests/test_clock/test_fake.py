"""FakeClock-specific behaviour: non-blocking sleep, advance, elapsed."""

from __future__ import annotations

import time

import pytest

from mcenroebot.clock import FakeClock


class TestFakeClockSleepIsNonBlocking:
    """await FakeClock().sleep(10.0) must complete in well under 1 wall-clock second."""

    async def test_large_sleep_completes_instantly(self) -> None:
        fc = FakeClock()
        wall_before = time.monotonic()
        await fc.sleep(10.0)
        wall_elapsed = time.monotonic() - wall_before
        # Should finish in microseconds; 1 second is a very generous ceiling.
        assert wall_elapsed < 1.0, f"FakeClock.sleep blocked for {wall_elapsed:.3f}s"

    async def test_very_large_sleep_completes_instantly(self) -> None:
        fc = FakeClock()
        wall_before = time.monotonic()
        await fc.sleep(1_000_000.0)
        wall_elapsed = time.monotonic() - wall_before
        assert wall_elapsed < 1.0


class TestFakeClockSleepAdvancesTime:
    @pytest.mark.parametrize("duration", [0.0, 0.001, 1.0, 2.5, 100.0])
    async def test_sleep_advances_now_by_duration(self, duration: float) -> None:
        fc = FakeClock()
        before = fc.now()
        await fc.sleep(duration)
        assert fc.now() == pytest.approx(before + duration)

    async def test_multiple_sleeps_accumulate(self) -> None:
        fc = FakeClock()
        await fc.sleep(1.0)
        await fc.sleep(1.5)
        await fc.sleep(0.5)
        assert fc.now() == pytest.approx(3.0)

    async def test_sleep_from_nonzero_start(self) -> None:
        fc = FakeClock(start=10.0)
        await fc.sleep(2.5)
        assert fc.now() == pytest.approx(12.5)


class TestFakeClockAdvance:
    @pytest.mark.parametrize("delta", [0.0, 0.1, 5.0, 1000.0])
    def test_advance_moves_now(self, delta: float) -> None:
        fc = FakeClock()
        fc.advance(delta)
        assert fc.now() == pytest.approx(delta)

    def test_advance_multiple_times_accumulates(self) -> None:
        fc = FakeClock()
        fc.advance(1.0)
        fc.advance(2.0)
        fc.advance(0.5)
        assert fc.now() == pytest.approx(3.5)

    def test_advance_moves_elapsed(self) -> None:
        fc = FakeClock()
        fc.advance(7.25)
        assert fc.elapsed == pytest.approx(7.25)

    def test_advance_from_nonzero_start(self) -> None:
        fc = FakeClock(start=100.0)
        fc.advance(3.0)
        assert fc.now() == pytest.approx(103.0)
        assert fc.elapsed == pytest.approx(3.0)


class TestFakeClockElapsed:
    def test_elapsed_starts_at_zero(self) -> None:
        assert FakeClock().elapsed == pytest.approx(0.0)

    def test_elapsed_unaffected_by_start_offset(self) -> None:
        # start=500 means now() begins at 500, but elapsed starts at 0.
        fc = FakeClock(start=500.0)
        assert fc.elapsed == pytest.approx(0.0)

    def test_elapsed_after_advance(self) -> None:
        fc = FakeClock(start=42.0)
        fc.advance(10.0)
        assert fc.elapsed == pytest.approx(10.0)
        assert fc.now() == pytest.approx(52.0)

    async def test_elapsed_after_sleep(self) -> None:
        fc = FakeClock(start=1_000.0)
        await fc.sleep(3.5)
        assert fc.elapsed == pytest.approx(3.5)

    def test_elapsed_with_mixed_advance_and_start(self) -> None:
        fc = FakeClock(start=7.0)
        fc.advance(1.0)
        fc.advance(2.0)
        assert fc.elapsed == pytest.approx(3.0)
        assert fc.now() == pytest.approx(10.0)
