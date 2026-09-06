"""The score-announcement grid, generated rather than hand-written.

Every reachable score gets its own clip. The alternative — stitching number
words together at playback — sounds exactly as robotic as it is, and it sounds
that way at the one moment the bot is supposed to sound smug. Baking the full
grid costs a couple of minutes of compute once, so we bake the full grid.
"""

from __future__ import annotations

from mcenroebot.voice.value_objects import Bucket, Line

__all__ = ["score_lines"]

_WORDS = (
    "Zero",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
)

_SCORE_REF = "smug"


def score_lines(max_points: int = 11) -> tuple[Line, ...]:
    """Every score from 0-0 up to ``max_points``-``max_points``.

    The robot's score is spoken first: it serves every ball, and the server's
    score is called first in table tennis.

    A standard game to 11 can reach 11-9 but deuce runs past it; scores beyond
    the grid fall back to the generic ``announce`` lines rather than growing the
    bake into a long tail nobody hears.

    Raises
    ------
    ValueError
        ``max_points`` is negative or beyond the spelled-out number words.
    """
    if not 0 <= max_points < len(_WORDS):
        raise ValueError(f"max_points={max_points} must be in 0..{len(_WORDS) - 1}")

    return tuple(
        Line(
            id=f"score_{robot}_{player}",
            bucket=Bucket.ANNOUNCE,
            ref=_SCORE_REF,
            text=f"{_WORDS[robot]}. {_WORDS[player]}.",
        )
        for robot in range(max_points + 1)
        for player in range(max_points + 1)
    )
