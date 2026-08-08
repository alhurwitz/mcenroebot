# Voice / Personality Plan — 2026-07-05 (rev 2: live conversation agent)

McEnroe talks — and listens. Two modes: **MATCH** (score announcing + trash talk, conversational
through the session) and **TRAINING** (coach mode: drills, per-shot feedback, pattern-based tips).
Rev 2 adds a **live voice agent** the player can talk to mid-game, with tools to run the robot.

## Provider decision — pending bake-off

Run `scripts/tts_bakeoff.py` with `OPENAI_API_KEY` / `XAI_API_KEY` set, listen, pick by ear.

| | OpenAI `gpt-4o-mini-tts` | Grok TTS (`api.x.ai/v1/tts`) |
|---|---|---|
| Prosody control | `instructions` free-text ("shout, indignant") | inline tags: `[pause]` `[sigh]` `[laugh]` `<loud>` `<soft>` |
| Voices | 13 (try ash/onyx/verse) | 5 (try rex/leo) |
| Price | ~$0.015/min | $15/1M chars (~similar) |
| Live agent option | Realtime API ($32/$64 per 1M audio tok) | Voice Agent API ($3/hr flat) |

Note: no cloning of McEnroe's real voice (both providers prohibit real-person mimicry).
We do McEnroe-*style* lines in a stock voice with angry prosody.

## Architecture (hybrid: canned + live)

```
RallyCoordinator events ──► ScoreKeeper ──► PersonalityEngine ──► AudioPlayer ──► BT speaker
                                                │
                                    canned WAV cache (instant)
                                    live LLM+TTS (async, ~1-2s, optional)
```

- **Canned library**: ~80–120 lines pre-rendered once via the winning TTS, stored as WAV on the
  Pi, categorized by event. Instant, offline, free at runtime. Anti-repeat shuffle per category.
- **Live lines** (optional, needs Wi-Fi): LLM writes a line referencing actual state ("that's
  three backhand misses in a row"), TTS renders it, plays *if* ready within budget (~2.5s after
  point end), else canned fallback. Generated async so it never blocks the feed loop.

### Events → speech

| Event | Source | MATCH mode | TRAINING mode |
|---|---|---|---|
| `BALL_FIRED` | feed servo cycle | (silent, or rare mid-rally chirp) | silent |
| `RETURN_DETECTED` | vision tracker sees ball come back within window | occasional "not bad" | per-shot feedback |
| `RETURN_MISSED` | timeout, no return | trash talk | corrective tip |
| `POINT_END` | ScoreKeeper | **announce score** ("seven–three"), taunt on streaks | streak encouragement |
| `GAME_POINT` / `GAME_END` | ScoreKeeper (to 11, win by 2) | big announce + gloat/grudging respect | session summary |
| `SESSION_STATS` | placement drill stats | — | pattern tips ("you're late on wide forehands") |

### ScoreKeeper (new, small)

