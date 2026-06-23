"""Shelved V3 rally coordinator — wires the predictor, aim controller, servo driver,
and swing controller into a return-rally loop.

Inactive under the V4 feeder build (see ``mcenroebot._shelved``). The feeder uses a
new ``mcenroebot.coordinator.FeederCoordinator`` instead, which does not import this
package. Kept for reference / possible future return-rally work.

Layout
------
    rally.py    — RallyCoordinator class.
    __main__.py — entry point for ``python -m mcenroebot._shelved.rally``.
"""

from __future__ import annotations

from mcenroebot._shelved.rally.rally import RallyCoordinator

__all__ = ["RallyCoordinator", "_demo"]


def _demo() -> None:
    """Run a short synthetic rally against mock drivers and print results.

    Run with ``python -m mcenroebot._shelved.rally``.
    """
    from mcenroebot._shelved.rally.__main__ import _demo as _main_demo

    _main_demo()
