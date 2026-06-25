"""Frozen value objects for the player-detection subsystem."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

__all__ = ["PlayerPosition"]


class PlayerPosition(BaseModel):
    """Where the human is, relative to court center, along their baseline.

    Attributes
    ----------
    side_offset_m : float
        Lateral position. Positive = robot +Y (left of center, viewed from
        above); negative = right. Magnitude is meters from center.
    confidence : float
        Detector confidence in ``[0, 1]``. The placement strategy falls back
        to a fixed pattern below its configured threshold.
    """

    model_config = ConfigDict(frozen=True)

    side_offset_m: float
    confidence: float

    @field_validator("confidence")
    @classmethod
    def _check_confidence(cls, value: float) -> float:
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"confidence={value} out of range [0, 1]")
        return value