Robot serves every ball, so scoring is simple: `RETURN_DETECTED` within T seconds of
`BALL_FIRED` = player point candidate; miss = robot point. V1 rule: any clean return = player
point (we can't judge in/out on the far side yet). Standard 11-point game, deuce at 10–10.
Pydantic frozen state, pure logic, fully unit-testable — matches repo standards.

### TRAINING mode (coach)

- Uses the existing vision placement drill stats: miss rate by target zone, reaction timing.
- Drill scripts: N balls to a zone, then coach line summarizing ("4 of 8 on the backhand —
  paddle up, wrist firm"). Live LLM line if online, canned generic tip if not.
- Difficulty ladder: coach bumps feed rate / wheel speed / placement spread when player clears
  a threshold, announces it ("Too easy? Fine. Let's see you handle THIS.").

### Repo integration (main python repo, not this folder)

- `voice/` package: `PersonalityEngine`, `ScoreKeeper`, `LineLibrary`, `AudioPlayer`
  Protocol + `MockAudioPlayer` + `BluetoothAudioPlayer`. Frozen pydantic models, mypy strict,
  tested against mocks — per CLAUDE.md standards.
- Rate limiting: max 1 line per point, min 4s between lines, never queue >1.

## Live conversation agent (rev 2)

The player talks to McEnroe mid-game ("what's the score?", "that was in!", "slow it down",
"it's jammed"), and McEnroe answers in voice, argues line calls, and actually operates the robot
via tools. Both realtime APIs support this; the bake-off picks the voice, this picks the plumbing:

- **Grok Voice Agent API** — `wss://api.x.ai/v1/realtime?model=grok-voice-latest`, mirrors the
  OpenAI Realtime event protocol (`session.update`, server VAD, function calling). **$3/hr flat**
  — a 2-hour session costs $6, predictable.
- **OpenAI Realtime (`gpt-realtime`)** — same shape, $32/$64 per 1M audio tokens (varies with
  how chatty the session is; often comparable but not flat).

Either way the Pi-side client is thin: one WebSocket, mic audio up, speaker audio down,
tool-call events dispatched to local functions.

### Do we need an agentic framework (deep agents, LangChain, etc.)?

Recommendation: **no — not for the realtime loop.** The Voice Agent API *is* the agent loop:
VAD, transcription, LLM, tool dispatch, and TTS all run server-side; our client just answers
tool calls with JSON. Frameworks like deepagents shine for long-horizon planning tasks
(sub-agents, task queues, filesystem scratch), but they add latency and complexity exactly where
a voice loop needs sub-second turnarounds — and none of our tools need multi-step planning.
Total client code is maybe 300 lines.

Where a planner *could* earn its keep later: an offline "coach analyst" that chews on several
sessions of placement stats and designs a drill plan. Even that is likely a single LLM call.
Start thin; add a framework only if a tool genuinely needs multi-step reasoning.

### Tool set (dispatched to RallyCoordinator / drivers)

| Tool | Args | Effect / guard |
|---|---|---|
| `get_state` | — | score, mode, difficulty, feed status, jam flag, balls remaining |
| `set_score` | player, robot | correct miscounts ("actually it's 7–4") — agent grumbles but complies |
| `start_game` / `end_game` / `rematch` | — | ScoreKeeper lifecycle |
| `pause_play` / `resume_play` | — | stops feed servo + spins down wheels; **"stop" always honored instantly** |
| `serve_ball` | — | single serve; guarded: only when wheels at speed + feed idle + play not paused |
| `set_difficulty` | 1–5 or {feed_rate, speed, spread} | maps to feed interval, wheel RPM, placement spread |
| `set_placement` | zone | target zone for next serves ("hit my backhand") |
| `clear_jam` | — | jam routine: feed servo re-cycle LOAD↔DISCH, auger reverse pulse, wheel blip; reports success |
| `set_mode` | match / training | swaps system-prompt persona (brat ↔ grudging coach) |
| `set_sass` | 0–3 | 0 = polite umpire, 3 = full McEnroe; player can say "tone it down" |
| `physical_tantrum` | — | pan-axis head shake + wheel rev-and-sigh; pan/tilt only, never fires a ball |
| `get_session_stats` | — | placement-drill stats for coaching answers |

Guardrails: anything that launches a ball goes through the same safety gate (player-ready +
not paused). The agent can never bypass it, and "stop"/"pause" is handled locally (keyword
spotted on-device) so it works even if Wi-Fi hiccups mid-rally.

### Score events + tantrums

Game events are injected into the session as text items ("EVENT: point ended, 7–3 robot.
EVENT: robot lost the game.") followed by `response.create`, so score announcing comes out in
the same live voice mid-conversation. The system prompt scripts the personality arc:

- Winning: smug, magnanimous, insufferable.
- Player on a streak: rattled, disputes imaginary line calls.
- **Robot loses: full meltdown.** "YOU CANNOT BE SERIOUS." Demands to see the umpire. Calls
  `physical_tantrum`. Accuses the net of bias. Then, sulkily, `rematch`.
- Trash talk stays about the *play* (that return, that streak, that flinch) — it's a bratty
  opponent, not a bully; `set_sass` lets the player dial it.

### Mic + duplex audio

- **Mic:** the Logitech webcam already on the robot has a built-in mic — zero new hardware,
  and it points at the player. Fallback: cheap USB conference mic. Avoid the BT speaker's mic:
  HFP profile drops the speaker to phone-call quality while active.
- **Echo:** the mic will hear McEnroe's own voice from the speaker and server VAD will
  self-interrupt. Enable PipeWire's `echo-cancel` module (webcam mic in, BT speaker out as the
  loopback pair); if it's flaky, fall back to half-duplex — mute mic while agent audio plays.
- The canned WAV cache (rev 1) stays as the **offline fallback**: no Wi-Fi → event-driven
  canned lines, no conversation, game still works.

## Bluetooth speaker on the Pi

- Bookworm uses PipeWire: pair once with `bluetoothctl` (scan on → pair → trust → connect),
  then it's the default sink; play with `paplay file.wav` or `mpv`.
- Adds ~100–300ms latency — irrelevant for post-point speech.
- Gotcha: many BT speakers sleep and swallow the first ~0.5s of audio. Fix: loop 1s of
  silence every 30s (keep-alive), or prepend 0.3s silence to every clip when baking the cache.
- Reconnect-on-boot: `bluetoothctl trust` + a systemd user unit that retries connect.

## Order of work

1. Bake-off → pick provider + voice (blocks the canned cache, nothing else)
2. `ScoreKeeper` + tool functions + mocks/tests (pure software; tools are plain methods,
   testable without any API)
3. Write the canned line set (~100 lines), bake WAV cache (offline fallback path)
4. BT speaker pairing + webcam mic + PipeWire echo-cancel on the Pi
5. Realtime agent bridge: WebSocket client, mic↑/speaker↓, tool dispatch, event injection —
   MATCH mode end-to-end conversational
6. Tantrum arc tuning + `physical_tantrum` choreography (pan shake needs the pan base built)
7. TRAINING mode persona on top of placement-drill stats

None of this blocks the feed→launcher coupler work — fully parallel track. Steps 1–3 and most
of 5 run on the laptop against mocks.
