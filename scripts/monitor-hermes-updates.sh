#!/bin/bash
# Hermes News: verificar upstream 3×/dia, anunciar releases e delta do main.
# Um resumo por lote novo, sem repetir acumulado; RC/canary não é estável.
# Política aprovada por Rodolfo: mensagem 1567760164319272970.
# Este monitor NÃO instala, configura ou reinicia Hermes.
set -euo pipefail
if [[ "${HERMES_MONITOR_DRY_RUN:-0}" != "1" && "${HERMES_MONITOR_SKIP_ENV_LOAD:-0}" != "1" ]]; then
    set -a
    source /root/mgs-agent/.env 2>/dev/null || true
    set +a
fi
exec python3 "$(dirname "${BASH_SOURCE[0]}")/mgs_hermes_release_monitor.py"
