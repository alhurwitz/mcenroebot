"""FeederCoordinator — periodic scheduler wiring the feeder control pipeline.

    Drill ──► LaunchController ──► wheel ESCs
          └─► AimController   ──► pan / tilt / head-roll servos
          └─► FeederDriver (release)  +  LiftDriver (recycle)

This is **not** a real-time loop. Per shot it aims, spins up the wheels, lets
them settle, releases a ball, runs the auger, and waits out the cadence. It
never imports the shelved V3 rally stack.
"""

from __future__ import annotations

import logging

from mcenroebot.aim import AimController
from mcenroebot.clock import Clock
from mcenroebot.drill import Drill
from mcenroebot.drivers import (
    BLDCDriver,
    FeederDriver,
    HopperSensor,
    LiftDriver,
    ServoDriver,
)
from mcenroebot.launch import LaunchController, ThrottleMap

__all__ = ["FeederCoordinator", "_demo"]

_log = logging.getLogger(__name__)


class FeederCoordinator:
    """Execute a drill: aim, launch, feed, and recycle, one shot at a time.

    Note on ``aim``: the reused :class:`AimController` treats its geometry's
    ``arm_length_m`` as a reachability bound. For the feeder that bound is the
    **placement range**, so construct the ``AimController`` with an
    ``arm_length_m`` at least as large as the farthest court target; otherwise
    every shot is reported unreachable and skipped.

    Args:
        drill: the Drill producing Shots.
        launch: LaunchController (holds its own LaunchGeometry).
        throttle_map: converts wheel rpm to ESC throttle.
        aim: AimController mapping a target to pan/tilt angles.
        servo: ServoDriver for pan + tilt (may be the same instance as ``head_roll``).
        head_roll: ServoDriver for the head-roll servo.
        wheel_top, wheel_bottom: the two launch-wheel ESC drivers.
        feeder: escapement driver.
        lift: auger driver.
        clock: Clock for pacing (settle + cadence).
        hopper: optional hopper-full sensor gating the auger.
        feed_rate_bpm: v1 continuous feed rate (set the caller's drill cadence to match).
        lift_duty: auger PWM duty while running.
        settle_s: dwell after commanding aim/wheels before releasing a ball.
        pan_channel, tilt_channel, head_roll_channel: PCA9685 servo channels.
        use_index_feeder: if True, release with ``feeder.fire()`` (index upgrade)
            instead of ``feeder.set_rate()``.
    """

    def __init__(
        self,
        drill: Drill,
        launch: LaunchController,
        throttle_map: ThrottleMap,
        aim: AimController,
        servo: ServoDriver,
        head_roll: ServoDriver,
        wheel_top: BLDCDriver,
        wheel_bottom: BLDCDriver,
        feeder: FeederDriver,
        lift: LiftDriver,
        clock: Clock,
        hopper: HopperSensor | None = None,
        feed_rate_bpm: float = 30.0,
        lift_duty: float = 1.0,
        settle_s: float = 0.3,
        pan_channel: int = 0,
        tilt_channel: int = 1,
        head_roll_channel: int = 2,
        use_index_feeder: bool = False,
    ) -> None:
        self._drill = drill
        self._launch = launch
        self._throttle_map = throttle_map
        self._aim = aim
        self._servo = servo
        self._head_roll = head_roll
        self._wheel_top = wheel_top
        self._wheel_bottom = wheel_bottom
        self._feeder = feeder
        self._lift = lift
        self._clock = clock
        self._hopper = hopper
        self._feed_rate_bpm = feed_rate_bpm
        self._lift_duty = lift_duty
        self._settle_s = settle_s
        self._pan_channel = pan_channel
        self._tilt_channel = tilt_channel
        self._head_roll_channel = head_roll_channel
        self._use_index_feeder = use_index_feeder

    async def run(self, n: int | None = None) -> None:
        """Run the drill for ``n`` shots (or until the drill stream ends).

        Guarantees on exit (normal or exceptional): both wheels are throttled
        to 0 and disarmed, the feeder is stopped, and the auger is off.
        """
        self._wheel_top.arm()
        self._wheel_bottom.arm()
        try:
            for shot in self._drill.shots(n):
                await self._run_shot(shot)
        finally:
            self._shutdown()

    async def _run_shot(self, shot: object) -> None:
        # mypy: shot is a drill.Shot; typed loosely to avoid a cyclic import note.
        spec = shot.spec  # type: ignore[attr-defined]
        target = shot.target  # type: ignore[attr-defined]
        delay_s = shot.delay_s  # type: ignore[attr-defined]

        command = self._launch.compute(spec)
        if command is None:
            _log.warning("Shot %s out of launch envelope — skipping", spec)
            return

        angles = self._aim.compute(target)
        if angles is None:
            _log.warning("Target %s unreachable (out of placement range) — skipping", target)
            return

        # Command head roll, then pan/tilt, then the wheel ESCs.
        self._head_roll.write_angle(self._head_roll_channel, command.head_roll_deg)
        self._servo.write_angle(self._pan_channel, angles.yaw_deg)
        self._servo.write_angle(self._tilt_channel, angles.pitch_deg)
        top_throttle, bottom_throttle = self._launch.throttles(command, self._throttle_map)
        self._wheel_top.set_throttle(top_throttle)
        self._wheel_bottom.set_throttle(bottom_throttle)

        # Let the wheels spin up and the servos settle before releasing.
        await self._clock.sleep(self._settle_s)

        if self._use_index_feeder:
            self._feeder.fire()
        else:
            self._feeder.set_rate(self._feed_rate_bpm)

        # Recycle: run the auger unless the hopper is already full.
        if self._hopper is not None and self._hopper.is_full():
            self._lift.off()
        else:
            self._lift.set_duty(self._lift_duty)

        await self._clock.sleep(delay_s)

    def _shutdown(self) -> None:
        """Zero + disarm the wheels, stop the feeder, and stop the auger."""
        self._wheel_top.set_throttle(0.0)
        self._wheel_bottom.set_throttle(0.0)
        self._wheel_top.disarm()
        self._wheel_bottom.disarm()
        self._feeder.stop()
        self._lift.off()


