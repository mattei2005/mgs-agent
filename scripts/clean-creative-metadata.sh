#!/usr/bin/env bash
set -euo pipefail
exec /usr/bin/env python3 /root/mgs-agent/scripts/clean-creative-metadata.py "$@"
