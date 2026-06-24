"""PlayerDetector protocol — the interface every player detector satisfies."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from numpy.typing import NDArray

from mcenroebot.player.value_objects import PlayerPosition

__all__ = ["PlayerDetector"]


@runtime_checkable
class PlayerDetector(Protocol):
    """Find the human in a camera frame.

    Returns ``None`` when no player is confidently found; the caller (a
    placement strategy) decides how to handle that — typically by falling
    back to a fixed pattern.
    """

    def detect(self, frame: NDArray[Any]) -> PlayerPosition | None:
        """Return the detected player position, or ``None`` if not found."""
        ...
