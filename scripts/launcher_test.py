#!/usr/bin/env python3

import curses
import time

import board
import busio
from adafruit_pca9685 import PCA9685

# ============================================================
# CONFIG
# ============================================================

PCA_ADDRESS = 0x40
PWM_FREQUENCY = 50

# PCA9685 channels connected to ESC signal wires
WHEEL_CHANNELS = [0, 1, 2]

# Typical RC ESC pulse range
ESC_MIN_US = 1000
ESC_MAX_US = 2000

# Starting test settings
START_THROTTLE = 25  # %
START_PULSE_MS = 250  # milliseconds

THROTTLE_STEP = 5  # %
PULSE_STEP_MS = 25  # ms

# Don't accidentally go crazy during initial testing.
MAX_TEST_THROTTLE = 70  # %

# ESC arming time at minimum throttle
ARM_SECONDS = 3


# ============================================================
# PCA9685 / ESC
# ============================================================

i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c, address=PCA_ADDRESS)
pca.frequency = PWM_FREQUENCY


def microseconds_to_duty(us: float) -> int:
    """
    Convert an RC servo/ESC pulse width in microseconds
    to PCA9685's 16-bit duty cycle.
    """

    period_us = 1_000_000 / PWM_FREQUENCY
    duty = int((us / period_us) * 65535)

    return max(0, min(65535, duty))


def set_esc_us(channel: int, pulse_us: float):
    pca.channels[channel].duty_cycle = microseconds_to_duty(pulse_us)


def throttle_to_us(percent: float) -> float:
    """
    0% -> ESC_MIN_US
    100% -> ESC_MAX_US
    """

    percent = max(0, min(100, percent))

    return ESC_MIN_US + ((ESC_MAX_US - ESC_MIN_US) * percent / 100)


def wheel_stop(wheel_index: int):
    channel = WHEEL_CHANNELS[wheel_index]
    set_esc_us(channel, ESC_MIN_US)


def wheel_run(wheel_index: int, throttle: float):
    channel = WHEEL_CHANNELS[wheel_index]
    set_esc_us(channel, throttle_to_us(throttle))


def stop_all():
    for i in range(3):
        wheel_stop(i)


def arm_escs():
    """
    Standard ESC arming:
    send minimum throttle for several seconds.
    """

    stop_all()
    time.sleep(ARM_SECONDS)


# ============================================================
# TUI
# ============================================================


def draw_screen(
    stdscr,
    throttle,
    pulse_ms,
    running,
    stats,
    last_action,
):
    stdscr.erase()

    height, width = stdscr.getmaxyx()

    def line(y, text):
        if y < height:
            stdscr.addstr(y, 2, text[: max(0, width - 4)])

    line(1, "McEnroeBot — Launcher Bench Test")
    line(2, "=" * 45)

    line(4, f"Throttle:       {throttle:3d}%")
    line(5, f"Pulse duration: {pulse_ms:4d} ms")

    line(7, "WHEELS")

    for i in range(3):
        status = "RUNNING" if running[i] else "STOPPED"
        line(8 + i, f"  Wheel {i + 1}: {status}")

    line(12, "CONTROLS")
    line(13, "  1 / 2 / 3    Toggle continuous wheel")
    line(14, "  A / S / D    Pulse wheel 1 / 2 / 3")
    line(15, "  SPACE        Pulse ALL wheels")
    line(16, "  + / -        Increase/decrease throttle")
    line(17, "  ] / [        Increase/decrease pulse time")
    line(18, "  X            EMERGENCY STOP")
    line(19, "  Q            Quit")

    line(21, "TEST RESULT")
    line(22, "  G = good single ball")
    line(23, "  B = double feed")
    line(24, "  J = jam")
    line(25, "  N = no launch")

    total = sum(stats.values())

    line(27, "RESULTS")
    line(28, f"  Single ball: {stats['good']}")
    line(29, f"  Double feed: {stats['double']}")
    line(30, f"  Jam:         {stats['jam']}")
    line(31, f"  No launch:   {stats['none']}")
    line(32, f"  Total tests: {total}")

    if total:
        success = stats["good"] / total * 100
        line(33, f"  Success:     {success:.1f}%")

    line(35, f"Last action: {last_action}")

    stdscr.refresh()


def restore_running_state(running, throttle):
    """
    After a pulse, return each wheel to its
    previous continuous-running state.
    """

    for i in range(3):
        if running[i]:
            wheel_run(i, throttle)
        else:
            wheel_stop(i)


def pulse_wheels(indices, throttle, pulse_ms, running):
    """
    Temporarily run selected wheels.

    Any wheels that were already continuously running
    remain running afterward.
    """

    # Start requested wheels
    for i in indices:
        wheel_run(i, throttle)

    time.sleep(pulse_ms / 1000.0)

    # Restore prior state
    restore_running_state(running, throttle)


