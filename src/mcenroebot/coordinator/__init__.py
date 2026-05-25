"""Top-level rally coordinator — wires the predictor, aim controller, servo driver,
and swing controller into a working rally loop.

This package is the final integration layer of the McEnroe V2 control software.
It connects the trajectory predictor and aim controller to the hardware drivers,
deciding when to update servo angles and when to fire the swing.

Layout
------
    rally.py    — RallyCoordinator class.
    __main__.py — entry point for ``python -m mcenroebot.coordinator``.

Pipeline (per observation)
--------------------------
::

    BallObservation
        └─► TrajectoryPredictor.add()
                └─► predict_strike(strike_plane_x)
                        └─► AimController.compute(impact_point)
                                └─► ServoDriver.write_angle()  ← servo update
                                └─► [timing check]
                                        └─► SwingController.fire()  ← swing

Firing logic
------------
The coordinator fires when:

  1. The predictor has enough observations and returns a valid ``StrikePrediction``.
  2. The aim controller can reach the predicted impact point.
  3. ``clock.now() >= impact_time - swing_latency_s``.
  4. At least ``rearm_min_interval_s`` has elapsed since the last fire.

The rearm interval enforces "one fire per arc" — once the swing triggers, it
will not trigger again on subsequent observations in the same incoming pass.

Swing arming
------------
The coordinator arms the swing lazily on the first fire attempt — not at
construction time.  Callers that manage the swing lifecycle across rallies
(e.g. pausing between points) should call ``swing.arm()`` explicitly before
handing the coordinator to a new rally loop, or they can disarm and re-arm as
needed after the ``RallyCoordinator`` completes.
"""

from __future__ import annotations

from mcenroebot.coordinator.rally import RallyCoordinator

__all__ = ["RallyCoordinator", "_demo"]


def _demo() -> None:
    """Run a short synthetic rally against mock drivers and print results.

    Run with ``python -m mcenroebot.coordinator``.
    """
    from mcenroebot.coordinator.__main__ import _demo as _main_demo

    _main_demo()
