"""Frozen pydantic value object describing one open-loop swing envelope."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["SwingProfile"]


class SwingProfile(BaseModel):
    """Open-loop throttle envelope for one swing.

    The envelope has three phases:
      - ramp_up_ms:   linear ramp 0 -> peak_throttle.
      - hold_ms:      sustained at peak_throttle (may be 0 for triangle profile).
      - ramp_down_ms: linear ramp peak_throttle -> 0.

    Total swing duration is the sum of the three phases.
    """

    model_config = ConfigDict(frozen=True)

    ramp_up_ms: float = Field(gt=0)
    hold_ms: float = Field(ge=0)
    ramp_down_ms: float = Field(gt=0)
    peak_throttle: float = Field(gt=0.0, le=1.0)

    @property
    def total_ms(self) -> float:
        """Sum of all three phase durations, in milliseconds."""
        return self.ramp_up_ms + self.hold_ms + self.ramp_down_ms
