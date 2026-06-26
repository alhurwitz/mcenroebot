"""Teach an ESC its throttle endpoints (min/max) — real-hardware runner.

Drives ``mcenroebot.calibrate.EscCalibrator`` against a real ``PCA9685BLDCDriver``
so the ESC learns its 1000 us (min) and 2000 us (max) endpoints. After this the
full 0-100% throttle range responds — this is the fix for the "only spins above
~80% throttle" symptom, which is an ESC whose endpoints were never taught.

The package only ships a *mock*-driven demo (``python -m mcenroebot.calibrate``);
this is the missing real-hardware entry point.

Run ON THE PI (needs ``uv sync --extra pi``), inside the project env:

    uv run python scripts/esc_calibrate.py --channel 2

Run once PER ESC. For the dual-wheel channel map that's:

    uv run python scripts/esc_calibrate.py --channel 3   # top wheel
    uv run python scripts/esc_calibrate.py --channel 4   # bottom wheel

PROCEDURE (the script prompts you through each step):
  1. Power OFF the ESC (unplug the LiPo). Press Enter.
  2. Script sends MAX throttle, then asks you to power ON the ESC. Plug in the
     LiPo now — the ESC reads max throttle and beeps (it has learned max).
     Press Enter once you hear the beeps.
  3. Script drops to MIN throttle — the ESC beeps to confirm (learns min and
     stores the calibration). Press Enter.
  4. Done. Endpoints are stored in the ESC's own memory and persist across
     power cycles. Re-run only if you swap ESCs.

SAFETY
  - Bare shaft: NO wheels, NO ball. The motor will beep/twitch and may spin
    briefly at the max step. Clamp the motor down; keep fingers clear.
  - On the ESC servo connector, lift the red (+5V BEC) lead; keep black (GND)
    connected. Power the PCA9685 rail from the HAT 5V PSU.
  - Ctrl-C aborts; the driver is disarmed on exit (try/finally in EscCalibrator).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from mcenroebot.calibrate.esc import EscCalibrator
from mcenroebot.clock import SystemClock
from mcenroebot.drivers import PCA9685BLDCDriver


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Teach an ESC its min/max throttle endpoints (real hardware)."
    )
    parser.add_argument(
        "--channel",
        type=int,
        default=2,
        help="PCA9685 channel the ESC signal is wired to (default: 2)",
    )
    parser.add_argument(
        "--i2c-address",
        type=lambda x: int(x, 0),
        default=0x40,
        help="PCA9685 I2C address (default: 0x40)",
    )
    args = parser.parse_args(argv)

    print(
        f"ESC endpoint calibration on PCA9685 channel {args.channel} "
        f"(I2C {hex(args.i2c_address)})."
    )
    print("Bare shaft only — no wheels, no ball. Follow the prompts.\n")

    driver = PCA9685BLDCDriver(channel=args.channel, i2c_address=args.i2c_address)
    calibrator = EscCalibrator(driver=driver, clock=SystemClock())

    try:
        asyncio.run(calibrator.run())
    except KeyboardInterrupt:
        print("\nAborted — ESC disarmed.")
        return 1

    print(
        "\nEndpoints taught. Re-run scripts/esc_bringup.py — the throttle range "
        "should now respond from low values instead of only above ~80%."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
