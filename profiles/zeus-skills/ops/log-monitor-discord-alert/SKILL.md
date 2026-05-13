---
name: log-monitor-discord-alert
description: "Monitoramento MGS com alertas Discord: template genérico de monitor de log (START/OK padrão), monitor de restarts de services systemd (zeus-gateway, atena-gateway, mgs-autocommit), e monitor de skills MGS sem REPORT-INFRA no inventário. Inclui state file JSON, anti-spam, resolução automática, padrão cron, set-a env export para cron, e padrão seguro para crontab. Referências: shell-env-crontab-patterns.md (set-a, crontab safety), mgs-audit-2026-05-02.md (auditoria 130 arquivos)."
tags: [monitoring, discord, cron, logs, alerting, bash, systemd, restart, infra, inventory, skills, report-infra, env-export, shell]
related_skills: [wp-plugin-mass-operation, discord-ops]
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

## Convenção de canal Discord por tipo de alerta

| Tipo de alerta | Canal | Webhook 1Password |
|---|---|---|
| Saúde Yoast SEO/Readability | `#alerts-yoast` (1498193722871910550) | `Discord Webhook - Alerts Yoast Channel` |
| Infra crítica (auto-push, deploy) | `#mgs-alerts` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |
| Cobrança operacional ao Zeus | `#zeus-admin-agent` (1496267442899521627) | `Discord Webhook - Zeus Channel` |

**Convenção de prefixo nas mensagens:** `[SITE.COM] [MÉTRICA] descrição`
- Site primeiro → identifica origem ao escanear canal
- Métrica segundo → tipo de dado ([YOAST], [BACKUP], [UPTIME], etc.)
- Exemplo: `[EGGBEV.COM] [YOAST] Relatório semanal (27/04 10h)`

**NÃO usar** o webhook `#zeus-admin-agent` para alertas de cron/monitor automatizado. Esse canal é exclusivo para conversa operacional Rodolfo ↔ Zeus, `[REPORT-INFRA]` de agentes, e hook git de commits interativos.

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

WEBHOOK_URL="$(op item get "Discord Webhook - MGS Alerts Channel" \
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

1. **`notify_on_complete=true` envia output bruto diretamente no canal Discord** — ao rodar scripts com `terminal(background=true, notify_on_complete=true)`, a plataforma Hermes entrega automaticamente o output completo do processo no canal assim que termina, **sem passar pelo agente**. Isso polui o canal com logs brutos. Usar sempre `process(action='wait')` ou `process(action='poll')` manualmente e sumarizar o resultado em 1-2 linhas. Nunca usar `notify_on_complete=true` para processos verbosos no canal de conversa.

   **Causa raiz mais profunda:** mesmo *sem* `notify_on_complete=true`, o gateway Hermes tem um watcher assíncrono que entrega o output de *qualquer* background process no canal quando `background_process_notifications != "off"`. Configurável em:
   - `~/.hermes/profiles/zeus/config.yaml` → `display.background_process_notifications: error` (só alerta em falha)
   - Env var: `HERMES_BACKGROUND_NOTIFICATIONS=error`
   
   Modos disponíveis: `all` (padrão — sempre entrega), `result` (só ao terminar), `error` (só se exit ≠ 0), `off` (silêncio total). O modo `error` é o ideal para o canal Zeus: silêncio em sucesso, alerta em falha. Código em `gateway/run.py` → `_load_background_notifications_mode()`.

2. **`os.environ` em `execute_code` não propaga para `terminal()`** — variáveis setadas com `os.environ[...] = ...` em Python NÃO chegam nos subprocessos do `terminal()`. Para credenciais 1Password dentro de `execute_code`, chamar `terminal("op item get ... --reveal")` diretamente e usar o output como string Python. Não tentar setar via `os.environ` e usar em `terminal()` subsequente.

2. **Campo do webhook no 1Password é `webhook_url`, não `url`** — o item "Discord Webhook - Zeus Channel" tem campo `label=webhook_url`. Usar `--fields label=webhook_url --reveal` (não `--fields label=url`).

3. **Sempre exportar `OP_SERVICE_ACCOUNT_TOKEN` antes do `op` em scripts shell** — scripts executados via cron não têm a env do `.env` carregada automaticamente. O `source "${BASE_DIR}/.env"` no início do script é obrigatório. Usar o padrão `set -a / source / set +a` descrito em `references/shell-env-crontab-patterns.md` (padrão canônico MGS para scripts que invocam `op`). Para segurança ao modificar crontab via script, ver a seção "Padrão Proibido" no mesmo arquivo.

4. **WINDOW_LINES pode estar vazio se o log não tem entradas recentes** — tratar o caso sem erro (script deve terminar normalmente com "OK: zero falhas").

5. **`jq -r '.field // 0'` para campos numéricos** — se o state file tiver `"consecutive_failures": null`, o `// 0` garante fallback para 0. Sem isso, aritmética bash pode falhar.

6. **Arquivo `.tmp` intermediário no jq** — sempre usar `jq ... "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"` para evitar truncar o state file em caso de erro do jq.

