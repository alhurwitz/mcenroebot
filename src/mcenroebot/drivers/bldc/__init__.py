"""BLDC/ESC driver sub-package — Protocol, real PCA9685 impl, and mock impl.

Layout
------
    protocol.py  — BLDCDriver protocol (runtime-checkable).
    pca9685.py   — PCA9685BLDCDriver (real hardware; lazy adafruit import).
    mock.py      — MockBLDCDriver (in-memory, for unit tests).
"""

from __future__ import annotations

from mcenroebot.drivers.bldc.mock import MockBLDCDriver
from mcenroebot.drivers.bldc.pca9685 import PCA9685BLDCDriver
from mcenroebot.drivers.bldc.protocol import BLDCDriver

__all__ = ["BLDCDriver", "MockBLDCDriver", "PCA9685BLDCDriver"]
