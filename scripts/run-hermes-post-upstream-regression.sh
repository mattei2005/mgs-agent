#!/usr/bin/env bash
set -euo pipefail

REPO="${REPO:-/root/.hermes/hermes-agent}"
PYBIN="${PYBIN:-$REPO/venv/bin/python}"
LOG="${LOG:-/tmp/hermes-post-upstream-regression.log}"

[[ -d "$REPO" ]] || { echo "missing repo: $REPO" >&2; exit 2; }
[[ -x "$PYBIN" ]] || { echo "missing python: $PYBIN" >&2; exit 2; }
mkdir -p "$(dirname "$LOG")"

TEST_HOME="$(mktemp -d /tmp/hermes-post-upstream-regression-XXXXXX)"
export TEST_HOME
cleanup() {
  python3 -c 'import os, shutil; shutil.rmtree(os.environ["TEST_HOME"], ignore_errors=True)'
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
  tests/cron/test_execution_ledger.py \
  tests/hermes_cli/test_config.py \
  tests/hermes_cli/test_doctor.py \
  2>&1 | tee -a "$LOG"
printf '[%s] PASS Hermes post-upstream regression pack\n' "$(date -Iseconds)" | tee -a "$LOG"
