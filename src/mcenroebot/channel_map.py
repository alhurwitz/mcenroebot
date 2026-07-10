"""Hardware channel + pin map — single source of truth for the V4 feeder.

Every script and driver should import channel/pin numbers from here instead of
hardcoding them, so the wiring is defined in exactly one place.

PCA9685 @ 0x40 (50 Hz — shared by all servos AND the wheel ESCs)
    ch0  PAN          MG996R positional servo      (aim, yaw about Z)
    ch1  TILT         MG996R positional servo      (aim, ballistic elevation)
    ch2  HEAD_ROLL    MG996R positional servo      (launch head, spin axis)
    ch3  WHEEL_TOP     A2212 + 30A ESC              (launch, continuous_servo)
    ch4  WHEEL_BOTTOM  A2212 + 30A ESC              (launch, continuous_servo)
    ch5  FEED_SERVO   MG996R positional servo      (feed airlock, LOAD/DISCH rock)
    ch6  WHEEL_TRI_BOTTOM  A2212 + 30A ESC         (launch, continuous_servo; v4 tri)

Pi GPIO (BCM) — everything that can't share the 50 Hz board
    AUGER_PWM_GPIO    hardware-PWM pin -> L298N ENA (auger speed). The auger
                      cannot live on the PCA9685: its driver wants ~1 kHz, but
                      PCA9685 frequency is board-wide and the servos/ESCs need
                      50 Hz. With a single PCA9685, the auger PWM goes here.
    HOPPER_SENSOR_GPIO endstop input, optional (gates the auger).

L298N direction pins (IN1/IN2) are hardwired for single-direction lift
(IN1 -> +5V, IN2 -> GND), so they are not software-controlled and not listed.
"""

from __future__ import annotations

__all__ = [
    "AUGER_PWM_GPIO",
    "AUGER_PWM_HZ",
    "ESC_MAX_US",
    "ESC_MIN_US",
    "FEED_MAX_US",
    "FEED_MIN_US",
    "FEED_SERVO",
    "HEAD_ROLL",
    "HOPPER_SENSOR_GPIO",
    "PAN",
    "PCA9685_ADDRESS",
    "PCA9685_FREQ_HZ",
    "TILT",
    "WHEEL_BOTTOM",
    "WHEEL_TOP",
    "WHEEL_TRI_BOTTOM",
]

# --- PCA9685 board (servos + ESCs share this one at 50 Hz) ---
PCA9685_ADDRESS = 0x40
PCA9685_FREQ_HZ = 50

# Positional servos (.angle, 0-180)
PAN = 0
TILT = 1
HEAD_ROLL = 2

# Launch-wheel ESCs (.throttle via continuous_servo, 0-1). The wheel pair is
# stacked vertically: ball drops into the nip, top/bottom rpm split sets spin.
WHEEL_TOP = 3
WHEEL_BOTTOM = 4

# Third launch wheel for the v4 tri bracket (bottom + upper pair at 120 deg,
# launcher_bracket_v4_tri, ESC in hand 2026-07-10). In the tri config the two
# original ESC channels (WHEEL_TOP/WHEEL_BOTTOM above — names kept, do NOT
# rename) drive the UPPER PAIR, and this channel drives the wheel under the
# ball path. Upper-pair-faster = topspin; tri-bottom-faster = backspin.
WHEEL_TRI_BOTTOM = 6

# Feed airlock metering servo (MG996R positional, .angle 0-180).
# Replaced the abandoned continuous-rotation escapement (2026-07-04): it holds
# two angles ~70 deg apart (LOAD/DISCHARGE, found empirically on the bench with
# scripts/feed_meter.py) instead of spinning a pocket disk.
FEED_SERVO = 5

# Standard unidirectional ESC pulse range (microseconds).
ESC_MIN_US = 1000
ESC_MAX_US = 2000

# MG996R feed-servo pulse range (microseconds) for the full 0-180 deg sweep.
FEED_MIN_US = 500
FEED_MAX_US = 2500

# --- Pi GPIO (BCM numbering) ---
# Auger lift: Pi hardware-PWM pin into the L298N ENA. GPIO12/13/18/19 are the
# Pi 5 hardware-PWM-capable pins; 18 is the conventional choice.
AUGER_PWM_GPIO = 18
AUGER_PWM_HZ = 1000

# Optional hopper-full endstop input.
HOPPER_SENSOR_GPIO = 23
