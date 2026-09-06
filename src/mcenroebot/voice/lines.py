"""LineLibrary — load the line script and deal lines without repeating."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import yaml

from mcenroebot.voice.value_objects import Bucket, Line

__all__ = ["LineLibrary"]


class LineLibrary:
    """The bot's script, grouped by :class:`Bucket`, dealt anti-repeat.

    Lines are dealt by shuffling each bucket into a deck and drawing until it
    is exhausted, then reshuffling. That guarantees every line in a bucket is
    heard once before any is heard twice, which is what keeps a 40-line insult
    bucket from feeling like a 5-line one.

    The reshuffle also refuses to put the just-dealt line at the front of the
    new deck, so no line ever lands twice in a row across the boundary — the
    one repeat a player actually notices.

    Stateful (the decks deplete), so unlike the controllers in this repo an
    instance is not reusable across independent sessions. Construct one per run
    and pass a seeded ``rng`` for reproducibility.
    """

    def __init__(self, lines: tuple[Line, ...], rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()
        self._by_bucket: dict[Bucket, tuple[Line, ...]] = {
            bucket: tuple(line for line in lines if line.bucket is bucket) for bucket in Bucket
        }
        self._decks: dict[Bucket, list[Line]] = {}
        self._last_dealt: dict[Bucket, str] = {}
        self._all = lines

    @classmethod
    def from_yaml(
        cls,
        path: Path,
        ref_dir: Path,
        rng: random.Random | None = None,
    ) -> LineLibrary:
        """Load and validate the line script at ``path``.

        Every ``ref`` must resolve to both ``<ref_dir>/<ref>.wav`` and its
        ``.txt`` transcript — checked here rather than at bake time so a typo
        surfaces in a fast ``--dry-run`` instead of after the model loads.

        Raises
        ------
        ValueError
            The file is empty, ids collide, or a reference is missing.
        """
        raw: Any = yaml.safe_load(path.read_text()) or []
        if not raw:
            raise ValueError(f"{path} contains no lines")

        lines = tuple(Line(**entry) for entry in raw)

        seen: set[str] = set()
        for line in lines:
            if line.id in seen:
                raise ValueError(f"duplicate line id {line.id!r} in {path}")
            seen.add(line.id)

        for ref in sorted({line.ref for line in lines}):
            if not (ref_dir / f"{ref}.wav").is_file():
                raise ValueError(f"reference voice {ref!r} has no {ref}.wav in {ref_dir}")
            if not (ref_dir / f"{ref}.txt").is_file():
                raise ValueError(
                    f"reference voice {ref!r} has no {ref}.txt transcript in {ref_dir}"
                )

        return cls(lines=lines, rng=rng)

    def __len__(self) -> int:
        return len(self._all)

    def lines(self, bucket: Bucket) -> tuple[Line, ...]:
        """Every line in ``bucket``, in file order."""
        return self._by_bucket[bucket]

    def buckets_in_use(self) -> tuple[Bucket, ...]:
        """The populated buckets, in :class:`Bucket` declaration order."""
        return tuple(bucket for bucket in Bucket if self._by_bucket[bucket])

    def next_line(self, bucket: Bucket) -> Line:
        """Deal the next line from ``bucket``.

        Raises
        ------
        KeyError
            ``bucket`` holds no lines.
        """
        if not self._by_bucket[bucket]:
            raise KeyError(f"no lines in bucket {bucket.value!r}")

        deck = self._decks.get(bucket)
        if not deck:
            deck = self._shuffled_deck(bucket)
            self._decks[bucket] = deck

        line = deck.pop()
        self._last_dealt[bucket] = line.id
        return line

    def _shuffled_deck(self, bucket: Bucket) -> list[Line]:
        """A fresh deck for ``bucket``, dealt from the end by :meth:`next_line`."""
        deck = list(self._by_bucket[bucket])
        self._rng.shuffle(deck)
        last = self._last_dealt.get(bucket)
        if len(deck) > 1 and deck[-1].id == last:
            swap_with = self._rng.randrange(len(deck) - 1)
            deck[-1], deck[swap_with] = deck[swap_with], deck[-1]
        return deck
