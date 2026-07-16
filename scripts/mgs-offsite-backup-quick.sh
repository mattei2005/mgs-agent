#!/usr/bin/env bash
set -euo pipefail
exec /usr/bin/python3 /root/mgs-agent/scripts/mgs-offsite-backup.py backup --mode quick
