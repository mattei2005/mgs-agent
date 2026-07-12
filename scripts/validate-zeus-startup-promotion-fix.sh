#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT=/root/mgs-agent
HERMES=/root/.hermes/hermes-agent
STATE="$ROOT/data/zeus-startup-promotion-fix-state.json"
LOG="$ROOT/logs/zeus-startup-promotion-fix-validator.log"
THREAD_ID=1525908344819286156
exec >>"$LOG" 2>&1

log(){ printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }
write_state(){
  local status="$1" detail="$2"
  python3 - "$STATE" "$status" "$detail" <<'PY'
import datetime,json,os,sys
path,status,detail=sys.argv[1:]
o={"updated_at":datetime.datetime.now().astimezone().isoformat(),"status":status,"detail":detail,"zeus_service":os.popen('systemctl is-active zeus-gateway.service 2>/dev/null').read().strip()}
tmp=path+'.tmp';open(tmp,'w',encoding='utf-8').write(json.dumps(o,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,path)
PY
}
audit(){
  python3 - "$ROOT/logs/events-audit.jsonl" "$1" "$2" <<'PY'
import datetime,json,sys
p,event,detail=sys.argv[1:]
row={"ts":datetime.datetime.now(datetime.timezone.utc).isoformat(),"event":event,"actor":"zeus-runtime-validator","requested_by":"344196393512075265","detail":detail}
with open(p,'a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
PY
}

log 'START post-restart validation'
write_state running 'validando gateway e regressão'

if [[ "$(systemctl is-active zeus-gateway.service 2>/dev/null || true)" != active ]]; then
  write_state failed 'zeus-gateway não está active'
  audit zeus_startup_promotion_fix_failed 'service not active'
  /root/.local/bin/hermes -p zeus send --to "discord:$THREAD_ID" --quiet '<@344196393512075265> A correção da mensagem genérica não passou no pós-restart: zeus-gateway não ficou ativo. O rollback está preservado e o detalhe técnico foi registrado em #alerts-infra.' || true
  exit 81
fi

python3 -m py_compile "$HERMES/gateway/run.py"
cd "$HERMES"
venv/bin/pytest -q \
  tests/gateway/test_busy_session_ack.py::TestBusySessionAck::test_reentrant_followup_promotion_reuses_current_agent \
  tests/gateway/test_busy_session_ack.py::TestBusySessionAck::test_reentrant_followup_does_not_mask_replaced_agent \
  tests/gateway/test_busy_session_ack.py::TestBusySessionAck::test_reentrant_followup_transfers_same_generation_rebuilt_agent \
  tests/gateway/test_busy_session_ack.py::TestBusySessionAck::test_recursive_run_enables_same_generation_replacement

/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh

ERRORS="$(journalctl -u zeus-gateway.service --since '-3 minutes' --no-pager -o cat 2>/dev/null | grep -c 'startup agent promotion lost ownership' || true)"
[[ "$ERRORS" == 0 ]] || {
  write_state failed "erro reapareceu após restart count=$ERRORS"
  audit zeus_startup_promotion_fix_failed "post-restart lost ownership count=$ERRORS"
  /root/.local/bin/hermes -p zeus send --to "discord:$THREAD_ID" --quiet '<@344196393512075265> A correção da mensagem genérica não passou: o erro de ownership reapareceu depois do restart. O detalhe foi registrado e não vou declarar resolvido.' || true
  exit 82
}

/root/mgs-agent/scripts/infra-discovery.sh
write_state completed 'Zeus active; 4 regressões passaram; patch guard passou; zero novos lost ownership no pós-restart'
audit zeus_startup_promotion_fix_validated 'Zeus active; 4 targeted tests PASS; patch guard PASS; post-restart lost ownership=0'

/root/mgs-agent/scripts/send-report-infra-embed.sh \
  --action modificada \
  --type 'runtime/patch/test/script/skill' \
  --path '/root/.hermes/hermes-agent/gateway/run.py; tests/gateway/test_busy_session_ack.py; patches/hermes/mgs-busy-steer-reentrant-rebuild-2026-07-12.patch; ensure-hermes-mgs-patches.sh; hermes-agent-operations' \
  --reason 'Corrigir erro Discord recorrente startup agent promotion lost ownership em follow-up recursivo após rebuild do AIAgent' \
  --evidence '43 busy-session tests PASS antes do restart; 4 regressões PASS pós-restart; patch guard PASS; zero novos lost ownership; backup seguro 20260712T1408-0400'

/root/.local/bin/hermes -p zeus send --to "discord:$THREAD_ID" --quiet 'Correção aplicada e validada após o restart: Zeus ativo, 4 regressões direcionadas aprovadas, patch guard aprovado e nenhum novo `startup agent promotion lost ownership` no pós-restart. A causa era uma corrida no follow-up recursivo quando o AIAgent era reconstruído após mudança de skill/config.'
log 'DONE validation PASS'
