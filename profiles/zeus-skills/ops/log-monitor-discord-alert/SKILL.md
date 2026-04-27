---
name: log-monitor-discord-alert
description: "Cria um monitor de log com alerta Discord, state file JSON e cron entry. Padrão reusável: detecta entradas START sem OK correspondente + erros explícitos + threshold + anti-spam + mensagem de RESOLVIDO."
tags: [monitoring, discord, cron, logs, alerting, bash]
related_skills: [git-hook-discord-notify, mgs-infra-inventory]
---

# Monitor de Log com Alerta Discord

## Quando usar

Qualquer situação onde um processo periódico grava em log com padrão START/OK e você quer:
- Detectar falhas silenciosas (START sem OK correspondente)
- Alertar via Discord Webhook quando threshold atingido
- Anti-spam (não repetir alerta a cada ciclo)
- Mensagem de "RESOLVIDO" quando o sistema se recupera

Exemplo validado: `monitor-auto-push.sh` para o auto-push do mgs-agent.

---

## Estrutura do sistema

```
scripts/monitor-NOME.sh          — script principal
data/NOME-monitor.json           — state file (persiste entre execuções)
logs/monitor-NOME.log            — output do cron
crontab root                     — entrada cron (frequência ajustável)
```

---

## State file inicial

```json
{
  "_meta": {
    "description": "Estado do monitor de NOME. Atualizado a cada execução.",
    "created": "YYYY-MM-DD",
    "threshold": 3,
    "anti_spam_window_hours": 2
  },
  "last_check": null,
  "consecutive_failures": 0,
  "last_alert_sent": null,
  "last_failure_details": []
}
```

---

## Template do script monitor

Copiar e adaptar — variáveis marcadas com `ALTERAR`:

