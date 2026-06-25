"""Integration tests for RallyCoordinator.

These tests exercise the full pipeline — TrajectoryPredictor → AimController →
MockServoDriver and SwingController(MockBLDCDriver) — using FakeClock for
deterministic timing.

Synthetic trajectory helper
---------------------------
All tests that need a trajectory use ``_make_observations()``, which generates
``BallObservation`` samples from a parameterised ballistic model:

    x(t) = x0 + vx*t
    y(t) = y0 + vy*t
    z(t) = z0 + vz*t - 0.5*g*t^2

The default setup uses ``strike_plane_x=0.1`` (not 0.0) to avoid the degenerate
geometry where x=0 causes ``horizontal_distance=|y|→0`` and undefined servo
angles.  The canonical "centered" trajectory is:

    x0=0.5, vx=-4.0, y0=0.0, z0=0.0, vz=0.4905
    → impact at x=0.1, y≈0, z≈0 at t≈0.1s from t_start.

This gives yaw≈90°, pitch≈90° and magnitude≈0.1m (well within arm_length=0.2m).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from mcenroebot.aim import AimController
from mcenroebot._shelved.ball import BallObservation
from mcenroebot.clock import FakeClock
from mcenroebot._shelved.rally.rally import RallyCoordinator
from mcenroebot.drivers import MockBLDCDriver, MockServoDriver
from mcenroebot._shelved.predictor import TrajectoryPredictor
from mcenroebot._shelved.swing import SwingController, SwingProfile

# ---------------------------------------------------------------------------
# Constants / defaults shared across tests
# ---------------------------------------------------------------------------

_G = 9.81
_STRIKE_PLANE = 0.1  # Use 0.1 m to avoid x=0 singularity in aim geometry
_SWING_LATENCY = 0.05  # seconds
_REARM_INTERVAL = 0.5  # seconds

# The "vz to cancel gravity at t=0.1 s" constant:
#   z_impact = z0 + vz*t - 0.5*g*t² = 0  with z0=0, t=0.1
#   → vz = 0.5*9.81*0.1 = 0.4905
_VZ_CANCEL_GRAVITY = 0.4905

# Default swing profile used in most tests.
_DEFAULT_PROFILE = SwingProfile(
    ramp_up_ms=50.0,
    hold_ms=50.0,
    ramp_down_ms=50.0,
    peak_throttle=0.5,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_observations(
    n: int = 8,
    x0: float = 0.50,
    y0: float = 0.0,
    z0: float = 0.0,
    vx: float = -4.0,
    vy: float = 0.0,
    vz: float = _VZ_CANCEL_GRAVITY,
    dt: float = 0.01,
    t_start: float = 0.0,
) -> list[BallObservation]:
    """Generate ``n`` BallObservation samples from a ballistic model.

    Default params: ball at x=0.50 m, moving at -4 m/s in x with vz=0.4905.
    Crosses strike_plane_x=0.1 at t≈0.1s with y≈0, z≈0 (yaw≈pitch≈90°).
    Magnitude at impact ≈ 0.1 m < arm_length=0.2 m (reachable).
    """
    obs = []
    for i in range(n):
        t_rel = i * dt
        t = t_start + t_rel
        obs.append(
            BallObservation(
                t=t,
                x=x0 + vx * t_rel,
                y=y0 + vy * t_rel,
                z=z0 + vz * t_rel - 0.5 * _G * t_rel * t_rel,
            )
        )
    return obs


def _make_coordinator(
    *,
    clock: FakeClock | None = None,
    servo: MockServoDriver | None = None,
    bldc: MockBLDCDriver | None = None,
    swing_profile: SwingProfile | None = None,
    servo_yaw_channel: int = 0,
    servo_pitch_channel: int = 1,
    strike_plane_x: float = _STRIKE_PLANE,
    swing_latency_s: float = _SWING_LATENCY,
    rearm_min_interval_s: float = _REARM_INTERVAL,
) -> tuple[RallyCoordinator, MockServoDriver, MockBLDCDriver, FakeClock]:
    """Build a RallyCoordinator wired to mock drivers."""
    if clock is None:
        clock = FakeClock(start=0.0)
    if servo is None:
        servo = MockServoDriver()
    if bldc is None:
        bldc = MockBLDCDriver()
    swing = SwingController(driver=bldc, clock=clock)
    coordinator = RallyCoordinator(
        aim=AimController(),
        predictor=TrajectoryPredictor(),
        servo_driver=servo,
        swing=swing,
        clock=clock,
        strike_plane_x=strike_plane_x,
        swing_latency_s=swing_latency_s,
        servo_yaw_channel=servo_yaw_channel,
        servo_pitch_channel=servo_pitch_channel,
        swing_profile=swing_profile or _DEFAULT_PROFILE,
        rearm_min_interval_s=rearm_min_interval_s,
    )
    return coordinator, servo, bldc, clock


# ---------------------------------------------------------------------------
# Test 1: Below min_observations — no servo writes, no swing
# ---------------------------------------------------------------------------


class TestBelowMinObservations:
    async def test_two_obs_does_not_write_servos_or_fire(self) -> None:
        coordinator, servo, bldc, _ = _make_coordinator()
        # Default min_observations=3; push only 2.
        observations = _make_observations(n=2)
        for obs in observations:
            await coordinator.step(obs)

        assert servo.history == [], "No servo writes expected before min_observations"
        assert bldc.throttle_history == [], "No swing expected before min_observations"

    async def test_one_obs_does_not_write_servos(self) -> None:
        coordinator, servo, bldc, _ = _make_coordinator()
        obs = _make_observations(n=1)[0]
        await coordinator.step(obs)
        assert servo.history == []
        assert bldc.throttle_history == []


# ---------------------------------------------------------------------------
# Test 2: Above min_observations writes servos with sensible angles
# ---------------------------------------------------------------------------


class TestAboveMinObservationsWritesServos:
    async def test_servo_writes_with_centered_trajectory(self) -> None:
        """Centered trajectory (y=0, z≈0 at impact) → yaw≈90°, pitch≈90°."""
        coordinator, servo, bldc, _ = _make_coordinator()
        # Default _make_observations: impact at x=0.1, y=0, z≈0 → both ≈ 90°.
        observations = _make_observations(n=5)
        for obs in observations:
            await coordinator.step(obs)

        history = servo.history
        assert len(history) >= 2, "Expected servo writes after 3+ observations"

        yaw_angles = [a for ch, a in history if ch == 0]
        pitch_angles = [a for ch, a in history if ch == 1]

        assert len(yaw_angles) >= 1
        assert len(pitch_angles) >= 1

        # Both angles should be in [0, 180] (valid servo range).
        for angle in yaw_angles:
            assert 0.0 <= angle <= 180.0, f"Yaw {angle}° out of range"
        for angle in pitch_angles:
            assert 0.0 <= angle <= 180.0, f"Pitch {angle}° out of range"

        # For a ball heading mostly forward with y=0, z≈0 at x=0.1:
        # yaw should be close to 90° (neutral).
        for angle in yaw_angles:
            assert 70.0 <= angle <= 110.0, f"Yaw {angle}° far from neutral 90°"

    async def test_both_channels_receive_writes(self) -> None:
        coordinator, servo, _, _ = _make_coordinator()
        observations = _make_observations(n=5)
        for obs in observations:
            await coordinator.step(obs)

        channels_written = {ch for ch, _ in servo.history}
        assert 0 in channels_written, "Channel 0 (yaw) must have been written"
        assert 1 in channels_written, "Channel 1 (pitch) must have been written"


# ---------------------------------------------------------------------------
# Test 3: Unreachable target — servos not written, swing not fired
# ---------------------------------------------------------------------------


class TestUnreachableTargetDoesNotFire:
    async def test_far_impact_point_skips_servo_and_swing(self) -> None:
        """Impact point 5 m away — aim.compute returns None, servos not written."""
        coordinator, servo, bldc, _ = _make_coordinator()
        # Ball with y=5.0 → impact point at y=5 m, well beyond arm_length=0.2 m.
        observations = _make_observations(n=8, y0=5.0)
        for obs in observations:
            await coordinator.step(obs)

        assert bldc.throttle_history == [], "Swing must not fire for unreachable target"
        # Servo writes must NOT happen when aim returns None.
        assert servo.history == [], "Servo writes must not happen when aim returns None"


# ---------------------------------------------------------------------------
# Test 4: Reachable + time arrives → fires once
# ---------------------------------------------------------------------------


class TestFiresWhenTimeArrives:
    async def test_fires_after_clock_advances_past_strike_time(self) -> None:
        """Push 5 obs with clock before fire_time, then advance clock and push 1 more."""
        clock = FakeClock(start=0.0)
        coordinator, servo, bldc, _ = _make_coordinator(clock=clock)

        # Push 5 obs to establish a trajectory.
        observations = _make_observations(n=5)
        for obs in observations:
            await coordinator.step(obs)

        assert bldc.throttle_history == [], "Should not fire before time arrives"

        # The ball crosses x=0.1 at t≈0.1 s from t_start=0.
        # fire_time = impact_time - swing_latency = ~0.1 - 0.05 = ~0.05 s.
        # Advance clock well past the fire window.
        clock.advance(1.0)

        # Push one more observation near the strike plane.
        extra_obs = BallObservation(t=0.07, x=0.12, y=0.0, z=0.0)
        await coordinator.step(extra_obs)

        assert len(bldc.throttle_history) > 0, "Swing must have fired"

    async def test_fired_throttle_history_nonempty(self) -> None:
        clock = FakeClock(start=0.0)
        coordinator, servo, bldc, _ = _make_coordinator(clock=clock)

        observations = _make_observations(n=5)
        for obs in observations:
            await coordinator.step(obs)

        clock.advance(1.0)
        extra_obs = BallObservation(t=0.07, x=0.12, y=0.0, z=0.0)
        await coordinator.step(extra_obs)

        assert len(bldc.throttle_history) > 0


# ---------------------------------------------------------------------------
# Test 5: One fire per arc — subsequent steps in same arc do NOT re-fire
# ---------------------------------------------------------------------------


class TestOneFirePerArc:
    async def test_fires_only_once_in_same_arc(self) -> None:
        clock = FakeClock(start=0.0)
        coordinator, servo, bldc, _ = _make_coordinator(clock=clock)

        observations = _make_observations(n=5)
        for obs in observations:
            await coordinator.step(obs)

        # Advance clock past fire window.
        clock.advance(1.0)

        # Push several more observations in the same arc (still close to impact).
        # All within the rearm interval (0.5 s), so only one fire should happen.
        follow_ups = [
            BallObservation(t=0.07 + i * 0.01, x=0.12 - i * 0.01, y=0.0, z=0.0)
            for i in range(5)
        ]
        for obs in follow_ups:
            await coordinator.step(obs)

        throttle_history = bldc.throttle_history

        # Count the number of "ramping-up from zero" events — each is one swing.
        swing_starts = 0
        prev = 0.0
        for val in throttle_history:
            if prev == 0.0 and val > 0.0:
                swing_starts += 1
            prev = val

        assert swing_starts == 1, (
            f"Expected exactly 1 swing in the same arc, "
            f"got {swing_starts}. History: {throttle_history}"
        )


# ---------------------------------------------------------------------------
# Test 6: Re-arm after rearm_min_interval_s — fires again on new arc
# ---------------------------------------------------------------------------


class TestRearmAfterInterval:
    async def test_fires_again_after_rearm_interval(self) -> None:
        rearm_interval = 0.5
        clock = FakeClock(start=0.0)
        bldc = MockBLDCDriver()
        servo = MockServoDriver()
        swing = SwingController(driver=bldc, clock=clock)

        # First coordinator — fires once.
        predictor1 = TrajectoryPredictor()
        coordinator1 = RallyCoordinator(
            aim=AimController(),
            predictor=predictor1,
            servo_driver=servo,
            swing=swing,
            clock=clock,
            strike_plane_x=_STRIKE_PLANE,
            swing_latency_s=_SWING_LATENCY,
            rearm_min_interval_s=rearm_interval,
            swing_profile=_DEFAULT_PROFILE,
        )

        # First arc: build trajectory and fire.
        observations = _make_observations(n=5)
        for obs in observations:
            await coordinator1.step(obs)

        clock.advance(1.0)  # past fire window
        fire_obs = BallObservation(t=0.07, x=0.12, y=0.0, z=0.0)
        await coordinator1.step(fire_obs)

        after_first_fire = len(bldc.throttle_history)
        assert after_first_fire > 0, "Should have fired at least once"

        # Advance clock past rearm interval.
        clock.advance(rearm_interval + 0.01)

        # Second arc: build a fresh trajectory with the SAME coordinator
        # (same _last_fire_time) to verify the rearm guard has reset.
        # New observations start at current clock time.
        t_now = clock.now()
        new_obs = _make_observations(n=5, t_start=t_now)
        for obs in new_obs:
            await coordinator1.step(obs)

        # Advance clock past the new fire window (impact ≈ t_now + 0.1).
        clock.advance(0.5)

        trigger_obs = BallObservation(
            t=t_now + 0.07, x=0.12, y=0.0, z=0.0
        )
        await coordinator1.step(trigger_obs)

        after_second_fire = len(bldc.throttle_history)
        assert after_second_fire > after_first_fire, (
            "Coordinator should have fired again after rearm interval elapsed. "
            f"Throttle history: {bldc.throttle_history}"
        )


# ---------------------------------------------------------------------------
# Test 7: run(stream) consumes an async iterator and exits cleanly
# ---------------------------------------------------------------------------


class TestRunConsumesStream:
    async def test_run_consumes_async_iterator(self) -> None:
        clock = FakeClock(start=0.0)
        coordinator, servo, bldc, _ = _make_coordinator(clock=clock)

        observations = _make_observations(n=5)

        async def _stream() -> AsyncGenerator[BallObservation, None]:
            for obs in observations:
                yield obs

        # Advance clock so the first potential fire window opens.
        clock.advance(1.0)

        await coordinator.run(_stream())

        # After exhausting the stream, some servo writes should have happened.
        assert len(servo.history) > 0, "run() should have processed observations"

    async def test_run_exits_when_stream_exhausted(self) -> None:
        coordinator, servo, bldc, clock = _make_coordinator()
        observations = _make_observations(n=3)

        async def _stream() -> AsyncGenerator[BallObservation, None]:
            for obs in observations:
                yield obs

        # Should complete without raising.
        await coordinator.run(_stream())

    async def test_run_fires_same_as_step(self) -> None:
        """run() with clock advanced past fire window should fire the swing."""
        clock = FakeClock(start=0.0)
        coordinator, servo, bldc, _ = _make_coordinator(clock=clock)

        observations = _make_observations(n=5)
        clock.advance(1.0)  # past fire window

        async def _stream() -> AsyncGenerator[BallObservation, None]:
            for obs in observations:
                yield obs

        await coordinator.run(_stream())
        assert len(bldc.throttle_history) > 0, "run() should have triggered a swing"


# ---------------------------------------------------------------------------
# Test 8: Servo channels are respected
# ---------------------------------------------------------------------------


class TestServoChannelsRespected:
    async def test_custom_channels_are_used(self) -> None:
        coordinator, servo, _, _ = _make_coordinator(
            servo_yaw_channel=5,
            servo_pitch_channel=7,
        )
        observations = _make_observations(n=5)
        for obs in observations:
            await coordinator.step(obs)

        channels_written = {ch for ch, _ in servo.history}
        assert 5 in channels_written, "Yaw must be written to channel 5"
        assert 7 in channels_written, "Pitch must be written to channel 7"

        assert 0 not in channels_written, "Channel 0 must NOT be written"
        assert 1 not in channels_written, "Channel 1 must NOT be written"


# ---------------------------------------------------------------------------
# Test 9: Custom swing_profile peak is respected
# ---------------------------------------------------------------------------


class TestCustomSwingProfile:
    async def test_custom_peak_throttle_appears_in_history(self) -> None:
        """peak=0.3 profile should produce max throttle ≈ 0.3."""
        clock = FakeClock(start=0.0)
        custom_profile = SwingProfile(
            ramp_up_ms=50.0,
            hold_ms=50.0,
            ramp_down_ms=50.0,
            peak_throttle=0.3,
        )
        coordinator, servo, bldc, _ = _make_coordinator(
            clock=clock,
            swing_profile=custom_profile,
        )

        observations = _make_observations(n=5)
        for obs in observations:
            await coordinator.step(obs)

        clock.advance(1.0)  # past fire window

        fire_obs = BallObservation(t=0.07, x=0.12, y=0.0, z=0.0)
        await coordinator.step(fire_obs)

        assert len(bldc.throttle_history) > 0
        peak_seen = max(bldc.throttle_history)
        assert peak_seen == pytest.approx(0.3, abs=0.01), (
            f"Expected peak ≈ 0.3 but got {peak_seen}"
        )

    async def test_default_profile_peak_is_0_5(self) -> None:
        """Default profile peak=0.5."""
        clock = FakeClock(start=0.0)
        coordinator, servo, bldc, _ = _make_coordinator(clock=clock)

        observations = _make_observations(n=5)
        for obs in observations:
            await coordinator.step(obs)

        clock.advance(1.0)
        fire_obs = BallObservation(t=0.07, x=0.12, y=0.0, z=0.0)
        await coordinator.step(fire_obs)

        assert len(bldc.throttle_history) > 0
        peak_seen = max(bldc.throttle_history)
        assert peak_seen == pytest.approx(0.5, abs=0.01)


# ---------------------------------------------------------------------------
# Test 10: No fire when impact is far in the future
# ---------------------------------------------------------------------------


class TestNoFireWhenImpactFarInFuture:
    async def test_does_not_fire_when_impact_is_10s_away(self) -> None:
        """impact_time ≈ clock.now() + 10s → should not fire (way before fire window)."""
        clock = FakeClock(start=0.0)
        coordinator, servo, bldc, _ = _make_coordinator(
            clock=clock,
            swing_latency_s=0.05,
        )

        # Ball is very far away moving slowly — impact in ~10 s.
        # x0=40.1, vx=-4 → crosses strike_plane_x=0.1 at t=(40.1-0.1)/4=10 s.
        observations = _make_observations(n=5, x0=40.1, vx=-4.0)
        for obs in observations:
            await coordinator.step(obs)

        # Clock is at 0 — impact is at ~10s, fire_time = 10 - 0.05 = 9.95s.
        # Way too early to fire.
        assert bldc.throttle_history == [], "Must not fire when impact is 10 s away"


# ---------------------------------------------------------------------------
# Test 11: BLDC throttle_history ends at 0.0 after a fire
# ---------------------------------------------------------------------------


class TestBLDCEndsAtZero:
    async def test_throttle_history_ends_at_zero_after_fire(self) -> None:
        """SwingController invariant: final throttle is always 0.0."""
        clock = FakeClock(start=0.0)
        coordinator, servo, bldc, _ = _make_coordinator(clock=clock)

        observations = _make_observations(n=5)
        for obs in observations:
            await coordinator.step(obs)

        clock.advance(1.0)
        fire_obs = BallObservation(t=0.07, x=0.12, y=0.0, z=0.0)
        await coordinator.step(fire_obs)

        assert len(bldc.throttle_history) > 0
        assert bldc.throttle_history[-1] == 0.0, (
            f"Last throttle must be 0.0, got {bldc.throttle_history[-1]}"
        )


# ---------------------------------------------------------------------------
# Test 12: Demo smoke test
# ---------------------------------------------------------------------------


class TestDemoSmoke:
    def test_demo_runs_without_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """_demo() must run without raising and print something to stdout."""
        from mcenroebot._shelved.rally.__main__ import _demo

        _demo()
        captured = capsys.readouterr()
        assert "RallyCoordinator demo" in captured.out
