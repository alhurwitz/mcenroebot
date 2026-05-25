"""Entry point for ``python -m mcenroebot.coordinator``."""

from __future__ import annotations

import asyncio


def _demo() -> None:
    """Run a synthetic rally against mock drivers and print results.

    Synthesises a ballistic trajectory aimed at the strike plane, pushes
    observations through the full pipeline, and prints a summary of servo
    writes and swing fires.
    """
    from mcenroebot.aim import AimController
    from mcenroebot.ball import BallObservation
    from mcenroebot.clock import FakeClock
    from mcenroebot.coordinator.rally import RallyCoordinator
    from mcenroebot.drivers import MockBLDCDriver, MockServoDriver
    from mcenroebot.predictor import TrajectoryPredictor
    from mcenroebot.swing import SwingController, SwingProfile

    # Build components.
    clock = FakeClock(start=0.0)
    servo = MockServoDriver()
    bldc = MockBLDCDriver()
    swing = SwingController(driver=bldc, clock=clock)
    profile = SwingProfile(ramp_up_ms=50.0, hold_ms=50.0, ramp_down_ms=50.0, peak_throttle=0.5)

    # Synthetic ballistic trajectory aimed at strike_plane_x=0.1.
    # Ball starts at x=0.5, vx=-4.0 m/s, vz=0.4905 → crosses x=0.1 at t=0.1 s
    # with z≈0 (gravity cancelled by vz) and magnitude≈0.1 m (reachable).
    x0, y0, z0 = 0.5, 0.0, 0.0
    vx, vy, vz = -4.0, 0.0, 0.4905
    g = 9.81
    n_obs = 8

    observations = [
        BallObservation(
            t=i * 0.01,
            x=x0 + vx * i * 0.01,
            y=y0 + vy * i * 0.01,
            z=z0 + vz * i * 0.01 - 0.5 * g * (i * 0.01) ** 2,
        )
        for i in range(n_obs)
    ]

    coordinator = RallyCoordinator(
        aim=AimController(),
        predictor=TrajectoryPredictor(),
        servo_driver=servo,
        swing=swing,
        clock=clock,
        strike_plane_x=0.1,
        swing_latency_s=0.05,
        swing_profile=profile,
    )

    async def _run() -> None:
        for obs in observations:
            clock.advance(0.01)
            await coordinator.step(obs)

    asyncio.run(_run())

    print("=== RallyCoordinator demo ===")
    print(f"  Observations pushed : {n_obs}")
    print(f"  Servo writes        : {len(servo.history)}")
    if servo.history:
        yaw_writes = [a for ch, a in servo.history if ch == 0]
        pitch_writes = [a for ch, a in servo.history if ch == 1]
        print(f"    yaw writes (ch 0)  : {[f'{a:.1f}' for a in yaw_writes]}")
        print(f"    pitch writes (ch 1): {[f'{a:.1f}' for a in pitch_writes]}")
    print(f"  BLDC throttle ticks : {len(bldc.throttle_history)}")
    if bldc.throttle_history:
        peak = max(bldc.throttle_history)
        print(f"    peak throttle : {peak:.3f}")
        print(f"    final value   : {bldc.throttle_history[-1]:.3f}")
    print()


if __name__ == "__main__":
    _demo()
