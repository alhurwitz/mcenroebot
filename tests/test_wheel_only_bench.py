"""Exercise shutdown with real Adafruit pulse mapping and fake PWM hardware."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


class PWM:
    frequency = 50

    def __init__(self) -> None:
        self.values: list[int] = [1234]
        self.fail_off = False

    @property
    def duty_cycle(self) -> int:
        return self.values[-1]

    @duty_cycle.setter
    def duty_cycle(self, value: int) -> None:
        if value == 0 and self.fail_off:
            raise OSError("injected I2C failure")
        self.values.append(value)


@pytest.fixture
def rig(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, dict[int, PWM]]:
    # Mock only physical PWM and board construction; keep Adafruit's actual
    # ContinuousServo setters so a permissive mock cannot hide None rejection.
    pwmio = ModuleType("pwmio")
    monkeypatch.setattr(pwmio, "PWMOut", PWM, raising=False)
    monkeypatch.setitem(sys.modules, "pwmio", pwmio)
    servo = pytest.importorskip("adafruit_motor.servo")
    outputs = {ch: PWM() for ch in (2, 3, 4)}
    escs = {ch: servo.ContinuousServo(pwm) for ch, pwm in outputs.items()}
    kit = SimpleNamespace(continuous_servo=escs)
    module = ModuleType("adafruit_servokit")
    monkeypatch.setattr(module, "ServoKit", lambda **kwargs: kit, raising=False)
    monkeypatch.setitem(sys.modules, "adafruit_servokit", module)
    path = Path(__file__).resolve().parents[1] / "scripts" / "wheel_only_bench.py"
    spec = importlib.util.spec_from_file_location("wheel_bench_under_test", path)
    assert spec is not None and spec.loader is not None
    bench = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bench)
    return bench, outputs


@pytest.mark.parametrize("command", ["q", "3 5", "all 5"])
def test_quit_and_completed_tests_disable_all_pwm(
    rig: tuple[Any, dict[int, PWM]], monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    bench, outputs = rig
    replies = iter(["", command])
    prompts = []

    def read(prompt: str) -> str:
        prompts.append(prompt)
        try:
            return next(replies)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr("builtins.input", read)
    monkeypatch.setattr(bench.time, "sleep", lambda seconds: None)
    bench.main()
    assert [outputs[ch].duty_cycle for ch in (2, 3, 4)] == [0, 0, 0]
    expected_spinning = {"q": [], "3 5": [3], "all 5": [2, 3, 4]}[command]
    assert [ch for ch in (2, 3, 4) if max(outputs[ch].values) > 3276] == expected_spinning
    assert len(prompts) == 2, "A completed run must disable signals and exit, not stay armed"


def test_interrupt_during_launch_disables_all_pwm(
    rig: tuple[Any, dict[int, PWM]], monkeypatch: pytest.MonkeyPatch
) -> None:
    bench, outputs = rig
    replies = iter(["", "all 5"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(replies))

    def interrupt(seconds: float) -> None:
        if seconds == 2:
            raise KeyboardInterrupt

    monkeypatch.setattr(bench.time, "sleep", interrupt)
    bench.main()
    assert [outputs[ch].duty_cycle for ch in (2, 3, 4)] == [0, 0, 0]


def test_one_failed_shutdown_write_does_not_skip_other_wheels(
    rig: tuple[Any, dict[int, PWM]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bench, outputs = rig
    outputs[3].fail_off = True
    replies = iter(["", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(replies))
    monkeypatch.setattr(bench.time, "sleep", lambda seconds: None)
    assert bench.main() == 1
    assert outputs[2].duty_cycle == outputs[4].duty_cycle == 0
    assert outputs[3].duty_cycle != 0
    assert "Disconnect LiPo" in capsys.readouterr().out


def test_invalid_commands_never_start_a_wheel(
    rig: tuple[Any, dict[int, PWM]], monkeypatch: pytest.MonkeyPatch
) -> None:
    bench, outputs = rig
    replies = iter(["", "5 5", "6 5", "all 9", "all nan", "all inf", "all -1", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(replies))
    monkeypatch.setattr(bench.time, "sleep", lambda seconds: None)
    assert bench.main() == 0
    assert all(max(pwm.values) == 3276 and pwm.duty_cycle == 0 for pwm in outputs.values())
