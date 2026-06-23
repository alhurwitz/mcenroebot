"""Stateless controller mapping a desired shot to two-wheel + head-roll commands."""

from __future__ import annotations

import math

from mcenroebot.launch.value_objects import (
    LaunchGeometry,
    ShotSpec,
    ThrottleMap,
    WheelCommand,
)

__all__ = ["LaunchController"]


class LaunchController:
    """Convert a :class:`ShotSpec` to a :class:`WheelCommand`.

    Two counter-rotating wheels grip the ball between them. Their mean surface
    speed sets exit speed; their surface-speed *difference* sets spin. Rolling
    the head (``head_roll_deg``) physically orients that spin axis in space.

    Stateless aside from the injected geometry; one instance is reused across
    many ``compute()`` calls. Out-of-envelope shots return ``None`` rather than
    raising — the caller decides what to do.

    Example
    -------
    >>> ctrl = LaunchController()
    >>> cmd = ctrl.compute(ShotSpec(speed_mps=6.0, spin_rad_s=0.0, spin_axis_deg=0.0))
    >>> cmd is not None and cmd.top_rpm == cmd.bottom_rpm
    True
    """

    def __init__(self, geometry: LaunchGeometry | None = None) -> None:
        self.geometry: LaunchGeometry = geometry or LaunchGeometry(
            wheel_diameter_m=0.055, max_wheel_rpm=10000.0
        )

    def compute(self, spec: ShotSpec) -> WheelCommand | None:
        """Compute the wheel speeds + head roll for a shot.

        Returns
        -------
        WheelCommand
            The two wheel rpms and the head-roll servo angle.
        None
            If the shot is outside the achievable envelope — spin too high for
            the speed (a wheel would need to spin backward), or a wheel rpm
            beyond ``max_wheel_rpm``.

        Notes
        -----
        ::

            mean_surface = speed_mps / grip_efficiency
            diff_surface = 2 * ball_radius_m * spin_rad_s / spin_efficiency
            u_top        = mean_surface + diff_surface / 2
            u_bottom     = mean_surface - diff_surface / 2
            rpm(u)       = u * 60 / (pi * wheel_diameter_m)
            head_roll    = spin_axis_deg folded into [0, 180)  (180 head symmetry)
        """
        geo = self.geometry

        mean_surface = spec.speed_mps / geo.grip_efficiency
        diff_surface = 2.0 * geo.ball_radius_m * spec.spin_rad_s / geo.spin_efficiency
        u_top = mean_surface + diff_surface / 2.0
        u_bottom = mean_surface - diff_surface / 2.0

        # Spin too high for the speed -> a wheel would need to run backward.
        if u_top < 0.0 or u_bottom < 0.0:
            return None

        top_rpm = self._rpm(u_top)
        bottom_rpm = self._rpm(u_bottom)
        if top_rpm > geo.max_wheel_rpm or bottom_rpm > geo.max_wheel_rpm:
            return None

        head_roll_deg = spec.spin_axis_deg % 180.0

        return WheelCommand(top_rpm=top_rpm, bottom_rpm=bottom_rpm, head_roll_deg=head_roll_deg)

    def throttles(self, command: WheelCommand, throttle_map: ThrottleMap) -> tuple[float, float]:
        """Convert a :class:`WheelCommand` to (top, bottom) ESC throttles in [0, 1]."""
        return (
            throttle_map.throttle_for(command.top_rpm),
            throttle_map.throttle_for(command.bottom_rpm),
        )

    def _rpm(self, u_surface: float) -> float:
        """Wheel rpm needed for a given surface speed (m/s)."""
        return u_surface * 60.0 / (math.pi * self.geometry.wheel_diameter_m)


def _demo() -> None:
    """Print WheelCommands for a few representative shots.

    Run with `python -m mcenroebot.launch`.
    """
    controller = LaunchController()
    cases = [
        ("Flat medium", ShotSpec(speed_mps=6.0, spin_rad_s=0.0, spin_axis_deg=0.0)),
        ("Heavy topspin", ShotSpec(speed_mps=8.0, spin_rad_s=120.0, spin_axis_deg=0.0)),
        ("Backspin", ShotSpec(speed_mps=5.0, spin_rad_s=-80.0, spin_axis_deg=0.0)),
        ("Sidespin", ShotSpec(speed_mps=7.0, spin_rad_s=90.0, spin_axis_deg=90.0)),
        ("Spin too high", ShotSpec(speed_mps=1.0, spin_rad_s=500.0, spin_axis_deg=0.0)),
    ]
    for label, spec in cases:
        cmd = controller.compute(spec)
        print(f"=== {label} ===")
        print(
            f"  speed={spec.speed_mps:.1f} m/s  spin={spec.spin_rad_s:+.1f} rad/s  "
            f"axis={spec.spin_axis_deg:.0f}°"
        )
        if cmd is None:
            print("  -> OUT OF ENVELOPE")
        else:
            print(
                f"  -> top={cmd.top_rpm:8.1f} rpm  bottom={cmd.bottom_rpm:8.1f} rpm  "
                f"roll={cmd.head_roll_deg:5.1f}°"
            )
        print()
