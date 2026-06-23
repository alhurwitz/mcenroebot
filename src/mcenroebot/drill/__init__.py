"""Drill engine — emit a stream of Shots from an aim pattern + cadence.

The behavior layer of the V4 feeder. A :class:`Drill` combines a launch
``ShotSpec``, an :class:`AimStrategy`, and a cadence into an iterator of
:class:`Shot` objects that the ``FeederCoordinator`` executes one at a time.

The ``AimStrategy`` Protocol is the pluggable seam between the vision-free
fixed patterns (Wave 3) and the optional ``VisionPlacementStrategy`` (Wave 6):
swapping strategies changes *where* balls go without touching the launch math,
the Drill, or the coordinator.

Layout
------
    value_objects.py — TableTarget, DrillContext, Shot (frozen pydantic).
    strategy.py      — AimStrategy Protocol, FixedPatternStrategy.
    engine.py        — Drill.
    __main__.py      — entry point for `python -m mcenroebot.drill`.
"""

from mcenroebot.drill.engine import Drill, _demo
from mcenroebot.drill.strategy import AimStrategy, FixedPatternStrategy, Pattern
from mcenroebot.drill.value_objects import DrillContext, Shot, TableTarget

__all__ = [
    "AimStrategy",
    "Drill",
    "DrillContext",
    "FixedPatternStrategy",
    "Pattern",
    "Shot",
    "TableTarget",
    "_demo",
]
