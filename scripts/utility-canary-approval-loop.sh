#!/usr/bin/env bash
set -euo pipefail
BASE_DIR=/root/mgs-agent
set -a
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a
cd "$BASE_DIR"
if [ -f "${BASE_DIR}/data/utility-canary-loop.paused" ]; then
  echo "Utility canary loop: pausado por safety flag ${BASE_DIR}/data/utility-canary-loop.paused"
  exit 0
fi
xvfb-run -a /tmp/sb-venv/bin/python "${BASE_DIR}/scripts/utility-canary-approval-loop.py"
