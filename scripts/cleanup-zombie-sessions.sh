#!/bin/bash
# Fecha sessoes Hermes "zombies" (ended_at NULL, sem atividade ha >30min).
#
# Bug raiz: Hermes nao chama end_session() em todos caminhos (crash, timeout,
# restart de gateway). Isso e band-aid ate atualizar pra v0.12.0+.
#
# Protecoes:
# - So fecha sessoes inativas ha >30min (grace period)
# - Marca end_reason = 'cleanup_zombie_cron' pra distinguir
# - Loga tudo em /root/mgs-agent/logs/cleanup-zombies.log
#
# Reverter: comentar linha do cron + (opcional) restaurar end_reason=NULL
#
# Roda via cron a cada hora.

set -u

LOG="/root/mgs-agent/logs/cleanup-zombies.log"
TIMESTAMP=$(date '+%Y-%m-%dT%H:%M:%S%z')
GRACE_MINUTES=30

mkdir -p "$(dirname "$LOG")"

for AGENT in atena zeus; do
    DB="/root/.hermes/profiles/$AGENT/state.db"
    [ ! -f "$DB" ] && continue

    # Contar zombies elegiveis (NULL ended_at + inativa ha >30min)
    OLD_COUNT=$(sqlite3 "$DB" "
        SELECT COUNT(*) FROM sessions
        WHERE ended_at IS NULL
          AND (strftime('%s', 'now') - started_at) > ($GRACE_MINUTES * 60);
    " 2>/dev/null || echo 0)

    if [ "$OLD_COUNT" -gt 0 ]; then
        # Fechar marcando end_reason explicito
        NOW=$(date +%s)
        sqlite3 "$DB" "
            UPDATE sessions
            SET ended_at = MAX(started_at + 1, $NOW - 60),
                end_reason = 'cleanup_zombie_cron'
            WHERE ended_at IS NULL
              AND (strftime('%s', 'now') - started_at) > ($GRACE_MINUTES * 60);
        " 2>/dev/null

        echo "[$TIMESTAMP] $AGENT: closed $OLD_COUNT zombie sessions (grace=${GRACE_MINUTES}min)" >> "$LOG"
    fi
done

# Truncar log se passar 1000 linhas
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt 1000 ]; then
    tail -500 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
fi
