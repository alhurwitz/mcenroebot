"""Top-level rally coordinator — wires predictor → aim → servo driver → swing."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from mcenroebot.aim import AimController
from mcenroebot.ball import BallObservation
from mcenroebot.clock import Clock
from mcenroebot.drivers import ServoDriver
from mcenroebot.predictor import TrajectoryPredictor
from mcenroebot.swing import SwingController, SwingProfile

__all__ = ["RallyCoordinator"]

_log = logging.getLogger(__name__)

# Default swing profile: 50 ms ramp-up / 50 ms hold / 50 ms ramp-down, peak=0.5.
_DEFAULT_SWING_PROFILE = SwingProfile(
    ramp_up_ms=50.0,
    hold_ms=50.0,
    ramp_down_ms=50.0,
    peak_throttle=0.5,
)


class RallyCoordinator:
    """Top-level rally controller. Wires:

        observation stream → TrajectoryPredictor → AimController → ServoDriver
                                                 → SwingController

    On each observation:
      1. Push the obs into the predictor.
      2. Predict the strike point (y, z, t) at x = strike_plane_x.
      3. If aim is reachable, write yaw + pitch to the servo driver.
      4. Decide whether to fire: when current time is within ``swing_latency_s``
         of the predicted impact_time, fire ONCE per arc.

    The "one fire per arc" rule is enforced via ``_last_fire_time`` — after a
    successful ``swing.fire()``, the coordinator refuses to fire again until at
    least ``rearm_min_interval_s`` seconds have elapsed.

    Swing arming (lazy):
        The coordinator calls ``swing.arm()`` lazily on the first ``step()`` call
        that produces a valid strike prediction.  This keeps construction simple and
        avoids arming the motor before any ball has been seen.  The coordinator
        NEVER disarms the swing — lifecycle management (disarm/re-arm between
        rallies) is the caller's responsibility.  If you need guaranteed cleanup,
        wrap the coordinator in an ``async with`` block on the ``SwingController``.

    Args:
        aim:                AimController for yaw/pitch computation.
        predictor:          TrajectoryPredictor to fit the trajectory.
        servo_driver:       ServoDriver to push servo commands to.
        swing:              SwingController for the actual paddle strike.
        clock:              Clock for ``now()`` (used to decide when to fire).
        strike_plane_x:     x-coordinate (m) of the strike plane. Default 0.0.
        swing_latency_s:    How long the swing takes from ``fire()`` to ball
                            contact. The coordinator fires this many seconds
                            BEFORE the predicted impact_time. Default 0.05.
        servo_yaw_channel:  PCA9685 channel for the yaw servo. Default 0.
        servo_pitch_channel:PCA9685 channel for the pitch servo. Default 1.
        swing_profile:      The SwingProfile to fire each strike with.
                            Default: ramp_up=50 ms / hold=50 ms / ramp_down=50 ms /
                            peak=0.5.
        rearm_min_interval_s:
                            How long the coordinator waits after a strike before it
                            will fire again. Default 0.5 s.
    """

    def __init__(
        self,
        aim: AimController,
        predictor: TrajectoryPredictor,
        servo_driver: ServoDriver,
        swing: SwingController,
        clock: Clock,
        strike_plane_x: float = 0.0,
        swing_latency_s: float = 0.05,
        servo_yaw_channel: int = 0,
        servo_pitch_channel: int = 1,
        swing_profile: SwingProfile | None = None,
        rearm_min_interval_s: float = 0.5,
    ) -> None:
        self._aim = aim
        self._predictor = predictor
        self._servo_driver = servo_driver
        self._swing = swing
        self._clock = clock
        self._strike_plane_x = strike_plane_x
        self._swing_latency_s = swing_latency_s
        self._servo_yaw_channel = servo_yaw_channel
        self._servo_pitch_channel = servo_pitch_channel
        self._swing_profile: SwingProfile = swing_profile or _DEFAULT_SWING_PROFILE
        self._rearm_min_interval_s = rearm_min_interval_s

        self._last_fire_time: float | None = None
        self._armed: bool = False

    async def step(self, obs: BallObservation) -> None:
        """Push one observation through the full pipeline.

        Steps:
          1. Add ``obs`` to the predictor.
          2. Query ``predict_strike`` — if None (too few obs or ball moving away),
             return early without touching servos or swing.
          3. Call ``aim.compute(impact_point)`` — if None (out of reach), log and
             return without servo writes or firing.
          4. Write yaw to ``servo_yaw_channel`` and pitch to ``servo_pitch_channel``.
          5. Decide whether to fire (timing + rearm guard).  If so, arm lazily then
             call ``swing.fire(swing_profile)``.
        """
        # Step 1: feed the observation to the predictor.
        self._predictor.add(obs)

        # Step 2: attempt a strike prediction.
        prediction = self._predictor.predict_strike(self._strike_plane_x)
        if prediction is None:
            return  # not enough observations, or ball not approaching

        # Step 3: compute servo angles.
        angles = self._aim.compute(prediction.impact_point)
        if angles is None:
            _log.debug("Impact point %s is out of reach — skipping", prediction.impact_point)
            return

        # Step 4: write servo angles.
        self._servo_driver.write_angle(self._servo_yaw_channel, angles.yaw_deg)
        self._servo_driver.write_angle(self._servo_pitch_channel, angles.pitch_deg)

        # Step 5: decide whether to fire.
        now = self._clock.now()
        fire_time = prediction.impact_time - self._swing_latency_s

        if now < fire_time:
            return  # still too early — don't fire yet

        # Enforce one-fire-per-arc via rearm guard.
        if self._last_fire_time is not None:
            elapsed_since_fire = now - self._last_fire_time
            if elapsed_since_fire < self._rearm_min_interval_s:
                return  # rearm interval not yet elapsed

        # Lazy arm: arm the swing on the first fire attempt.
        if not self._armed:
            self._swing.arm()
            self._armed = True

        self._last_fire_time = now
        await self._swing.fire(self._swing_profile)

    async def run(self, stream: AsyncIterator[BallObservation]) -> None:
        """Consume an async iterator of observations, calling ``step`` for each.

        Returns when the stream is exhausted.  Any exception raised by ``step``
        (including hardware faults from the swing controller) propagates
        immediately — the caller is responsible for deciding whether to restart
        or abort the rally loop.
        """
        async for obs in stream:
            await self.step(obs)
