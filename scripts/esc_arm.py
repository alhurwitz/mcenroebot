"""Arm the BLDC ESC on PCA9685 channel 2 — minimum throttle only.

This sends the minimum-throttle (arming) signal and holds it. It does NOT
spin the motor up. Listen for the ESC's arm-confirmation beeps.

    uv run python esc_arm.py

Ctrl+C to stop. On exit it leaves the channel at minimum throttle.

SAFETY: the swing arm CAN move. Clear the swing path before running.
Keep hands and everything else out of the paddle's arc.
"""

import time

from adafruit_servokit import ServoKit

ESC_CHANNEL = 2
# Standard unidirectional ESC pulse range (microseconds).
MIN_US = 1000
MAX_US = 2000

kit = ServoKit(channels=16)
kit.continuous_servo[ESC_CHANNEL].set_pulse_width_range(MIN_US, MAX_US)

print("Sending minimum throttle (arming signal) on channel 2...")
# throttle = -1.0 -> MIN_US pulse = minimum throttle = arm
kit.continuous_servo[ESC_CHANNEL].throttle = -1.0

try:
    print("Holding minimum throttle. Listen for arm-confirmation beeps.")
    print("Motor should NOT spin. Ctrl+C to stop.")
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nStopping — leaving channel at minimum throttle.")
    kit.continuous_servo[ESC_CHANNEL].throttle = -1.0
