"""SimpleBlobDetector — locate the player as the largest bright contour.

A deliberately simple, forgiving detector for the slow placement loop: it
thresholds the frame, takes the largest contour as the player, and maps its
horizontal centroid to a lateral offset. Good enough for "which side is the
player on"; not a precise tracker. Swap in something better behind the
``PlayerDetector`` Protocol when needed.
"""

from __future__ import annotations

from typing import Any

import cv2
from numpy.typing import NDArray

from mcenroebot.player.value_objects import PlayerPosition

__all__ = ["SimpleBlobDetector", "offset_from_centroid"]


def offset_from_centroid(cx: float, frame_width: int, half_width_m: float) -> float:
    """Map a centroid pixel x to a lateral offset in meters.

    Image-right (``cx`` past center) maps to robot -Y (negative offset);
    image-left maps to +Y. Assumes a non-mirrored, forward-facing camera.
    """
    center = frame_width / 2.0
    normalized = (cx - center) / center  # [-1, 1], +1 = image right edge
    return -normalized * half_width_m


class SimpleBlobDetector:
    """Threshold + largest-contour player detector.

    Args:
        half_width_m: lateral half-extent the image edges map to (meters).
        threshold: grayscale threshold for foreground (0..255).
        min_area_frac: ignore contours smaller than this fraction of the frame.
        full_area_frac: contour area fraction treated as confidence 1.0.
    """

    def __init__(
        self,
        half_width_m: float,
        threshold: int = 127,
        min_area_frac: float = 0.001,
        full_area_frac: float = 0.1,
    ) -> None:
        self.half_width_m = half_width_m
        self.threshold = threshold
        self.min_area_frac = min_area_frac
        self.full_area_frac = full_area_frac

    def detect(self, frame: NDArray[Any]) -> PlayerPosition | None:
        """Return the player's lateral position, or None if no blob is found."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        _, mask = cv2.threshold(gray, self.threshold, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(largest))
        frame_area = float(gray.shape[0] * gray.shape[1])
        if area < self.min_area_frac * frame_area:
            return None

        moments = cv2.moments(largest)
        if moments["m00"] == 0.0:  # pragma: no cover - defensive; area>=min_area implies m00>0
            return None
        cx = moments["m10"] / moments["m00"]

        offset = offset_from_centroid(cx, gray.shape[1], self.half_width_m)
        confidence = min(1.0, area / (frame_area * self.full_area_frac))
        return PlayerPosition(side_offset_m=offset, confidence=confidence)
