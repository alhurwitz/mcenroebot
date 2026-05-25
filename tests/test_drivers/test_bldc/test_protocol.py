"""Protocol-level tests for BLDCDriver."""

from __future__ import annotations

import pytest

from mcenroebot.drivers.bldc import BLDCDriver, MockBLDCDriver, PCA9685BLDCDriver


class TestBLDCDriverProtocol:
    """BLDCDriver is a Protocol and mock implementations satisfy it."""

    def test_protocol_is_accessible(self) -> None:
        assert BLDCDriver is not None

    def test_mock_satisfies_protocol_isinstance(self) -> None:
        # BLDCDriver is @runtime_checkable so isinstance works.
        mock: BLDCDriver = MockBLDCDriver()
        assert isinstance(mock, BLDCDriver)

    def test_pca9685_satisfies_protocol_structurally(self) -> None:
        # PCA9685BLDCDriver has all three required methods.
        assert hasattr(PCA9685BLDCDriver, "arm")
        assert hasattr(PCA9685BLDCDriver, "set_throttle")
        assert hasattr(PCA9685BLDCDriver, "disarm")

    def test_mock_assignable_as_bldc_driver(self) -> None:
        driver: BLDCDriver = MockBLDCDriver()
        driver.arm()
        driver.set_throttle(0.5)
        driver.disarm()


class TestBLDCDriverProtocolCompliance:
    """BLDCDriver lifecycle contract is enforced by all implementations."""

    @pytest.mark.parametrize("throttle", [0.0, 0.5, 1.0])
    def test_mock_set_throttle_accepts_valid_values_after_arm(
        self, throttle: float
    ) -> None:
        driver: BLDCDriver = MockBLDCDriver()
        driver.arm()
        driver.set_throttle(throttle)  # must not raise

    def test_mock_set_throttle_before_arm_raises_runtime_error(self) -> None:
        driver: BLDCDriver = MockBLDCDriver()
        with pytest.raises(RuntimeError):
            driver.set_throttle(0.5)

    def test_mock_disarm_after_arm(self) -> None:
        driver: BLDCDriver = MockBLDCDriver()
        driver.arm()
        driver.disarm()  # must not raise
