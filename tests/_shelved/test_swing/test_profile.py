"""Tests for SwingProfile frozen pydantic value object."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcenroebot._shelved.swing.profile import SwingProfile


class TestSwingProfileConstruction:
    def test_happy_path_all_fields_readable(self) -> None:
        p = SwingProfile(
            ramp_up_ms=50.0,
            hold_ms=100.0,
            ramp_down_ms=50.0,
            peak_throttle=0.8,
        )
        assert p.ramp_up_ms == 50.0
        assert p.hold_ms == 100.0
        assert p.ramp_down_ms == 50.0
        assert p.peak_throttle == 0.8

    def test_total_ms_sums_three_phases(self) -> None:
        p = SwingProfile(
            ramp_up_ms=50.0,
            hold_ms=100.0,
            ramp_down_ms=50.0,
            peak_throttle=0.8,
        )
        assert p.total_ms == pytest.approx(200.0)


class TestSwingProfileTotalMs:
    @pytest.mark.parametrize(
        "ramp_up,hold,ramp_down,expected",
        [
            (50.0, 100.0, 50.0, 200.0),
            (10.0, 0.0, 10.0, 20.0),       # triangle — hold=0
            (25.0, 75.0, 25.0, 125.0),
            (100.0, 200.0, 100.0, 400.0),
        ],
    )
    def test_total_ms_parametrized(
        self,
        ramp_up: float,
        hold: float,
        ramp_down: float,
        expected: float,
    ) -> None:
        p = SwingProfile(
            ramp_up_ms=ramp_up,
            hold_ms=hold,
            ramp_down_ms=ramp_down,
            peak_throttle=0.5,
        )
        assert p.total_ms == pytest.approx(expected)


class TestSwingProfileFrozen:
    def test_assign_field_raises_validation_error(self) -> None:
        p = SwingProfile(
            ramp_up_ms=50.0,
            hold_ms=100.0,
            ramp_down_ms=50.0,
            peak_throttle=0.5,
        )
        with pytest.raises(ValidationError):
            p.ramp_up_ms = 99.0  # type: ignore[misc]


class TestSwingProfileValidators:
    def test_ramp_up_ms_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            SwingProfile(
                ramp_up_ms=0.0,
                hold_ms=100.0,
                ramp_down_ms=50.0,
                peak_throttle=0.5,
            )

    def test_ramp_up_ms_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            SwingProfile(
                ramp_up_ms=-1.0,
                hold_ms=100.0,
                ramp_down_ms=50.0,
                peak_throttle=0.5,
            )

    def test_ramp_down_ms_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            SwingProfile(
                ramp_up_ms=50.0,
                hold_ms=100.0,
                ramp_down_ms=0.0,
                peak_throttle=0.5,
            )

    def test_ramp_down_ms_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            SwingProfile(
                ramp_up_ms=50.0,
                hold_ms=100.0,
                ramp_down_ms=-5.0,
                peak_throttle=0.5,
            )

    def test_hold_ms_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            SwingProfile(
                ramp_up_ms=50.0,
                hold_ms=-1.0,
                ramp_down_ms=50.0,
                peak_throttle=0.5,
            )

    def test_hold_ms_zero_is_accepted(self) -> None:
        p = SwingProfile(
            ramp_up_ms=50.0,
            hold_ms=0.0,
            ramp_down_ms=50.0,
            peak_throttle=0.5,
        )
        assert p.hold_ms == 0.0

    def test_peak_throttle_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            SwingProfile(
                ramp_up_ms=50.0,
                hold_ms=100.0,
                ramp_down_ms=50.0,
                peak_throttle=0.0,
            )

    def test_peak_throttle_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            SwingProfile(
                ramp_up_ms=50.0,
                hold_ms=100.0,
                ramp_down_ms=50.0,
                peak_throttle=-0.1,
            )

    def test_peak_throttle_above_one_raises(self) -> None:
        with pytest.raises(ValidationError):
            SwingProfile(
                ramp_up_ms=50.0,
                hold_ms=100.0,
                ramp_down_ms=50.0,
                peak_throttle=1.1,
            )

    def test_peak_throttle_exactly_one_is_accepted(self) -> None:
        p = SwingProfile(
            ramp_up_ms=50.0,
            hold_ms=100.0,
            ramp_down_ms=50.0,
            peak_throttle=1.0,
        )
        assert p.peak_throttle == 1.0
