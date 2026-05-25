"""Protocol-level tests for ServoDriver."""

from __future__ import annotations

import pytest

from mcenroebot.drivers.servo import MockServoDriver, PCA9685ServoDriver, ServoDriver


class TestServoDriverProtocol:
    """ServoDriver is a Protocol and mock implementations satisfy it."""

    def test_protocol_is_accessible(self) -> None:
        # Just importing ServoDriver and accessing it is the assertion.
        assert ServoDriver is not None

    def test_mock_satisfies_protocol_isinstance(self) -> None:
        # ServoDriver is @runtime_checkable so isinstance works.
        mock: ServoDriver = MockServoDriver()
        assert isinstance(mock, ServoDriver)

    def test_pca9685_satisfies_protocol_structurally(self) -> None:
        # PCA9685ServoDriver has write_angle — structurally compatible.
        # We only check the class itself (not the instance which needs hardware).
        assert hasattr(PCA9685ServoDriver, "write_angle")

    def test_mock_assignable_as_servo_driver(self) -> None:
        # Typed variable assignment — static check passes if mypy is happy,
        # and runtime confirms the object works through the protocol.
        driver: ServoDriver = MockServoDriver()
        driver.write_angle(0, 90.0)  # must not raise


class TestServoDriverProtocolCompliance:
    """Both concrete classes expose the required method signatures."""

    @pytest.mark.parametrize(
        "channel,angle_deg",
        [(0, 0.0), (1, 90.0), (15, 180.0)],
    )
    def test_mock_write_angle_accepts_valid_inputs(
        self, channel: int, angle_deg: float
    ) -> None:
        driver: ServoDriver = MockServoDriver()
        driver.write_angle(channel, angle_deg)  # must not raise

    def test_mock_write_angle_rejects_invalid_angle(self) -> None:
        driver: ServoDriver = MockServoDriver()
        with pytest.raises(ValueError):
            driver.write_angle(0, -1.0)
