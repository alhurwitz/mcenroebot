"""Tests for MockFeederDriver — records escapement calls for assertions."""

from __future__ import annotations

import pytest

from mcenroebot.drivers.feeder import MockFeederDriver


class TestMockFeederDriver:
    def test_records_calls_in_order(self) -> None:
        driver = MockFeederDriver()
        driver.set_rate(40.0)
        driver.set_rate(55.0)
        driver.stop()
        assert driver.calls == [("set_rate", 40.0), ("set_rate", 55.0), ("stop", None)]

    def test_records_fire(self) -> None:
        driver = MockFeederDriver()
        driver.fire()
        assert driver.calls == [("fire", None)]

    def test_negative_rate_raises_and_is_not_recorded(self) -> None:
        driver = MockFeederDriver()
        with pytest.raises(ValueError, match=r"balls_per_min"):
            driver.set_rate(-5.0)
        assert driver.calls == []

    def test_calls_is_defensive_copy(self) -> None:
        driver = MockFeederDriver()
        driver.set_rate(40.0)
        driver.calls.clear()
        assert driver.calls == [("set_rate", 40.0)]
