"""Player detection — find the human so the feeder can target the open court.

The *easy* slice of vision (Wave 6): in the forgiving 1-2 s feed interval,
look at the player and decide which side is open. No incoming-ball 3D tracking,
no sub-100 ms timing. Plugs into the feeder via ``drill.VisionPlacementStrategy``
behind the ``AimStrategy`` Protocol — swapping it in changes *where* balls go
without touching the launch math, the Drill, or the FeederCoordinator.

Layout
------
    value_objects.py — PlayerPosition (frozen pydantic).
    protocol.py      — PlayerDetector Protocol.
    blob.py          — SimpleBlobDetector + offset_from_centroid helper.
    mock.py          — MockPlayerDetector for tests.
"""

from mcenroebot.player.blob import SimpleBlobDetector, offset_from_centroid
from mcenroebot.player.mock import MockPlayerDetector
from mcenroebot.player.protocol import PlayerDetector
from mcenroebot.player.value_objects import PlayerPosition

__all__ = [
    "MockPlayerDetector",
    "PlayerDetector",
    "PlayerPosition",
    "SimpleBlobDetector",
    "offset_from_centroid",
]
