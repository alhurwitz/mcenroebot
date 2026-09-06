"""Frozen value objects for the voice subsystem."""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator

__all__ = ["Bucket", "Line"]

_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class Bucket(StrEnum):
    """Which rally moment a line answers.

    Maps onto the event vocabulary in ``scripts/vision/EVENT_PIPELINE.md``:
    ``DOUBLE_BOUNCE`` -> :attr:`INSULT`, a long ``RETURN_HIT`` streak ->
    :attr:`GRUDGING_RESPECT`, ``BALL_LOST`` -> :attr:`SELF_DEPRECATION`.
    """

    INSULT = "insult"
    WHINE = "whine"
    GRUDGING_RESPECT = "grudging_respect"
    SELF_DEPRECATION = "self_deprecation"
    ANNOUNCE = "announce"


class Line(BaseModel):
    """One spoken line: what to say, in which register, keyed for the WAV cache.

    Attributes
    ----------
    id : str
        Stable identifier. Becomes the cache filename, so it is restricted to
        ``[A-Za-z0-9_-]``.
    bucket : Bucket
        The rally moment this line answers.
    ref : str
        Reference-voice key, resolving to ``<ref_dir>/<ref>.wav`` plus its
        ``.txt`` transcript. Chooses the emotional register the clone speaks in.
    text : str
        The line itself. May carry OmniVoice non-verbal tags such as
        ``[sigh]`` or ``[dissatisfaction-hnn]``.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    bucket: Bucket
    ref: str
    text: str

    @field_validator("id", "ref", "text")
    @classmethod
    def _check_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("id")
    @classmethod
    def _check_filename_safe(cls, value: str) -> str:
        if not _ID_RE.match(value):
            raise ValueError(f"id={value!r} must match {_ID_RE.pattern} (it becomes a filename)")
        return value
