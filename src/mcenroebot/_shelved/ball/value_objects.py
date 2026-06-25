"""Frozen pydantic value objects for the ball-observation subsystem."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mcenroebot.aim import Position3D

__all__ = [
    "BallObservation",
    "BallState",
    "PixelObservation",
    "StrikePrediction",
]


class BallObservation(BaseModel):
    """One ball sample, in robot frame.

    ``t`` is seconds (from the same clock that produced everything else —
    typically a ``Clock.now()`` value).

    The four scalar fields (``t``, ``x``, ``y``, ``z``) are intentionally
    flat rather than using a nested ``Position3D`` so that downstream code
    can convert an observation into a ``Position3D`` on its own schedule,
    without creating an intermediate copy.
    """

    model_config = ConfigDict(frozen=True)

    t: float
    x: float
    y: float
    z: float


class BallState(BaseModel):
    """Estimated ball position and velocity at a given time.

    Both ``position`` and ``velocity`` are ``Position3D`` instances in the
    robot frame. Velocity is in m/s.
    """

    model_config = ConfigDict(frozen=True)

    t: float
    position: Position3D
    velocity: Position3D  # m/s, robot frame


class StrikePrediction(BaseModel):
    """Predicted strike point and time, with a confidence score in [0, 1].

    ``confidence`` is a dimensionless probability-like score where 0.0
    indicates no confidence and 1.0 indicates maximum confidence. Values
    outside [0, 1] are rejected by pydantic.
    """

    model_config = ConfigDict(frozen=True)

    impact_point: Position3D
    impact_time: float
    confidence: float = Field(ge=0.0, le=1.0)


class PixelObservation(BaseModel):
    """One ball sample in image coordinates, fed into a ``DepthEstimator``.

    ``u_px`` and ``v_px`` are the pixel column and row of the ball centre.
    ``radius_px`` is the apparent ball radius in pixels — this must be
    strictly positive; a radius of zero or less is physically meaningless.
    """

    model_config = ConfigDict(frozen=True)

    t: float
    u_px: float
    v_px: float
    radius_px: float  # apparent ball radius in pixels

    @field_validator("radius_px")
    @classmethod
    def _radius_must_be_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError(f"radius_px must be strictly positive, got {value!r}")
        return value
