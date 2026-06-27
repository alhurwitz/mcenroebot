"""Dual-ESC bring-up for the V4 two-wheel launcher.

Arms BOTH launch-wheel ESCs, then lets you throttle each wheel independently
so you can verify:

  1. Both ESCs arm (listen for the arm-confirmation beeps).
  2. Each wheel spins up on its own, throttle is independent.
  3. The wheels COUNTER-ROTATE (top surface and bottom surface both move
     toward the throat exit). If a wheel spins the wrong way, swap any two
     of its three motor leads — do NOT try to fix direction in software,
     these are unidirectional ESCs.

    uv run python esc_bringup.py

WIRING NOTES
  - Top wheel ESC signal    -> PCA9685 channel 3
  - Bottom wheel ESC signal -> PCA9685 channel 4
  - Both ESC power (XT60) -> 3S LiPo via a Y-harness.
  - Lift the red (+5V BEC) wire on BOTH ESC servo connectors; power the
    PCA9685 servo rail from the HAT 5V/3A PSU. Keep the black (GND) wire
    connected on both so the PWM signal shares a ground reference.

SAFETY
  - Spinning launch wheels fling balls hard and will hurt fingers. Clear the
    throat, keep hands clear, and run the first time with NO ball loaded.
  - Throttle is capped at MAX_BRINGUP_THROTTLE so a bare-shaft test can't
    redline. Raise it deliberately once you trust the setup.
  - On exit, both channels are returned to minimum throttle.
"""

import time

from adafruit_servokit import ServoKit

# Channels come from the shared map; fall back to literals so a broken package
# import can never block a bench session.
try:
    from mcenroebot.channel_map import ESC_MAX_US, ESC_MIN_US, WHEEL_BOTTOM, WHEEL_TOP

    TOP_CHANNEL = WHEEL_TOP
    BOTTOM_CHANNEL = WHEEL_BOTTOM
    MIN_US = ESC_MIN_US
    MAX_US = ESC_MAX_US
except Exception:
    TOP_CHANNEL = 3
    BOTTOM_CHANNEL = 4
    MIN_US = 1000
    MAX_US = 2000

# Bench-test safety cap. throttle is 0.0..1.0 of the usable range above arm.
# 0.35 is plenty to confirm spin/direction without flinging anything.
MAX_BRINGUP_THROTTLE = 0.35

# Gentle ramp so the ESC never sees a throttle step it reads as noise.
RAMP_STEP = 0.02
RAMP_DT = 0.03

kit = ServoKit(channels=16)
for ch in (TOP_CHANNEL, BOTTOM_CHANNEL):
    kit.continuous_servo[ch].set_pulse_width_range(MIN_US, MAX_US)

# Track commanded throttle per channel as 0.0..1.0 (0 = armed/idle, 1 = cap).
_state = {TOP_CHANNEL: 0.0, BOTTOM_CHANNEL: 0.0}


def _apply(channel: int, frac: float) -> None:
    """Set a channel to `frac` (0..1) of the bring-up range. -1.0 = arm/idle."""
    frac = max(0.0, min(1.0, frac))
    _state[channel] = frac
    # Map 0..1 of the *capped* range onto the ESC's -1..+1 throttle.
    throttle = -1.0 + 2.0 * (frac * MAX_BRINGUP_THROTTLE)
    kit.continuous_servo[channel].throttle = throttle


def _ramp(channel: int, target: float) -> None:
    """Ramp a channel from its current frac to `target` (0..1) gently."""
    target = max(0.0, min(1.0, target))
    current = _state[channel]
    step = RAMP_STEP if target >= current else -RAMP_STEP
    while abs(current - target) > 1e-6:
        current += step
        if (step > 0 and current > target) or (step < 0 and current < target):
            current = target
        _apply(channel, current)
        time.sleep(RAMP_DT)


def _idle_both() -> None:
    _apply(TOP_CHANNEL, 0.0)
    _apply(BOTTOM_CHANNEL, 0.0)


def arm() -> None:
    print("Arming both ESCs (minimum throttle)...")
    kit.continuous_servo[TOP_CHANNEL].throttle = -1.0
    kit.continuous_servo[BOTTOM_CHANNEL].throttle = -1.0
    _state[TOP_CHANNEL] = 0.0
    _state[BOTTOM_CHANNEL] = 0.0
    print("Listen for arm-confirmation beeps. Motors should NOT spin.")
    print("Waiting 3s for both ESCs to arm...")
    time.sleep(3.0)
    print("Armed.\n")


HELP = """\
Commands:
  t <0-100>   set TOP wheel throttle (percent of bench-test cap)
  b <0-100>   set BOTTOM wheel throttle (percent of bench-test cap)
  both <0-100> set both wheels together
  stop        ramp both wheels back to idle
  status      print current throttle on each channel
  help        show this
  q           idle both and quit
"""


def _parse_pct(arg: str) -> float | None:
    try:
        pct = float(arg)
    except ValueError:
        return None
    if not 0.0 <= pct <= 100.0:
        return None
    return pct / 100.0


def main() -> None:
    arm()
    print(HELP)
    print(f"(throttle cap = {int(MAX_BRINGUP_THROTTLE * 100)}% of full ESC range)\n")
    try:
        while True:
            raw = input("launcher> ").strip().split()
            if not raw:
                continue
            cmd = raw[0].lower()

            if cmd == "q":
                break
            if cmd in ("help", "h", "?"):
                print(HELP)
                continue
            if cmd == "status":
                print(
                    f"  top    = {_state[TOP_CHANNEL] * 100:5.1f}%  "
                    f"bottom = {_state[BOTTOM_CHANNEL] * 100:5.1f}%  "
                    "(of bench cap)"
                )
                continue
            if cmd == "stop":
                _ramp(TOP_CHANNEL, 0.0)
                _ramp(BOTTOM_CHANNEL, 0.0)
                print("  both idle.")
                continue

            if cmd in ("t", "b", "both"):
                if len(raw) < 2:
                    print("  need a value, e.g. 't 30'")
                    continue
                frac = _parse_pct(raw[1])
                if frac is None:
                    print("  value must be 0-100")
                    continue
                if cmd == "t":
                    _ramp(TOP_CHANNEL, frac)
                    print(f"  top -> {frac * 100:.0f}%")
                elif cmd == "b":
                    _ramp(BOTTOM_CHANNEL, frac)
                    print(f"  bottom -> {frac * 100:.0f}%")
                else:
                    _ramp(TOP_CHANNEL, frac)
                    _ramp(BOTTOM_CHANNEL, frac)
                    print(f"  both -> {frac * 100:.0f}%")
                continue

            print("  unknown command. type 'help'.")
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        print("Returning both channels to minimum throttle.")
        _idle_both()


if __name__ == "__main__":
    main()
