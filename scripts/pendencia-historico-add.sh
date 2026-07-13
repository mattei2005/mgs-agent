#!/usr/bin/env bash
# pendencia-historico-add.sh — registra histórico via store transacional canônico.
set -euo pipefail
exec python3 /root/mgs-agent/scripts/pendencia_store.py historico-add "$@"
