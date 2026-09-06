"""Bake planning — decide what to render before any model is loaded.

Kept separate from ``scripts/bake_voice.py`` so the "what would this do?"
question is answerable, and testable, without importing torch.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict

from mcenroebot.voice.value_objects import Bucket, Line

__all__ = ["BakeItem", "pad_leading_silence", "plan_bake"]


class BakeItem(BaseModel):
    """One line and the cache path its WAV belongs at."""

    model_config = ConfigDict(frozen=True)

    line: Line
    path: Path


def plan_bake(
    lines: Sequence[Line],
    out_dir: Path,
    buckets: Iterable[Bucket] | None = None,
    ids: Iterable[str] | None = None,
    force: bool = False,
) -> tuple[BakeItem, ...]:
    """Work out which lines still need rendering, and where each WAV goes.

    Clips land at ``<out_dir>/<bucket>/<id>.wav``. Already-baked clips are
    skipped so adding ten lines re-bakes ten, not two hundred.

    Naming ``ids`` explicitly always re-bakes them regardless of ``force`` —
    that is the tuning loop, where you rewrite one line and want to hear it
    again immediately.

    Raises
    ------
    ValueError
        An entry in ``ids`` matches no line.
    """
    selected = list(lines)

    if buckets is not None:
        wanted = set(buckets)
        selected = [line for line in selected if line.bucket in wanted]

    if ids is not None:
        wanted_ids = set(ids)
        found = {line.id for line in selected}
        if missing := sorted(wanted_ids - found):
            raise ValueError(f"no such line id: {', '.join(missing)}")
        selected = [line for line in selected if line.id in wanted_ids]
        force = True

    items: list[BakeItem] = []
    for line in selected:
        path = out_dir / line.bucket.value / f"{line.id}.wav"
        if force or not path.is_file():
            items.append(BakeItem(line=line, path=path))
    return tuple(items)


def pad_leading_silence(
    audio: npt.NDArray[np.float32],
    seconds: float,
    sample_rate: int,
) -> npt.NDArray[np.float32]:
    """Prepend ``seconds`` of silence to a rendered clip.

    Bluetooth speakers sleep between clips and swallow the first fraction of a
    second when they wake — which, untreated, eats the first word of every
    taunt. Baking the padding in costs nothing and removes a whole class of
    "it cut off" debugging on the Pi.

    Raises
    ------
    ValueError
        ``seconds`` is negative.
    """
    if seconds < 0.0:
        raise ValueError(f"seconds={seconds} must be >= 0")
    pad = np.zeros(int(seconds * sample_rate), dtype=audio.dtype)
    return np.concatenate((pad, audio))
