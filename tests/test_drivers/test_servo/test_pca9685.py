"""Tests for PCA9685ServoDriver — import-safety + off-Pi behaviour."""

from __future__ import annotations

import pytest


class TestPCA9685ServoDriverImport:
    """Importing PCA9685ServoDriver must succeed without Adafruit libs."""

    def test_module_imports_without_adafruit_installed(self) -> None:
        # If this test even runs, the import succeeded — that is the assertion.
        from mcenroebot.drivers.servo.pca9685 import PCA9685ServoDriver  # noqa: F401

    def test_package_import_without_adafruit_installed(self) -> None:
        # The servo package __init__ re-exports PCA9685ServoDriver — verify
        # that also works without Adafruit installed.
        from mcenroebot.drivers.servo import PCA9685ServoDriver  # noqa: F401

    def test_top_level_drivers_import_without_adafruit_installed(self) -> None:
        # The top-level drivers package re-exports PCA9685ServoDriver too.
        from mcenroebot.drivers import PCA9685ServoDriver  # noqa: F401


class TestPCA9685ServoDriverOffPi:
    """Off-Pi, the constructor must fail with a clear ImportError."""

    @pytest.mark.integration
    def test_constructor_fails_off_pi(self) -> None:
        """Off-Pi, instantiating PCA9685ServoDriver should raise ImportError."""
        from mcenroebot.drivers.servo.pca9685 import PCA9685ServoDriver

        with pytest.raises((ImportError, RuntimeError), match="adafruit|pi"):
            PCA9685ServoDriver()

    @pytest.mark.integration
    def test_constructor_error_message_mentions_install_command(self) -> None:
        """The ImportError message should tell the user how to fix it."""
        from mcenroebot.drivers.servo.pca9685 import PCA9685ServoDriver

        with pytest.raises((ImportError, RuntimeError)) as exc_info:
            PCA9685ServoDriver()
        msg = str(exc_info.value).lower()
        # Must mention either 'adafruit' or 'pi' extra
        assert "adafruit" in msg or "pi" in msg


class TestPCA9685ServoDriverOnPi:
    """Real hardware tests — skipped when Adafruit is not installed."""

    @pytest.fixture(autouse=True)
    def require_adafruit_servokit(self) -> None:
        pytest.importorskip("adafruit_servokit")

    @pytest.mark.integration
    def test_driver_instantiates_on_pi(self) -> None:
        from mcenroebot.drivers.servo.pca9685 import PCA9685ServoDriver

        driver = PCA9685ServoDriver()
        assert driver is not None

    @pytest.mark.integration
    def test_write_angle_validates_channel_range(self) -> None:
        from mcenroebot.drivers.servo.pca9685 import PCA9685ServoDriver

        driver = PCA9685ServoDriver(channel_count=16)
        with pytest.raises(ValueError, match="channel"):
            driver.write_angle(16, 90.0)

    @pytest.mark.integration
    def test_write_angle_validates_angle_range(self) -> None:
        from mcenroebot.drivers.servo.pca9685 import PCA9685ServoDriver

        driver = PCA9685ServoDriver(channel_count=16)
        with pytest.raises(ValueError, match="angle_deg"):
            driver.write_angle(0, 181.0)
