"""Teach an ESC its throttle endpoints (min/max) — real-hardware runner.

Makes the ESC learn its 1000 us (min) and 2000 us (max) endpoints so the full
0-100% throttle range responds, instead of only spinning above ~80% (the symptom
of an ESC whose endpoints were never taught).

Why this is standalone (not EscCalibrator): entering an ESC's calibration mode
requires it to see MAX throttle *at the instant it powers on*. So the order must
be: stream max FIRST, then power on. EscCalibrator arms (min) before sending max,
which is the normal arming order, not the teach order — wrong for this job.

Uses the same ServoKit path as esc_bringup.py (known-good on this Pi).

Run ON THE PI, in the project env:

    uv run python -u scripts/esc_calibrate.py --channel 2

Run once PER ESC (--channel 3 top, --channel 4 bottom on the dual-wheel map).

PROCEDURE — the script tells you exactly when to plug/unplug the LiPo:
  1. START WITH THE LIPO UNPLUGGED. Press Enter.
  2. Script streams MAX throttle, then says "power ON now." Plug in the LiPo.
     The ESC boots seeing max -> enters calibration -> beeps to confirm MAX.
     Press Enter.
  3. Script drops to MIN. The ESC beeps to confirm MIN and stores the range.
     Press Enter.
  4. Done. The endpoints persist in the ESC across power cycles.

SAFETY: bare shaft, NO wheels, NO ball. Clamp the motor; it may spin at the max
step. Lift the red (+5V BEC) lead on the ESC connector; keep black (GND). Ctrl-C
drops to min throttle and exits.
"""

from __future__ import annotations

import argparse
import sys

from adafruit_servokit import ServoKit

# Channels/pulse range from the shared map; fall back to literals so a broken
# package import can never block a bench session.
try:
    from mcenroebot.channel_map import ESC_MAX_US, ESC_MIN_US, WHEEL_FRONT

    DEFAULT_CHANNEL = WHEEL_FRONT
    MIN_US = ESC_MIN_US
    MAX_US = ESC_MAX_US
except Exception:
    DEFAULT_CHANNEL = 3
    MIN_US = 1000
    MAX_US = 2000


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Teach an ESC its min/max throttle endpoints (real hardware)."
    )
    parser.add_argument(
        "--channel", type=int, default=DEFAULT_CHANNEL, help="PCA9685 channel (default: top wheel)"
    )
    args = parser.parse_args(argv)
    ch = args.channel

    kit = ServoKit(channels=16)
    servo = kit.continuous_servo[ch]
    servo.set_pulse_width_range(MIN_US, MAX_US)

    print(f"ESC endpoint calibration on PCA9685 channel {ch}.")
    print("Bare shaft only — no wheels, no ball.\n")

    try:
        input("Step 1: Make sure the LiPo is UNPLUGGED. Press Enter: ")

        # Stream MAX *before* power-on — this is what puts the ESC into teach mode.
        servo.throttle = 1.0
        print("  -> streaming MAX throttle.")
        input(
            "Step 2: Plug in the LiPo NOW. Wait for the ESC's max-confirm beeps, then press Enter: "
        )

        # Drop to MIN — the ESC records the span and stores it.
        servo.throttle = -1.0
        print("  -> streaming MIN throttle.")
        input("Step 3: Wait for the min-confirm beeps (endpoints stored), then press Enter: ")

        print("\nDone. Endpoints taught and stored in the ESC.")
        print("Re-run scripts/esc_bringup.py — it should now spin from low throttle.")
        return 0
    except KeyboardInterrupt:
        print("\nAborted.")
        return 1
    finally:
        servo.throttle = -1.0  # leave at min


if __name__ == "__main__":
    sys.exit(main())
