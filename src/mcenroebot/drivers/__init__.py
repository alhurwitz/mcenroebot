"""Hardware-driver layer for McEnroe V2.

This package provides the servo and BLDC/ESC drivers used by the turret
control loop.  Each sub-package exposes a runtime-checkable ``Protocol``
interface plus two concrete implementations: a real driver that talks to
the PCA9685 over I2C (Pi only), and an in-memory mock suitable for unit tests.

Sub-packages
------------
    servo/  — ServoDriver, PCA9685ServoDriver, MockServoDriver.
    bldc/   — BLDCDriver, PCA9685BLDCDriver, MockBLDCDriver.

Pi-only Adafruit libraries are imported lazily inside each real driver's
``__init__`` method so that importing this package on a Mac never raises
``ImportError``.  Install them on the Pi with ``uv sync --extra pi``.
"""

from __future__ import annotations

from mcenroebot.drivers.bldc import BLDCDriver, MockBLDCDriver, PCA9685BLDCDriver
from mcenroebot.drivers.servo import MockServoDriver, PCA9685ServoDriver, ServoDriver

__all__ = [
    "BLDCDriver",
    "MockBLDCDriver",
    "MockServoDriver",
    "PCA9685BLDCDriver",
    "PCA9685ServoDriver",
    "ServoDriver",
]
