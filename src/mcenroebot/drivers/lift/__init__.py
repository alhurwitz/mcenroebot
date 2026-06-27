"""Lift (auger) driver — recycle balls from the catch trough up to the hopper.

The auger is a 12 V gearmotor turning a helical screw, driven single-direction
through a MOSFET/L298N from a PCA9685 PWM channel. An optional hopper-full
endstop gates the auger so it stops when the buffer hopper is topped up.

Layout
------
    protocol.py   — LiftDriver + HopperSensor Protocols.
    pca9685.py    — Pca9685LiftDriver (PWM->MOSFET/ENA on a PCA9685; two-board
                    setups only — needs its own board at ~1 kHz).
    gpio_lift.py  — GpioLiftDriver (Pi hardware-PWM -> L298N ENA; the
                    single-PCA9685 auger path). Lazy RPi.GPIO; Pi only.
    gpio.py       — GpioHopperSensor (real endstop, lazy RPi.GPIO; Pi only).
    mock.py       — MockLiftDriver + MockHopperSensor for tests.
"""

from __future__ import annotations

from mcenroebot.drivers.lift.gpio import GpioHopperSensor
from mcenroebot.drivers.lift.gpio_lift import GpioLiftDriver
from mcenroebot.drivers.lift.mock import MockHopperSensor, MockLiftDriver
from mcenroebot.drivers.lift.pca9685 import Pca9685LiftDriver
from mcenroebot.drivers.lift.protocol import HopperSensor, LiftDriver

__all__ = [
    "GpioHopperSensor",
    "GpioLiftDriver",
    "HopperSensor",
    "LiftDriver",
    "MockHopperSensor",
    "MockLiftDriver",
    "Pca9685LiftDriver",
]
