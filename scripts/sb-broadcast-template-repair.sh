#!/usr/bin/env bash
set -euo pipefail
BASE=/root/mgs-agent
CMD=${1:-status}
case "$CMD" in
  dispatch)
    exec xvfb-run -a python3 "$BASE/scripts/sb-broadcast-template-repair.py" dispatch --apply --notify
    ;;
  check)
    exec xvfb-run -a python3 "$BASE/scripts/sb-broadcast-template-repair.py" check --notify
    ;;
  digest)
    exec python3 "$BASE/scripts/sb-broadcast-template-repair.py" digest --notify
    ;;
  audit)
    exec xvfb-run -a python3 "$BASE/scripts/sb-broadcast-template-repair.py" audit --json
    ;;
  *)
    exec python3 "$BASE/scripts/sb-broadcast-template-repair.py" "$CMD" --json
    ;;
esac
