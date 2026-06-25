"""Frozen value objects for the drill subsystem."""

from __future__ import annotations

import random

from pydantic import BaseModel, ConfigDict, field_validator

from mcenroebot.aim import Position3D
from mcenroebot.launch import ShotSpec

__all__ = ["DrillContext", "Shot", "TableTarget"]


class TableTarget(BaseModel):
    """The court target region an aim pattern places balls within.

    Targets are points in the robot frame (see the aim coordinate convention):
    ``x`` forward toward the player, ``y`` left, ``z`` up.

    Attributes
    ----------
    center_x_m : float
        Forward depth of the target region center. Must be > 0.
    half_depth_m : float
        Half the near<->far depth span (x varies in center_x ± half_depth).
        0 for purely lateral patterns. Must be >= 0.
    half_width_m : float
        Half the left<->right span (y varies in ± half_width). Must be > 0.
    z_m : float
        Target height. Default 0.
    """

    model_config = ConfigDict(frozen=True)

    center_x_m: float
    half_width_m: float
    half_depth_m: float = 0.0
    z_m: float = 0.0

    @field_validator("center_x_m", "half_width_m")
    @classmethod
    def _check_positive(cls, value: float) -> float:
        if value <= 0.0:
            raise ValueError(f"{value} must be > 0")
        return value

    @field_validator("half_depth_m")
    @classmethod
    def _check_non_negative(cls, value: float) -> float:
        if value < 0.0:
            raise ValueError(f"half_depth_m={value} must be >= 0")
        return value


class DrillContext(BaseModel):
    """Per-shot context handed to an ``AimStrategy``.

    Carries the shot index and the drill's single seeded RNG, so all
    randomness flows from one seed and a fixed seed yields an identical
    Shot sequence. Frozen binding; the ``rng`` object itself is mutable
    (it advances as the strategy draws from it).
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    shot_index: int
    rng: random.Random


class Shot(BaseModel):
    """One scheduled shot: what to launch, where to aim, and when next."""

    model_config = ConfigDict(frozen=True)

    spec: ShotSpec
    target: Position3D
    delay_s: float

    @field_validator("delay_s")
    @classmethod
    def _check_delay(cls, value: float) -> float:
        if value < 0.0:
            raise ValueError(f"delay_s={value} must be >= 0")
        return value
