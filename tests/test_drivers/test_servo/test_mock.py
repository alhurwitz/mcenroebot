"""Behaviour tests for MockServoDriver."""

from __future__ import annotations

import pytest

from mcenroebot.drivers.servo import MockServoDriver, ServoDriver


class TestMockServoDriverProtocolCompliance:
    """MockServoDriver satisfies the ServoDriver Protocol."""

    def test_isinstance_servo_driver(self) -> None:
        assert isinstance(MockServoDriver(), ServoDriver)

    def test_assignable_to_servo_driver_typed_var(self) -> None:
        _: ServoDriver = MockServoDriver()


class TestMockServoDriverRecording:
    """Writes are recorded in order; failed writes are not recorded."""

    def test_empty_history_on_construction(self) -> None:
        driver = MockServoDriver()
        assert driver.history == []

    def test_single_write_recorded(self) -> None:
        driver = MockServoDriver()
        driver.write_angle(0, 45.0)
        assert driver.history == [(0, 45.0)]

    def test_three_writes_recorded_in_order(self) -> None:
        driver = MockServoDriver()
        driver.write_angle(0, 0.0)
        driver.write_angle(1, 90.0)
        driver.write_angle(2, 180.0)
        assert driver.history == [(0, 0.0), (1, 90.0), (2, 180.0)]

    def test_writes_from_different_channels_recorded(self) -> None:
        driver = MockServoDriver()
        driver.write_angle(5, 30.0)
        driver.write_angle(5, 60.0)
        driver.write_angle(5, 90.0)
        assert driver.history == [(5, 30.0), (5, 60.0), (5, 90.0)]

    def test_history_is_defensive_copy(self) -> None:
        """Mutating the returned list must NOT affect internal state."""
        driver = MockServoDriver()
        driver.write_angle(0, 10.0)
        snapshot = driver.history
        snapshot.append((99, 99.0))  # mutate the returned list
        assert driver.history == [(0, 10.0)]  # internal state unchanged


class TestMockServoDriverValidation:
    """Angle validation mirrors the real driver — keeps tests honest."""

    @pytest.mark.parametrize("angle_deg", [0.0, 45.0, 90.0, 135.0, 180.0])
    def test_valid_angles_accepted(self, angle_deg: float) -> None:
        driver = MockServoDriver()
        driver.write_angle(0, angle_deg)  # must not raise
        assert driver.history == [(0, angle_deg)]

    @pytest.mark.parametrize("angle_deg", [-0.001, -1.0, 180.001, 270.0, 360.0])
    def test_invalid_angle_raises_value_error(self, angle_deg: float) -> None:
        driver = MockServoDriver()
        with pytest.raises(ValueError, match="angle_deg"):
            driver.write_angle(0, angle_deg)

    def test_invalid_angle_not_recorded_in_history(self) -> None:
        driver = MockServoDriver()
        driver.write_angle(0, 90.0)  # valid
        with pytest.raises(ValueError):
            driver.write_angle(0, 999.0)  # invalid
        # Only the successful write should be in history.
        assert driver.history == [(0, 90.0)]

    def test_channel_not_validated_by_mock(self) -> None:
        """Mock does not enforce channel range — it has no channel_count."""
        driver = MockServoDriver()
        # Channel 99 would be out-of-range on a real 16-channel board but
        # the mock is lenient about config it doesn't own.
        driver.write_angle(99, 90.0)
        assert driver.history == [(99, 90.0)]

    def test_boundary_angle_0(self) -> None:
        driver = MockServoDriver()
        driver.write_angle(0, 0.0)
        assert driver.history[-1] == (0, 0.0)

    def test_boundary_angle_180(self) -> None:
        driver = MockServoDriver()
        driver.write_angle(0, 180.0)
        assert driver.history[-1] == (0, 180.0)
