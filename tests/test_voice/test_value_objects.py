"""Tests for the voice value objects."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcenroebot.voice import Bucket, Line


def _line(**overrides: object) -> Line:
    kwargs: dict[str, object] = {
        "id": "insult_shank_01",
        "bucket": Bucket.INSULT,
        "ref": "rage",
        "text": "You have GOT to be kidding me.",
    }
    kwargs.update(overrides)
    return Line(**kwargs)  # type: ignore[arg-type]


class TestBucket:
    def test_buckets_map_to_event_pipeline_vocabulary(self) -> None:
        assert {b.value for b in Bucket} == {
            "insult",
            "whine",
            "grudging_respect",
            "self_deprecation",
            "announce",
        }

    def test_parses_from_yaml_string(self) -> None:
        assert Bucket("grudging_respect") is Bucket.GRUDGING_RESPECT


class TestLine:
    def test_holds_its_fields(self) -> None:
        line = _line()
        assert line.id == "insult_shank_01"
        assert line.bucket is Bucket.INSULT
        assert line.ref == "rage"
        assert line.text == "You have GOT to be kidding me."

    def test_is_frozen(self) -> None:
        line = _line()
        with pytest.raises(ValidationError):
            line.text = "nope"  # type: ignore[misc]

    def test_unknown_bucket_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _line(bucket="applause")

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_blank_text_rejected(self, blank: str) -> None:
        with pytest.raises(ValidationError):
            _line(text=blank)

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_blank_id_rejected(self, blank: str) -> None:
        with pytest.raises(ValidationError):
            _line(id=blank)

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_blank_ref_rejected(self, blank: str) -> None:
        with pytest.raises(ValidationError):
            _line(ref=blank)

    def test_id_must_be_filename_safe(self) -> None:
        """ids become WAV filenames, so path separators would escape the cache dir."""
        with pytest.raises(ValidationError):
            _line(id="../../etc/passwd")