def main(stdscr):

    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)

    throttle = START_THROTTLE
    pulse_ms = START_PULSE_MS

    running = [False, False, False]

    stats = {
        "good": 0,
        "double": 0,
        "jam": 0,
        "none": 0,
    }

    last_action = "ESCs armed — ready"

    draw_screen(stdscr, throttle, pulse_ms, running, stats, "Arming ESCs...")

    arm_escs()

    while True:
        draw_screen(
            stdscr,
            throttle,
            pulse_ms,
            running,
            stats,
            last_action,
        )

        key = stdscr.getch()

        # ----------------------------------------------------
        # QUIT
        # ----------------------------------------------------

        if key in (ord("q"), ord("Q")):
            stop_all()
            break

        # ----------------------------------------------------
        # EMERGENCY STOP
        # ----------------------------------------------------

        elif key in (ord("x"), ord("X")):
            stop_all()

            running = [False, False, False]

            last_action = "EMERGENCY STOP"

        # ----------------------------------------------------
        # THROTTLE
        # ----------------------------------------------------

        elif key in (ord("+"), ord("=")):
            throttle = min(MAX_TEST_THROTTLE, throttle + THROTTLE_STEP)

            # Update continuously running wheels
            restore_running_state(running, throttle)

            last_action = f"Throttle -> {throttle}%"

        elif key == ord("-"):
            throttle = max(0, throttle - THROTTLE_STEP)

            restore_running_state(running, throttle)

            last_action = f"Throttle -> {throttle}%"

        # ----------------------------------------------------
        # PULSE TIME
        # ----------------------------------------------------

        elif key == ord("]"):
            pulse_ms += PULSE_STEP_MS

            last_action = f"Pulse -> {pulse_ms} ms"

        elif key == ord("["):
            pulse_ms = max(PULSE_STEP_MS, pulse_ms - PULSE_STEP_MS)

            last_action = f"Pulse -> {pulse_ms} ms"

        # ----------------------------------------------------
        # CONTINUOUS WHEELS
        # ----------------------------------------------------

        elif key == ord("1"):
            running[0] = not running[0]

            if running[0]:
                wheel_run(0, throttle)
            else:
                wheel_stop(0)

            last_action = f"Wheel 1 {'ON' if running[0] else 'OFF'}"

        elif key == ord("2"):
            running[1] = not running[1]

            if running[1]:
                wheel_run(1, throttle)
            else:
                wheel_stop(1)

            last_action = f"Wheel 2 {'ON' if running[1] else 'OFF'}"

        elif key == ord("3"):
            running[2] = not running[2]

            if running[2]:
                wheel_run(2, throttle)
            else:
                wheel_stop(2)

            last_action = f"Wheel 3 {'ON' if running[2] else 'OFF'}"

        # ----------------------------------------------------
        # INDIVIDUAL PULSES
        # ----------------------------------------------------

        elif key in (ord("a"), ord("A")):
            pulse_wheels([0], throttle, pulse_ms, running)

            last_action = f"Pulsed Wheel 1 @ {throttle}% for {pulse_ms} ms"

        elif key in (ord("s"), ord("S")):
            pulse_wheels([1], throttle, pulse_ms, running)

            last_action = f"Pulsed Wheel 2 @ {throttle}% for {pulse_ms} ms"

        elif key in (ord("d"), ord("D")):
            pulse_wheels([2], throttle, pulse_ms, running)

            last_action = f"Pulsed Wheel 3 @ {throttle}% for {pulse_ms} ms"

        # ----------------------------------------------------
        # ALL-WHEEL PULSE
        # ----------------------------------------------------

        elif key == ord(" "):
            pulse_wheels([0, 1, 2], throttle, pulse_ms, running)

            last_action = f"Pulsed ALL @ {throttle}% for {pulse_ms} ms"

        # ----------------------------------------------------
        # RESULTS
        # ----------------------------------------------------

        elif key in (ord("g"), ord("G")):
            stats["good"] += 1
            last_action = "Recorded: GOOD single-ball launch"

        elif key in (ord("b"), ord("B")):
            stats["double"] += 1
            last_action = "Recorded: DOUBLE FEED"

        elif key in (ord("j"), ord("J")):
            stats["jam"] += 1
            last_action = "Recorded: JAM"

        elif key in (ord("n"), ord("N")):
            stats["none"] += 1
            last_action = "Recorded: NO LAUNCH"


if __name__ == "__main__":
    try:
        curses.wrapper(main)

    finally:
        # Always send minimum throttle if program crashes/exits
        stop_all()
        pca.deinit()
