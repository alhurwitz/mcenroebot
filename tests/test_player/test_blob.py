"""Tests for SimpleBlobDetector and the pure offset_from_centroid helper."""

from __future__ import annotations

import numpy as np
import pytest

from mcenroebot.player import MockPlayerDetector, PlayerPosition, SimpleBlobDetector
from mcenroebot.player.blob import offset_from_centroid


class TestOffsetFromCentroid:
    def test_center_is_zero(self) -> None:
        assert offset_from_centroid(100.0, frame_width=200, half_width_m=0.6) == pytest.approx(0.0)

    def test_image_right_is_negative_y(self) -> None:
        # cx past center (image right) -> player to robot -Y -> negative offset.
        assert offset_from_centroid(200.0, frame_width=200, half_width_m=0.6) == pytest.approx(-0.6)

    def test_image_left_is_positive_y(self) -> None:
        assert offset_from_centroid(0.0, frame_width=200, half_width_m=0.6) == pytest.approx(0.6)


def _frame_with_square(x0: int, x1: int, width: int = 200, height: int = 100) -> np.ndarray:
    frame = np.zeros((height, width), dtype=np.uint8)
    frame[20:80, x0:x1] = 255
    return frame


class TestSimpleBlobDetector:
    def test_blank_frame_returns_none(self) -> None:
        det = SimpleBlobDetector(half_width_m=0.6)
        assert det.detect(np.zeros((100, 200), dtype=np.uint8)) is None

    def test_blob_on_left_gives_positive_offset(self) -> None:
        det = SimpleBlobDetector(half_width_m=0.6)
        pos = det.detect(_frame_with_square(10, 60))  # left of center (cx ~35)
        assert pos is not None
        assert pos.side_offset_m > 0
        assert 0.0 < pos.confidence <= 1.0

    def test_blob_on_right_gives_negative_offset(self) -> None:
        det = SimpleBlobDetector(half_width_m=0.6)
        pos = det.detect(_frame_with_square(140, 190))  # right of center
        assert pos is not None
        assert pos.side_offset_m < 0

    def test_accepts_3_channel_frame(self) -> None:
        det = SimpleBlobDetector(half_width_m=0.6)
        gray = _frame_with_square(140, 190)
        bgr = np.stack([gray, gray, gray], axis=-1)
        pos = det.detect(bgr)
        assert pos is not None
        assert pos.side_offset_m < 0

    def test_tiny_blob_below_min_area_returns_none(self) -> None:
        det = SimpleBlobDetector(half_width_m=0.6, min_area_frac=0.5)
        pos = det.detect(_frame_with_square(95, 100))  # small
        assert pos is None


class TestMockPlayerDetector:
    def test_returns_configured_position(self) -> None:
        pos = PlayerPosition(side_offset_m=0.2, confidence=0.9)
        det = MockPlayerDetector(position=pos)
        assert det.detect(np.zeros((10, 10), dtype=np.uint8)) is pos

    def test_returns_none_when_configured(self) -> None:
        det = MockPlayerDetector(position=None)
        assert det.detect(np.zeros((10, 10), dtype=np.uint8)) is None
