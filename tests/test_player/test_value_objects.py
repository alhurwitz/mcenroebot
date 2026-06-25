"""Tests for PlayerPosition value object."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcenroebot.player import PlayerPosition


class TestPlayerPosition:
    def test_valid(self) -> None:
        p = PlayerPosition(side_offset_m=0.3, confidence=0.8)
        assert p.side_offset_m == 0.3
        assert p.confidence == 0.8

    @pytest.mark.parametrize("conf", [-0.1, 1.1])
    def test_confidence_out_of_range_raises(self, conf: float) -> None:
        with pytest.raises(ValidationError, match=r"confidence"):
            PlayerPosition(side_offset_m=0.0, confidence=conf)

    def test_confidence_boundaries(self) -> None:
        PlayerPosition(side_offset_m=0.0, confidence=0.0)
        PlayerPosition(side_offset_m=0.0, confidence=1.0)

    def test_is_frozen(self) -> None:
        p = PlayerPosition(side_offset_m=0.0, confidence=0.5)
        with pytest.raises(ValidationError):
            p.side_offset_m = 1.0  # type: ignore[misc]
