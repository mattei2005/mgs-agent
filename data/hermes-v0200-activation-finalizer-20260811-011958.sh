#!/usr/bin/env bash
set -euo pipefail

ROOT=/root/mgs-agent
LOG="$ROOT/logs/hermes-v0200-activation-finalizer-20260811-011958.log"
AUDIT="$ROOT/logs/events-audit.jsonl"
INVENTORY="$ROOT/data/infra-inventory.json"
CHECKPOINT_ID=vps-final-closure-20260811
OLD_LAUNCHER=/root/.local/bin/hermes-v0191-mgs
NEW_REPO=/root/.hermes/hermes-agent-port-v2026-8-3-9d6c5a92
NEW_LAUNCHER=/root/.local/bin/hermes-v0200-mgs
CANONICAL=/root/.local/bin/hermes
EXPECTED_COMMIT=8c8a6b4b79d85d00da173ce81aafca5e78c12249
EXPECTED_PATCH_SHA=6372cde1232efbede375600a6563868cab279ff2f4b22882fe52553f6af0eafb
EXPECTED_GUARD_SHA=cf7cfd8f1216bf9134581e5d90dedb3d6b6acfc0a70a3368bf2b4c9497c77aa9
PATCH="$ROOT/patches/hermes/mgs-runtime-customizations-2026-08-11-v0200.patch"
GUARD="$ROOT/scripts/ensure-hermes-local-patches.sh"
REPORT_HELPER="$ROOT/scripts/send-report-infra-embed.sh"
RESTART_HELPER="$ROOT/scripts/mgs-gateway-restart-safe.sh"

mkdir -p "$ROOT/logs"
exec >>"$LOG" 2>&1