async def _demo() -> None:
    """Run a short mock-driven feeder drill end-to-end and print the result.

    Wires the whole feeder pipeline (drill -> launch + aim + servos + wheels +
    feeder + lift) against mock drivers and a FakeClock, so it runs anywhere —
    no Pi, no real time. Run with `python -m mcenroebot.coordinator`.
    """
    from mcenroebot.aim import AimController, TurretGeometry
    from mcenroebot.clock import FakeClock
    from mcenroebot.drill import Drill, FixedPatternStrategy, TableTarget
    from mcenroebot.drivers import (
        MockBLDCDriver,
        MockFeederDriver,
        MockLiftDriver,
        MockServoDriver,
    )
    from mcenroebot.launch import LaunchGeometry, ShotSpec, ThrottleMap

    target = TableTarget(center_x_m=2.0, half_width_m=0.6)
    drill = Drill(
        spec=ShotSpec(speed_mps=7.0, spin_rad_s=40.0, spin_axis_deg=15.0),
        strategy=FixedPatternStrategy(pattern="oscillate", target=target),
        cadence_s=1.2,
    )
    servo = MockServoDriver()
    head_roll = MockServoDriver()
    wheel_top = MockBLDCDriver()
    wheel_bottom = MockBLDCDriver()
    feeder = MockFeederDriver()
    lift = MockLiftDriver()
    coordinator = FeederCoordinator(
        drill=drill,
        launch=LaunchController(
            geometry=LaunchGeometry(wheel_diameter_m=0.055, max_wheel_rpm=10000.0)
        ),
        throttle_map=ThrottleMap(rpm_at_full_throttle=10000.0),
        aim=AimController(TurretGeometry(arm_length_m=5.0)),
        servo=servo,
        head_roll=head_roll,
        wheel_top=wheel_top,
        wheel_bottom=wheel_bottom,
        feeder=feeder,
        lift=lift,
        clock=FakeClock(),
    )

    n = 4
    print(f"=== feeder drill demo ({n} shots, mock drivers + FakeClock) ===")
    await coordinator.run(n)

    pans = [a for c, a in servo.history if c == 0]
    tilts = [a for c, a in servo.history if c == 1]
    rolls = [a for _, a in head_roll.history]
    feeds = [bpm for name, bpm in feeder.calls if name == "set_rate"]
    for i in range(n):
        top_t = wheel_top.throttle_history[i]
        bottom_t = wheel_bottom.throttle_history[i]
        print(
            f"  shot {i}: pan={pans[i]:6.1f}°  tilt={tilts[i]:6.1f}°  roll={rolls[i]:5.1f}°  "
            f"top={top_t:.3f}  bottom={bottom_t:.3f}  feed={feeds[i]:.0f} bpm"
        )
    print(
        f"  shutdown: wheels at {wheel_top.throttle_history[-1]:.1f} "
        f"(armed={wheel_top.armed}), feeder {feeder.calls[-1][0]}, "
        f"lift {lift.duty_history[-1]:.1f}"
    )
