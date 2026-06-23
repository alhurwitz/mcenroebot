"""Pure rate->throttle mapping for the continuous-rotation escapement servo.

Kept separate from the hardware driver so it is fully unit-testable off-Pi.
The ``throttle_per_bpm`` factor is calibrated by ``scripts/calibrate_feeder.py``.
"""

from __future__ import annotations

__all__ = ["throttle_for_rate"]


def throttle_for_rate(balls_per_min: float, throttle_per_bpm: float) -> float:
    """Map a desired feed rate to a continuous-servo throttle in [-1, 1].

    Linear v1 model: ``throttle = balls_per_min * throttle_per_bpm``, clamped
    to the continuous-servo range. Feed rate is non-negative, so the result is
    in ``[0, 1]`` for a positive factor.

    Raises
    ------
    ValueError
        If ``balls_per_min`` is negative.
    """
    if balls_per_min < 0.0:
        raise ValueError(f"balls_per_min={balls_per_min} must be >= 0")
    throttle = balls_per_min * throttle_per_bpm
    return min(1.0, max(-1.0, throttle))
