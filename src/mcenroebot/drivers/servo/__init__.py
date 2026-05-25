"""Servo driver sub-package — Protocol, real PCA9685 impl, and mock impl.

Layout
------
    protocol.py  — ServoDriver protocol (runtime-checkable).
    pca9685.py   — PCA9685ServoDriver (real hardware; lazy adafruit import).
    mock.py      — MockServoDriver (in-memory, for unit tests).
"""

from __future__ import annotations

from mcenroebot.drivers.servo.mock import MockServoDriver
from mcenroebot.drivers.servo.pca9685 import PCA9685ServoDriver
from mcenroebot.drivers.servo.protocol import ServoDriver

__all__ = ["MockServoDriver", "PCA9685ServoDriver", "ServoDriver"]
