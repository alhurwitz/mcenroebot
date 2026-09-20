"""Wheel dashboard throttle boundaries, without energizing hardware."""
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def bench():
    path = Path(__file__).resolve().parents[2] / "scripts" / "wheel_bench_tui.py"
    spec = importlib.util.spec_from_file_location("wheel_tui_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("percent", ["1", "8", "70", "99.5", "100"])
def test_dashboard_accepts_full_throttle_range(bench, percent):
    request = bench.parse_run("all", percent, "10")
    assert request.percent == float(percent)


@pytest.mark.parametrize("percent", ["0", "-1", "100.01", "101", "nan", "inf"])
def test_dashboard_rejects_invalid_throttle(bench, percent):
    with pytest.raises(ValueError):
        bench.parse_run("all", percent, "10")


async def test_full_throttle_run_restores_minimum_after_interrupt(bench):
    class Rig:
        percent = 0
        def spin(self, target, percent):
            self.percent = percent
        def minimum_all(self):
            self.percent = 0
    rig = Rig()
    async def interrupt(seconds):
        assert rig.percent == 100
        raise RuntimeError("interrupted")
    request = bench.parse_run("all", "100", "10")
    with pytest.raises(RuntimeError, match="interrupted"):
        await bench.execute_run(rig, request, lambda text: None, sleep=interrupt)
    assert rig.percent == 0
