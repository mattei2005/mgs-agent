#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT="/root/mgs-agent"
LOG="$ROOT/logs/ares-hera-finalizer-20260712.log"
STATE="$ROOT/data/ares/hera-deactivation-state.json"
AUDIT="$ROOT/logs/events-audit.jsonl"
LOCK="$ROOT/data/ares/.hera-deactivation-finalizer.lock"
exec 9>"$LOCK"
flock -n 9 || exit 75
exec >>"$LOG" 2>&1

log(){ printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }
audit(){
  local event="$1" detail="$2"
  python3 - "$AUDIT" "$event" "$detail" <<'PY'
import datetime,json,sys
path,event,detail=sys.argv[1:]
row={"ts":datetime.datetime.now(datetime.timezone.utc).isoformat(),"event":event,"actor":"zeus","requested_by":"344196393512075265","scope":"ares-hera-unification","detail":detail}
with open(path,"a",encoding="utf-8") as f:f.write(json.dumps(row,ensure_ascii=False)+"\n")
PY
}
write_state(){
  local status="$1" detail="$2"
  python3 - "$STATE" "$status" "$detail" <<'PY'
import datetime,json,os,sys
path,status,detail=sys.argv[1:]
o={"updated_at":datetime.datetime.now().astimezone().isoformat(),"status":status,"detail":detail,"ares_service":os.popen('systemctl is-active ares-gateway.service 2>/dev/null').read().strip(),"hera_service":os.popen('systemctl is-active hera-gateway.service 2>/dev/null').read().strip(),"hera_enabled":os.popen('systemctl is-enabled hera-gateway.service 2>/dev/null').read().strip()}
tmp=path+'.tmp';open(tmp,'w',encoding='utf-8').write(json.dumps(o,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,path)
PY
}

log "START Hera deactivation + Ares activation finalizer"
audit "ares_hera_finalizer_started" "desativar Hera reversivelmente, reiniciar Ares e validar"
write_state "running" "finalizer iniciado"

# Pre-flight: required Ares runtime artifacts.
for p in \
  /root/.hermes/profiles/ares/SOUL.md \
  /root/.hermes/profiles/ares/config.yaml \
  /root/.hermes/profiles/ares/skills/growth/creative-operations-mgs/SKILL.md \
  /root/.hermes/profiles/ares/skills/growth/meta-library-reference-intake/SKILL.md \
  /root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl \
  /root/mgs-agent/scripts/ares-meta-library-collector.sh; do
  [[ -e "$p" ]] || { write_state "failed" "preflight ausente: $p"; audit "ares_hera_finalizer_failed" "preflight ausente: $p"; exit 76; }
done
python3 -m json.tool /root/mgs-agent/data/authorized-users.json >/dev/null
python3 -m py_compile /root/mgs-agent/scripts/mgs-grok-generate.py /root/mgs-agent/scripts/monitor-vps-health.py
bash -n /root/mgs-agent/scripts/sync-souls.sh /root/mgs-agent/scripts/ares-meta-library-collector.sh

# Hera is disabled, not deleted: unit/profile/data/channel remain for rollback.
systemctl disable --now hera-gateway.service
for _ in $(seq 1 30); do
  [[ "$(systemctl is-active hera-gateway.service 2>/dev/null || true)" != "active" ]] && break
  sleep 1
done
HERA_ACTIVE="$(systemctl is-active hera-gateway.service 2>/dev/null || true)"
HERA_ENABLED="$(systemctl is-enabled hera-gateway.service 2>/dev/null || true)"
[[ "$HERA_ACTIVE" != "active" ]] || { write_state "failed" "Hera continuou ativa"; audit "ares_hera_finalizer_failed" "Hera continuou ativa"; exit 77; }
[[ "$HERA_ENABLED" != "enabled" ]] || { write_state "failed" "Hera continuou enabled"; audit "ares_hera_finalizer_failed" "Hera continuou enabled"; exit 78; }
audit "hera_gateway_deactivated" "service=hera-gateway.service active=$HERA_ACTIVE enabled=$HERA_ENABLED profile/data preservados"

# External detached job: safe place to restart Ares and wait for readiness.
systemctl restart ares-gateway.service
for _ in $(seq 1 45); do
  [[ "$(systemctl is-active ares-gateway.service 2>/dev/null || true)" == "active" ]] && break
  sleep 1
done
[[ "$(systemctl is-active ares-gateway.service 2>/dev/null || true)" == "active" ]] || { write_state "failed" "Ares não ficou active"; audit "ares_hera_finalizer_failed" "Ares não ficou active"; exit 79; }

READY=0
for _ in $(seq 1 45); do
  if journalctl -u ares-gateway.service --since '-2 minutes' --no-pager 2>/dev/null | grep -Eqi 'Connected as|gateway running|logged in as|discord.*ready|ready'; then READY=1; break; fi
  sleep 1
done
[[ "$READY" -eq 1 ]] || { write_state "failed" "Ares active sem marker Discord de readiness"; audit "ares_hera_finalizer_failed" "Ares active sem marker Discord de readiness"; exit 80; }
audit "ares_gateway_restarted" "service=ares-gateway.service active e Discord ready"

# Regenerate inventory from final live state.
/root/mgs-agent/scripts/infra-discovery.sh
python3 -m json.tool /root/mgs-agent/data/infra-inventory.json >/dev/null

ARES_MESSAGE='<@1496296175014252634> A Hera foi desativada e consolidada em você. A partir de agora, você é o único agente responsável pelo fluxo completo de Creative Operations + Campaign Operations: pedido/upload → criação ou tratamento → sanitização → naming e Drive → inventário/linhagem → reserva e elegibilidade → conciliação Meta × Drive → campanhas/testes → performance e ROI. Fontes atuais: seu SOUL, context/ares-operational-map.md e skills growth. Referências da Hera são somente histórico/rollback. Usuários permanentes autorizados: Rodolfo, Geizian, Icaro, Isliago, Joe, Kelly e Nicolas; gates específicos de budget, billing, credencial e produção crítica continuam valendo.'
if hermes -p zeus send --to discord:1508853425952133180 --quiet "$ARES_MESSAGE"; then
  audit "ares_handoff_notified" "channel=1508853425952133180 message entregue"
  HANDOFF="sent"
else
  audit "ares_handoff_notification_failed" "channel=1508853425952133180"
  HANDOFF="failed"
fi

write_state "completed" "Hera inactive/disabled; Ares active/ready; handoff=$HANDOFF; inventory atualizado"
audit "ares_hera_unification_completed" "Hera inactive/disabled; Ares active/ready; handoff=$HANDOFF; rollback preservado"

EVIDENCE="state=$STATE; Meta auth HTTP 200; Meta Library HTTP 200/24 IDs; sanitizer clean=true; Grok xAI smoke ok; Ares skills enabled; Hera inactive/disabled; Ares active/ready"
/root/mgs-agent/scripts/send-report-infra-embed.sh \
  --action modificada \
  --type 'agent/skill/script/config/data/systemd' \
  --path '/root/.hermes/profiles/ares; /root/mgs-agent/profiles/ares-*; /root/mgs-agent/context; /root/mgs-agent/data/ares; /root/mgs-agent/scripts/ares-*; hera-gateway.service' \
  --reason 'Unificação autorizada Hera → Ares com Creative Ops + Campaign Ops e rollback preservado' \
  --evidence "$EVIDENCE"

log "DONE Hera=$HERA_ACTIVE/$HERA_ENABLED Ares=active/ready handoff=$HANDOFF"
