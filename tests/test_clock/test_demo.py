"""Smoke-cover the `_demo()` helper so coverage stays high."""

from __future__ import annotations

import pytest

from mcenroebot.clock import _demo


class TestDemo:
    def test_demo_runs_without_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        _demo()
        captured = capsys.readouterr()
        assert "SystemClock" in captured.out
        assert "FakeClock" in captured.out
