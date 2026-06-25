"""Tests for drill value objects: DrillContext and Shot."""

from __future__ import annotations

import random

import pytest
from pydantic import ValidationError

from mcenroebot.aim import Position3D
from mcenroebot.drill import DrillContext, Shot, TableTarget
from mcenroebot.launch import ShotSpec


class TestTableTarget:
    def test_valid(self) -> None:
        t = TableTarget(center_x_m=2.0, half_width_m=0.6, half_depth_m=0.4, z_m=0.1)
        assert t.center_x_m == 2.0
        assert t.half_depth_m == 0.4

    def test_defaults(self) -> None:
        t = TableTarget(center_x_m=2.0, half_width_m=0.6)
        assert t.half_depth_m == 0.0
        assert t.z_m == 0.0

    @pytest.mark.parametrize("field,value", [("center_x_m", 0.0), ("half_width_m", -0.1)])
    def test_non_positive_raises(self, field: str, value: float) -> None:
        kwargs: dict[str, float] = {"center_x_m": 2.0, "half_width_m": 0.6}
        kwargs[field] = value
        with pytest.raises(ValidationError):
            TableTarget(**kwargs)

    def test_negative_half_depth_raises(self) -> None:
        with pytest.raises(ValidationError, match=r"half_depth_m"):
            TableTarget(center_x_m=2.0, half_width_m=0.6, half_depth_m=-0.1)


class TestDrillContext:
    def test_holds_index_and_rng(self) -> None:
        rng = random.Random(0)
        ctx = DrillContext(shot_index=3, rng=rng)
        assert ctx.shot_index == 3
        assert ctx.rng is rng

    def test_is_frozen(self) -> None:
        ctx = DrillContext(shot_index=0, rng=random.Random(0))
        with pytest.raises(ValidationError):
            ctx.shot_index = 1  # type: ignore[misc]


class TestShot:
    def test_holds_spec_target_delay(self) -> None:
        spec = ShotSpec(speed_mps=6.0, spin_rad_s=0.0, spin_axis_deg=0.0)
        target = Position3D(x=2.0, y=0.1, z=0.0)
        shot = Shot(spec=spec, target=target, delay_s=1.5)
        assert shot.spec is spec
        assert shot.target is target
        assert shot.delay_s == 1.5

    def test_negative_delay_raises(self) -> None:
        spec = ShotSpec(speed_mps=6.0, spin_rad_s=0.0, spin_axis_deg=0.0)
        target = Position3D(x=2.0, y=0.0, z=0.0)
        with pytest.raises(ValidationError, match=r"delay_s"):
            Shot(spec=spec, target=target, delay_s=-0.1)

    def test_is_frozen(self) -> None:
        spec = ShotSpec(speed_mps=6.0, spin_rad_s=0.0, spin_axis_deg=0.0)
        shot = Shot(spec=spec, target=Position3D(x=2.0, y=0.0, z=0.0), delay_s=1.0)
        with pytest.raises(ValidationError):
            shot.delay_s = 2.0  # type: ignore[misc]
