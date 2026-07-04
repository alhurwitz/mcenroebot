#!/usr/bin/env bash
# CANCELLED (2026-07-04) — do not run. Safe to delete this file.
#
# This staged rename (WHEEL_TOP/BOTTOM -> WHEEL_FRONT/BACK) was backwards:
# the launch wheels straddle the ball path perpendicular to the shot axis
# (vertical drop into the nip), so at zero head roll they are physically the
# TOP and BOTTOM wheels — matching WheelCommand.top_rpm/bottom_rpm, the
# u_top/u_bottom math, and esc_bringup.py's TOP/BOTTOM channels. There is no
# fore/aft wheel in a two-wheel pinch pair.
#
# The rename had already been applied once (commit ec59cb4); it was reverted
# back to WHEEL_TOP/WHEEL_BOTTOM, top_floor/bottom_floor,
# throttle_for_top/throttle_for_bottom on 2026-07-04. See NEXT_STEPS.md §5.
echo "CANCELLED: this rename was backwards and has been reverted. See header." >&2
exit 1
