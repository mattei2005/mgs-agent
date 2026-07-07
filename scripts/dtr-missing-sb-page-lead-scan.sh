#!/usr/bin/env bash
set -euo pipefail
BASE_DIR=/root/mgs-agent
set -a
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a
cd "$BASE_DIR"
xvfb-run -a /tmp/sb-venv/bin/python "${BASE_DIR}/scripts/dtr-missing-sb-page-lead-scan.py" "$@"
