#!/usr/bin/env bash
set -euo pipefail
# Candidate-only successor: fresh interpreter per module; retained scratch.
HERMES_BIN="${HERMES_BIN:-/root/.local/bin/hermes}"
resolve_active_hermes_repo() {
  python3 "${MGS_RUNTIME_RESOLVER:-/root/mgs-agent/scripts/mgs-hermes-runtime-resolve.py}" --launcher "$HERMES_BIN" --field repo
}
REPO="${REPO:-$(resolve_active_hermes_repo)}"
PYBIN="${PYBIN:-$(python3 "${MGS_RUNTIME_RESOLVER:-/root/mgs-agent/scripts/mgs-hermes-runtime-resolve.py}" --launcher "$HERMES_BIN" --field python)}"
[[ -x "$PYBIN" ]] || { printf 'missing repo interpreter\n' >&2; exit 2; }
if ! "$PYBIN" -c "import pytest" >/dev/null 2>&1; then
  PYBIN="$(python3 "${MGS_RUNTIME_RESOLVER:-/root/mgs-agent/scripts/mgs-hermes-runtime-resolve.py}" --launcher "$HERMES_BIN" --field test_python)"
fi
[[ -x "$PYBIN" ]] || { printf 'prebuilt test environment missing\n' >&2; exit 2; }
TMPDIR="${TMPDIR:-/root/.hermes/profiles/zeus/cache/scratch}"
TEST_ROOT="$(mktemp -d "$TMPDIR/hermes-post-upstream-regression-XXXXXX")"
mkdir -p "$TEST_ROOT/os-home" "$TEST_ROOT/temp"
export HOME="$TEST_ROOT/os-home" TMPDIR="$TEST_ROOT/temp" TMP="$TEST_ROOT/temp" TEMP="$TEST_ROOT/temp"
# The native conftest must allocate HERMES_HOME, not mistake a pre-import home
# for a live profile. Native runner drops credentials/routing variables.
unset HERMES_HOME HERMES_PROFILE DISCORD_ALLOWED_USERS DISCORD_ALLOWED_CHANNELS DISCORD_FREE_RESPONSE_CHANNELS || true
LOG="${LOG:-$TEST_ROOT/regression.log}"
mkdir -p "$(dirname "$LOG")"
cd "$REPO"
printf 'START post-upstream regression; scratch retained: %s\n' "$TEST_ROOT" | tee "$LOG"
HERMES_PYTHON="$PYBIN" HERMES_TEST_WORKERS="${HERMES_PATCH_TEST_WORKERS:-2}" HERMES_TEST_FILE_TIMEOUT=180 HERMES_TEST_FILE_RETRIES=0 \
  "$PYBIN" "${MGS_TEST_RUNNER_WRAPPER:-/root/mgs-agent/scripts/mgs-native-test-runner.py}" "$REPO" -q \
  tests/gateway/test_delivery_ledger.py \
  tests/gateway/test_delivery_ledger_producer.py \
  tests/gateway/test_turn_lease.py \
  tests/gateway/test_platform_reconnect.py \
  tests/gateway/test_run_progress_topics.py \
  tests/cron/test_execution_ledger.py \
  tests/hermes_cli/test_config.py \
  tests/hermes_cli/test_doctor.py 2>&1 | tee -a "$LOG"
printf 'PASS post-upstream regression; no scratch deleted\n' | tee -a "$LOG"
