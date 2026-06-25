"""Trajectory predictor -- fit incoming ball observations to a 3D ballistic model.

This package maintains a rolling buffer of ``BallObservation`` samples and
fits a weighted least-squares ballistic trajectory to them.  The fitted model
predicts where and when the ball will cross a user-specified vertical strike
plane (``x = strike_plane_x``).

Layout
------
    trajectory.py  -- ``TrajectoryPredictor`` class.
    __main__.py    -- entry point for ``python -m mcenroebot._shelved.predictor``.

Physical model
--------------
The ballistic model has constant velocity in X and Y, and parabolic (gravity-
braked) motion in Z::

    x(t) = x0 + vx * dt
    y(t) = y0 + vy * dt
    z(t) = z0 + vz * dt - 0.5 * g * dt**2

where ``dt = t - t_ref`` and ``t_ref`` is the timestamp of the most-recent
observation.  Using ``t_ref`` as the time reference keeps the regression
matrices well-conditioned even when absolute timestamps are large.

Fitting strategy
----------------
X, Y, and Z are fit independently as three two-parameter weighted linear
regressions.  Gravity enters the Z regression as a known offset on the RHS,
keeping all six unknowns linear.  Each observation ``i`` receives weight::

    w_i = 0.5 ** ((t_ref - t_i) / weight_halflife_s)

so the most-recent sample has weight 1 and older samples decay exponentially.

Confidence model
----------------
``StrikePrediction.confidence`` combines:

* **n_factor** = ``min(n / buffer_size, 1.0)``   -- saturates at full buffer.
* **residual_factor** = ``exp(-residual_norm / 0.01)``  -- a 1 cm (0.01 m)
  weighted-RMS position residual reduces the residual factor to exp(-1) ~ 0.37.
  The ``characteristic_residual_m = 0.01`` constant is documented on
  ``TrajectoryPredictor``.

``confidence = clip(n_factor * residual_factor, 0.0, 1.0)``
"""

from __future__ import annotations

from mcenroebot._shelved.predictor.trajectory import TrajectoryPredictor, _demo

__all__ = ["TrajectoryPredictor", "_demo"]
