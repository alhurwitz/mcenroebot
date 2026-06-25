"""Tests for VisionPlacementStrategy — aim the open side away from the player."""

from __future__ import annotations

import random

import numpy as np

from mcenroebot.drill import (
    DrillContext,
    FixedPatternStrategy,
    TableTarget,
    VisionPlacementStrategy,
)
from mcenroebot.player import MockPlayerDetector, PlayerPosition


def _ctx() -> DrillContext:
    return DrillContext(shot_index=0, rng=random.Random(0))


def _frame() -> np.ndarray:
    return np.zeros((10, 10), dtype=np.uint8)


def _target() -> TableTarget:
    return TableTarget(center_x_m=2.0, half_width_m=0.6)


def _fallback(y: float = 0.123) -> FixedPatternStrategy:
    return FixedPatternStrategy(pattern="static", target=_target(), static_y_m=y)


def _strategy(
    detector: MockPlayerDetector, min_confidence: float = 0.5
) -> VisionPlacementStrategy:
    return VisionPlacementStrategy(
        detector=detector,
        frame_source=_frame,
        target=_target(),
        fallback=_fallback(),
        min_confidence=min_confidence,
    )


class TestOpenSideSelection:
    def test_player_left_aims_right(self) -> None:
        det = MockPlayerDetector(PlayerPosition(side_offset_m=0.4, confidence=0.9))
        p = _strategy(det).next_target(_ctx())
        assert p.x == 2.0
        assert p.y == -0.6  # opposite side from the player

    def test_player_right_aims_left(self) -> None:
        det = MockPlayerDetector(PlayerPosition(side_offset_m=-0.4, confidence=0.9))
        p = _strategy(det).next_target(_ctx())
        assert p.y == 0.6

    def test_frame_source_is_consulted(self) -> None:
        det = MockPlayerDetector(PlayerPosition(side_offset_m=0.4, confidence=0.9))
        _strategy(det).next_target(_ctx())
        assert det.calls == 1


class TestFallback:
    def test_low_confidence_falls_back(self) -> None:
        det = MockPlayerDetector(PlayerPosition(side_offset_m=0.4, confidence=0.2))
        p = _strategy(det, min_confidence=0.5).next_target(_ctx())
        assert p.y == 0.123  # fallback static target

    def test_no_detection_falls_back(self) -> None:
        det = MockPlayerDetector(None)
        p = _strategy(det).next_target(_ctx())
        assert p.y == 0.123
