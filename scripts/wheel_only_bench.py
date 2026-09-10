"""Run from the Pi repository: uv run python /path/to/wheel_only_bench.py.

No feeder commands. Start with LiPo disconnected and an empty, guarded rig.
Each requested wheel pulse stops automatically after one second.
"""

import time

from mcenroebot.channel_map import (
    ESC_MAX_US,
    ESC_MIN_US,
    PCA9685_ADDRESS,
    PCA9685_FREQ_HZ,
    WHEEL_BOTTOM,
    WHEEL_TOP,
    WHEEL_TRI_BOTTOM,
)

CHANNELS = (WHEEL_TOP, WHEEL_BOTTOM, WHEEL_TRI_BOTTOM)


def main() -> None:
    from adafruit_servokit import ServoKit

    kit = ServoKit(channels=16, address=PCA9685_ADDRESS, frequency=PCA9685_FREQ_HZ)
    escs = []
    try:
        for ch in CHANNELS:
            esc = kit.continuous_servo[ch]
            escs.append(esc)
            esc.set_pulse_width_range(ESC_MIN_US, ESC_MAX_US)
            esc.throttle = -1.0
        input("Minimum pulses set. Connect LiPo, wait for arming tones, then Enter. ")
        print("Wheels must remain stopped. If one spins at idle, unplug LiPo and quit.")
        print("Enter channel and percent, e.g. 3 5. Allowed: channels 3/4/6, 1-8 percent.")
        print("Each test lasts 1 second. q or Ctrl+C stops and exits. No balls.")
        while True:
            raw = input("wheel> ").strip()
            if raw.lower() == "q":
                break
            try:
                ch_text, pct_text = raw.split()
                ch, pct = int(ch_text), float(pct_text)
                if ch not in CHANNELS or not 1 <= pct <= 8:
                    raise ValueError
            except ValueError:
                print("Use 3, 4 or 6 and a percent from 1 to 8; or q.")
                continue
            esc = escs[CHANNELS.index(ch)]
            try:
                esc.throttle = -1.0 + 2.0 * pct / 100.0
                time.sleep(1.0)
            finally:
                esc.throttle = -1.0
            print("Back at minimum. Confirm the wheel stops before another test.")
    except (KeyboardInterrupt, EOFError):
        print("\nStopping.")
    finally:
        # Attempt each stop even if one I2C write fails. Battery disconnect is
        # the physical stop if software or ESC behavior is faulty.
        for esc in escs:
            try:
                esc.throttle = -1.0
            except Exception as exc:
                print(f"Stop write failed: {exc}. Disconnect LiPo.")
        time.sleep(0.4)
        for esc in escs:
            try:
                esc.throttle = None
            except Exception as exc:
                print(f"PWM-off failed: {exc}. Disconnect LiPo.")
        print("Disconnect LiPo before touching wheels or wiring.")


if __name__ == "__main__":
    main()
