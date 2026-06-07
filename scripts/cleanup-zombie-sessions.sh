#!/bin/bash
# Fecha sessoes Hermes "zombies" (ended_at NULL, sem atividade recente).
#
# Protecoes:
# - Varre todos os profiles com state.db em /root/.hermes/profiles/*
# - Usa ultima atividade real: max(sessions.started_at, messages.timestamp)
# - Grace period default 180min para nao fechar sessoes longas ativas por engano
# - Marca end_reason = 'cleanup_zombie_cron' pra distinguir
# - --dry-run conta/lista elegiveis sem atualizar state.db
#
# Roda via cron a cada hora.

set -euo pipefail

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
elif [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    echo "Usage: $0 [--dry-run]"
    exit 0
elif [ -n "${1:-}" ]; then
    echo "ERROR: argumento desconhecido: $1" >&2
    echo "Usage: $0 [--dry-run]" >&2
    exit 2
fi

LOG="/root/mgs-agent/logs/cleanup-zombie-sessions.log"
TIMESTAMP=$(date '+%Y-%m-%dT%H:%M:%S%z')
GRACE_MINUTES="${GRACE_MINUTES:-180}"
TOTAL=0
PROFILES_DIR="/root/.hermes/profiles"

mkdir -p "$(dirname "$LOG")"

echo "[$TIMESTAMP] START cleanup-zombie-sessions dry_run=$DRY_RUN grace=${GRACE_MINUTES}min" >> "$LOG"

for DB in "$PROFILES_DIR"/*/state.db; do
    [ -f "$DB" ] || continue
    AGENT=$(basename "$(dirname "$DB")")

    OLD_COUNT=$(sqlite3 "$DB" "
        WITH activity AS (
          SELECT s.id,
                 MAX(s.started_at, COALESCE(MAX(m.timestamp), s.started_at)) AS last_activity
          FROM sessions s
          LEFT JOIN messages m ON m.session_id = s.id
          WHERE s.ended_at IS NULL
          GROUP BY s.id
        )
        SELECT COUNT(*) FROM activity
        WHERE (strftime('%s', 'now') - last_activity) > ($GRACE_MINUTES * 60);
    " 2>/dev/null || echo 0)

    TOTAL=$((TOTAL + OLD_COUNT))

    if [ "$OLD_COUNT" -gt 0 ]; then
        SAMPLE=$(sqlite3 "$DB" "
            WITH activity AS (
              SELECT s.id,
                     MAX(s.started_at, COALESCE(MAX(m.timestamp), s.started_at)) AS last_activity
              FROM sessions s
              LEFT JOIN messages m ON m.session_id = s.id
              WHERE s.ended_at IS NULL
              GROUP BY s.id
            )
            SELECT substr(id,1,12) || '@' || datetime(last_activity, 'unixepoch')
            FROM activity
            WHERE (strftime('%s', 'now') - last_activity) > ($GRACE_MINUTES * 60)
            ORDER BY last_activity ASC
            LIMIT 8;
        " 2>/dev/null | paste -sd ', ' - || true)

        if [ "$DRY_RUN" -eq 1 ]; then
            echo "[$TIMESTAMP] DRY-RUN $AGENT: would close $OLD_COUNT zombie sessions (grace=${GRACE_MINUTES}min; sample=${SAMPLE:-n/a})" >> "$LOG"
        else
            NOW=$(date +%s)
            sqlite3 "$DB" "
                WITH activity AS (
                  SELECT s.id,
                         MAX(s.started_at, COALESCE(MAX(m.timestamp), s.started_at)) AS last_activity
                  FROM sessions s
                  LEFT JOIN messages m ON m.session_id = s.id
                  WHERE s.ended_at IS NULL
                  GROUP BY s.id
                )
                UPDATE sessions
                SET ended_at = MAX(started_at + 1, $NOW - 60),
                    end_reason = 'cleanup_zombie_cron'
                WHERE ended_at IS NULL
                  AND id IN (
                    SELECT id FROM activity
                    WHERE (strftime('%s', 'now') - last_activity) > ($GRACE_MINUTES * 60)
                  );
            " 2>/dev/null

            echo "[$TIMESTAMP] $AGENT: closed $OLD_COUNT zombie sessions (grace=${GRACE_MINUTES}min; sample=${SAMPLE:-n/a})" >> "$LOG"
        fi
    else
        echo "[$TIMESTAMP] OK $AGENT: zero eligible zombie sessions (grace=${GRACE_MINUTES}min)" >> "$LOG"
    fi
done

if [ "$DRY_RUN" -eq 1 ]; then
    echo "[$TIMESTAMP] DRY-RUN total eligible zombie sessions: $TOTAL" >> "$LOG"
    echo "DRY-RUN total eligible zombie sessions: $TOTAL"
elif [ "$TOTAL" -eq 0 ]; then
    echo "[$TIMESTAMP] OK total closed zombie sessions: 0 (grace=${GRACE_MINUTES}min)" >> "$LOG"
else
    echo "[$TIMESTAMP] DONE total closed zombie sessions: $TOTAL (grace=${GRACE_MINUTES}min)" >> "$LOG"
fi

# Truncar log se passar 1000 linhas
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt 1000 ]; then
    tail -500 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
fi
