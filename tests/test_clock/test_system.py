"""SystemClock-specific behaviour."""

from __future__ import annotations

import time

from mcenroebot.clock import SystemClock


class TestSystemClockSleepAwaits:
    async def test_sleep_50ms_takes_real_time(self) -> None:
        sc = SystemClock()
        wall_before = time.monotonic()
        await sc.sleep(0.05)
        wall_elapsed = time.monotonic() - wall_before
        # ≥0.04s (allow 20% under-run from OS scheduling jitter).
        # ≤0.5s  (allow generous over-run for slow/loaded CI).
        assert wall_elapsed >= 0.04, f"sleep(0.05) returned too fast: {wall_elapsed:.4f}s"
        assert wall_elapsed <= 0.5, f"sleep(0.05) took too long: {wall_elapsed:.4f}s"

    async def test_sleep_zero_does_not_block(self) -> None:
        """sleep(0) should yield to the event loop but return quickly."""
        sc = SystemClock()
        wall_before = time.monotonic()
        await sc.sleep(0.0)
        wall_elapsed = time.monotonic() - wall_before
        assert wall_elapsed < 1.0
