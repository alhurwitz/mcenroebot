"""Servo bring-up for the V4 aim + launch head.

Sweeps each positional servo through its range and parks them centered (90 deg),
so you can confirm all three move smoothly and find any mechanical end-stops.

    uv run python -u scripts/servo_test.py            # sweep all three, then center
    uv run python -u scripts/servo_test.py --center   # just center all (known home)
    uv run python -u scripts/servo_test.py --only pan  # sweep one (pan|tilt|roll)

Channels: pan=0, tilt=1, head-roll=2 (PCA9685 @ 0x40, 50 Hz). Wire all three
servo leads (signal + 5V + GND); power the rail from the HAT 5V PSU. These are
the servo channels only — do NOT have an ESC armed on ch3/ch4 elsewhere while
running this if they share the board.

Watch for: smooth full travel, and NO buzzing/grinding at the extremes (that
means the servo is fighting a mechanical limit — note the angle where it stalls).
"""

from __future__ import annotations

import argparse
import sys
import time

from adafruit_servokit import ServoKit

# Channels from the shared map; fall back to literals so a broken package import
# can never block a bench session.
try:
    from mcenroebot.channel_map import HEAD_ROLL, PAN, TILT
except Exception:
    PAN, TILT, HEAD_ROLL = 0, 1, 2

CENTER_DEG = 90.0
SWEEP_STEP = 10
SWEEP_DT = 0.05

_SERVOS = {"pan": PAN, "tilt": TILT, "roll": HEAD_ROLL}

kit = ServoKit(channels=16)


def sweep(name: str, channel: int) -> None:
    """Sweep one servo 0 -> 180 -> 0, then leave it centered."""
    print(f"{name} (ch{channel}): sweeping...")
    for angle in range(0, 181, SWEEP_STEP):
        kit.servo[channel].angle = angle
        time.sleep(SWEEP_DT)
    for angle in range(180, -1, -SWEEP_STEP):
        kit.servo[channel].angle = angle
        time.sleep(SWEEP_DT)
    kit.servo[channel].angle = CENTER_DEG


def center_all() -> None:
    """Park all three servos at center (90 deg) — the known home pose."""
    print("Centering all servos to 90 deg...")
    for name, channel in _SERVOS.items():
        kit.servo[channel].angle = CENTER_DEG
        print(f"  {name} (ch{channel}) -> {CENTER_DEG:.0f} deg")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sweep / center the V4 head servos.")
    parser.add_argument("--center", action="store_true", help="only center all servos, no sweep")
    parser.add_argument(
        "--only", choices=sorted(_SERVOS), help="sweep just one servo (pan|tilt|roll)"
    )
    args = parser.parse_args(argv)

    try:
        if args.center:
            center_all()
        elif args.only:
            sweep(args.only, _SERVOS[args.only])
        else:
            for name, channel in _SERVOS.items():
                sweep(name, channel)
            center_all()
        print("Done!")
        return 0
    except KeyboardInterrupt:
        print("\nAborted.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
