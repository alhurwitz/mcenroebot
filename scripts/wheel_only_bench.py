"""Run from the Pi repository: uv run python /path/to/wheel_only_bench.py.

No feeder commands. Start with LiPo disconnected and an empty, guarded rig.
An optional third command value sets the run time from 1 to 30 seconds.
Without it, individual wheel tests last one second and 'all' lasts five seconds.
Each run returns to minimum throttle and keeps the command prompt open.
Typing q or pressing Ctrl+C disables all three wheel signals and exits.
"""

import math
import time

from mcenroebot.channel_map import (
    ESC_MAX_US,
    ESC_MIN_US,
    PCA9685_ADDRESS,
    PCA9685_FREQ_HZ,
)

# Bench wiring override: ch2 is a wheel ESC here, not the head-roll servo.
# Other robot scripts still use the canonical channel map.
CHANNELS = (2, 3, 4)


def main() -> int:
    from adafruit_servokit import ServoKit

    kit = ServoKit(channels=16, address=PCA9685_ADDRESS, frequency=PCA9685_FREQ_HZ)
    escs = []
    status = 0
    try:
        for channel in CHANNELS:
            esc = kit.continuous_servo[channel]
            escs.append(esc)
            esc.set_pulse_width_range(ESC_MIN_US, ESC_MAX_US)
            esc.throttle = -1.0
        input("Minimum pulses set. Connect LiPo, wait for arming tones, then Enter. ")
        print("Wheels must remain stopped. If one spins at idle, unplug LiPo and quit.")
        print("Enter channel, percent, and optional seconds, e.g. 3 5 10.")
        print("Allowed: channels 2/3/4, 1-8 percent, and 1-30 seconds.")
        print("Defaults: individual tests 1 second; 'all 5' runs for 5 seconds.")
        print("For a launch: one ball through the guarded chute after the FEED message.")
        print("Ctrl+C interrupts a running test. q exits at the prompt.")
        print("After each test: minimum throttle, then the wheel prompt stays open.")
        print("q or Ctrl+C switches OFF all three wheel PWM signals and exits.")
        while True:
            raw = input("wheel> ").strip()
            if raw.lower() == "q":
                break
            try:
                parts = raw.split()
                if len(parts) not in (2, 3):
                    raise ValueError
                ch_text, pct_text = parts[:2]
                pct = float(pct_text)
                ch = None if ch_text.lower() == "all" else int(ch_text)
                duration = float(parts[2]) if len(parts) == 3 else (5.0 if ch is None else 1.0)
                if (
                    (ch is not None and ch not in CHANNELS)
                    or not math.isfinite(pct)
                    or not 1 <= pct <= 8
                    or not math.isfinite(duration)
                    or not 1 <= duration <= 30
                ):
                    raise ValueError
            except (TypeError, ValueError):
                print("Use: 2|3|4|all PERCENT [SECONDS]; percent 1-8, seconds 1-30; or q.")
                continue
            selected = escs if ch is None else [escs[CHANNELS.index(ch)]]
            try:
                for esc in selected:
                    esc.throttle = -1.0 + 2.0 * pct / 100.0
                if ch is None:
                    print("Spinning up all three wheels...", flush=True)
                    spinup = min(2.0, duration)
                    time.sleep(spinup)
                    remaining = duration - spinup
                    if remaining > 0:
                        print(
                            "FEED ONE BALL only if all three spin smoothly. "
                            f"Stopping in {remaining:g} seconds.",
                            flush=True,
                        )
                        time.sleep(remaining)
                else:
                    time.sleep(duration)
            finally:
                for esc in selected:
                    esc.throttle = -1.0
            print("Back at minimum. Enter another test or q to switch PWM off and exit.")
    except (KeyboardInterrupt, EOFError):
        print("\nStopping.")
    except Exception as exc:
        status = 1
        print(f"Wheel test failed: {exc}. Disconnect LiPo.")
    finally:
        # Real motor library 3.4.20 rejects throttle=None. Its public fraction
        # property accepts None and writes duty_cycle=0 to the PWM output.
        # Do not delay shutdown or skip other channels when one write fails.
        for channel, esc in zip(CHANNELS, escs, strict=False):
            try:
                esc.fraction = None
                print(f"ch{channel}: PWM OFF written.", flush=True)
            except Exception as exc:
                status = 1
                print(f"ch{channel}: PWM-off failed: {exc}. Disconnect LiPo.", flush=True)
        print("Disconnect LiPo before touching wheels or wiring.")
        print("Signal-off is not proof of a stopped motor; confirm physically.")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
