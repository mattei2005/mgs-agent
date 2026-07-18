#!/usr/bin/env bash
# cron-smoke-test.sh — Executa smoke test dos crons MGS sem alterar schedules.
#
# Política:
# - Executa jobs seguros/idempotentes.
# - Executa jobs de risco somente em --dry-run quando disponível.
# - Skip por design para jobs que disparam alertas/webhooks ou são sensíveis a horário.
# - Escreve relatório em logs/cron-smoke-test.log e retorna 1 se algum RUN falhar.

set -euo pipefail

BASE="/root/mgs-agent"
LOG="${BASE}/logs/cron-smoke-test.log"
mkdir -p "$(dirname "$LOG")"

TS="$(date -Iseconds)"
FAILS=0
RUNS=0
SKIPS=0

run_job() {
  local name="$1"
  local mode="$2"
  local cmd="$3"
  local start end rc duration
  start=$(date +%s)
  echo "[$TS] RUN ${name} (${mode})" | tee -a "$LOG"
  set +e
  timeout 180 bash -lc "$cmd" >> "$LOG" 2>&1
  rc=$?
  set -e
  end=$(date +%s)
  duration=$((end-start))
  RUNS=$((RUNS+1))
  if [[ "$rc" -eq 0 ]]; then
    printf '%-32s | %-8s | OK   | %ss\n' "$name" "$mode" "$duration"
    echo "[$TS] OK ${name} rc=0 duration=${duration}s" >> "$LOG"
  else
    printf '%-32s | %-8s | FAIL | rc=%s %ss\n' "$name" "$mode" "$rc" "$duration"
    echo "[$TS] FAIL ${name} rc=${rc} duration=${duration}s" >> "$LOG"
    FAILS=$((FAILS+1))
  fi
}

skip_job() {
  local name="$1"
  local reason="$2"
  SKIPS=$((SKIPS+1))
  printf '%-32s | %-8s | SKIP | %s\n' "$name" "skip" "$reason"
  echo "[$TS] SKIP ${name}: ${reason}" >> "$LOG"
}

printf 'Cron smoke test — %s\n' "$TS"
printf '%-32s | %-8s | %-4s | %s\n' "Script" "Modo" "Stat" "Detalhe"
printf '%-32s-+-%-8s-+-%-4s-+-%s\n' "--------------------------------" "--------" "----" "------------------------------"

# Safe/idempotentes
run_job "sync-souls.sh" "safe" "${BASE}/scripts/sync-souls.sh"
run_job "monitor-auto-push.sh" "safe" "${BASE}/scripts/monitor-auto-push.sh"
run_job "check-pending-reports.sh" "safe" "${BASE}/scripts/check-pending-reports.sh"
run_job "monitor-service-restarts.sh" "safe" "${BASE}/scripts/monitor-service-restarts.sh"
run_job "monitor-tool-loops.sh" "safe" "${BASE}/scripts/monitor-tool-loops.sh"
run_job "monitor-hermes-updates.sh" "safe" "${BASE}/scripts/monitor-hermes-updates.sh"
run_job "track-article-cost.sh" "safe" "${BASE}/scripts/track-article-cost.sh"
run_job "pendencia-render-md.sh" "safe" "${BASE}/scripts/pendencia-render-md.sh"
run_job "chat-log.sh --rebuild-index" "safe" "${BASE}/scripts/chat-log.sh --rebuild-index"
run_job "sync-codex-oauth.sh --dry-run" "dry-run" "${BASE}/scripts/sync-codex-oauth.sh --dry-run"
run_job "cron-control-plane.py" "safe" "${BASE}/scripts/cron-control-plane.py --write-doc"
run_job "monitor-cron-stale-logs.sh --dry-run" "dry-run" "${BASE}/scripts/monitor-cron-stale-logs.sh --dry-run"
run_job "hermes-news-watchdog.py --dry-run" "dry-run" "${BASE}/scripts/hermes-news-explainer-watchdog.py --dry-run"
run_job "monitor-gpt55-oauth-cost.sh --dry-run" "dry-run" "${BASE}/scripts/monitor-gpt55-oauth-cost.sh --dry-run"
run_job "monitor-yoast-health-eggbev.sh --dry-run" "dry-run" "${BASE}/scripts/monitor-yoast-health-eggbev.sh --dry-run"
run_job "mgs-safety-backup.sh --dry-run" "dry-run" "${BASE}/scripts/mgs-safety-backup.sh --dry-run"
run_job "infra-discovery.sh" "safe" "${BASE}/scripts/infra-discovery.sh"

# Risky/write-heavy: dry-run when possible
run_job "cleanup-zombie-sessions.sh" "dry-run" "${BASE}/scripts/cleanup-zombie-sessions.sh --dry-run"
run_job "housekeeping-bak-cleanup.sh" "dry-run" "RETENTION_DAYS=15 ${BASE}/scripts/housekeeping-bak-cleanup.sh --dry-run"

# Skip by design
# Nenhum skip fixo: jobs que poderiam postar/deletar rodam em --dry-run acima.

printf '\nResumo: runs=%d skips=%d fails=%d log=%s\n' "$RUNS" "$SKIPS" "$FAILS" "$LOG"
echo "[$TS] SUMMARY runs=${RUNS} skips=${SKIPS} fails=${FAILS}" >> "$LOG"

if [[ "$FAILS" -gt 0 ]]; then
  exit 1
fi