```bash
#!/usr/bin/env bash
# monitor-NOME.sh — Monitor de falhas em PROCESSO
# Roda via cron. State em data/NOME-monitor.json
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
PUSH_LOG="${BASE_DIR}/logs/NOME-DO-LOG.log"          # ALTERAR
STATE_FILE="${BASE_DIR}/data/NOME-monitor.json"       # ALTERAR
WINDOW_MINUTES="${WINDOW_MINUTES:-60}"
THRESHOLD="${THRESHOLD:-3}"
ANTI_SPAM_HOURS="${ANTI_SPAM_HOURS:-2}"

source "${BASE_DIR}/.env" 2>/dev/null || true

WEBHOOK_URL="$(op item get "Discord Webhook - Zeus Channel" \
    --vault 'MGS Conteúdo' \
    --fields label=webhook_url \
    --reveal 2>/dev/null)"

NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
NOW_EPOCH="$(date +%s)"
CUTOFF_EPOCH=$(( NOW_EPOCH - WINDOW_MINUTES * 60 ))

log() { echo "[$(date -Iseconds)] monitor-NOME: $*"; }

# ─── Garantir state file ──────────────────────────────────────────────────────
if [[ ! -f "$STATE_FILE" ]]; then
  cat > "$STATE_FILE" <<'EOF'
{"_meta":{},"last_check":null,"consecutive_failures":0,"last_alert_sent":null,"last_failure_details":[]}
EOF
fi

CONSECUTIVE=$(jq -r '.consecutive_failures // 0' "$STATE_FILE")
LAST_ALERT=$(jq -r '.last_alert_sent // "null"' "$STATE_FILE")

# ─── Verificar log existe ─────────────────────────────────────────────────────
if [[ ! -f "$PUSH_LOG" ]]; then
  log "WARN: log não encontrado"
  jq --arg ts "$NOW_ISO" '.last_check = $ts' "$STATE_FILE" > "${STATE_FILE}.tmp" \
    && mv "${STATE_FILE}.tmp" "$STATE_FILE"
  exit 0
fi

# ─── Filtrar janela de tempo ──────────────────────────────────────────────────
WINDOW_LINES=""
while IFS= read -r line; do
  ts="$(echo "$line" | grep -oP '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}')" || continue
  line_epoch="$(date -d "$ts" +%s 2>/dev/null)" || continue
  if (( line_epoch >= CUTOFF_EPOCH )); then
    WINDOW_LINES+="$line"$'\n'
  fi
done < "$PUSH_LOG"

# ─── Detectar falhas (ALTERAR padrões de START/OK) ───────────────────────────
NEW_FAILURES=()
LAST_OK_COMMIT=""
LAST_OK_TS=""

while IFS= read -r line; do
  if echo "$line" | grep -q "PROCESSO START"; then              # ALTERAR
    id="$(echo "$line" | grep -oP 'id=\K\S+')" || continue
    ts="$(echo "$line" | grep -oP '\[\K[^\]]+')" || continue
    if ! grep -q "PROCESSO OK id=${id}" "$PUSH_LOG"; then       # ALTERAR
      NEW_FAILURES+=("${ts} id=${id} [START sem OK]")
    fi
  fi
done <<< "$WINDOW_LINES"

# ─── Detectar erros explícitos ────────────────────────────────────────────────
ERROR_PATTERNS="rejected|failed|Authentication failed|fatal:|error:|timeout"  # ALTERAR
EXPLICIT_ERRORS=()
while IFS= read -r line; do
  if echo "$line" | grep -qiE "$ERROR_PATTERNS"; then
    EXPLICIT_ERRORS+=("$line")
  fi
done <<< "$WINDOW_LINES"

# ─── Último OK (para report) ──────────────────────────────────────────────────
if grep -q "PROCESSO OK" "$PUSH_LOG"; then                      # ALTERAR
  LAST_OK_LINE="$(grep "PROCESSO OK" "$PUSH_LOG" | tail -1)"   # ALTERAR
  LAST_OK_COMMIT="$(echo "$LAST_OK_LINE" | grep -oP 'id=\K\S+')" || true
  LAST_OK_TS="$(echo "$LAST_OK_LINE" | grep -oP '\[\K[^\]]+' | head -1)" || true
fi

# ─── Contabilizar ────────────────────────────────────────────────────────────
TOTAL_NEW=$(( ${#NEW_FAILURES[@]} + ${#EXPLICIT_ERRORS[@]} ))
ALL_DETAILS=("${NEW_FAILURES[@]}" "${EXPLICIT_ERRORS[@]}")
ALERT_WAS_ACTIVE=false
(( CONSECUTIVE >= THRESHOLD )) && ALERT_WAS_ACTIVE=true

# ─── Lógica de alerta ────────────────────────────────────────────────────────
send_discord() {
  local payload="$1"
  curl -s -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "$payload" --max-time 10 >/dev/null
}

if (( TOTAL_NEW > 0 )); then
  NEW_CONSECUTIVE=$(( CONSECUTIVE + TOTAL_NEW ))
  FAILURE_JSON="$(printf '%s\n' "${ALL_DETAILS[@]}" | jq -R . | jq -s .)"
  log "FALHA: ${TOTAL_NEW} nova(s), total=${NEW_CONSECUTIVE}"

  SEND_ALERT=false
  if (( NEW_CONSECUTIVE >= THRESHOLD )); then
    if [[ "$LAST_ALERT" == "null" ]]; then
      SEND_ALERT=true
    else
      LAST_ALERT_EPOCH="$(date -d "$LAST_ALERT" +%s 2>/dev/null || echo 0)"
      (( NOW_EPOCH - LAST_ALERT_EPOCH > ANTI_SPAM_HOURS * 3600 )) && SEND_ALERT=true \
        || log "Anti-spam: suprimindo (enviado há menos de ${ANTI_SPAM_HOURS}h)"
    fi
  fi

  if [[ "$SEND_ALERT" == "true" ]]; then
    ALERT_TS="$NOW_ISO"
    LAST_DETAIL="${ALL_DETAILS[0]:-desconhecido}"
    log "Enviando alerta Discord"
    send_discord "$(jq -n \
      --arg n "$NEW_CONSECUTIVE" --arg d "$LAST_DETAIL" --arg t "${LAST_OK_TS:-nunca}" \
      '{content:"🚨 **PROCESSO FALHANDO**\nFalhas consecutivas: \($n)\nÚltimo erro: \($d)\nÚltimo OK: \($t)\nAção: investigar log"}')"
  else
    ALERT_TS="$LAST_ALERT"
  fi

  jq --arg ts "$NOW_ISO" --argjson c "$NEW_CONSECUTIVE" --arg at "$ALERT_TS" --argjson fd "$FAILURE_JSON" \
    '.last_check=$ts | .consecutive_failures=$c | .last_alert_sent=$at | .last_failure_details=$fd' \
    "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

else
  if (( CONSECUTIVE > 0 )); then
    log "RESOLVIDO (anterior: ${CONSECUTIVE} falhas)"
    if [[ "$ALERT_WAS_ACTIVE" == "true" ]]; then
      send_discord "$(jq -n \
        --arg n "$CONSECUTIVE" --arg c "${LAST_OK_COMMIT:-?}" --arg t "${LAST_OK_TS:-?}" \
        '{content:"✅ **PROCESSO RESTABELECIDO**\nApós \($n) falhas, voltou a funcionar.\nÚltimo OK: \($c) em \($t)"}')"
    fi
  else
    log "OK: zero falhas na janela de ${WINDOW_MINUTES}min"
  fi

  jq --arg ts "$NOW_ISO" '.last_check=$ts | .consecutive_failures=0 | .last_failure_details=[]' \
    "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
fi

log "Concluído. consecutive=$(jq -r '.consecutive_failures' "$STATE_FILE") last_ok=${LAST_OK_COMMIT:-n/a}"
```

