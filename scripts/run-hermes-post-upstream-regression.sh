#!/usr/bin/env bash
set -euo pipefail

HERMES_BIN="${HERMES_BIN:-/root/.local/bin/hermes}"
resolve_active_hermes_repo() {
  local launcher shebang python_path candidate
  launcher="$(readlink -f "$HERMES_BIN")"
  [[ -f "$launcher" ]] || return 1
  shebang="$(head -n 1 "$launcher")"
  python_path="${shebang#\#!}"
  candidate="$(dirname "$(dirname "$(dirname "$python_path")")")"
  [[ -f "$candidate/gateway/run.py" && -x "$candidate/venv/bin/python" ]] || return 1
  printf '%s\n' "$candidate"
}
REPO="${REPO:-$(resolve_active_hermes_repo)}"
PYBIN="${PYBIN:-$REPO/venv/bin/python}"
LOG="${LOG:-/tmp/hermes-post-upstream-regression.log}"

[[ -d "$REPO" ]] || { echo "missing repo: $REPO" >&2; exit 2; }
[[ -x "$PYBIN" ]] || { echo "missing python: $PYBIN" >&2; exit 2; }
mkdir -p "$(dirname "$LOG")"

TEST_ROOT="$(mktemp -d /tmp/hermes-post-upstream-regression-XXXXXX)"
TEST_HOME="$TEST_ROOT/hermes-home"
OS_HOME="$TEST_ROOT/os-home"
mkdir -p "$TEST_HOME" "$OS_HOME"
export TEST_ROOT TEST_HOME
export HOME="$OS_HOME"
cleanup() {
  python3 -c 'import os, shutil; shutil.rmtree(os.environ["TEST_ROOT"], ignore_errors=True)'
}
trap cleanup EXIT

export HERMES_HOME="$TEST_HOME"
unset DISCORD_ALLOWED_USERS DISCORD_ALLOWED_CHANNELS DISCORD_FREE_RESPONSE_CHANNELS || true

cd "$REPO"
printf '[%s] START Hermes post-upstream regression pack\n' "$(date -Iseconds)" | tee "$LOG"
"$PYBIN" -m pytest -q \
  tests/gateway/test_delivery_ledger.py \
  tests/gateway/test_delivery_ledger_producer.py \
  tests/gateway/test_turn_lease.py \
  tests/gateway/test_platform_reconnect.py \
  tests/gateway/test_run_progress_topics.py::test_run_agent_merges_leftover_steer_into_earlier_queued_turn \
  tests/cron/test_execution_ledger.py \
  tests/hermes_cli/test_config.py \
  tests/hermes_cli/test_doctor.py \
  2>&1 | tee -a "$LOG"
printf '[%s] PASS Hermes post-upstream regression pack\n' "$(date -Iseconds)" | tee -a "$LOG"
