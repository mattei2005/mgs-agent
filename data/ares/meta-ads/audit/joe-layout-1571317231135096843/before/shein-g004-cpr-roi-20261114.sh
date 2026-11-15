#!/usr/bin/env bash
set -euo pipefail
export HERMES_HOME=/root/.hermes/profiles/ares
export TMPDIR=/root/.hermes/profiles/ares/cache/scratch
exec timeout 170s python3 /root/.hermes/profiles/ares/scripts/shein-g004-cpr-roi-20261114.py "$@"
