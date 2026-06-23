"""Low-throttle spin test for the BLDC on PCA9685 channel 2.

Arms, then ramps to a LOW throttle, holds briefly, then returns to minimum.
Keep the throttle ceiling low for the first test.

    uv run python esc_spin_test.py

SAFETY: the swing arm WILL move. Clear the full arc of the paddle AND the
counterweight. Secure the base. Stand out of the swing plane. Ctrl+C aborts
to minimum throttle.
"""

import time

from adafruit_servokit import ServoKit

ESC_CHANNEL = 2
MIN_US = 1000
MAX_US = 2000

# Keep this LOW for the first test. throttle is -1.0 (min) .. +1.0 (max).
# -0.8 is just above minimum — a gentle nudge.
TEST_THROTTLE = -0.4
HOLD_SECONDS = 1.0

kit = ServoKit(channels=16)
kit.continuous_servo[ESC_CHANNEL].set_pulse_width_range(MIN_US, MAX_US)

print("Arming (minimum throttle)...")
kit.continuous_servo[ESC_CHANNEL].throttle = -1.0
time.sleep(2.0)  # let the ESC arm / confirm

try:
    print(f"Ramping to low throttle ({TEST_THROTTLE})...")
    kit.continuous_servo[ESC_CHANNEL].throttle = TEST_THROTTLE
    time.sleep(HOLD_SECONDS)
    print("Returning to minimum throttle.")
    kit.continuous_servo[ESC_CHANNEL].throttle = -1.0
    print("Done.")
except KeyboardInterrupt:
    print("\nAbort — minimum throttle.")
    kit.continuous_servo[ESC_CHANNEL].throttle = -1.0
