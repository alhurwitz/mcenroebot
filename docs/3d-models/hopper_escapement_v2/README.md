# hopper_escapement_v2 — drive-train redesign

> **CURRENT PATH (AJ, 2026-08-29): `drive_rod_v3`.** One printed part, ~5 cm3,
> straight onto the `escapement_disk_v1` you already have. No disk reprint, no
> drilling. See **drive_rod_v3** below. The earlier routes on this page —
> reprinting the disk (`escapement_disk_v2` + `spline_coupler_v2` +
> `spline_clamp_v2`/`spline_hub_v3`) and the `*_v2b` reuse variant — are kept
> for their reasoning but are **not the thing to print**.

---

# drive_rod_v3 — spline to disk, one part, THROUGH the disk

    generate_rod_v3.py   ->  drive_rod_glue_v3.stl   bore 5.6  <- PRINT THIS
                             drive_rod_press_v3.stl  bore 5.2
    check_rod_v3.py          all checks pass, ray-cast off the printed parts
    preview_rod_v3.py    ->  preview_rod_v3.png      section at y=0

| | |
|---|---|
| Print | **nose DOWN, with a brim.** 4 perimeters, 40%, no supports. ~5 cm3, well under an hour |
| Hardware | **4x M3x10.** Not M3x12, not M3x16 — see below |
| Disk | `escapement_disk_v1`, **as printed**. Not reprinted, not drilled |
| Replaces | `spline_coupler_v2` + `spline_hub_v3` + `escapement_disk_v2` |

## What it is

A single rod: a 19.9 mm socket for the servo spline at the bottom, a Ø25.2
flange that bolts up into the disk's existing underside recess, and a Ø6 pin
that carries on **up through the disk's existing Ø6.5 centre hole** to just
below the top face.

    z 48.0  nose Ø10, socket mouth  (3.4 mm into the saddle cutout)
    z 54.0  45 deg cone
    z 61.6  flange Ø25.2, 4x M3 head pockets
    z 67.9  flange top — SEATS on the recess floor
    z 107.4 pin top — 1.0 mm below the disk top, 2.0 mm below the lid

## Why through-and-not-just-bolted

`generate_reuse.py` (the v2b route) named its own worst property: reusing the
printed disk drops the drive onto a 3.5 mm spigot at the disk's underside —
"strictly the weaker joint," because 3.5 mm of engagement is all that keeps the
disk square on the rod.

Running the rod through the disk fixes exactly that, for nothing. **The pin
journals the disk over 39.5 mm instead of 3.5.** The disk cannot cock on the rod
regardless of what the four screws do. And it needs no drilling — v2b had to
open the centre hole Ø6.5 -> Ø13; a Ø6 pin just goes through it.

## Why the socket is long and glued, not short and pressed

The one dimension this project has never had is how far the MG996R spline stands
above the tab plane. It killed `SV_TAB_TO_HORN = 13.0`, and it cannot be
recovered from the STLs either — the saddle (z 45.4..51.4, an 18x42 body cutout)
and the flat floor underside at 51.4 do not pin down where the spline top lands.

So the rod has no opinion about it. **The socket is 19.9 mm deep and open at the
bottom; the spline stops wherever it stops and the adhesive takes it from
there.** There is no SPAN, no gauge rod, no fit coupon.

A press fit cannot do that. Interference has to be *where the spline is*, and on
a 19.9 mm socket with an unknown spline height you cannot place a 10 mm
interference band and know the spline is inside it — put it at the mouth and a
high spline sits in clear air above it. A uniform Ø5.2 interference over 19.9 mm
is a 20 mm press, which is the galling failure `drive_rod_v1` was rejected for.
Adhesive does not care where the spline stops. That is the whole argument.

`drive_rod_press_v3` (bore 5.2, no grooves) exists only if 5.6 feels loose on
your actual spline. Expect a hard push; open it with a 5.5 mm bit if it will not
start. Too tight is fixable, too loose is a reprint — same reasoning as
`generate_hub.py`.

## The nose is deliberately too long

It hangs 3.4 mm below the floor underside, into the saddle's servo cutout. If it
fouls the servo case, **saw it back** — there are scribe rings at z=49.0 and
z=52.0 (1 mm and 4 mm up from the tip). Long-and-trimmable is the recoverable
direction; short is a reprint.

Write down which ring you cut to. That number is the spline height this project
has never actually had, and every future part on this axis wants it.

## M3x10 ONLY — the trap in the disk