7. **Regex `[a-f0-9]+` falha silenciosamente em IDs não-hex** — o padrão `grep -oP 'commit=\K[a-f0-9]+'` retorna vazio (e dispara `|| continue`) quando o ID começa com caractere não-hex (ex: `test001` → `t` não é hex → zero match → falha ignorada silenciosamente). Em testes de stress, usar sempre IDs com prefixo hex válido (ex: `dead001`, `cafe001`, `beef001`). Em produção, hashes git reais são sempre hex — não é bug do script, é armadilha nos testes.

8. **Não adicionar o cron manualmente ao crontab** — usar `(crontab -l 2>/dev/null; echo "ENTRY") | crontab -` para preservar entradas existentes. `crontab -l > /tmp/crontab_current.txt && echo "..." >> /tmp/crontab_current.txt && crontab /tmp/crontab_current.txt` também funciona (alternativa usada em 2026-04-26).

---

---

## SEÇÃO B — Monitor de Restarts de Services Systemd

### Quando usar
- Service Hermes crasha repetidamente e ninguém percebe
- Detectar padrão de instabilidade antes de virar incidente crítico

### Como funciona

Cron `*/5 * * * *` → `/root/mgs-agent/scripts/monitor-service-restarts.sh`:
1. Lê `NRestarts` de cada service via `systemctl show`
2. Calcula delta desde baseline da janela de 24h
3. Compara com thresholds e envia alerta via webhook Discord
4. Persiste estado em `/root/mgs-agent/data/service-restart-state.json`

### Services monitorados

| Service | Descrição |
|---|---|
| `zeus-gateway` | Gateway do agente Zeus (Discord) |
| `atena-gateway` | Gateway do agente Atena (Discord) |
| `mgs-autocommit` | Watcher de auto-commit git |

### Thresholds

| Nível | Delta em 24h | Ação |
|---|---|---|
| Silencioso | 0–2 | Nada |
| INFO | 3–4 | ⚠️ `[INFRA] [RESTART]` em #alerts-infra |
| WARN | 5+ | 🚨 `[INFRA] [RESTART]` + mention `<@344196393512075265>` |

Anti-spam: não reenviar mesmo nível por 12h por service.

### Schema do state file

```json
{
  "_meta": {
    "description": "Estado do monitor service-restart-watcher",
    "thresholds": {"info": 3, "warn": 5},
    "window_hours": 24,
    "anti_spam_hours": 12
  },
  "services": {
    "zeus-gateway": {
      "baseline_nrestarts": 0,
      "baseline_timestamp": "ISO8601Z",
      "window_start": "ISO8601Z",
      "last_alert_sent": null,
      "last_alert_level": null
    }
  }
}
```

### Adicionar novo service

```bash
# No script monitor-service-restarts.sh
SERVICES=("zeus-gateway" "atena-gateway" "mgs-autocommit" "novo-service")
bash /root/mgs-agent/scripts/monitor-service-restarts.sh   # cria entrada no state
```

### Mensagens Discord

- INFO: `⚠️ [INFRA] [RESTART] \`{service}\` reiniciou {N}x nas últimas 24h. Acompanhar.`
- WARN: `🚨 [INFRA] [RESTART] \`{service}\` reiniciou {N}x nas últimas 24h. Investigar urgente. <@344196393512075265>`

### Credencial

Webhook: 1Password vault `MGS Conteúdo`, item `Discord Webhook - Alerts Infra Channel`, field `webhook_url`.

---

## SEÇÃO C — Monitor de Skills MGS sem REPORT-INFRA

### Contexto

"Opção C" do sistema defense-in-depth MGS (implementado 2026-04-27). A "Opção A" é o checklist de encerramento nos SOUL.md dos agentes. Juntos, garantem que nenhuma skill MGS seja criada sem registro no inventário.

### Arquivos do sistema

```
/root/mgs-agent/scripts/check-pending-reports.sh   — script principal
/root/mgs-agent/data/pending-reports-state.json    — state anti-spam
/root/mgs-agent/logs/check-pending-reports.log     — output do cron
crontab: */15 * * * *
```

### Diretórios monitorados

| Agente | Diretório |
|--------|-----------|
| Zeus | `/root/.hermes/profiles/zeus/skills/ops/` |
| Atena | `/root/.hermes/profiles/atena/skills/wordpress/` |
| Atena | `/root/.hermes/profiles/atena/skills/devops/` |

**NÃO monitorados** (propositalmente): skills genéricas Hermes (apple/, creative/, mlops/ etc.).

### Schema do state file (pending-reports)

```json
{
  "alerted": {
    "zeus:skill-name": {
      "alerted_at": 1745726823,
      "skill_name": "skill-name",
      "agent": "zeus",
      "path": "/root/.hermes/profiles/zeus/skills/ops/skill-name"
    }
  },
  "resolved": {}
}
```

- Anti-spam: se `now - alerted_at < 86400s (24h)`, não reaterta
- Resolução: quando skill entra no inventário, remove de `alerted` e posta `✅ RESOLVIDO`

### Adicionar novo agente/diretório ao monitor

