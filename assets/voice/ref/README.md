# Reference voices

Four short recordings of **your own** McEnroe impression. OmniVoice clones the
voice in these clips and speaks every line in `../lines.yaml` with it.

Each key needs two files:

| File | What it is |
|---|---|
| `<key>.wav` | the recording — 24 kHz mono |
| `<key>.txt` | its exact transcript, plain words only |

## What to record

Prosody transfers from the reference, not just timbre. One neutral clip gives
240 clips of the same flat reading, so record four registers:

| Key | Direction | Drives |
|---|---|---|
| `rage` | Full shout, throat open. *"YOU CANNOT BE SERIOUS. That was IN!"* | insults, tantrums |
| `whine` | Nasal, aggrieved, drawn out. *"Ohhh come on, that's not even close…"* | disputed calls, self-pity |
| `smug` | Clipped, flat, insufferably pleased. *"Seven. Three."* | score announcements, gloating |
| `grudging` | Quiet, almost sincere, like it costs you. *"…yeah, alright. That was a good one."* | streak respect, rare praise |

20–30 seconds each is plenty; the model only needs about three.

## Record all four in one sitting

Same mic, same distance, same gain, one session. If they're captured on
different days or different hardware, the four registers clone as four
different *people* — and the bot audibly changes voice between the taunt and
the score. That's the main failure mode of this design and it's only audible
when you play the four back to back.

Use the Logitech webcam mic already on the robot: it's the same device that
will hear you during play, so the acoustic character stays consistent.

## Transcripts

Write exactly what's audible — no timestamps, no alignment, no stage
directions. Keep the punctuation, since it hints at the delivery.

Don't put audio tags like `[sigh]` in a transcript; those aren't in the
recording. They belong in the generated lines in `lines.yaml`.

## Whose voice

Yours, or someone who has agreed to it. Not a clip of the real John McEnroe —
see the note at the top of `lines.yaml`'s design doc and `VOICE_PLAN.md`.
