#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "omnivoice",
#     "soundfile",
#     "torch",
#     "torchaudio",
#     "numpy>=1.24",
#     "pydantic>=2.13.4",
#     "pyyaml",
# ]
# ///
"""Bake the canned line cache: clone the reference voice, render every line.

Run ON THE LAPTOP (needs the ``voice`` extra — ``uv sync --extra voice``).
The Pi never runs this; it only plays the WAVs this produces.

    uv run scripts/bake_voice.py --dry-run          # what would be baked
    uv run scripts/bake_voice.py --id insult_kidding_01
    uv run scripts/bake_voice.py --bucket insult
    uv run scripts/bake_voice.py --scores           # the 0-11 x 0-11 grid
    uv run scripts/bake_voice.py                    # everything not yet baked

Each line names a reference key (``ref: rage``), resolving to
``assets/voice/ref/<ref>.wav`` plus its ``.txt`` transcript. OmniVoice clones
that voice and speaks the line in it — so the *register* comes from which clip
you recorded, not from the words. That is why there are four references rather
than one.

Clips land at ``assets/voice/cache/<bucket>/<id>.wav`` (24 kHz, gitignored,
regenerable). Already-baked clips are skipped unless ``--force`` or ``--id``.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

from mcenroebot.voice import (
    Bucket,
    Line,
    LineLibrary,
    pad_leading_silence,
    plan_bake,
    score_lines,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_LINES = _REPO_ROOT / "assets" / "voice" / "lines.yaml"
_DEFAULT_REF_DIR = _REPO_ROOT / "assets" / "voice" / "ref"
_DEFAULT_OUT = _REPO_ROOT / "assets" / "voice" / "cache"

_SAMPLE_RATE = 24_000  # OmniVoice output rate
_PAD_SECONDS = 0.3  # covers Bluetooth speaker wake-up


def _pick_device(requested: str) -> str:
    """Resolve ``auto`` to the best available backend."""
    if requested != "auto":
        return requested
    import torch

    if torch.cuda.is_available():
        return "cuda:0"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _load_model(device: str, dtype_name: str) -> Any:
    """Load OmniVoice. Imported lazily so ``--dry-run`` needs no torch."""
    import torch
    from omnivoice import OmniVoice

    # float16 is the documented example but is CUDA-oriented; MPS and CPU are
    # markedly less reliable in half precision, so they default to float32.
    if dtype_name == "auto":
        dtype = torch.float16 if device.startswith("cuda") else torch.float32
    else:
        dtype = getattr(torch, dtype_name)

    print(f"loading OmniVoice on {device} ({str(dtype).removeprefix('torch.')}) ...")
    return OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=device, dtype=dtype)


def _read_references(ref_dir: Path, refs: set[str]) -> dict[str, tuple[Path, str]]:
    """Map each reference key to its wav path and transcript text."""
    return {
        ref: (ref_dir / f"{ref}.wav", (ref_dir / f"{ref}.txt").read_text().strip()) for ref in refs
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--lines", type=Path, default=_DEFAULT_LINES, help="line script YAML")
    parser.add_argument("--ref-dir", type=Path, default=_DEFAULT_REF_DIR, help="reference voices")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT, help="WAV cache directory")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list what would be baked and exit; loads no model",
    )
    parser.add_argument(
        "--bucket",
        action="append",
        choices=[b.value for b in Bucket],
        help="only this bucket (repeatable)",
    )
    parser.add_argument(
        "--id", action="append", help="only this line id (repeatable); always re-bakes"
    )
    parser.add_argument("--scores", action="store_true", help="include the score-announcement grid")
    parser.add_argument("--only-scores", action="store_true", help="bake only the score grid")
    parser.add_argument("--max-points", type=int, default=11, help="score grid size")
    parser.add_argument("--force", action="store_true", help="re-bake clips that already exist")
    parser.add_argument("--num-step", type=int, default=32, help="diffusion steps (16 = faster)")
    parser.add_argument("--device", default="auto", help="auto | mps | cuda:0 | cpu")
    parser.add_argument("--dtype", default="auto", help="auto | float32 | float16")
    args = parser.parse_args(argv)

    library = LineLibrary.from_yaml(path=args.lines, ref_dir=args.ref_dir)

    lines: list[Line] = []
    if not args.only_scores:
        lines.extend(line for bucket in library.buckets_in_use() for line in library.lines(bucket))
    if args.scores or args.only_scores:
        lines.extend(score_lines(max_points=args.max_points))

    buckets = tuple(Bucket(b) for b in args.bucket) if args.bucket else None
    plan = plan_bake(
        lines=lines,
        out_dir=args.out,
        buckets=buckets,
        ids=tuple(args.id) if args.id else None,
        force=args.force,
    )

    print(f"{len(lines)} lines in scope, {len(plan)} to bake -> {args.out}")
    if args.dry_run:
        for item in plan:
            print(f"  [{item.line.ref:>8}] {item.line.id:<28} {item.line.text}")
        return 0
    if not plan:
        print("nothing to do (use --force to re-bake)")
        return 0

    references = _read_references(args.ref_dir, {item.line.ref for item in plan})
    model = _load_model(_pick_device(args.device), args.dtype)

    import soundfile as sf

    started = time.monotonic()
    for index, item in enumerate(plan, start=1):
        ref_wav, ref_text = references[item.line.ref]
        audio = model.generate(
            text=item.line.text,
            ref_audio=str(ref_wav),
            ref_text=ref_text,
            num_step=args.num_step,
        )
        padded = pad_leading_silence(audio=audio[0], seconds=_PAD_SECONDS, sample_rate=_SAMPLE_RATE)
        item.path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(item.path, padded, _SAMPLE_RATE)
        print(f"  [{index}/{len(plan)}] {item.line.id}")

    elapsed = time.monotonic() - started
    print(f"\nbaked {len(plan)} clips in {elapsed:.1f}s -> {args.out}")
    print("Listen to a whole bucket, then one line from each bucket back to back —")
    print("the four registers must sound like one person in four moods.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
