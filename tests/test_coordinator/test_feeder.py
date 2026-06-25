"""Tests for FeederCoordinator — drill -> launch + aim + feeder + lift wiring.

Everything is mock-driven with a FakeClock; no hardware, no real time.
"""

from __future__ import annotations

from typing import NamedTuple

import pytest

from mcenroebot.aim import AimController, TurretGeometry
from mcenroebot.clock import FakeClock
from mcenroebot.coordinator import FeederCoordinator
from mcenroebot.drill import Drill, FixedPatternStrategy, TableTarget
from mcenroebot.drivers import (
    MockBLDCDriver,
    MockFeederDriver,
    MockHopperSensor,
    MockLiftDriver,
    MockServoDriver,
)
from mcenroebot.launch import LaunchController, LaunchGeometry, ShotSpec, ThrottleMap


class Harness(NamedTuple):
    coord: FeederCoordinator
    servo: MockServoDriver
    head_roll: MockServoDriver
    wheel_top: MockBLDCDriver
    wheel_bottom: MockBLDCDriver
    feeder: MockFeederDriver
    lift: MockLiftDriver
    clock: FakeClock
    launch: LaunchController
    throttle_map: ThrottleMap


def _make(
    *,
    spec: ShotSpec | None = None,
    aim_reach_m: float = 5.0,
    cadence_s: float = 1.0,
    settle_s: float = 0.3,
    feed_rate_bpm: float = 30.0,
    lift_duty: float = 1.0,
    hopper: MockHopperSensor | None = None,
    use_index_feeder: bool = False,
    feeder: MockFeederDriver | None = None,
    lift: MockLiftDriver | None = None,
    pattern: str = "static",
) -> Harness:
    target = TableTarget(center_x_m=1.5, half_width_m=0.5)
    strategy = FixedPatternStrategy(pattern=pattern, target=target)  # type: ignore[arg-type]
    spec = spec or ShotSpec(speed_mps=6.0, spin_rad_s=0.0, spin_axis_deg=0.0)
    drill = Drill(spec=spec, strategy=strategy, cadence_s=cadence_s)
    launch = LaunchController(
        geometry=LaunchGeometry(wheel_diameter_m=0.055, max_wheel_rpm=10000.0)
    )
    throttle_map = ThrottleMap(rpm_at_full_throttle=10000.0)
    aim = AimController(TurretGeometry(arm_length_m=aim_reach_m))
    servo = MockServoDriver()
    head_roll = MockServoDriver()
    wheel_top = MockBLDCDriver()
    wheel_bottom = MockBLDCDriver()
    feeder = feeder or MockFeederDriver()
    lift = lift or MockLiftDriver()
    clock = FakeClock()
    coord = FeederCoordinator(
        drill=drill,
        launch=launch,
        throttle_map=throttle_map,
        aim=aim,
        servo=servo,
        head_roll=head_roll,
        wheel_top=wheel_top,
        wheel_bottom=wheel_bottom,
        feeder=feeder,
        lift=lift,
        clock=clock,
        hopper=hopper,
        feed_rate_bpm=feed_rate_bpm,
        lift_duty=lift_duty,
        settle_s=settle_s,
        use_index_feeder=use_index_feeder,
    )
    return Harness(
        coord=coord,
        servo=servo,
        head_roll=head_roll,
        wheel_top=wheel_top,
        wheel_bottom=wheel_bottom,
        feeder=feeder,
        lift=lift,
        clock=clock,
        launch=launch,
        throttle_map=throttle_map,
    )


