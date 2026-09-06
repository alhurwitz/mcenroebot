"""Tests for bake planning — what gets rendered, where, and what gets skipped."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from mcenroebot.voice import Bucket, Line, pad_leading_silence, plan_bake

_LINES = (
    Line(id="insult_01", bucket=Bucket.INSULT, ref="rage", text="One."),
    Line(id="insult_02", bucket=Bucket.INSULT, ref="rage", text="Two."),
    Line(id="respect_01", bucket=Bucket.GRUDGING_RESPECT, ref="grudging", text="Three."),
)


@pytest.fixture
def out_dir(tmp_path: Path) -> Path:
    return tmp_path / "cache"


class TestPlanBake:
    def test_plans_every_line_when_cache_is_empty(self, out_dir: Path) -> None:
        assert len(plan_bake(lines=_LINES, out_dir=out_dir)) == 3

    def test_output_path_is_bucket_then_id(self, out_dir: Path) -> None:
        item = plan_bake(lines=_LINES, out_dir=out_dir)[0]
        assert item.path == out_dir / "insult" / "insult_01.wav"

    def test_skips_lines_already_baked(self, out_dir: Path) -> None:
        (out_dir / "insult").mkdir(parents=True)
        (out_dir / "insult" / "insult_01.wav").write_bytes(b"RIFF")
        planned = {item.line.id for item in plan_bake(lines=_LINES, out_dir=out_dir)}
        assert planned == {"insult_02", "respect_01"}

    def test_force_rebakes_existing(self, out_dir: Path) -> None:
        (out_dir / "insult").mkdir(parents=True)
        (out_dir / "insult" / "insult_01.wav").write_bytes(b"RIFF")
        assert len(plan_bake(lines=_LINES, out_dir=out_dir, force=True)) == 3

    def test_bucket_filter(self, out_dir: Path) -> None:
        planned = plan_bake(lines=_LINES, out_dir=out_dir, buckets=(Bucket.INSULT,))
        assert {item.line.id for item in planned} == {"insult_01", "insult_02"}

    def test_id_filter(self, out_dir: Path) -> None:
        planned = plan_bake(lines=_LINES, out_dir=out_dir, ids=("respect_01",))
        assert [item.line.id for item in planned] == ["respect_01"]

    def test_id_filter_beats_the_skip_check(self, out_dir: Path) -> None:
        """Naming one line explicitly is the tuning loop — it must always re-bake."""
        (out_dir / "insult").mkdir(parents=True)
        (out_dir / "insult" / "insult_01.wav").write_bytes(b"RIFF")
        planned = plan_bake(lines=_LINES, out_dir=out_dir, ids=("insult_01",))
        assert [item.line.id for item in planned] == ["insult_01"]

    def test_unknown_id_raises(self, out_dir: Path) -> None:
        with pytest.raises(ValueError, match="nope"):
            plan_bake(lines=_LINES, out_dir=out_dir, ids=("nope",))

    def test_empty_plan_when_everything_is_baked(self, out_dir: Path) -> None:
        for bucket, name in (("insult", "insult_01"), ("insult", "insult_02")):
            (out_dir / bucket).mkdir(parents=True, exist_ok=True)
            (out_dir / bucket / f"{name}.wav").write_bytes(b"RIFF")
        (out_dir / "grudging_respect").mkdir(parents=True)
        (out_dir / "grudging_respect" / "respect_01.wav").write_bytes(b"RIFF")
        assert plan_bake(lines=_LINES, out_dir=out_dir) == ()


class TestPadLeadingSilence:
    def test_prepends_the_requested_duration(self) -> None:
        audio = np.ones(100, dtype=np.float32)
        padded = pad_leading_silence(audio=audio, seconds=0.3, sample_rate=24_000)
        assert len(padded) == 7_200 + 100

    def test_padding_is_actually_silent(self) -> None:
        padded = pad_leading_silence(
            audio=np.ones(10, dtype=np.float32), seconds=0.1, sample_rate=100
        )
        assert not padded[:10].any()

    def test_original_audio_is_preserved_after_the_pad(self) -> None:
        audio = np.array([0.5, -0.5], dtype=np.float32)
        padded = pad_leading_silence(audio=audio, seconds=0.1, sample_rate=10)
        assert padded[-2:].tolist() == [0.5, -0.5]

    def test_zero_seconds_is_a_no_op(self) -> None:
        audio = np.ones(5, dtype=np.float32)
        assert len(pad_leading_silence(audio=audio, seconds=0.0, sample_rate=24_000)) == 5

    def test_preserves_dtype(self) -> None:
        audio = np.ones(5, dtype=np.float32)
        assert pad_leading_silence(audio=audio, seconds=0.1, sample_rate=100).dtype == np.float32

    def test_rejects_negative_padding(self) -> None:
        with pytest.raises(ValueError, match="seconds"):
            pad_leading_silence(audio=np.ones(5, dtype=np.float32), seconds=-0.1, sample_rate=100)
