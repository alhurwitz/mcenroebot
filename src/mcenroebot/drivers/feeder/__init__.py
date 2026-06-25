"""Feeder (escapement) driver — meter balls from the hopper one at a time.

The v1 escapement is a continuous-rotation servo spinning a single-pocket
indexing disk at a fixed rate. Single-ball metering is geometric (one pocket =
one ball per revolution), so the control surface is ``set_rate(balls_per_min)``;
``fire()`` (one ball per call) is the deferred index-endstop upgrade.

Layout
------
    protocol.py  — FeederDriver Protocol.
    mapping.py   — pure throttle_for_rate() (off-Pi testable).
    pca9685.py   — Pca9685FeederDriver (real, lazy Adafruit import; Pi only).
    mock.py      — MockFeederDriver (records calls for assertions).
"""

from __future__ import annotations

from mcenroebot.drivers.feeder.mapping import throttle_for_rate
from mcenroebot.drivers.feeder.mock import MockFeederDriver
from mcenroebot.drivers.feeder.pca9685 import Pca9685FeederDriver
from mcenroebot.drivers.feeder.protocol import FeederDriver

__all__ = [
    "FeederDriver",
    "MockFeederDriver",
    "Pca9685FeederDriver",
    "throttle_for_rate",
]
