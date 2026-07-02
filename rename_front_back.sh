#!/usr/bin/env bash
# McEnroe Bot V4 — rename launcher wheel naming top/bottom -> front/back.
# Scope (locked):
#   WHEEL_TOP -> WHEEL_FRONT          (channel_map.py ch3 + all references)
#   WHEEL_BOTTOM -> WHEEL_BACK        (channel_map.py ch4 + all references)
#   ThrottleMap.top_floor -> front_floor
#   ThrottleMap.bottom_floor -> back_floor
#   throttle_for_top -> throttle_for_front
#   throttle_for_bottom -> throttle_for_back
# EXCLUDED (intentional): WheelCommand.top_rpm / bottom_rpm, u_top / u_bottom.
# Excluded paths: _shelved/, .venv/, docs/3d-models/
set -euo pipefail
cd "$(dirname "$0")"
[ -f pyproject.toml ] || { echo "run from repo root (pyproject.toml not found)"; exit 1; }

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "!! working tree dirty — commit or stash first so this rename is one clean diff"
  exit 1
fi

PRUNE=( -path ./.venv -prune -o -path ./src/mcenroebot/_shelved -prune -o -path ./tests/_shelved -prune -o -path ./docs/3d-models -prune -o )
FILES=$(find . "${PRUNE[@]}" -name '*.py' -print)

echo "=== BEFORE: references to be renamed ==="
grep -nE '\bWHEEL_TOP\b|\bWHEEL_BOTTOM\b|\btop_floor\b|\bbottom_floor\b|\bthrottle_for_top\b|\bthrottle_for_bottom\b' $FILES || { echo "(none found — nothing to do?)"; exit 1; }
echo
read -r -p "Apply rename to the files above? [y/N] " ans
[ "${ans:-n}" = "y" ] || { echo "aborted"; exit 0; }

for f in $(grep -lE '\bWHEEL_TOP\b|\bWHEEL_BOTTOM\b|\btop_floor\b|\bbottom_floor\b|\bthrottle_for_top\b|\bthrottle_for_bottom\b' $FILES); do
  perl -pi -e '
    s/\bWHEEL_TOP\b/WHEEL_FRONT/g;
    s/\bWHEEL_BOTTOM\b/WHEEL_BACK/g;
    s/\btop_floor\b/front_floor/g;
    s/\bbottom_floor\b/back_floor/g;
    s/\bthrottle_for_top\b/throttle_for_front/g;
    s/\bthrottle_for_bottom\b/throttle_for_back/g;
  ' "$f"
  echo "edited: $f"
done

echo
echo "=== AFTER: any stragglers (should be empty) ==="
grep -nE '\bWHEEL_TOP\b|\bWHEEL_BOTTOM\b|\btop_floor\b|\bbottom_floor\b|\bthrottle_for_top\b|\bthrottle_for_bottom\b' $FILES && { echo "!! stragglers above"; exit 1; } || echo "clean"

echo
echo "=== prose mentions of top/bottom wheels (docstrings/comments — review by eye) ==="
grep -nE 'top wheel|bottom wheel|top 0\.08|bottom 0\.05|WHEEL_(FRONT|BACK).*(top|bottom)' $FILES || echo "(none)"

echo
echo "=== tests ==="
uv run pytest -q
echo
echo "Done. Review 'git diff', fix any prose flagged above, commit."
