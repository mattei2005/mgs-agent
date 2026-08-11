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
  local launcher python_path candidate
  launcher="$(readlink -f "$HERMES_BIN")"
  [[ -f "$launcher" ]] || return 1
  python_path="$(sed -n '1s/^#!//p' "$launcher")"
  candidate="$(dirname "$(dirname "$(dirname "$python_path")")")"
  [[ -f "$candidate/gateway/run.py" ]] || return 1
  printf '%s\n' "$candidate"
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
PATCHES=(
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
