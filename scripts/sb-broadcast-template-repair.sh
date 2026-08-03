#!/usr/bin/env bash
set -euo pipefail
BASE=/root/mgs-agent
PY=/root/mgs-agent/.venv-sb/bin/python
CMD=${1:-status}
case "$CMD" in
  dispatch)
    exec xvfb-run -a "$PY" "$BASE/scripts/sb-broadcast-template-repair.py" dispatch --apply --notify
    ;;
  check)
    exec xvfb-run -a "$PY" "$BASE/scripts/sb-broadcast-template-repair.py" check --notify
    ;;
  digest)
    exec "$PY" "$BASE/scripts/sb-broadcast-template-repair.py" digest --notify
    ;;
  audit)
    exec xvfb-run -a "$PY" "$BASE/scripts/sb-broadcast-template-repair.py" audit --json
    ;;
  *)
    exec "$PY" "$BASE/scripts/sb-broadcast-template-repair.py" "$CMD" --json
    ;;
esac
