# V4 Next Steps — 2026-07-02

All software done. Everything below is hardware bring-up, in dependency order.

## 1. Print queue (PETG, in order)
1. ~~motor_mount_coupon~~ **DONE (v3, 2026-07-05):** mounting goes through the silver X-mount outer holes (~16–18mm pitch radius, flush motor screws) — coupon v3 confirmed flush + snug. Motor-face pattern no longer used.
2. ~~`launcher_bracket_v3`~~ **SUPERSEDED 2026-07-04 by `launcher_bracket_v4_tri`** — three wheels at 120° (bottom + upper pair), sidespin-capable, axial feed through bulkhead tube (no top wheel, no corridor dodge). Motors: 3× 1000KV from stock. Bottom module keeps the v3 flat plate → `launcher_bench_dock_v1` (dock + 0/10/20/30° wedges) holds it for table testing. With only 2 ESCs: drive the upper pair, bottom idles. Print dock + wedges too.
3. `feed_unit_v1` — **regenerated 2026-07-05** against the printed arm's measured geometry (sweep r=61.4, not the doc's 68). Known bench-tune item: mouth pinch at gate on arm return (`LIP_THETA` in script). Servo near-side tabs (x=+14) clamp with M3 + washers — by the servo's own geometry those holes land at the window edge. Shim servo along Y so spline face = arm face.
4. `scoop_arm_FINAL_cup26`
5. **NEW** `scoop_endstops_v1` — adjustable, prints now; no driven-run measurement needed anymore
6. **NEW** `hopper_neckdown_v1` — parametric; placeholder torso dims labeled in script
7. **NEW** `feed_launcher_coupler_v1` — telescoping, gap adjustable 55–85mm; flange patterns are placeholders until matched against the real flanges

## 2. Bench sequence
1. **Feed unit:** drive HD3512MG by timed pulses → confirm exactly-one-ball metering, clean cup-26 release at speed, no pinch at chute mouth (tune lip if it catches). Slide end-stop blocks to observed LOAD/DISCH edges, tighten.
2. **Launcher:** single wheel driven (until 2nd A2212 arrives), other idle → ball drops the vertical chute into the V and fires. Set nip squeeze (37mm nip / 3mm squeeze nominal).
3. **Coupled:** feed unit + coupler + launcher — meter → drop → fire, one ball per rock.

## 3. Measurements still owed
| Measurement | Unblocks |
|---|---|
| Torso gap (both parts in hand) | Coupler final length → set `GAP` and reprint or lock telescope |
| Torso cavity dims | Hopper final size → re-run `generate_parts.py` with real `HOPPER_TOP_W/H` |
| Flange hole patterns (from printed feed unit + bracket) | Coupler flange bolt patterns |
| Stomach port Z, launcher X offset + swing cone, pan axis offset | Chassis deck placeholders |

## 4. Purchases
- 3rd ESC (30A) — full tri-wheel drive; 2-of-3 bench works meanwhile
- ~~2nd A2212 1400KV~~ (stale: stock is 4× 1000KV + 1× 1400KV, motors covered)
- Possible 5V/5A servo rail upgrade if brownouts under loaded head

## 5. Repo hygiene (software, quick)
- ~~Execute staged rename~~ **CANCELLED + REVERTED (2026-07-04):** the front/back rename was backwards — the wheel pair straddles the vertical drop path, so at zero head roll they are physically TOP/BOTTOM (matches `WheelCommand.top_rpm/bottom_rpm`, `u_top/u_bottom`, esc_bringup's counter-rotation check). The rename had already been applied (commit ec59cb4); reverted code back to `WHEEL_TOP/BOTTOM`, `top_floor/bottom_floor`, `throttle_for_top/bottom`. `rename_front_back.sh` neutered (marked CANCELLED, exits 1 — safe to delete). `ThrottleMap` floors + helpers and `controller.throttles()` already exist (commit 3873e6c) and keep working; 520 tests pass.
- ~~Mark `FEEDER_PLAN.md` deprecated header~~ **DONE (2026-07-04):** no `docs/FEEDER_PLAN.md` exists; the escapement-disc/auger design doc is `docs/superpowers/specs/2026-06-23-feeder-design.md` — deprecation header added there. **NOTE:** `docs/feed_launch_reconciled.md` (the canonical spec, referenced as SSOT by `launcher_bracket_v3/generate_parts.py`) is missing from the repo — commit it if it exists in a session, else the SSOT is the bracket generator + this file.

## 6. After bench passes
- Lock torso layout → final coupler + hopper dims
- Chassis deck stack: fill the three gated placeholder values
- Vision placement drill on-Pi smoke test (software already done)
