"""Tests for Pca9685LiftDriver and GpioHopperSensor — import-safety + off-Pi."""

from __future__ import annotations

import pytest


class TestImportSafety:
    """Importing the real drivers must succeed without Adafruit / RPi libs."""

    def test_lift_module_imports(self) -> None:
        from mcenroebot.drivers.lift.pca9685 import Pca9685LiftDriver  # noqa: F401

    def test_lift_package_imports(self) -> None:
        from mcenroebot.drivers.lift import Pca9685LiftDriver  # noqa: F401

    def test_hopper_sensor_imports(self) -> None:
        from mcenroebot.drivers.lift import GpioHopperSensor  # noqa: F401


class TestOffPi:
    @pytest.mark.integration
    def test_lift_constructor_fails_off_pi(self) -> None:
        from mcenroebot.drivers.lift.pca9685 import Pca9685LiftDriver

        with pytest.raises(ImportError, match=r"adafruit|pi"):
            Pca9685LiftDriver(channel=4)

    @pytest.mark.integration
    def test_hopper_sensor_constructor_fails_off_pi(self) -> None:
        from mcenroebot.drivers.lift.gpio import GpioHopperSensor

        with pytest.raises(ImportError, match=r"RPi|GPIO|pi"):
            GpioHopperSensor(pin=17)