Memory recorded the disk's tapped holes as "11 mm deep". They are, measured from
the disk's underside — but **the first 3.5 mm of that is the recess, which is
open space.** There is only **7.5 mm of threadable material**, z 67.9..75.4.

    M3x10  ->  6.7 mm of engagement.        Correct.
    M3x12  ->  8.7 mm needed in 7.5.        Bottoms out and jacks the rod
    M3x16  ->  worse.                        off its seat.

`check_rod_v3.py` measures the tap ceiling off the real STL and asserts this.

## Nothing carries the disk but the floor

v1 hung the disk off the spline; that is the *only* reason its height ever
mattered. Here the disk sits on the base floor and the rod hangs from the disk.
The rod has no shoulder anywhere near the disk's underside, on purpose — its
only contact with the disk is the flange **top** face against the recess floor,
which the four screws pull up into. The Ø3 vent up the pin means the spline
cannot bottom in the socket and lift the disk either.

## Assembly

1. Disk upside down on the bench.
2. Rod pin-first through the centre hole, flange into the recess, **4x M3x10**
   up from below. Heads recess into their pockets; nothing sits proud.
3. Drop disk + rod into the drum from above. **The disk lands on the floor.**
   The rod hangs down the Ø28 bore.
4. Adhesive on the spline. Lift the servo up until its tabs meet the saddle and
   screw the saddle. The spline slides into the socket as far as it goes and
   stops there. Nothing is forced and nothing is measured.
5. Look down the Ø3 vent from the disk's top face to confirm engagement **before
   the adhesive goes off.** Then lid, cone, done.

Pin fit: Ø6.0 into a printed Ø6.5 hole. If it will not enter, run a 6.5 mm bit
through once — it self-pilots. Do not force it; the pin is the centring datum.

## Verify

    python3 generate_rod_v3.py && python3 check_rod_v3.py && python3 preview_rod_v3.py

## Still outstanding elsewhere

`scripts/triwheel_spin_test.py` still reads `LOAD_ANGLE 70.0 / DISCH_ANGLE 175.0`
(lines 113-114). The escapement wants **LOAD 15 / DISCH 165**. That edit has
never landed — fix it before powering the servo. `drum_lid_v1.stl` is still
unprinted.

---

# Earlier routes on this axis (kept for the reasoning, do not print)

The mechanism is unchanged. What changed is how torque gets from the MG996R
into the disk, because that joint failed three times in a row.

## ~~Print these three~~ (SUPERSEDED by drive_rod_v3 — do not print)

| Part | Vol | Print |
|---|---|---|
| `escapement_disk_v2.stl` | 556 cm³ | **underside down**, 10–15% gyroid, no supports (~110 g filament) |
| `spline_coupler_v2.stl` | 8.3 cm³ | boss up, 4 perims, 40%, no supports |
| `spline_clamp_v2.stl` | 6.0 cm³ | hex up, 4 perims, 50%, no supports |

**Print the disk underside-down.** Its underside is deliberately flat, so the
first layer is the full 136 mm face. An earlier cut relieved it to a narrow
r60–68 bearing land; that was wrong twice over — it *raises* friction (the
sliding radius moves from 45.3 mm to 64.1 mm, 0.26 → 0.36 kg·cm, because thrust
torque follows mean radius, not contact area), and it puts a 120 mm unsupported
span 0.4 mm off the glass on layer one. The only real overhang left is the
counterbore ceiling at z=86 — a 7.6 mm annular bridge, which any slicer walks.

Plus `drum_lid_v1.stl` from v1 — unchanged, still unprinted, print it as-is.

**Kept and not reprinted:** `hopper_base_v1` (805 cm³) and `hopper_cone_v1`.
A clean sheet was authorised; this doesn't spend it, because the base was never
what was broken — its Ø28 bore and open-from-below cavity are exactly what v2
needs. All v2 geometry is verified against the **real** `hopper_base_v1.stl`,
not against v1's source constants.

Hardware: 4× M3×35, 1× M3×16 + nut. No heat-set inserts. No grub screws.

## The root cause

Three failures, one cause — and it isn't any of the individual numbers:

- 2026-07-25 `SV_TAB_TO_HORN = 13.0` was a guess; the spline never reached.
- 2026-08-16 `drive_rod_v1`'s 30 mm slip socket: *"slides in and off rather than being tight."*
- The tight version needs a press bore → needs a fit coupon → another round trip.

