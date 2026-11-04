#!/usr/bin/env bash
set -euo pipefail

HERMES_BIN="${HERMES_BIN:-/root/.local/bin/hermes}"
REPO="${REPO:-}"
MODE="apply"
if [[ "${1:-}" == "--check" || "${1:-}" == "--check-only" ]]; then
  MODE="check"
elif [[ -n "${1:-}" ]]; then
  echo "usage: $0 [--check]" >&2
  exit 2
fi

resolve_repo() {
  python3 "${MGS_RUNTIME_RESOLVER:-/root/mgs-agent/scripts/mgs-hermes-runtime-resolve.py}" --launcher "$HERMES_BIN" --field repo
}

if [[ -z "$REPO" ]]; then
  REPO="$(resolve_repo)" || {
    echo "ERROR cannot resolve Hermes repo from $HERMES_BIN" >&2
    exit 3
  }
fi
[[ -d "$REPO/.git" || -f "$REPO/.git" ]] || {
  echo "ERROR not a Git checkout: $REPO" >&2
  exit 3
}

PATCH_DIR="${PATCH_DIR:-/root/mgs-agent/patches/hermes}"
CANONICAL_PATCHES=()
if [[ -f "$PATCH_DIR/current-runtime-manifest.json" ]]; then
  mapfile -t CANONICAL_PATCHES < <(python3 - "$PATCH_DIR/current-runtime-manifest.json" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
for name in [m["primary_patch"], *m.get("supplemental_patches", [])]:
    print(name)
PY
  )
fi
PATCHES=(
  "${CANONICAL_PATCHES[@]/#/$PATCH_DIR/}"
  "$PATCH_DIR/mgs-runtime-customizations-2026-10-21-main-4d043038.patch"
  "$PATCH_DIR/mgs-runtime-customizations-2026-08-11-main-c0106e50.patch"
  "$PATCH_DIR/mgs-runtime-customizations-2026-08-11-v0200.patch"
  "$PATCH_DIR/mgs-runtime-customizations-2026-08-02-v0191.patch"
)

for patch in "${PATCHES[@]}"; do
  [[ -s "$patch" ]] || continue
  if git -C "$REPO" apply --reverse --check "$patch" >/dev/null 2>&1; then
    echo "PASS customizations already present patch=$(basename "$patch") repo=$REPO"
    exit 0
  fi
done

for patch in "${PATCHES[@]}"; do
  [[ -s "$patch" ]] || continue
  if git -C "$REPO" apply --check "$patch" >/dev/null 2>&1; then
    if [[ "$MODE" == "check" ]]; then
      echo "PASS patch applicable patch=$(basename "$patch") repo=$REPO"
    else
      git -C "$REPO" apply "$patch"
      git -C "$REPO" diff --check
      echo "APPLIED patch=$(basename "$patch") repo=$REPO"
    fi
    exit 0
  fi
done

echo "ERROR no known MGS customization patch is present or applicable repo=$REPO" >&2
exit 1
