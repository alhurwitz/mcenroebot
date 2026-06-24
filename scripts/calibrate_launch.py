#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "adafruit-blinka>=9.1.0",
#     "adafruit-circuitpython-servokit>=1.3.24",
# ]
# ///
"""Calibrate launch geometry: grip / spin efficiency and the wheel rpm ceiling.

Run ON THE PI (needs the ``pi`` extra / Adafruit libs). Arm both wheel ESCs
first (e.g. via ``mcenroebot.calibrate.EscCalibrator`` or ``scripts/esc_arm.py``).

    uv run scripts/calibrate_launch.py \
        --top-channel 3 --bottom-channel 4 \
        --wheel-diameter-m 0.055 --ball-radius-m 0.02 \
        --max-wheel-rpm 9000 --launch-angle-deg 20 --launch-height-m 0.25 \
        --out launch_geometry.json

Workflow:

  1. You supply the **measured** no-load wheel rpm at full throttle
     (``--max-wheel-rpm``) — tach or slow-motion video.
  2. EQUAL-throttle shots (zero spin) calibrate ``grip_efficiency`` from the
     ball's measured landing range (range -> exit speed via projectile motion).
  3. DIFFERENTIAL-throttle shots calibrate ``spin_efficiency`` from a measured
     spin rate (slow-motion video), if you have it; otherwise it defaults.

Writes a JSON file that loads directly into a ``LaunchGeometry``:

    from mcenroebot.launch import LaunchGeometry
    geo = LaunchGeometry.model_validate_json(Path("launch_geometry.json").read_text())

The v1 model is linear (throttle = rpm / max_wheel_rpm); if launch speed is
inconsistent under load, upgrade to a measured rpm<->throttle curve.

SAFETY: launch wheels throw balls hard. Clear the room, wear eye protection,
and keep hands away from the wheels while throttled.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from adafruit_servokit import ServoKit

_G = 9.81  # m/s^2


def surface_speed_mps(rpm: float, wheel_diameter_m: float) -> float:
    """Wheel rim surface speed (m/s) for a given rpm."""
    return rpm * math.pi * wheel_diameter_m / 60.0


def speed_from_range(
    range_m: float,
    launch_angle_deg: float,
    launch_height_m: float = 0.0,
    g: float = _G,
) -> float:
    """Exit speed (m/s) that lands a projectile at ``range_m`` on flat ground.

    Solves the projectile range equation for launch speed by bisection, so it
    handles a non-zero launch height. Assumes no drag (a v1 approximation).
    """
    theta = math.radians(launch_angle_deg)

    def landing_range(v: float) -> float:
        vy = v * math.sin(theta)
        vx = v * math.cos(theta)
        flight = (vy + math.sqrt(vy * vy + 2.0 * g * launch_height_m)) / g
        return vx * flight

    lo, hi = 0.0, 100.0
    for _ in range(80):  # ~1e-22 m resolution — far past need
        mid = (lo + hi) / 2.0
        if landing_range(mid) < range_m:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def grip_efficiency(ball_speed_mps: float, mean_surface_mps: float) -> float:
    """eta = ball exit speed / mean wheel-surface speed."""
    if mean_surface_mps <= 0.0:
        raise ValueError("mean_surface_mps must be > 0")
    return ball_speed_mps / mean_surface_mps


def spin_efficiency(spin_rad_s: float, diff_surface_mps: float, ball_radius_m: float) -> float:
    """eta_spin = (2 * r * spin) / surface-speed difference."""
    if diff_surface_mps == 0.0:
        raise ValueError("diff_surface_mps must be non-zero")
    return (2.0 * ball_radius_m * spin_rad_s) / diff_surface_mps


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-channel", type=int, default=3)
    parser.add_argument("--bottom-channel", type=int, default=4)
    parser.add_argument("--wheel-diameter-m", type=float, default=0.055)
    parser.add_argument("--ball-radius-m", type=float, default=0.02)
    parser.add_argument("--max-wheel-rpm", type=float, required=True, help="measured no-load rpm")
    parser.add_argument("--launch-angle-deg", type=float, default=20.0)
    parser.add_argument("--launch-height-m", type=float, default=0.25)
    parser.add_argument("--grip-throttles", type=float, nargs="+", default=[0.4, 0.6, 0.8])
    parser.add_argument("--spin-throttle", type=float, default=0.6)
    parser.add_argument("--spin-diff", type=float, default=0.3, help="top-bottom throttle delta")
    parser.add_argument("--out", type=Path, default=Path("launch_geometry.json"))
    args = parser.parse_args(argv)

    kit = ServoKit(channels=16)
    top = kit.continuous_servo[args.top_channel]
    bottom = kit.continuous_servo[args.bottom_channel]
    top.throttle = -1.0
    bottom.throttle = -1.0

    grip_samples: list[float] = []
    spin_samples: list[float] = []
    try:
        # --- grip: equal throttle, zero spin, measure landing range ---
        for throttle in args.grip_throttles:
            input(f"\nEqual throttle {throttle:.2f} — Enter to spin up, then fire a ball.")
            top.throttle = throttle
            bottom.throttle = throttle
            range_m = float(input("Measured landing range (m)? "))
            top.throttle = bottom.throttle = -1.0
            rpm = throttle * args.max_wheel_rpm
            mean_surface = surface_speed_mps(rpm, args.wheel_diameter_m)
            ball_speed = speed_from_range(range_m, args.launch_angle_deg, args.launch_height_m)
            eta = grip_efficiency(ball_speed, mean_surface)
            grip_samples.append(eta)
            print(f"  ball {ball_speed:.2f} m/s / surface {mean_surface:.2f} m/s -> grip {eta:.3f}")

        # --- spin: throttle differential, measure spin if available ---
        t_top = args.spin_throttle + args.spin_diff / 2.0
        t_bottom = args.spin_throttle - args.spin_diff / 2.0
        input(f"\nSpin shot: top {t_top:.2f} / bottom {t_bottom:.2f} — Enter, then fire.")
        top.throttle, bottom.throttle = t_top, t_bottom
        raw = input("Measured spin (rad/s, blank to skip)? ").strip()
        top.throttle = bottom.throttle = -1.0
        if raw:
            diff_surface = surface_speed_mps(
                (t_top - t_bottom) * args.max_wheel_rpm, args.wheel_diameter_m
            )
            spin_samples.append(spin_efficiency(float(raw), diff_surface, args.ball_radius_m))
    finally:
        top.throttle = bottom.throttle = -1.0

    geometry = {
        "wheel_diameter_m": args.wheel_diameter_m,
        "ball_radius_m": args.ball_radius_m,
        "grip_efficiency": round(_mean(grip_samples), 4) if grip_samples else 0.85,
        "spin_efficiency": round(_mean(spin_samples), 4) if spin_samples else 0.85,
        "max_wheel_rpm": args.max_wheel_rpm,
    }
    args.out.write_text(json.dumps(geometry, indent=2))
    print(f"\n=== launch calibration ===\n{json.dumps(geometry, indent=2)}")
    print(f"\nWrote {args.out} — load with LaunchGeometry.model_validate_json(...).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