**The tight joint was buried where nobody can see or reach it.** A coaxial
coupling inside a Ø28 bore, under the floor, beneath a 568 cm³ disk, has to be
perfect *before* assembly because there's no way to adjust it after. Every fix
that keeps it there inherits the problem.

## The fix — split the joint where the requirements conflict

```
servo spline --[ spline_clamp_v2 ]-- hex --[ spline_coupler_v2 ]-- disk
                 TIGHT, adjustable          LOOSE, form-locked
                 done on the BENCH          slides together blind
```

- **The clamp** grips the spline and is tightened **in your hand, off the
  machine**. Being a clamp and not a press fit, it doesn't care what your
  printer does to hole diameters. The fit coupon is off the critical path.
- **The coupler** screws to the disk **from above** and ends in a hex socket
  that drops over the clamp's boss. That joint is deliberately sloppy —
  0.5 mm across flats. Torque goes by **shape**, so slop costs nothing, and it
  engages blind because a hex self-orients within 60°.

The split is physical too: the clamp owns the floor bore, the coupler lives
entirely above the floor. Only a Ø10 hex ever crosses z=64.

### What that buys

**A 20 mm tolerance window on the servo's spline height** (−13.4 / +6.5 mm off
nominal, ≥8 mm of hex engagement throughout). SPAN is not a dimension in this
design. There is nothing to measure and nothing to get wrong.

The bias is deliberate: v1 failed because the real spline sits *lower* than
13 mm, so the window is skewed to tolerate a low spline.

## Other changes

**The disk now rides on the floor** (`DISK_GAP` 0.4 → 0). In v1 the disk *hung
from the servo spline* — that's the only reason `SV_TAB_TO_HORN` was critical
at all. Let the floor carry it and the dimension stops mattering. Friction cost
is ~0.36 kg·cm on an 8 mm annular land at r=64, against ~10 kg·cm available.

**The coupler boss runs up to the disk's mid-height (z=86).** Your idea, and
it's right — ball centre is z=84, so drive torque and ball reaction now act in
the same plane and the disk can't cock about a shallow bottom flange.

**The hex socket is a through hole** with a Ø12 relief above it in the disk. The
boss can never bottom out and jack the disk off its floor. The relief doubles as
a sight line — look down it to confirm the hex is engaged.

## Why the disk is still 44 mm — I didn't take this one

You proposed thinning it. It breaks the metering, and here's the arithmetic.

The disk top face **is** the shear plane. The queued ball under the cone throat
has to rest on it. Carried ball sits on the floor (z=64) so its crown is at 104.
Any disk top below 104 and the queued ball rests on the *carried* ball instead
and follows it out of the pocket — double feed or jam. They don't clear until
their centres are 40 mm apart, which at 28 mm of vertical offset needs **28.6 mm
of lateral travel** — far more than the pocket has moved when the queued ball
commits.

That's why v1 has `DISK_T = 44.0  # >= ball, so the stack never sees the pocket
sideways`. `check.py` now asserts it so nobody thins it by eye later.

Also: **568 cm³ is displaced volume, not filament.** At 10–15% gyroid that disk
is ~110 g.

## Assembly

1. Clamp onto the servo spline **on the bench** — pinch bolt, real torque, you
   can see it. Optionally add the servo's own centre screw through the Ø4 bore.
2. Coupler into the disk's underside counterbore; 4× M3×35 **down from the disk's
   top face**, self-tapping into the coupler.
3. Drop the disk into the drum. It sits on the floor.
4. Lift servo + clamp up into the cavity from below. The hex finds the socket.
   Check engagement down the sight line. Screw the saddle up as before.
5. Lid, cone, done.

Removal is the reverse and needs no tools inside the drum — pull the servo down
and the hex just disengages.

## Verify

```
python3 generate_parts.py && python3 check.py
```

`check.py` ray-casts against the real v1 STLs. Point it elsewhere with
`V1_DIR=...` if the sibling folder moves. All checks currently pass.

## Still assumed

| Value | Risk |
|---|---|
| MG996R spline Ø5.92 | low — the clamp is adjustable, so being wrong costs a pinch-bolt turn, not a reprint |
| `servo_saddle_v1` positions the servo | low — exact height no longer matters (20 mm window) |

## Still outstanding elsewhere

`scripts/triwheel_spin_test.py` still reads `LOAD_ANGLE 70.0 / DISCH_ANGLE 175.0`
(lines 113–114). The escapement wants **LOAD 15 / DISCH 165**. That edit never
landed — fix before powering the servo.
