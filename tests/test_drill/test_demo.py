"""Smoke-cover the drill `_demo()` helper so coverage stays high."""

from __future__ import annotations

import pytest

from mcenroebot.drill import _demo


class TestDemo:
    def test_demo_runs_without_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        _demo()
        captured = capsys.readouterr()
        assert "oscillate drill" in captured.out
        assert "shot 0" in captured.out