```bash
# Em SKILL_DIRS:
SKILL_DIRS["novo_agente"]="/root/.hermes/profiles/novo_agente/skills/ops"
# Em DIR_AGENT:
DIR_AGENT["novo_agente"]="novo_agente"
```

### Formato das mensagens Discord

**Alerta:**
```
🚨 [PENDING-REPORT] Skills detectadas SEM REPORT-INFRA:
• `zeus` criou skill `nome-skill`
  Path: `/root/.hermes/profiles/zeus/skills/ops/nome-skill`
Aguardo REPORT-INFRA + atualização de `infra-inventory.json`. <@1496296175014252634>
```

**Resolução:**
```
✅ [PENDING-REPORT] Skill `nome-skill` (agente: `zeus`) agora está no inventário (commit XXXX). Pendência fechada.
```

### Pitfalls específicos do pending-report monitor

1. **Source correto:** `source "/root/mgs-agent/.env"` (tem `OP_SERVICE_ACCOUNT_TOKEN`), não `/root/.hermes/profiles/zeus/.env`
2. **Separador `|` não `:`:** `agent:skill_name` usa `:` — usar `|` como separador em arrays shell; `:` causa colisão e bugs silenciosos
3. **Persistir state ANTES de `curl`:** se curl falha, state deve já ter sido salvo (idempotência evita loop infinito)
4. **Bug histórico 2026-04-27:** combinação dos bugs acima causou ~120 mensagens duplicadas em 8h. Sempre validar com dry-run após modificar lógica de state transitions
5. **Resetar state:** `echo '{"alerted": {}, "resolved": {}}' > /root/mgs-agent/data/pending-reports-state.json`

### Fluxo completo esperado

```
[t=0]   Skill nova criada no filesystem mas não no inventário
[t=15m] Cron detecta → alerta Discord → state atualizado (alerted_at=now)
[t=30m] Cron → anti-spam (< 24h) → silêncio
[t=Xh]  Zeus/Atena atualiza infra-inventory.json
[t=X+15m] Cron → skill está no inventário → ✅ RESOLVIDO → remove de alerted
```

---

## SEÇÃO D — Hardening de Monitors em Produção (checklist obrigatório)

Lições da sessão de auditoria 02/05/2026 — aplicar a todo monitor novo ou existente:

### 1. flock — Proteger contra execuções paralelas

Sem flock, crons `*/5` ou `*/15` podem sobrepor quando o monitor demora mais que o intervalo (ex: timeout de rede).

```bash
# Cron entry com flock:
*/15 * * * * flock -n /tmp/monitor-NOME.lock /root/mgs-agent/scripts/monitor-NOME.sh >> /root/mgs-agent/logs/monitor-NOME.log 2>&1
```

`-n` = não bloqueia (pula a execução se lock estiver ocupado). Sem `-n`, execuções empilham.

**7 crons MGS com flock (aplicado 02/05/2026):** sync-souls, monitor-auto-push, check-pending-reports, monitor-service-restarts, monitor-tool-loops, track-article-cost, cleanup-zombie-sessions.

### 2. --max-time em todo curl

Sem `--max-time`, um webhook Discord lento ou rede instável trava o script indefinidamente, bloqueando o flock e impedindo execuções subsequentes.

```bash
# OBRIGATORIO em qualquer curl para webhook ou API externa:
curl -s -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "$payload" \
  --max-time 15 >/dev/null
```

**3 monitors corrigidos (02/05/2026):** monitor-tool-loops, monitor-anthropic-cost, monitor-service-restarts.

### 3. Logrotate — Nunca deixar logs crescer sem controle

Sem rotação, logs de crons `*/5` ou `*/15` crescem 100-200 linhas/hora. `monitor-service-restarts.log` atingiu 4.2 MB em semanas.

Config em `/etc/logrotate.d/mgs-agent` (criado 02/05/2026):
```
/root/mgs-agent/logs/*.log {
    daily
    maxsize 10M
    rotate 14
    compress
    delaycompress
    copytruncate
    missingok
    notifempty
}
```

`copytruncate` = trunca o log original sem restart do processo (safe para crons). `delaycompress` = mantém o log do dia anterior descomprimido (útil para debug imediato).

### 4. Heurística de frequência vs erros consecutivos

Detectar só erros consecutivos não é suficiente. Cloudflare e similares retornam HTTP 200 em páginas de challenge — o monitor precisa checar frequência também.

```python
# Adicionado em monitor-tool-loops.py (Patch 7, 01/05/2026):
# browser_navigate > 15 em 30 turns = alerta de loop
# Independente de estar retornando 200
```

---

## SEÇÃO E — Bug History: Regras Universais para Monitors com State File

Lessons learned 2026-04-27 (`check-pending-reports.sh` loop de ~120 msgs):

1. **Detectar mudança SEM atualizar estado = loop garantido.** Persistir ANTES da ação externa (curl)
2. **Separador `:` em arrays shell que carregam `agent:skill_name` causa colisão silenciosa** — usar `|`
3. **`declare -A RESOLVED_DEDUP`** para dedup dentro de uma execução
4. **Sempre fazer dry-run manual** após qualquer modificação em monitor com state file

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
