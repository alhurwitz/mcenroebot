#!/usr/bin/env python3
"""Rally event detection over the ball-observation stream.

Consumes (t, x, y, r) observations from ball_detect (live or CSV replay) and
emits high-level events for training mode / scoring / smack talk:

  LAUNCH        ball appears and moves away fast (shot fired)
  BOUNCE        vertical direction flip: falling -> rising (image y grows down)
  RETURN_HIT    horizontal reversal at player end: ball coming back toward us
  DOUBLE_BOUNCE two bounces without a return -> point to the machine
  BALL_LOST     track dropped mid-rally (left frame / occluded)

Usage:
  python3 events.py --cam 0                 # live, on top of ball_detect tracking
  python3 events.py --replay track.csv      # offline, from a saved t,x,y,r log
  python3 ball_detect.py --cam 0 > track.csv   # how to make such a log

Events print as JSON lines; anything (rally_mode, TTS smack talk) can tail them.
All thresholds are image-space heuristics for a single fixed camera — tune the
CONSTANTS block against real footage, then lock. See EVENT_PIPELINE.md.
"""

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# ---- CONSTANTS: tune against real footage ---------------------------------
LAUNCH_SPEED_PX_S = 400  # min |v| to call it a launch
JUMP_REJECT_PX = 300  # obs farther than this from last point = decoy blob, drop
BOUNCE_VY_FLIP_PX_S = 60  # vy must swing from > +this to < -this
RETURN_VX_FLIP_PX_S = 80  # vx reversal magnitude for a return hit
LOST_TIMEOUT_S = 0.5  # gap that ends a track
MIN_TRACK_PTS = 3  # observations before velocity is trusted
RALLY_RESET_S = 3.0  # quiet time -> next launch starts a new rally
# ----------------------------------------------------------------------------


@dataclass
class Track:
    ts: list[float] = field(default_factory=list)
    xs: list[float] = field(default_factory=list)
    ys: list[float] = field(default_factory=list)

    def add(self, t: float, x: float, y: float) -> None:
        self.ts.append(t)
        self.xs.append(x)
        self.ys.append(y)
        if len(self.ts) > 8:  # short window: velocities stay current
            self.ts.pop(0)
            self.xs.pop(0)
            self.ys.pop(0)

    def vel(self) -> tuple[float, float] | None:
        """(vx, vy) px/s smoothed over the window, or None. For launch detection."""
        if len(self.ts) < MIN_TRACK_PTS or self.ts[-1] == self.ts[0]:
            return None
        dt = self.ts[-1] - self.ts[0]
        return ((self.xs[-1] - self.xs[0]) / dt, (self.ys[-1] - self.ys[0]) / dt)

    def vel_inst(self) -> tuple[float, float] | None:
        """(vx, vy) px/s from the last two points. For flip (bounce/return) detection —
        smoothing blurs sign reversals across the window."""
        if len(self.ts) < 2 or self.ts[-1] == self.ts[-2]:
            return None
        dt = self.ts[-1] - self.ts[-2]
        return ((self.xs[-1] - self.xs[-2]) / dt, (self.ys[-1] - self.ys[-2]) / dt)


class EventDetector:
    """Feed observe(); emits events via callback (default: JSON to stdout)."""

    def __init__(self, on_event: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.on_event = on_event or self._print
        self.track = Track()
        self.prev_vel: tuple[float, float] | None = None
        self.last_seen_t: float | None = None
        self.in_rally = False
        self.bounces = 0
        self.last_event_t = -1e9

    @staticmethod
    def _print(evt: dict[str, Any]) -> None:
        print(json.dumps(evt), flush=True)

    def emit(self, t: float, name: str, **data: Any) -> None:
        self.last_event_t = t
        self.on_event({"t": round(t, 3), "event": name, **data})

    def observe(self, t: float, x: float | None, y: float | None, r: float | None = None) -> None:
        if x is None or y is None:  # 'lost' frame
            if (
                self.in_rally
                and self.last_seen_t is not None
                and t - self.last_seen_t > LOST_TIMEOUT_S
            ):
                self.emit(t, "BALL_LOST", bounces=self.bounces)
                self._reset()
            return
        self.last_seen_t = t
        if self.track.ts and t - self.track.ts[-1] > RALLY_RESET_S:
            self._reset()
        # teleport guard: >JUMP_REJECT_PX between consecutive frames is a second
        # orange object flickering in, not ball motion — drop the observation.
        # (Live tracking also gates in ball_detect; this protects CSV replays.)
        if (
            self.track.ts
            and ((x - self.track.xs[-1]) ** 2 + (y - self.track.ys[-1]) ** 2) ** 0.5
            > JUMP_REJECT_PX
        ):
            return
        self.track.add(t, x, y)
        vel = self.track.vel()
        inst = self.track.vel_inst()
        if vel is None or inst is None:
            return
        vx, vy = inst

        if not self.in_rally:
            svx, svy = vel
            if (svx * svx + svy * svy) ** 0.5 > LAUNCH_SPEED_PX_S:
                self.in_rally = True
                self.bounces = 0
                self.emit(t, "LAUNCH", vx=round(svx), vy=round(svy))
        elif self.prev_vel is not None:
            pvx, pvy = self.prev_vel
            # bounce: was falling fast, now rising fast (image y is down)
            if pvy > BOUNCE_VY_FLIP_PX_S and vy < -BOUNCE_VY_FLIP_PX_S:
                self.bounces += 1
                self.emit(t, "BOUNCE", n=self.bounces, x=round(x), y=round(y))
                if self.bounces >= 2:
                    self.emit(t, "DOUBLE_BOUNCE", verdict="machine_point")
                    self._reset()
                    return
            # return hit: strong horizontal reversal after >=1 bounce
            if (
                self.bounces >= 1
                and abs(pvx) > RETURN_VX_FLIP_PX_S
                and abs(vx) > RETURN_VX_FLIP_PX_S
                and (pvx > 0) != (vx > 0)
            ):
                self.emit(t, "RETURN_HIT", verdict="player_returned")
                self._reset()
                return
        self.prev_vel = inst

    def _reset(self) -> None:
        self.track = Track()
        self.prev_vel = None
        self.in_rally = False
        self.bounces = 0


def replay(path: str) -> None:
    det = EventDetector()
    with open(path) as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 2:
                continue
            t = float(parts[0])
            if parts[1] == "lost":
                det.observe(t, None, None)
            else:
                det.observe(t, float(parts[1]), float(parts[2]))
    print("replay done", file=sys.stderr)


def live(cam: int) -> None:
    from ball_detect import track as bd_track

    det = EventDetector()
    bd_track(cam, on_obs=det.observe)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cam", type=int, default=None)
    ap.add_argument("--replay", type=str, default=None)
    args = ap.parse_args()
    if args.replay:
        replay(args.replay)
    elif args.cam is not None:
        live(args.cam)
    else:
        ap.print_help()
