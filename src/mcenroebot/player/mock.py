"""MockPlayerDetector — returns a programmed PlayerPosition for tests."""

from __future__ import annotations

from typing import Any

from numpy.typing import NDArray

from mcenroebot.player.value_objects import PlayerPosition

__all__ = ["MockPlayerDetector"]


class MockPlayerDetector:
    """PlayerDetector that ignores the frame and returns a fixed result.

    Set ``position`` (a PlayerPosition or None) to drive deterministic tests
    of the placement strategy. Records how many times ``detect`` was called.
    """

    def __init__(self, position: PlayerPosition | None) -> None:
        self.position = position
        self.calls = 0

    def detect(self, frame: NDArray[Any]) -> PlayerPosition | None:
        """Return the configured ``position`` regardless of ``frame``."""
        self.calls += 1
        return self.position
