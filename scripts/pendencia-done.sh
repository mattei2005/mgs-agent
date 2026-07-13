#!/usr/bin/env bash
# pendencia-done.sh — resolve pendência via store transacional canônico.
set -euo pipefail
exec python3 /root/mgs-agent/scripts/pendencia_store.py done "$@"
