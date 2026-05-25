"""Behaviour tests for MockBLDCDriver."""

from __future__ import annotations

import pytest

from mcenroebot.drivers.bldc import BLDCDriver, MockBLDCDriver


class TestMockBLDCDriverProtocolCompliance:
    """MockBLDCDriver satisfies the BLDCDriver Protocol."""

    def test_isinstance_bldc_driver(self) -> None:
        assert isinstance(MockBLDCDriver(), BLDCDriver)

    def test_assignable_to_bldc_driver_typed_var(self) -> None:
        _: BLDCDriver = MockBLDCDriver()


class TestMockBLDCDriverArmedState:
    """Armed flag transitions."""

    def test_not_armed_on_construction(self) -> None:
        driver = MockBLDCDriver()
        assert driver.armed is False

    def test_arm_sets_armed_flag(self) -> None:
        driver = MockBLDCDriver()
        driver.arm()
        assert driver.armed is True

    def test_disarm_clears_armed_flag(self) -> None:
        driver = MockBLDCDriver()
        driver.arm()
        driver.disarm()
        assert driver.armed is False

    def test_set_throttle_before_arm_raises_runtime_error(self) -> None:
        driver = MockBLDCDriver()
        with pytest.raises(RuntimeError, match="armed"):
            driver.set_throttle(0.5)

    def test_set_throttle_after_disarm_raises_runtime_error(self) -> None:
        driver = MockBLDCDriver()
        driver.arm()
        driver.disarm()
        with pytest.raises(RuntimeError, match="armed"):
            driver.set_throttle(0.5)

    def test_re_arm_after_disarm_allows_throttle(self) -> None:
        driver = MockBLDCDriver()
        driver.arm()
        driver.disarm()
        driver.arm()
        driver.set_throttle(0.3)  # must not raise
        assert 0.3 in driver.throttle_history


class TestMockBLDCDriverThrottleHistory:
    """Throttle history records set_throttle calls + disarm sentinel."""

    def test_empty_history_on_construction(self) -> None:
        driver = MockBLDCDriver()
        assert driver.throttle_history == []

    def test_arm_does_not_append_to_history(self) -> None:
        driver = MockBLDCDriver()
        driver.arm()
        assert driver.throttle_history == []

    def test_single_set_throttle_recorded(self) -> None:
        driver = MockBLDCDriver()
        driver.arm()
        driver.set_throttle(0.5)
        assert driver.throttle_history == [0.5]

    def test_three_set_throttle_calls_recorded_in_order(self) -> None:
        driver = MockBLDCDriver()
        driver.arm()
        driver.set_throttle(0.2)
        driver.set_throttle(0.6)
        driver.set_throttle(1.0)
        assert driver.throttle_history == [0.2, 0.6, 1.0]

    def test_disarm_appends_zero_to_history(self) -> None:
        driver = MockBLDCDriver()
        driver.arm()
        driver.set_throttle(0.8)
        driver.disarm()
        assert driver.throttle_history == [0.8, 0.0]

    def test_throttle_history_is_defensive_copy(self) -> None:
        """Mutating the returned list must NOT affect internal state."""
        driver = MockBLDCDriver()
        driver.arm()
        driver.set_throttle(0.4)
        snapshot = driver.throttle_history
        snapshot.append(999.0)  # mutate the returned list
        assert driver.throttle_history == [0.4]  # internal state unchanged


class TestMockBLDCDriverValidation:
    """Throttle validation mirrors the real driver."""

    @pytest.mark.parametrize("throttle", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_valid_throttle_accepted(self, throttle: float) -> None:
        driver = MockBLDCDriver()
        driver.arm()
        driver.set_throttle(throttle)
        assert throttle in driver.throttle_history

    @pytest.mark.parametrize("throttle", [-0.001, -1.0, 1.001, 2.0])
    def test_invalid_throttle_raises_value_error(self, throttle: float) -> None:
        driver = MockBLDCDriver()
        driver.arm()
        with pytest.raises(ValueError, match="throttle"):
            driver.set_throttle(throttle)

    def test_invalid_throttle_not_recorded_in_history(self) -> None:
        driver = MockBLDCDriver()
        driver.arm()
        driver.set_throttle(0.5)  # valid
        with pytest.raises(ValueError):
            driver.set_throttle(-0.1)  # invalid
        assert driver.throttle_history == [0.5]

    def test_boundary_throttle_0(self) -> None:
        driver = MockBLDCDriver()
        driver.arm()
        driver.set_throttle(0.0)
        assert driver.throttle_history[-1] == 0.0

    def test_boundary_throttle_1(self) -> None:
        driver = MockBLDCDriver()
        driver.arm()
        driver.set_throttle(1.0)
        assert driver.throttle_history[-1] == 1.0
