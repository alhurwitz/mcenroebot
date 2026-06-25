"""Tests for the pure rate->throttle mapping used by the feeder driver."""

from __future__ import annotations

import pytest

from mcenroebot.drivers.feeder import throttle_for_rate


class TestThrottleForRate:
    def test_zero_rate_is_zero_throttle(self) -> None:
        assert throttle_for_rate(0.0, throttle_per_bpm=0.01) == 0.0

    def test_linear_in_rate(self) -> None:
        assert throttle_for_rate(40.0, throttle_per_bpm=0.01) == pytest.approx(0.4)
        assert throttle_for_rate(60.0, throttle_per_bpm=0.01) == pytest.approx(0.6)

    def test_monotonic_increasing(self) -> None:
        rates = [0.0, 10.0, 20.0, 40.0, 60.0]
        throttles = [throttle_for_rate(r, throttle_per_bpm=0.01) for r in rates]
        assert throttles == sorted(throttles)
        assert len(set(throttles)) == len(throttles)  # strictly increasing

    def test_clamped_to_one(self) -> None:
        assert throttle_for_rate(1000.0, throttle_per_bpm=0.01) == 1.0

    def test_negative_rate_raises(self) -> None:
        with pytest.raises(ValueError, match=r"balls_per_min"):
            throttle_for_rate(-1.0, throttle_per_bpm=0.01)
