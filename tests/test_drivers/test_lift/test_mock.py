"""Tests for MockLiftDriver and MockHopperSensor."""

from __future__ import annotations

import pytest

from mcenroebot.drivers.lift import MockHopperSensor, MockLiftDriver


class TestMockLiftDriver:
    def test_records_duty_in_order(self) -> None:
        driver = MockLiftDriver()
        driver.set_duty(0.5)
        driver.set_duty(1.0)
        driver.off()
        assert driver.duty_history == [0.5, 1.0, 0.0]

    @pytest.mark.parametrize("duty", [-0.1, 1.1])
    def test_out_of_range_raises_and_not_recorded(self, duty: float) -> None:
        driver = MockLiftDriver()
        with pytest.raises(ValueError, match=r"duty|fraction"):
            driver.set_duty(duty)
        assert driver.duty_history == []

    def test_boundaries_accepted(self) -> None:
        driver = MockLiftDriver()
        driver.set_duty(0.0)
        driver.set_duty(1.0)
        assert driver.duty_history == [0.0, 1.0]

    def test_history_is_defensive_copy(self) -> None:
        driver = MockLiftDriver()
        driver.set_duty(0.5)
        driver.duty_history.clear()
        assert driver.duty_history == [0.5]


class TestMockHopperSensor:
    def test_defaults_not_full(self) -> None:
        assert MockHopperSensor().is_full() is False

    def test_constructed_full(self) -> None:
        assert MockHopperSensor(full=True).is_full() is True

    def test_toggle(self) -> None:
        sensor = MockHopperSensor()
        assert sensor.is_full() is False
        sensor.full = True
        assert sensor.is_full() is True