class TestHappyPath:
    async def test_servos_commanded_per_shot(self) -> None:
        h = _make()
        await h.coord.run(3)
        # 3 pan (ch0) + 3 tilt (ch1)
        assert [c for c, _ in h.servo.history] == [0, 1, 0, 1, 0, 1]

    async def test_head_roll_commanded_per_shot(self) -> None:
        h = _make()
        await h.coord.run(3)
        assert [c for c, _ in h.head_roll.history] == [2, 2, 2]

    async def test_wheels_armed_throttled_and_stopped(self) -> None:
        h = _make()
        await h.coord.run(2)
        cmd = h.launch.compute(ShotSpec(speed_mps=6.0, spin_rad_s=0.0, spin_axis_deg=0.0))
        assert cmd is not None
        expected = h.throttle_map.throttle_for(cmd.top_rpm)
        assert h.wheel_top.throttle_history[:2] == pytest.approx([expected, expected])
        assert h.wheel_top.throttle_history[-1] == 0.0  # zeroed on shutdown
        assert h.wheel_top.armed is False  # disarmed on shutdown

    async def test_feeder_releases_each_shot_then_stops(self) -> None:
        h = _make()
        await h.coord.run(3)
        assert h.feeder.calls == [
            ("set_rate", 30.0),
            ("set_rate", 30.0),
            ("set_rate", 30.0),
            ("stop", None),
        ]

    async def test_lift_runs_each_shot_then_off(self) -> None:
        h = _make()
        await h.coord.run(2)
        assert h.lift.duty_history == [1.0, 1.0, 0.0]

    async def test_clock_paces_settle_plus_cadence(self) -> None:
        h = _make(cadence_s=1.0, settle_s=0.3)
        await h.coord.run(3)
        assert h.clock.elapsed == pytest.approx(3 * (0.3 + 1.0))


class TestHundredShotDrill:
    async def test_100_shots_all_issue_full_command_set(self) -> None:
        # Phase gate: a 100-shot oscillate drill issues correct, ordered
        # commands for 100/100 cases (no skips, every actuator commanded).
        h = _make(
            spec=ShotSpec(speed_mps=7.0, spin_rad_s=30.0, spin_axis_deg=20.0),
            pattern="oscillate",
        )
        await h.coord.run(100)
        assert len(h.head_roll.history) == 100  # one roll command per shot
        assert len(h.servo.history) == 200  # pan + tilt per shot
        first = h.wheel_top.throttle_history[0]
        assert h.wheel_top.throttle_history[:100] == pytest.approx([first] * 100)
        assert len([c for c in h.feeder.calls if c[0] == "set_rate"]) == 100
        assert len([d for d in h.lift.duty_history if d > 0.0]) == 100


class TestIndexFeeder:
    async def test_uses_fire_when_index_upgrade(self) -> None:
        h = _make(use_index_feeder=True)
        await h.coord.run(2)
        assert h.feeder.calls == [("fire", None), ("fire", None), ("stop", None)]


class TestSkips:
    async def test_out_of_envelope_shot_skipped(self) -> None:
        # Spin far too high for the speed -> launch.compute returns None.
        h = _make(spec=ShotSpec(speed_mps=1.0, spin_rad_s=500.0, spin_axis_deg=0.0))
        await h.coord.run(3)
        assert h.servo.history == []
        # no per-shot throttle; only the shutdown zero + disarm
        assert h.wheel_top.throttle_history == [0.0, 0.0]
        assert h.feeder.calls == [("stop", None)]  # only shutdown stop()

    async def test_unreachable_target_skipped(self) -> None:
        # Tiny aim reach -> the 1.5 m target is unreachable -> aim.compute None.
        h = _make(aim_reach_m=0.2)
        await h.coord.run(3)
        assert h.servo.history == []
        assert h.feeder.calls == [("stop", None)]


class TestHopper:
    async def test_hopper_full_turns_lift_off(self) -> None:
        h = _make(hopper=MockHopperSensor(full=True))
        await h.coord.run(2)
        # full every shot -> only off() entries (per shot + shutdown)
        assert h.lift.duty_history == [0.0, 0.0, 0.0]

    async def test_hopper_not_full_runs_lift(self) -> None:
        h = _make(hopper=MockHopperSensor(full=False))
        await h.coord.run(1)
        assert h.lift.duty_history == [1.0, 0.0]


class _RaisingFeeder(MockFeederDriver):
    def set_rate(self, balls_per_min: float) -> None:
        raise RuntimeError("boom")


class TestShutdown:
    async def test_cleanup_on_exception(self) -> None:
        feeder = _RaisingFeeder()
        lift = MockLiftDriver()
        h = _make(feeder=feeder, lift=lift)
        with pytest.raises(RuntimeError, match="boom"):
            await h.coord.run(3)
        # try/finally still zeroed wheels, stopped feeder, turned lift off
        assert h.wheel_top.throttle_history[-1] == 0.0
        assert h.wheel_top.armed is False
        assert feeder.calls[-1] == ("stop", None)
        assert lift.duty_history[-1] == 0.0
