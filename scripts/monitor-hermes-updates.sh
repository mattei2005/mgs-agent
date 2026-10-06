#!/bin/bash
# Hermes News: verificar upstream 3×/dia, anunciar apenas novas releases oficiais.
# Avanço do main/RC/canary fica no state para consulta, sem alerta recorrente.
# Política aprovada por Rodolfo: mensagem 1556908630278803478.
# Este monitor NÃO instala, configura ou reinicia Hermes.
set -euo pipefail
if [[ "${HERMES_MONITOR_DRY_RUN:-0}" != "1" && "${HERMES_MONITOR_SKIP_ENV_LOAD:-0}" != "1" ]]; then
    set -a
    source /root/mgs-agent/.env 2>/dev/null || true
    set +a
fi
exec python3 "$(dirname "${BASH_SOURCE[0]}")/mgs_hermes_release_monitor.py"
