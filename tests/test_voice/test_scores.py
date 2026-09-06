"""Tests for the generated score-announcement grid."""

from __future__ import annotations

import pytest

from mcenroebot.voice import Bucket, score_lines


class TestScoreLines:
    def test_covers_the_full_grid(self) -> None:
        assert len(score_lines(max_points=11)) == 12 * 12

    def test_smaller_grid(self) -> None:
        assert len(score_lines(max_points=2)) == 9

    def test_all_announce_bucket(self) -> None:
        assert all(line.bucket is Bucket.ANNOUNCE for line in score_lines(max_points=3))

    def test_all_use_the_smug_reference(self) -> None:
        assert all(line.ref == "smug" for line in score_lines(max_points=3))

    def test_ids_are_unique_and_filename_safe(self) -> None:
        lines = score_lines(max_points=11)
        ids = [line.id for line in lines]
        assert len(set(ids)) == len(ids)
        assert all(line.id.startswith("score_") for line in lines)

    def test_robot_score_is_called_first(self) -> None:
        """The robot serves every ball, so its score leads, as in table tennis."""
        (line,) = [ln for ln in score_lines(max_points=11) if ln.id == "score_7_3"]
        assert line.text == "Seven. Three."

    def test_spells_numbers_as_words(self) -> None:
        by_id = {line.id: line.text for line in score_lines(max_points=11)}
        assert by_id["score_0_0"] == "Zero. Zero."
        assert by_id["score_11_9"] == "Eleven. Nine."

    def test_rejects_grid_beyond_supported_words(self) -> None:
        with pytest.raises(ValueError, match="max_points"):
            score_lines(max_points=12)

    def test_rejects_negative_grid(self) -> None:
        with pytest.raises(ValueError, match="max_points"):
            score_lines(max_points=-1)
