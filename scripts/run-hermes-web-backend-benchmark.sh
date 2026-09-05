#!/usr/bin/env bash
# Run the shared web-backend benchmark with the active Hermes Python.
set -euo pipefail

HERMES_BIN="$(readlink -f "$(command -v hermes)")"
if [[ ! -r "$HERMES_BIN" ]]; then
  printf 'ERROR: Hermes executable is not readable\n' >&2
  exit 1
fi

IFS= read -r SHEBANG < "$HERMES_BIN"
HERMES_PYTHON="${SHEBANG#\#!}"
if [[ "$SHEBANG" == "$HERMES_PYTHON" || ! -x "$HERMES_PYTHON" ]]; then
  printf 'ERROR: could not resolve the active Hermes Python from %s\n' "$HERMES_BIN" >&2
  exit 1
fi

exec "$HERMES_PYTHON" /root/mgs-agent/scripts/benchmark-hermes-web-search-backends.py "$@"
