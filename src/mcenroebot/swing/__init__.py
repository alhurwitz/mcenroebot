"""Swing controller — open-loop BLDC throttle envelope for one paddle swing.

This package drives the brushless motor (J3) through a timed throttle profile
to produce a single paddle swing.  The controller is designed for FakeClock-
testable timing and implements the async context-manager protocol so callers
are guaranteed the driver is disarmed on exit even if ``fire()`` raises.

Layout
------
    profile.py    — ``SwingProfile`` frozen pydantic model (ramp-up / hold / ramp-down).
    controller.py — ``SwingController`` async context manager.
    __main__.py   — entry point for ``python -m mcenroebot.swing``.

Throttle convention
-------------------
Throttle is a normalised float in ``[0.0, 1.0]``:
  ``0.0`` → 1000 µs ESC pulse (idle / arming signal).
  ``1.0`` → 2000 µs ESC pulse (full throttle).

The BLDC must be armed by calling ``arm()`` (or entering the context manager)
before ``fire()`` is called.  The context manager always calls ``disarm()`` on
exit, zeroing the throttle and clearing the armed flag.

Tick cadence
------------
The controller samples the envelope at ``_TICK_MS = 5 ms`` (~200 Hz), well
above the PCA9685's 50 Hz PWM update rate and small relative to a typical
100-200 ms swing duration.  Import ``_TICK_MS`` from ``controller`` if you need
to monkeypatch it in tests.
"""

from __future__ import annotations

from mcenroebot.swing.controller import SwingController, _demo
from mcenroebot.swing.profile import SwingProfile

__all__ = [
    "SwingController",
    "SwingProfile",
    "_demo",
]
