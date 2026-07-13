#!/usr/bin/env bash
# pendencia-add.sh — adiciona nova pendência via store transacional canônico.
set -euo pipefail
exec python3 /root/mgs-agent/scripts/pendencia_store.py add "$@"
