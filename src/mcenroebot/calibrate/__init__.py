"""ESC calibration routine for McEnroe V2.

This package runs the one-shot ESC throttle calibration sequence needed
before the first motor use.  The operator is guided through power-cycling
the ESC while the calibrator sends max- then min-throttle PWM signals,
locking the ESC's throttle endpoints.

Layout
------
    esc.py       — ``EscCalibrator`` class + private ``_demo`` helper.
    __main__.py  — entry point for ``python -m mcenroebot.calibrate``.

Typical usage
-------------
    from mcenroebot.calibrate import EscCalibrator
    from mcenroebot.clock import SystemClock
    from mcenroebot.drivers import PCA9685BLDCDriver

    driver = PCA9685BLDCDriver(channel=2)
    calibrator = EscCalibrator(driver=driver, clock=SystemClock())
    await calibrator.run()
"""

from __future__ import annotations

from mcenroebot.calibrate.esc import EscCalibrator, _demo

__all__ = [
    "EscCalibrator",
    "_demo",
]
