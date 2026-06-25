"""TrajectoryPredictor -- weighted ballistic fit from a rolling observation buffer."""

from __future__ import annotations

import math
from collections import deque

import numpy as np

from mcenroebot._shelved.ball import BallObservation, BallState, StrikePrediction
from mcenroebot.aim import Position3D

__all__ = ["TrajectoryPredictor"]

# Weighted-RMS residual (metres) that sets the residual factor scale.
# At residual_norm == characteristic_residual_m the factor is exp(-1) ≈ 0.37.
# A 1 cm fit error is reasonable for table-tennis-scale geometry.
_CHARACTERISTIC_RESIDUAL_M: float = 0.01

# Minimum absolute vx (m/s) below which the ball is treated as not moving
# toward any strike plane.  Avoids astronomically large dt from near-zero vx.
_VX_MIN_MS: float = 1e-6


class TrajectoryPredictor:
    """Maintains a rolling buffer of BallObservations and fits a 3D ballistic
    trajectory: constant velocity in X and Y; gravity (-g) on Z.

    Fitting uses weighted least squares.  Observations more recent in time get
    higher weight via an exponential-decay schedule with the given half-life.

    ``predict_strike(strike_plane_x)`` returns the predicted (y, z, t) at which
    the ball will cross the vertical plane ``x = strike_plane_x``, or ``None`` if:

    * fewer than ``min_observations`` samples have been recorded, OR
    * the ball is moving away from the strike plane (vx is the wrong sign).

    Physical model (dt = t - t_ref, t_ref = timestamp of most-recent obs)::

        x(t) = x0 + vx * dt
        y(t) = y0 + vy * dt
        z(t) = z0 + vz * dt - 0.5 * g * dt**2

    The six free parameters ``(x0, y0, z0, vx, vy, vz)`` are fit per-axis via
    two-parameter weighted linear regression.  Gravity is a *known* constant
    and is moved to the RHS of the Z regression so all unknowns remain linear.

    Confidence model::

        n_factor        = min(n / buffer_size, 1.0)
        residual_norm   = sqrt(weighted_sum_sq_residuals / total_weight)
        residual_factor = exp(-residual_norm / characteristic_residual_m)
        confidence      = clip(n_factor * residual_factor, 0.0, 1.0)

    ``characteristic_residual_m = 0.01`` m (1 cm) -- a 1 cm weighted-RMS
    residual reduces the residual factor to ``exp(-1) ~ 0.37``; larger errors
    push confidence toward zero faster.

    Args:
        buffer_size: Max number of observations retained (FIFO). Default 16.
        gravity_mps2: Magnitude of gravity, applied as -g on the Z axis.
                      Default 9.81.
        weight_halflife_s: Half-life of the exponential weight decay applied
                           to the time-delta between the most-recent
                           observation and each older one. Default 0.1 s.
        min_observations: Minimum number of buffered observations required
                          before fit / predict will produce a result.
                          Default 3.
    """

    def __init__(
        self,
        buffer_size: int = 16,
        gravity_mps2: float = 9.81,
        weight_halflife_s: float = 0.1,
        min_observations: int = 3,
    ) -> None:
        if buffer_size < 1:
            raise ValueError(f"buffer_size must be >= 1, got {buffer_size!r}")
        if gravity_mps2 <= 0.0:
            raise ValueError(f"gravity_mps2 must be positive, got {gravity_mps2!r}")
        if weight_halflife_s <= 0.0:
            raise ValueError(f"weight_halflife_s must be positive, got {weight_halflife_s!r}")
        if min_observations < 2:
            raise ValueError(f"min_observations must be >= 2, got {min_observations!r}")

        self._buffer_size = buffer_size
        self._gravity = gravity_mps2
        self._halflife = weight_halflife_s
        self._min_obs = min_observations
        self._buffer: deque[BallObservation] = deque(maxlen=buffer_size)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def add(self, obs: BallObservation) -> None:
        """Append an observation to the rolling buffer.

        The oldest observation is dropped when the buffer is at capacity.
        """
        self._buffer.append(obs)

    def current_state(self) -> BallState | None:
        """Best-estimate (position, velocity) at the time of the most recent
        observation.

        Returns ``None`` if fewer than ``min_observations`` are present.
        """
        fit = self._fit()
        if fit is None:
            return None
        x0, y0, z0, vx, vy, vz, t_ref, _conf = fit
        return BallState(
            t=t_ref,
            position=Position3D(x=x0, y=y0, z=z0),
            velocity=Position3D(x=vx, y=vy, z=vz),
        )

    def predict_strike(self, strike_plane_x: float) -> StrikePrediction | None:
        """Solve for the time and (y, z) at which the fitted trajectory crosses
        ``x = strike_plane_x``, integrating gravity on Z.

        Returns ``None`` if:

        * not enough observations, OR
        * the ball's predicted x-velocity does not move it toward the plane
          (moving away or stationary).
        * ``Δt < 0`` (ball has already passed the plane in the fitted model).

        A ball that is *exactly* at the strike plane (Δt == 0) counts as
        "impact is now" and returns a valid prediction.
        """
        fit = self._fit()
        if fit is None:
            return None
        x0, y0, z0, vx, vy, vz, t_ref, conf = fit

        # Solve x0 + vx * Δt = strike_plane_x  =>  Δt = (strike_plane_x - x0) / vx
        dx = strike_plane_x - x0

        if abs(vx) < _VX_MIN_MS:
            # No meaningful x-motion — treat as stationary; will never reach the plane.
            return None

        dt = dx / vx

        if dt < 0.0:
            # Ball is moving away from the plane (already past it, or wrong direction).
            return None

        y_impact = y0 + vy * dt
        z_impact = z0 + vz * dt - 0.5 * self._gravity * dt * dt
        impact_time = t_ref + dt

        return StrikePrediction(
            impact_point=Position3D(x=strike_plane_x, y=y_impact, z=z_impact),
            impact_time=impact_time,
            confidence=conf,
        )

    def __len__(self) -> int:
        """Return the number of observations currently in the buffer."""
        return len(self._buffer)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fit(self) -> tuple[float, float, float, float, float, float, float, float] | None:
        """Fit the ballistic model to the buffered observations.

        Returns ``(x0, y0, z0, vx, vy, vz, t_ref, confidence)`` or ``None``
        if the buffer is too small.

        Each axis is fit independently as a 2-parameter weighted linear
        regression (intercept + slope).  Z gets the gravity quadratic term
        moved to the RHS so the unknowns stay linear.
        """
        n = len(self._buffer)
        if n < self._min_obs:
            return None

        obs_list = list(self._buffer)
        t_ref = obs_list[-1].t  # most-recent timestamp

        # Build arrays
        times = np.array([o.t for o in obs_list], dtype=float)
        xs = np.array([o.x for o in obs_list], dtype=float)
        ys = np.array([o.y for o in obs_list], dtype=float)
        zs = np.array([o.z for o in obs_list], dtype=float)

        dt_arr = times - t_ref  # dt_i = t_i - t_ref  (<= 0 for past obs)

        # Weights: w_i = 0.5 ** ((t_ref - t_i) / halflife) = 0.5 ** (-dt / halflife)
        # Since dt <= 0, -dt >= 0, so weights in (0, 1].  Most recent gets 1.
        weights = np.power(0.5, (-dt_arr) / self._halflife)
        sqrt_w = np.sqrt(weights)

        # Design matrix for a 2-parameter linear model: [1, dt]
        # Shape (n, 2): column 0 = 1 (intercept), column 1 = dt (slope)
        A = np.column_stack([np.ones(n), dt_arr])

        # Scale rows by sqrt(weight) to perform weighted least squares via
        # unweighted lstsq on the scaled system.
        Aw = A * sqrt_w[:, np.newaxis]

        # ------ Fit X ------
        bx = xs * sqrt_w
        sol_x, _, _, _ = np.linalg.lstsq(Aw, bx, rcond=None)
        x0, vx = float(sol_x[0]), float(sol_x[1])

        # ------ Fit Y ------
        by = ys * sqrt_w
        sol_y, _, _, _ = np.linalg.lstsq(Aw, by, rcond=None)
        y0, vy = float(sol_y[0]), float(sol_y[1])

        # ------ Fit Z ------
        # z(dt) = z0 + vz*dt - 0.5*g*dt**2
        # Move gravity term to RHS: z + 0.5*g*dt**2 = z0 + vz*dt
        gravity_offset = 0.5 * self._gravity * dt_arr * dt_arr
        bz = (zs + gravity_offset) * sqrt_w
        sol_z, _, _, _ = np.linalg.lstsq(Aw, bz, rcond=None)
        z0, vz = float(sol_z[0]), float(sol_z[1])

        # ------ Confidence ------
        conf = self._confidence(x0, y0, z0, vx, vy, vz, dt_arr, xs, ys, zs, weights, n)

        return x0, y0, z0, vx, vy, vz, t_ref, conf

    def _confidence(
        self,
        x0: float,
        y0: float,
        z0: float,
        vx: float,
        vy: float,
        vz: float,
        dt_arr: np.ndarray,
        xs: np.ndarray,
        ys: np.ndarray,
        zs: np.ndarray,
        weights: np.ndarray,
        n: int,
    ) -> float:
        """Compute a confidence score in [0, 1].

        ``n_factor = min(n / buffer_size, 1.0)``  — saturates at full buffer.
        ``residual_norm = sqrt(Σ w_i * r_i² / Σ w_i)``  — weighted RMS residual
        across all three axes combined.
        ``residual_factor = exp(-residual_norm / characteristic_residual_m)``
        ``confidence = clip(n_factor * residual_factor, 0.0, 1.0)``
        """
        n_factor = min(n / self._buffer_size, 1.0)

        # Predicted values under the fit
        x_pred = x0 + vx * dt_arr
        y_pred = y0 + vy * dt_arr
        z_pred = z0 + vz * dt_arr - 0.5 * self._gravity * dt_arr * dt_arr

        # Per-observation sum-of-squared residuals across X, Y, Z
        sq_res = (xs - x_pred) ** 2 + (ys - y_pred) ** 2 + (zs - z_pred) ** 2
        total_weight = float(np.sum(weights))
        weighted_sq = float(np.dot(weights, sq_res))

        residual_norm = math.sqrt(weighted_sq / total_weight) if total_weight > 0.0 else 0.0
        residual_factor = math.exp(-residual_norm / _CHARACTERISTIC_RESIDUAL_M)

        return float(np.clip(n_factor * residual_factor, 0.0, 1.0))


