#!/usr/bin/env bash
set -euo pipefail
set -a
source /root/mgs-agent/.env
set +a
set +e
python3 /root/mgs-agent/scripts/ares-cpv-meta-reader-gate.py \
  --account-id 1046241194533786 \
  --state-root /root/mgs-agent/data/ares/meta-ads/engine-v3/state \
  --operation-state /root/mgs-agent/data/ares/meta-ads/engine-v3/state/cpv-daily.json
rc=$?
set -e
if [[ "$rc" -eq 75 ]]; then exit 0; fi
if [[ "$rc" -ne 0 ]]; then exit "$rc"; fi
hour_sp=$(TZ=America/Sao_Paulo date +%H)
args=(--mode intraday --gate)
if [[ "$hour_sp" == "08" || "$hour_sp" == "12" || "$hour_sp" == "16" ]]; then
  args=(--mode intraday --actions-only --gate)
fi
set +e
flock -s -E 75 -n /run/lock/ares-cpv-meta-lane-1046241194533786.lock \
  python3 /root/.hermes/profiles/ares/scripts/creditoparaveiculo-fixed-reports.py "${args[@]}"
rc=$?
set -e
if [[ "$rc" -eq 75 ]]; then exit 0; fi
exit "$rc"
