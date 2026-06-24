#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "adafruit-blinka>=9.1.0",
#     "adafruit-circuitpython-servokit>=1.3.24",
# ]
# ///
"""Calibrate the escapement feed rate <-> CR-servo throttle factor.

Run ON THE PI (needs the ``pi`` extra / Adafruit libs):

    uv run scripts/calibrate_feeder.py --channel 5 --seconds 60

For each throttle in the sweep the script spins the continuous-rotation
escapement servo for ``--seconds`` while you **count the balls it drops**,
then enter the count. From the (throttle, balls-per-minute) samples it fits
the linear factor used by ``mcenroebot.drivers.feeder.Pca9685FeederDriver``:

    throttle = balls_per_min * throttle_per_bpm

Paste the printed ``throttle_per_bpm`` into the driver (or pass it to its
constructor). Fill the hopper before each run so the feed isn't starved.

SAFETY: keep fingers clear of the escapement disk and launch throat.
"""

from __future__ import annotations

import argparse
import sys

from adafruit_servokit import ServoKit


def fit_throttle_per_bpm(samples: list[tuple[float, float]]) -> float:
    """Least-squares slope through the origin for (balls_per_min, throttle).

    Returns ``throttle_per_bpm = sum(bpm*throttle) / sum(bpm^2)``. Samples
    with ``bpm == 0`` contribute nothing. Raises ``ValueError`` if no sample
    has a positive feed rate.
    """
    num = sum(bpm * throttle for bpm, throttle in samples)
    den = sum(bpm * bpm for bpm, _ in samples)
    if den <= 0.0:
        raise ValueError("need at least one sample with balls_per_min > 0")
    return num / den


def _sweep(channel: int, seconds: float, throttles: list[float]) -> list[tuple[float, float]]:
    import time

    kit = ServoKit(channels=16)
    samples: list[tuple[float, float]] = []
    try:
        for throttle in throttles:
            input(f"\nReady to run throttle={throttle:.2f} for {seconds:.0f}s — press Enter.")
            kit.continuous_servo[channel].throttle = throttle
            time.sleep(seconds)
            kit.continuous_servo[channel].throttle = 0.0
            count = float(input("How many balls dropped? "))
            bpm = count * 60.0 / seconds
            samples.append((bpm, throttle))
            print(f"  -> {bpm:.1f} balls/min at throttle {throttle:.2f}")
    finally:
        kit.continuous_servo[channel].throttle = 0.0
    return samples


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", type=int, default=5, help="PCA9685 CR-servo channel")
    parser.add_argument("--seconds", type=float, default=60.0, help="run time per throttle")
    parser.add_argument(
        "--throttles",
        type=float,
        nargs="+",
        default=[0.2, 0.4, 0.6, 0.8, 1.0],
        help="throttle values to sweep (continuous-servo units, 0..1)",
    )
    args = parser.parse_args(argv)

    samples = _sweep(args.channel, args.seconds, args.throttles)
    factor = fit_throttle_per_bpm(samples)
    print("\n=== feeder calibration ===")
    for bpm, throttle in samples:
        print(f"  {bpm:7.1f} balls/min -> throttle {throttle:.2f}")
    print(f"\nthrottle_per_bpm = {factor:.6f}")
    print("Pass this to Pca9685FeederDriver(channel=..., throttle_per_bpm=<value>).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
