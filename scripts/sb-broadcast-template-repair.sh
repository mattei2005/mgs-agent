#!/usr/bin/env bash
set -euo pipefail
BASE=/root/mgs-agent
PY=/root/mgs-agent/.venv-sb/bin/python
CMD=${1:-status}
case "$CMD" in
  dispatch)
    candidate_rc=0
    xvfb-run -a "$PY" "$BASE/scripts/sb-utility-candidate-approval.py" stage --apply --notify || candidate_rc=$?
    repair_rc=0
    xvfb-run -a "$PY" "$BASE/scripts/sb-broadcast-template-repair.py" dispatch --apply --notify || repair_rc=$?
    if (( candidate_rc != 0 )); then exit "$candidate_rc"; fi
    exit "$repair_rc"
    ;;
  check)
    candidate_rc=0
    xvfb-run -a "$PY" "$BASE/scripts/sb-utility-candidate-approval.py" check --notify || candidate_rc=$?
    repair_rc=0
    xvfb-run -a "$PY" "$BASE/scripts/sb-broadcast-template-repair.py" check --notify || repair_rc=$?
    if (( candidate_rc != 0 )); then exit "$candidate_rc"; fi
    exit "$repair_rc"
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