def _demo() -> None:
    """Print sanity-check results for a simple synthetic trajectory.

    Run with ``python -m mcenroebot._shelved.predictor``.
    """
    import textwrap

    from mcenroebot._shelved.ball import BallObservation

    predictor = TrajectoryPredictor(buffer_size=16)

    # Synthetic trajectory: x advances at 3 m/s, y at 0.5 m/s, z at -1 m/s
    # starting from (0.5, 0.1, 1.0) at t=0.
    x0, y0, z0 = 0.5, 0.1, 1.0
    vx, vy, vz = 3.0, 0.5, -1.0
    g = 9.81
    times = [i * 0.02 for i in range(10)]
    for t in times:
        obs = BallObservation(
            t=t,
            x=x0 + vx * t,
            y=y0 + vy * t,
            z=z0 + vz * t - 0.5 * g * t * t,
        )
        predictor.add(obs)

    print(
        textwrap.dedent(f"""\
        TrajectoryPredictor demo
        ========================
        True trajectory: x0={x0}, y0={y0}, z0={z0}  vx={vx}, vy={vy}, vz={vz}  g={g}
        Buffer occupancy: {len(predictor)} / 16 observations
        """)
    )

    state = predictor.current_state()
    if state is None:
        print("  current_state() -> None  (too few observations)")
    else:
        p = state.position
        v = state.velocity
        print(f"  current_state() at t={state.t:.3f} s")
        print(f"    position = ({p.x:+.4f}, {p.y:+.4f}, {p.z:+.4f}) m")
        print(f"    velocity = ({v.x:+.4f}, {v.y:+.4f}, {v.z:+.4f}) m/s")
        print()

    for plane_x in (1.0, 1.5, 2.0):
        pred = predictor.predict_strike(strike_plane_x=plane_x)
        if pred is None:
            print(f"  predict_strike(x={plane_x:.1f}) -> None")
        else:
            ip = pred.impact_point
            print(
                f"  predict_strike(x={plane_x:.1f}) -> "
                f"y={ip.y:+.4f}  z={ip.z:+.4f}  t={pred.impact_time:.4f} s  "
                f"conf={pred.confidence:.3f}"
            )
