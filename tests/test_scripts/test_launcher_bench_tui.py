"""Exercise timing, stop behavior, and cleanup without powering the launcher."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def bench_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "launcher_test.py"
    assert path.exists(), "The launcher bench script has not been added yet"
    spec = importlib.util.spec_from_file_location("launcher_bench_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PWM:
    def __init__(self):
        self.values = []
        self.fail = False

    @property
    def duty_cycle(self):
        return self.values[-1]

    @duty_cycle.setter
    def duty_cycle(self, value):
        if self.fail:
            raise OSError("injected write failure")
        self.values.append(value)


@pytest.fixture
def hardware(bench_module, monkeypatch):
    outputs = [PWM() for _ in range(16)]
    released = []
    pca = SimpleNamespace(channels=outputs, deinit=lambda: released.append("pca"))
    bus = SimpleNamespace(deinit=lambda: released.append("bus"))
    monkeypatch.setitem(sys.modules, "board", SimpleNamespace(SCL=1, SDA=2))
    monkeypatch.setitem(sys.modules, "busio", SimpleNamespace(I2C=lambda *args: bus))
    monkeypatch.setitem(
        sys.modules, "adafruit_pca9685", SimpleNamespace(PCA9685=lambda *a, **kw: pca)
    )
    rig = bench_module.WheelRig((2, 3, 4))
    rig.connect()
    return rig, outputs, released


@pytest.fixture
def control(bench_module, hardware):
    rig, outputs, _ = hardware
    now = [10.0]
    controller = bench_module.LauncherBench(rig, clock=lambda: now[0])
    return controller, outputs, now


def arm(controller, now):
    controller.handle_key(10)
    now[0] += 3.0
    controller.tick()


def duties(outputs):
    return [outputs[ch].duty_cycle for ch in (2, 3, 4)]


def test_no_motion_until_full_arming_interval(control):
    controller, outputs, now = control
    for key in "1asd ":
        controller.handle_key(ord(key))
    assert duties(outputs) == [0, 0, 0]
    controller.handle_key(10)
    controller.handle_key(ord("1"))
    now[0] += 2.99
    controller.tick()
    assert not controller.armed
    assert duties(outputs) == [3276, 3276, 3276]
    now[0] += 0.02
    controller.tick()
    assert controller.armed
    controller.handle_key(ord("1"))
    assert duties(outputs) == [3440, 3276, 3276]


def test_two_continuous_wheels_survive_third_wheel_pulse(control):
    controller, outputs, now = control
    arm(controller, now)
    for key in "12D":
        controller.handle_key(ord(key))
    assert duties(outputs) == [3440, 3440, 3440]
    now[0] += 0.249
    controller.tick()
    assert duties(outputs) == [3440, 3440, 3440]
    now[0] += 0.002
    controller.tick()
    assert duties(outputs) == [3440, 3440, 3276]


@pytest.mark.parametrize(
    "key,expected",
    [
        ("a", [3440, 3276, 3276]),
        ("S", [3276, 3440, 3276]),
        ("d", [3276, 3276, 3440]),
        (" ", [3440, 3440, 3440]),
    ],
)
def test_each_pulse_stops_on_its_deadline(control, key, expected):
    controller, outputs, now = control
    arm(controller, now)
    controller.handle_key(ord(key))
    assert duties(outputs) == expected
    now[0] += 0.251
    controller.tick()
    assert duties(outputs) == [3276, 3276, 3276]


def test_emergency_stop_cancels_pulses_and_requires_rearming(control):
    controller, outputs, now = control
    arm(controller, now)
    controller.handle_key(ord("1"))
    controller.handle_key(ord(" "))
    controller.handle_key(ord("X"))
    assert duties(outputs) == [0, 0, 0]
    assert not controller.armed
    for key in "123asd ":
        controller.handle_key(ord(key))
    now[0] += 10.0
    controller.tick()
    assert duties(outputs) == [0, 0, 0]
    arm(controller, now)
    assert duties(outputs) == [3276, 3276, 3276]


def test_stop_during_arming_never_becomes_armed(control):
    controller, outputs, now = control
    controller.handle_key(10)
    controller.handle_key(ord("x"))
    now[0] += 4.0
    controller.tick()
    assert not controller.armed
    assert duties(outputs) == [0, 0, 0]


def test_live_settings_are_bounded_and_do_not_extend_active_pulse(control):
    controller, outputs, now = control
    arm(controller, now)
    controller.handle_key(ord("1"))
    controller.handle_key(ord("d"))
    for key in "+]]":
        controller.handle_key(ord(key))
    assert controller.throttle == 6
    assert controller.pulse_ms == 300
    assert duties(outputs) == [3473, 3276, 3473]
    now[0] += 0.251
    controller.tick()
    assert duties(outputs) == [3473, 3276, 3276]
    for _ in range(220):
        controller.handle_key(ord("+"))
        controller.handle_key(ord("]"))
    assert (controller.throttle, controller.pulse_ms) == (8, 5000)
    for _ in range(220):
        controller.handle_key(ord("-"))
        controller.handle_key(ord("["))
    assert (controller.throttle, controller.pulse_ms) == (0, 25)
    assert duties(outputs) == [3276, 3276, 3276]


def test_repeat_pulse_does_not_extend_deadline(control):
    controller, outputs, now = control
    arm(controller, now)
    controller.handle_key(ord("d"))
    now[0] += 0.2
    controller.handle_key(ord("d"))
    now[0] += 0.06
    controller.tick()
    assert duties(outputs) == [3276, 3276, 3276]


def test_toggle_off_cancels_pulse_for_that_wheel(control):
    controller, outputs, now = control
    arm(controller, now)
    for key in "1a1":
        controller.handle_key(ord(key))
    assert duties(outputs) == [3276, 3276, 3276]


def test_results_and_quit(control):
    controller, outputs, now = control
    arm(controller, now)
    for key in "gGbJn":
        controller.handle_key(ord(key))
    assert controller.stats == {"good": 2, "double": 1, "jam": 1, "none": 1}
    controller.handle_key(ord(" "))
    assert controller.handle_key(ord("Q")) is False
    assert duties(outputs) == [0, 0, 0]


def test_cleanup_attempts_all_channels_and_releases_resources_after_failure(hardware):
    rig, outputs, released = hardware
    outputs[2].fail = True
    errors = rig.close()
    assert errors and all("ch2" in error for error in errors)
    assert outputs[3].values[-2:] == [3276, 0]
    assert outputs[4].values[-2:] == [3276, 0]
    assert all(not outputs[ch].values for ch in (0, 1, 5, 6))
    assert released == ["pca", "bus"]


@pytest.mark.parametrize("failure", [RuntimeError("render failed"), KeyboardInterrupt()])
def test_main_cleans_up_after_ui_failure(bench_module, hardware, monkeypatch, failure):
    _, outputs, released = hardware

    def fail(*args):
        raise failure

    monkeypatch.setattr(bench_module.curses, "wrapper", fail)
    assert bench_module.main([]) == (130 if isinstance(failure, KeyboardInterrupt) else 1)
    assert duties(outputs) == [0, 0, 0]
    assert released == ["pca", "bus"]


def test_main_cleans_up_after_partial_hardware_initialization(bench_module, hardware, monkeypatch):
    _, outputs, released = hardware
    outputs[2].fail = True
    assert bench_module.main([]) == 1
    assert outputs[3].duty_cycle == outputs[4].duty_cycle == 0
    assert released == ["pca", "bus"]


@pytest.mark.parametrize(
    "args",
    [
        ["--channels", "2", "2", "4"],
        ["--channels", "2", "3", "16"],
        ["--throttle", "9"],
        ["--throttle", "-1"],
        ["--max-throttle", "71"],
        ["--pulse-ms", "0"],
        ["--pulse-ms", "5001"],
    ],
)
def test_invalid_settings_fail_before_hardware_access(bench_module, args):
    with pytest.raises(SystemExit) as exc:
        bench_module.main(args)
    assert exc.value.code == 2


def test_dry_run_does_not_import_hardware(bench_module, monkeypatch):
    monkeypatch.setitem(sys.modules, "board", None)
    monkeypatch.setitem(sys.modules, "adafruit_pca9685", None)

    def rehearse(callback, controller):
        assert controller.rig.dry_run
        assert controller.handle_key(ord("q")) is False

    monkeypatch.setattr(bench_module.curses, "wrapper", rehearse)
    assert bench_module.main(["--dry-run"]) == 0