now_utc(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
log(){ printf '[%s] %s\n' "$(now_utc)" "$*"; }
audit(){
  local event="$1" detail="$2"
  python3 - "$AUDIT" "$event" "$detail" <<'PY'
import json,os,sys
from datetime import datetime,timezone
from pathlib import Path
p=Path(sys.argv[1]); event=sys.argv[2]; detail=sys.argv[3]
row={"ts":datetime.now(timezone.utc).isoformat(),"event":event,"actor":"hermes-v0200-activation-finalizer","detail":detail}
with p.open("a",encoding="utf-8") as f:
    f.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
    f.flush(); os.fsync(f.fileno())
PY
}
atomic_link(){
  local target="$1" tmp="${CANONICAL}.tmp.$$"
  ln -s "$target" "$tmp"
  mv -Tf "$tmp" "$CANONICAL"
  [[ "$(readlink -f "$CANONICAL")" == "$(readlink -f "$target")" ]]
}
prepare_and_run_restart(){
  local reason="$1" out finalizer
  out="$(env -u HERMES_HOME -u HERMES_PROFILE HOME=/root "$RESTART_HELPER" --agents 'ares atena zeus' --reason "$reason")"
  printf '%s\n' "$out"
  finalizer="$(printf '%s\n' "$out" | python3 -c 'import sys; lines=[x.strip() for x in sys.stdin if x.startswith("Prepared detached finalizer only")]; print(lines[-1].split(": ",1)[1] if lines else "")')"
  [[ -x "$finalizer" ]]
  "$finalizer"
}
update_inventory(){
  local status="$1" detail="$2"
  python3 - "$INVENTORY" "$status" "$detail" "$LOG" <<'PY'
import json,os,sys
from datetime import datetime,timezone
from pathlib import Path
p=Path(sys.argv[1]); status=sys.argv[2]; detail=sys.argv[3]; log=sys.argv[4]
d=json.loads(p.read_text()); rid="hermes-port-9d6c5a92-20260811"
items=[x for x in d.get("runtime_artifacts",[]) if x.get("id")==rid]
if len(items)!=1: raise SystemExit("runtime artifact not unique")
x=items[0]; x["status"]=status; x["activation_detail"]=detail; x["activation_log"]=log; x["active_launcher"]="/root/.local/bin/hermes"; x["updated_at"]=datetime.now(timezone.utc).isoformat()
if status=="activated_validated":
    x["active_runtime_path"]="/root/.hermes/hermes-agent-port-v2026-8-3-9d6c5a92"
    x["activation_order"]=["ares","atena","zeus"]
    x["oneshot_smokes"]="Zeus/Atena/Ares 3/3 exact MGS_V0200_OK"
tmp=p.with_suffix(p.suffix+".tmp"); tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n"); os.chmod(tmp,0o644); os.replace(tmp,p)
PY
}
post_report(){
  local action="$1" reason="$2" evidence="$3"
  "$REPORT_HELPER" --action "$action" --type 'runtime/script/data' \
    --path "$NEW_REPO; $CANONICAL; $PATCH; $GUARD; $INVENTORY" \
    --reason "$reason" --evidence "$evidence"
}

log "START Hermes v0.20.0 activation"
audit hermes_v0200_activation_started "new=$NEW_REPO old=$OLD_LAUNCHER log=$LOG"

# Immutable preflight.
[[ -x "$NEW_LAUNCHER" && -x "$OLD_LAUNCHER" && -x "$GUARD" ]]
[[ "$(git -C "$NEW_REPO" rev-parse HEAD)" == "$EXPECTED_COMMIT" ]]
[[ "$(sha256sum "$PATCH" | cut -d' ' -f1)" == "$EXPECTED_PATCH_SHA" ]]
[[ "$(sha256sum "$GUARD" | cut -d' ' -f1)" == "$EXPECTED_GUARD_SHA" ]]
REPO="$NEW_REPO" "$GUARD" --check
uv pip check --python "$NEW_REPO/venv/bin/python"
"$NEW_REPO/venv/bin/python" -m py_compile "$NEW_REPO/gateway/run.py" "$NEW_REPO/plugins/platforms/discord/adapter.py"

activation_rc=0
atomic_link "$NEW_LAUNCHER" || activation_rc=$?
if [[ "$activation_rc" -eq 0 ]]; then
  env -u HERMES_HOME -u HERMES_PROFILE HOME=/root "$CANONICAL" --version | tee /dev/stderr
  prepare_and_run_restart hermes-v0200-9d6c5a92-activation || activation_rc=$?
fi

if [[ "$activation_rc" -eq 0 ]]; then
  for svc in ares-gateway.service atena-gateway.service zeus-gateway.service; do
    [[ "$(systemctl is-active "$svc")" == active ]] || { activation_rc=81; break; }
  done
fi

if [[ "$activation_rc" -eq 0 ]]; then
  for profile in zeus atena ares; do
    ok=0
    for attempt in 1 2; do
      set +e
      out="$(timeout 240 env -u HERMES_HOME -u HERMES_PROFILE HOME=/root "$CANONICAL" -p "$profile" -z 'Return exactly MGS_V0200_OK' 2>>"$LOG")"
      rc=$?
      set -e
      if [[ "$rc" -eq 0 && "$(printf '%s' "$out" | tr -d '\r\n')" == MGS_V0200_OK ]]; then ok=1; break; fi
      log "oneshot retry profile=$profile attempt=$attempt rc=$rc"
    done
    [[ "$ok" -eq 1 ]] || { activation_rc=82; break; }
    log "oneshot PASS profile=$profile"
  done
fi

if [[ "$activation_rc" -ne 0 ]]; then
  log "ACTIVATION FAILED rc=$activation_rc; starting rollback"
  audit hermes_v0200_activation_failed "rc=$activation_rc rollback=starting log=$LOG"
  rollback_rc=0
  atomic_link "$OLD_LAUNCHER" || rollback_rc=$?
  if [[ "$rollback_rc" -eq 0 ]]; then
    prepare_and_run_restart hermes-v0200-rollback-after-activation-failure || rollback_rc=$?
  fi
  if [[ "$rollback_rc" -eq 0 ]]; then
    update_inventory activation_failed_rolled_back "activation_rc=$activation_rc; old runtime restored and gateways ready"
    audit hermes_v0200_rollback_finished "activation_rc=$activation_rc status=PASS log=$LOG"
    post_report modificada 'Ativação Hermes 0.20.0 falhou; rollback automático para 0.19.1 concluído.' "activation_rc=$activation_rc; rollback=PASS; log=$LOG" || true
  else
    update_inventory activation_failed_rollback_failed "activation_rc=$activation_rc; rollback_rc=$rollback_rc"
    audit hermes_v0200_rollback_failed "activation_rc=$activation_rc rollback_rc=$rollback_rc log=$LOG"
    post_report modificada 'Falha crítica na ativação Hermes 0.20.0 e no rollback automático.' "activation_rc=$activation_rc; rollback_rc=$rollback_rc; log=$LOG" || true
  fi
  exit "$activation_rc"
fi

version="$(env -u HERMES_HOME -u HERMES_PROFILE HOME=/root "$CANONICAL" --version | tr -d '\r\n')"
launcher="$(readlink -f "$CANONICAL")"
pids="$(systemctl show ares-gateway.service atena-gateway.service zeus-gateway.service -p Id -p MainPID -p ActiveState -p SubState --no-pager | tr '\n' ' ')"
update_inventory activated_validated "version=$version launcher=$launcher services=3/3 active smokes=3/3"
audit hermes_v0200_activation_finished "version=$version launcher=$launcher order=ares,atena,zeus smokes=3/3 log=$LOG"
if [[ -f "$ROOT/data/vps-esm-completed-20260811.json" ]] && python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); raise SystemExit(d.get("status")!="completed_validated")' "$ROOT/data/vps-esm-completed-20260811.json"; then
  checkpoint_state=completed
  checkpoint_next='Monitorar apenas exceções pós-ativação; SB residual depende de reparo backend'
  esm_state=completed_validated
else
  checkpoint_state=blocked_external_ubuntu_pro
  checkpoint_next='Concluir vínculo Ubuntu Pro e aplicar/readback das correções ESM; SB residual depende de reparo backend'
  esm_state=pending_external
fi
"$ROOT/scripts/mgs-knowledge-control.py" checkpoint-upsert --id "$CHECKPOINT_ID" --agent zeus --thread-id 1536567182824308839 --objective 'Fechar manutenção VPS, ESM, Hermes e residual DTR/SB' --state "$checkpoint_state" --next-step "$checkpoint_next" --source 'discord:1536567182824308839' || true
post_report modificada 'Hermes 0.20.0 ativado com port MGS preservado e restart seguro Ares→Atena→Zeus.' "version=$version; commit=$EXPECTED_COMMIT; tests=532+6 e 193; configs=3/3; smokes=3/3; services=3/3; esm=$esm_state; launcher=$launcher"
log "DONE Hermes v0.20.0 activation $pids"
