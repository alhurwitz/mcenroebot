"""Tests for Pca9685FeederDriver — import-safety + off-Pi behaviour."""

from __future__ import annotations

import pytest


class TestPca9685FeederDriverImport:
    """Importing the real driver must succeed without Adafruit libs."""

    def test_module_imports_without_adafruit_installed(self) -> None:
        from mcenroebot.drivers.feeder.pca9685 import Pca9685FeederDriver  # noqa: F401

    def test_package_import_without_adafruit_installed(self) -> None:
        from mcenroebot.drivers.feeder import Pca9685FeederDriver  # noqa: F401


class TestPca9685FeederDriverOffPi:
    """Off-Pi, the constructor must fail with a clear ImportError."""

    @pytest.mark.integration
    def test_constructor_fails_off_pi(self) -> None:
        from mcenroebot.drivers.feeder.pca9685 import Pca9685FeederDriver

        with pytest.raises(ImportError, match=r"adafruit|pi"):
            Pca9685FeederDriver(channel=3)


class TestPca9685FeederDriverOnPi:
    """Real hardware tests — skipped when servokit is not installed."""

    @pytest.fixture(autouse=True)
    def require_servokit(self) -> None:
        pytest.importorskip("adafruit_servokit")

    @pytest.mark.integration
    def test_driver_instantiates_on_pi(self) -> None:
        from mcenroebot.drivers.feeder.pca9685 import Pca9685FeederDriver

        driver = Pca9685FeederDriver(channel=3)
        assert driver is not None

    @pytest.mark.integration
    def test_fire_raises_not_implemented_in_v1(self) -> None:
        from mcenroebot.drivers.feeder.pca9685 import Pca9685FeederDriver

        driver = Pca9685FeederDriver(channel=3)
        with pytest.raises(NotImplementedError, match="index"):
            driver.fire()
