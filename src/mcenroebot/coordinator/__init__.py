"""Top-level coordinators wiring the control pipeline to hardware drivers.

The V3 ``RallyCoordinator`` has been shelved to ``mcenroebot._shelved.rally`` for the
V4 feeder build. The active coordinator here is ``FeederCoordinator``, which wires the
drill -> launch + aim + feeder + lift pipeline (see
``docs/superpowers/specs/2026-06-23-feeder-design.md`` §6).
"""

from __future__ import annotations

from mcenroebot.coordinator.feeder import FeederCoordinator, _demo

__all__ = ["FeederCoordinator", "_demo"]
