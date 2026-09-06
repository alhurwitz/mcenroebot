"""Voice — the bot's script and the cloned voice that speaks it.

The personality layer designed in ``docs/handoff/reference/design/VOICE_PLAN.md``.
Lines are written as data (``assets/voice/lines.yaml``), spoken by a voice cloned
from short reference recordings via OmniVoice, and baked once into a WAV cache
that the Pi plays back instantly and offline.

This package holds only the pure, torch-free half: the script and the dealing
logic. Model loading and WAV rendering live in ``scripts/bake_voice.py``, which
runs on the laptop and never ships to the Pi.

Layout
------
    value_objects.py — Bucket, Line (frozen pydantic).
    lines.py         — LineLibrary: loading, validation, anti-repeat dealing.
    scores.py        — the generated score-announcement grid.
    bake.py          — bake planning (what to render, where), torch-free.
"""

from mcenroebot.voice.bake import BakeItem, pad_leading_silence, plan_bake
from mcenroebot.voice.lines import LineLibrary
from mcenroebot.voice.scores import score_lines
from mcenroebot.voice.value_objects import Bucket, Line

__all__ = [
    "BakeItem",
    "Bucket",
    "Line",
    "LineLibrary",
    "pad_leading_silence",
    "plan_bake",
    "score_lines",
]
