"""Tests for PCA9685BLDCDriver — import-safety + off-Pi behaviour."""

from __future__ import annotations

import pytest


class TestPCA9685BLDCDriverImport:
    """Importing PCA9685BLDCDriver must succeed without Adafruit libs."""

    def test_module_imports_without_adafruit_installed(self) -> None:
        # If this test even runs, the import succeeded — that is the assertion.
        from mcenroebot.drivers.bldc.pca9685 import PCA9685BLDCDriver  # noqa: F401

    def test_package_import_without_adafruit_installed(self) -> None:
        from mcenroebot.drivers.bldc import PCA9685BLDCDriver  # noqa: F401

    def test_top_level_drivers_import_without_adafruit_installed(self) -> None:
        from mcenroebot.drivers import PCA9685BLDCDriver  # noqa: F401


class TestPCA9685BLDCDriverOffPi:
    """Off-Pi, the constructor must fail with a clear ImportError."""

    @pytest.mark.integration
    def test_constructor_fails_off_pi(self) -> None:
        """Off-Pi, instantiating PCA9685BLDCDriver should raise ImportError."""
        from mcenroebot.drivers.bldc.pca9685 import PCA9685BLDCDriver

        with pytest.raises((ImportError, RuntimeError), match="adafruit|pi"):
            PCA9685BLDCDriver()

    @pytest.mark.integration
    def test_constructor_error_message_mentions_install_command(self) -> None:
        """The ImportError message should tell the user how to fix it."""
        from mcenroebot.drivers.bldc.pca9685 import PCA9685BLDCDriver

        with pytest.raises((ImportError, RuntimeError)) as exc_info:
            PCA9685BLDCDriver()
        msg = str(exc_info.value).lower()
        assert "adafruit" in msg or "pi" in msg


class TestPCA9685BLDCDriverOnPi:
    """Real hardware tests — skipped when Adafruit is not installed."""

    @pytest.fixture(autouse=True)
    def require_adafruit_pca9685(self) -> None:
        # Require both the pca9685 lib and board (which needs pkg_resources on
        # some platforms).  If either is missing/broken, skip the whole class.
        pytest.importorskip("adafruit_pca9685")
        pytest.importorskip("board")

    @pytest.mark.integration
    def test_driver_instantiates_on_pi(self) -> None:
        from mcenroebot.drivers.bldc.pca9685 import PCA9685BLDCDriver

        driver = PCA9685BLDCDriver()
        assert driver is not None

    @pytest.mark.integration
    def test_set_throttle_before_arm_raises_runtime_error(self) -> None:
        from mcenroebot.drivers.bldc.pca9685 import PCA9685BLDCDriver

        driver = PCA9685BLDCDriver()
        with pytest.raises(RuntimeError, match="armed"):
            driver.set_throttle(0.5)

    @pytest.mark.integration
    def test_set_throttle_validates_range(self) -> None:
        from mcenroebot.drivers.bldc.pca9685 import PCA9685BLDCDriver

        driver = PCA9685BLDCDriver()
        driver.arm()
        with pytest.raises(ValueError, match="throttle"):
            driver.set_throttle(1.1)
