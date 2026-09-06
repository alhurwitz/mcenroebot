"""Tests for LineLibrary loading, validation, and the anti-repeat shuffle."""

from __future__ import annotations

import itertools
import random
from pathlib import Path

import pytest

from mcenroebot.voice import Bucket, LineLibrary

_YAML = """
- id: insult_01
  bucket: insult
  ref: rage
  text: "You have GOT to be kidding me."
- id: insult_02
  bucket: insult
  ref: rage
  text: "My grandmother returns that."
- id: insult_03
  bucket: insult
  ref: rage
  text: "Were you even looking?"
- id: respect_01
  bucket: grudging_respect
  ref: grudging
  text: "Fine. That was a good one."
"""


@pytest.fixture
def ref_dir(tmp_path: Path) -> Path:
    d = tmp_path / "ref"
    d.mkdir()
    for key in ("rage", "grudging"):
        (d / f"{key}.wav").write_bytes(b"RIFF")
        (d / f"{key}.txt").write_text("reference transcript")
    return d


@pytest.fixture
def lines_path(tmp_path: Path) -> Path:
    p = tmp_path / "lines.yaml"
    p.write_text(_YAML)
    return p


def _library(lines_path: Path, ref_dir: Path, seed: int = 0) -> LineLibrary:
    return LineLibrary.from_yaml(path=lines_path, ref_dir=ref_dir, rng=random.Random(seed))


class TestLoading:
    def test_loads_every_line(self, lines_path: Path, ref_dir: Path) -> None:
        assert len(_library(lines_path, ref_dir)) == 4

    def test_groups_by_bucket(self, lines_path: Path, ref_dir: Path) -> None:
        lib = _library(lines_path, ref_dir)
        assert len(lib.lines(bucket=Bucket.INSULT)) == 3
        assert len(lib.lines(bucket=Bucket.GRUDGING_RESPECT)) == 1

    def test_empty_bucket_returns_nothing(self, lines_path: Path, ref_dir: Path) -> None:
        assert _library(lines_path, ref_dir).lines(bucket=Bucket.WHINE) == ()

    def test_buckets_in_use_reports_populated_buckets(
        self, lines_path: Path, ref_dir: Path
    ) -> None:
        lib = _library(lines_path, ref_dir)
        assert lib.buckets_in_use() == (Bucket.INSULT, Bucket.GRUDGING_RESPECT)


class TestValidation:
    def test_duplicate_ids_rejected(self, tmp_path: Path, ref_dir: Path) -> None:
        p = tmp_path / "dupe.yaml"
        p.write_text(
            "- {id: a, bucket: insult, ref: rage, text: one}\n"
            "- {id: a, bucket: insult, ref: rage, text: two}\n"
        )
        with pytest.raises(ValueError, match="duplicate line id"):
            _library(p, ref_dir)

    def test_missing_reference_wav_rejected(self, tmp_path: Path, ref_dir: Path) -> None:
        p = tmp_path / "badref.yaml"
        p.write_text("- {id: a, bucket: insult, ref: smug, text: one}\n")
        with pytest.raises(ValueError, match="smug"):
            _library(p, ref_dir)

    def test_missing_reference_transcript_rejected(self, tmp_path: Path, ref_dir: Path) -> None:
        (ref_dir / "smug.wav").write_bytes(b"RIFF")  # wav present, .txt absent
        p = tmp_path / "notxt.yaml"
        p.write_text("- {id: a, bucket: insult, ref: smug, text: one}\n")
        with pytest.raises(ValueError, match="transcript"):
            _library(p, ref_dir)

    def test_empty_file_rejected(self, tmp_path: Path, ref_dir: Path) -> None:
        p = tmp_path / "empty.yaml"
        p.write_text("")
        with pytest.raises(ValueError, match="no lines"):
            _library(p, ref_dir)


class TestAntiRepeatShuffle:
    def test_deals_whole_bucket_before_repeating(self, lines_path: Path, ref_dir: Path) -> None:
        lib = _library(lines_path, ref_dir)
        drawn = [lib.next_line(bucket=Bucket.INSULT).id for _ in range(3)]
        assert sorted(drawn) == ["insult_01", "insult_02", "insult_03"]

    def test_reshuffles_and_keeps_dealing_past_exhaustion(
        self, lines_path: Path, ref_dir: Path
    ) -> None:
        lib = _library(lines_path, ref_dir)
        drawn = [lib.next_line(bucket=Bucket.INSULT).id for _ in range(9)]
        for start in (0, 3, 6):
            assert sorted(drawn[start : start + 3]) == [
                "insult_01",
                "insult_02",
                "insult_03",
            ]

    def test_never_repeats_across_the_reshuffle_boundary(
        self, lines_path: Path, ref_dir: Path
    ) -> None:
        """The worst failure mode is the same taunt twice in a row."""
        for seed in range(25):
            lib = _library(lines_path, ref_dir, seed=seed)
            drawn = [lib.next_line(bucket=Bucket.INSULT).id for _ in range(30)]
            assert all(a != b for a, b in itertools.pairwise(drawn))

    def test_single_line_bucket_repeats_rather_than_hanging(
        self, lines_path: Path, ref_dir: Path
    ) -> None:
        lib = _library(lines_path, ref_dir)
        drawn = [lib.next_line(bucket=Bucket.GRUDGING_RESPECT).id for _ in range(3)]
        assert drawn == ["respect_01"] * 3

    def test_buckets_deal_independently(self, lines_path: Path, ref_dir: Path) -> None:
        lib = _library(lines_path, ref_dir)
        lib.next_line(bucket=Bucket.INSULT)
        assert lib.next_line(bucket=Bucket.GRUDGING_RESPECT).id == "respect_01"
        assert len(lib.lines(bucket=Bucket.INSULT)) == 3

    def test_same_seed_gives_same_sequence(self, lines_path: Path, ref_dir: Path) -> None:
        a = [_library(lines_path, ref_dir, seed=7).next_line(bucket=Bucket.INSULT).id for _ in "x"]
        b = [_library(lines_path, ref_dir, seed=7).next_line(bucket=Bucket.INSULT).id for _ in "x"]
        assert a == b

    def test_empty_bucket_raises(self, lines_path: Path, ref_dir: Path) -> None:
        lib = _library(lines_path, ref_dir)
        with pytest.raises(KeyError, match="whine"):
            lib.next_line(bucket=Bucket.WHINE)
