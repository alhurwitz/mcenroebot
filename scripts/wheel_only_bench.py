"""Run from the Pi repository: uv run python /path/to/wheel_only_bench.py.

No feeder commands. Start with LiPo disconnected and an empty, guarded rig.
Individual wheel tests last one second; 'all' runs all wheels for five seconds.
Each run then disables all three wheel signals and exits. Restart to re-arm.
"""

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
        print("Enter channel and percent, e.g. 3 5. Allowed: channels 2/3/4, 1-8 percent.")
        print("Individual tests: 1 second, no balls. 'all 5': all wheels at 5% for 5 seconds.")
        print("For a launch: one ball through the guarded chute after the FEED message.")
        print("Ctrl+C interrupts a running test. q exits at the prompt.")
        print("Shutdown v2: each completed test switches OFF all wheel PWM and exits.")
        while True:
            raw = input("wheel> ").strip()
            if raw.lower() == "q":
                break
            try:
                ch_text, pct_text = raw.split()
                pct = float(pct_text)
                ch = None if ch_text.lower() == "all" else int(ch_text)
                if (ch is not None and ch not in CHANNELS) or not 1 <= pct <= 8:
                    raise ValueError
            except ValueError:
                print("Use 2, 3, 4 or all and a percent from 1 to 8; or q.")
                continue
            selected = escs if ch is None else [escs[CHANNELS.index(ch)]]
            for esc in selected:
                esc.throttle = -1.0 + 2.0 * pct / 100.0
            if ch is None:
                print("Spinning up all three wheels...", flush=True)
                time.sleep(2.0)
                print(
                    "FEED ONE BALL only if all three spin smoothly. Stopping in 3 seconds.",
                    flush=True,
                )
                time.sleep(3.0)
            else:
                time.sleep(1.0)
            # Minimum throttle did not stop one ESC on this rig. End the run
            # and cut pulses instead of leaving it armed at the next prompt.
            break
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
