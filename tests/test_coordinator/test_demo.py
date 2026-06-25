"""Smoke-cover the FeederCoordinator `_demo()` helper so coverage stays high."""

from __future__ import annotations

import pytest

from mcenroebot.coordinator import _demo


class TestDemo:
    async def test_demo_runs_and_prints_shot_log(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        await _demo()
        captured = capsys.readouterr()
        assert "feeder drill" in captured.out
        # the mock-driven demo fires several shots and reports a clean shutdown
        assert "shot" in captured.out
        assert "shutdown" in captured.out