---

## Cron entry

```bash
# Adicionar ao crontab root (sem modificar entradas existentes)
(crontab -l 2>/dev/null; echo "*/15 * * * * /root/mgs-agent/scripts/monitor-NOME.sh >> /root/mgs-agent/logs/monitor-NOME.log 2>&1") | crontab -
```

---

## Validação pós-criação

```bash
# 1. Permissões
chmod +x /root/mgs-agent/scripts/monitor-NOME.sh
ls -la /root/mgs-agent/scripts/monitor-NOME.sh
# Esperado: -rwxr-xr-x

# 2. Dry-run manual
bash /root/mgs-agent/scripts/monitor-NOME.sh
# Esperado: "OK: zero falhas" + sem Discord enviado

# 3. State file populado
jq . /root/mgs-agent/data/NOME-monitor.json
# Esperado: last_check com timestamp, consecutive_failures=0

# 4. Cron ativo
crontab -l | grep monitor-NOME
```

---

## Atualizar infra-inventory.json

Após criar os artefatos, atualizar manualmente 3 seções do inventário:

```json
// crons: adicionar
{
  "entry": "*/15 * * * * /root/mgs-agent/scripts/monitor-NOME.sh >> /root/mgs-agent/logs/monitor-NOME.log 2>&1",
  "description": "Monitor de ..."
}

// scripts: adicionar
{
  "path": "/root/mgs-agent/scripts/monitor-NOME.sh",
  "size_bytes": N,
  "modified_at": "TIMESTAMP",
  "description": "..."
}

// data_files: adicionar
{
  "path": "/root/mgs-agent/data/NOME-monitor.json",
  "description": "Estado do monitor. Campos: last_check, consecutive_failures, last_alert_sent, last_failure_details.",
  "modified_at": "TIMESTAMP"
}
```

---

## Pitfalls

1. **`os.environ` em `execute_code` não propaga para `terminal()`** — variáveis setadas com `os.environ[...] = ...` em Python NÃO chegam nos subprocessos do `terminal()`. Para credenciais 1Password dentro de `execute_code`, chamar `terminal("op item get ... --reveal")` diretamente e usar o output como string Python. Não tentar setar via `os.environ` e usar em `terminal()` subsequente.

2. **Campo do webhook no 1Password é `webhook_url`, não `url`** — o item "Discord Webhook - Zeus Channel" tem campo `label=webhook_url`. Usar `--fields label=webhook_url --reveal` (não `--fields label=url`).

3. **Sempre exportar `OP_SERVICE_ACCOUNT_TOKEN` antes do `op` em scripts shell** — scripts executados via cron não têm a env do `.env` carregada automaticamente. O `source "${BASE_DIR}/.env"` no início do script é obrigatório.

4. **WINDOW_LINES pode estar vazio se o log não tem entradas recentes** — tratar o caso sem erro (script deve terminar normalmente com "OK: zero falhas").

5. **`jq -r '.field // 0'` para campos numéricos** — se o state file tiver `"consecutive_failures": null`, o `// 0` garante fallback para 0. Sem isso, aritmética bash pode falhar.

6. **Arquivo `.tmp` intermediário no jq** — sempre usar `jq ... "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"` para evitar truncar o state file em caso de erro do jq.

7. **Não adicionar o cron manualmente ao crontab** — usar `(crontab -l 2>/dev/null; echo "ENTRY") | crontab -` para preservar entradas existentes. `crontab -l > /tmp/crontab_current.txt && echo "..." >> /tmp/crontab_current.txt && crontab /tmp/crontab_current.txt` também funciona (alternativa usada em 2026-04-26).

---

## Exemplo real — monitor-auto-push.sh

Padrão de log real detectado:
```
[2026-04-26T16:27:40-04:00] auto-push START commit=e286604 msg="..."
[2026-04-26T16:27:41-04:00] auto-push OK commit=e286604
```

Adaptação dos padrões no template:
- START pattern: `auto-push START`
- OK pattern: `auto-push OK commit=${commit}`
- id extraído via: `grep -oP 'commit=\K[a-f0-9]+'`
- Arquivo em: `/root/mgs-agent/scripts/monitor-auto-push.sh`
- State em: `/root/mgs-agent/data/auto-push-monitor.json`
- Cron: `*/15 * * * *`
