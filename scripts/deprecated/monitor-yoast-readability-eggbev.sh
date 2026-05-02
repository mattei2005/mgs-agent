#!/usr/bin/env bash
# =============================================================================
# monitor-yoast-readability-eggbev.sh — Monitor de saúde readability Yoast
#
# Varre TODOS os posts publicados do eggbev via SQL na wp_yoast_indexable.
# Thresholds Yoast padrão: ≥71 verde, 41-70 amarelo, ≤40 vermelho, NULL n/a.
#
# Lógica de postagem:
#   - Primeira execução (sem snapshot anterior) → baseline sempre
#   - Segunda-feira                             → relatório semanal sempre
#   - Degradou significativamente               → alerta
#       * ≥3 pontos percentuais a mais de vermelhos (vs total do dia anterior)
#       * OU ≥5 novos amarelos (absoluto)
#   - Estável ou melhorou                       → silencioso (sem post)
#
# Canal destino: MGS Alerts Channel (via webhook 1Password)
# Estado:   /root/mgs-agent/data/yoast-readability-eggbev-snapshots.json
# Log:      /root/mgs-agent/logs/monitor-yoast-readability-eggbev.log
#
# Arquitetura: cron Linux standalone (não Hermes interno)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
SNAPSHOT_FILE="${BASE_DIR}/data/yoast-readability-eggbev-snapshots.json"
LOG_PREFIX="monitor-yoast-readability-eggbev"

# Carregar env (OP_SERVICE_ACCOUNT_TOKEN etc)
# shellcheck source=/dev/null
source "${BASE_DIR}/.env" 2>/dev/null || true

NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
NOW_DATE="$(date +%Y-%m-%d)"
DAY_OF_WEEK="$(date +%u)"  # 1=Mon ... 7=Sun

log() { echo "[$(date -Iseconds)] ${LOG_PREFIX}: $*"; }

log "=== Iniciando monitor-yoast-readability-eggbev ==="
log "Data: ${NOW_DATE} | Dia semana: ${DAY_OF_WEEK}"

# ── Credenciais ───────────────────────────────────────────────────────────────
log "Buscando credenciais via 1Password..."

# Retry helper: 3 tentativas com 2s de espera entre elas
# Necessário porque runs consecutivos rápidos podem causar rate-limit transitório do op CLI
op_get_retry() {
    local item="$1" vault="$2" field="$3"
    local val="" attempt=0
    while [[ $attempt -lt 3 ]]; do
        val="$(op item get "$item" --vault "$vault" --fields "$field" --reveal 2>/dev/null)" || true
        [[ -n "$val" ]] && echo "$val" && return 0
        attempt=$(( attempt + 1 ))
        [[ $attempt -lt 3 ]] && sleep 2
    done
    return 1
}

WEBHOOK_URL="$(op_get_retry 'Discord Webhook - Alerts Infra Channel' 'MGS Conteúdo' 'label=webhook_url')" || true
S03_PASS="$(op_get_retry 'Runcloud Server 03 - 46.4.95.117- zeus Acesso' 'MGS Conteúdo' 'password')" || true
S01_PASS="$(op_get_retry 'Runcloud Server 01 - 162.55.28.178- zeus Acesso' 'MGS Conteúdo' 'password')" || true

if [[ -z "$WEBHOOK_URL" ]]; then
    log "ERRO CRÍTICO: Webhook URL vazio após 3 tentativas — abortando"
    exit 1
fi
if [[ -z "$S03_PASS" || -z "$S01_PASS" ]]; then
    log "ERRO CRÍTICO: Credenciais SSH vazias após 3 tentativas — abortando"
    exit 1
fi
log "Credenciais OK."

# ── Script remoto ─────────────────────────────────────────────────────────────
# Roda no S01 (eggbev). Usa Python subprocess para WP-CLI — evita
# heredoc aninhado e problemas de expansão de variáveis.
cat > /tmp/yoast_health_query_eggbev.sh << 'EOFREMOTE'
#!/bin/bash
# Executado remotamente no S01 via SSH.
# Consulta wp_yoast_indexable e emite "YOAST_DATA:{json}" no stdout.

python3 - << 'PYEOF'
import subprocess, json, sys

WP_PATH = "/home/runcloud/webapps/eggbev"

SQL = (
    "SELECT COALESCE(i.readability_score, -1) AS score, COUNT(*) AS cnt "
    "FROM wp_yoast_indexable i "
    "INNER JOIN wp_posts p ON i.object_id = p.ID "
    "WHERE i.object_type = 'post' "
    "AND p.post_status = 'publish' "
    "GROUP BY score "
    "ORDER BY score"
)

result = subprocess.run(
    ["sudo", "-u", "runcloud", "wp", f"--path={WP_PATH}",
     "db", "query", SQL, "--skip-column-names"],
    capture_output=True, text=True, timeout=60
)

if result.returncode != 0:
    print(f"YOAST_ERROR:{result.stderr.strip()}", flush=True)
    sys.exit(1)

green = amber = red = not_analyzed = 0

for line in result.stdout.strip().split("\n"):
    line = line.strip()
    if not line:
        continue
    parts = line.split("\t")
    if len(parts) != 2:
        continue
    try:
        score = int(parts[0].strip())
        count = int(parts[1].strip())
    except ValueError:
        continue

    if score == -1:
        not_analyzed += count
    elif score >= 71:
        green += count
    elif score >= 41:
        amber += count
    else:
        red += count

total = green + amber + red + not_analyzed

print("YOAST_DATA:" + json.dumps({
    "green":        green,
    "amber":        amber,
    "red":          red,
    "not_analyzed": not_analyzed,
    "total":        total
}), flush=True)
PYEOF
EOFREMOTE
chmod +x /tmp/yoast_health_query_eggbev.sh

# ── SCP do script remoto ──────────────────────────────────────────────────────
log "Enviando script remoto via SCP (S03→S01)..."

cat > /tmp/_yoast_scp.exp << 'EOFEXP'
#!/usr/bin/expect -f
set s03 [lindex $argv 0]
set s01 [lindex $argv 1]
set timeout 30
spawn scp -o StrictHostKeyChecking=no -J zeus@46.4.95.117 \
    /tmp/yoast_health_query_eggbev.sh \
    zeus@162.55.28.178:/tmp/yoast_health_query_eggbev.sh
expect "46.4.95.117's password:"
send "$s03\r"
expect "162.55.28.178's password:"
send "$s01\r"
expect {
    "100%" { exp_continue }
    eof    {}
}
EOFEXP
chmod +x /tmp/_yoast_scp.exp
/tmp/_yoast_scp.exp "$S03_PASS" "$S01_PASS" > /dev/null 2>&1
log "SCP OK."

# ── SSH execute + captura output ──────────────────────────────────────────────
log "Executando query no eggbev via SSH (S03→S01)..."

cat > /tmp/_yoast_ssh.exp << 'EOFEXP'
#!/usr/bin/expect -f
set s03 [lindex $argv 0]
set s01 [lindex $argv 1]
set timeout 120
spawn ssh -o StrictHostKeyChecking=no -J zeus@46.4.95.117 zeus@162.55.28.178
expect "46.4.95.117's password:"
send "$s03\r"
expect "162.55.28.178's password:"
send "$s01\r"
expect "Made with"
sleep 3
send "bash /tmp/yoast_health_query_eggbev.sh\r"
sleep 45
send "exit\r"
expect eof
EOFEXP
chmod +x /tmp/_yoast_ssh.exp

SSH_OUT=$(/tmp/_yoast_ssh.exp "$S03_PASS" "$S01_PASS" 2>/dev/null)

# ── Parse resultado ───────────────────────────────────────────────────────────
YOAST_LINE=$(echo "$SSH_OUT" | grep "^YOAST_DATA:" | head -1 || true)
ERROR_LINE=$(echo "$SSH_OUT"  | grep "^YOAST_ERROR:" | head -1 || true)

if [[ -n "$ERROR_LINE" ]]; then
    log "ERRO REMOTO: ${ERROR_LINE#YOAST_ERROR:}"
    exit 1
fi

if [[ -z "$YOAST_LINE" ]]; then
    log "ERRO: marcador YOAST_DATA não encontrado no output SSH"
    log "Últimas 30 linhas do output:"
    echo "$SSH_OUT" | tail -30 | while IFS= read -r l; do log "  > $l"; done
    exit 1
fi

SCORES_JSON="${YOAST_LINE#YOAST_DATA:}"

GREEN=$(echo        "$SCORES_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['green'])")
AMBER=$(echo        "$SCORES_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['amber'])")
RED=$(echo          "$SCORES_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['red'])")
NOT_ANALYZED=$(echo "$SCORES_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['not_analyzed'])")
TOTAL=$(echo        "$SCORES_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])")

log "Scores recebidos: verde=${GREEN} amarelo=${AMBER} vermelho=${RED} n/a=${NOT_ANALYZED} total=${TOTAL}"

# ── Garantir snapshot file ────────────────────────────────────────────────────
if [[ ! -f "$SNAPSHOT_FILE" ]]; then
    python3 - << PYEOF
import json
data = {
    "_meta": {
        "description": "Histórico diário de saúde readability Yoast — eggbev. Max 90 snapshots (~3 meses).",
        "site": "eggbev",
        "thresholds": {"green_min": 71, "amber_min": 41, "red_max": 40},
        "created": "${NOW_ISO}"
    },
    "snapshots": []
}
with open("${SNAPSHOT_FILE}", "w") as f:
    json.dump(data, f, indent=2)
print("Snapshot file criado.")
PYEOF
    log "Snapshot file inicializado em $SNAPSHOT_FILE"
fi

# ── Ler snapshot anterior ─────────────────────────────────────────────────────
PREV_RESULT=$(python3 - << PYEOF
import json
with open("${SNAPSHOT_FILE}") as f:
    data = json.load(f)
snaps = data.get("snapshots", [])
if snaps:
    print(json.dumps(snaps[-1]))
else:
    print("null")
PYEOF
)

# ── Lógica de decisão ─────────────────────────────────────────────────────────
IS_MONDAY="false"
IS_FIRST_RUN="false"
SHOULD_POST="false"
POST_TYPE="silent"
DELTA_RED=0
DELTA_AMBER=0
DELTA_GREEN=0
PREV_GREEN=0
PREV_AMBER=0
PREV_RED=0
PREV_TOTAL=0

[[ "$DAY_OF_WEEK" == "1" ]] && IS_MONDAY="true"

if [[ "$PREV_RESULT" == "null" ]]; then
    IS_FIRST_RUN="true"
    SHOULD_POST="true"
    POST_TYPE="baseline"
    log "Primeira execução — baseline será postado"
else
    PREV_GREEN=$(echo "$PREV_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['green'])")
    PREV_AMBER=$(echo "$PREV_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['amber'])")
    PREV_RED=$(echo   "$PREV_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['red'])")
    PREV_TOTAL=$(echo "$PREV_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])")

    DELTA_RED=$(( RED - PREV_RED ))
    DELTA_AMBER=$(( AMBER - PREV_AMBER ))
    DELTA_GREEN=$(( GREEN - PREV_GREEN ))

    # Verificar degradação
    DEGRADED_RED="false"
    DEGRADED_AMBER="false"

    if [[ "$PREV_TOTAL" -gt 0 && "$DELTA_RED" -gt 0 ]]; then
        # ≥3 pontos percentuais a mais de vermelhos
        RED_PP=$(python3 -c "print(round(($RED - $PREV_RED) * 100 / $PREV_TOTAL))")
        log "Variação vermelhos: +${DELTA_RED} posts = +${RED_PP}pp"
        if [[ "$RED_PP" -ge 3 ]]; then
            DEGRADED_RED="true"
            log "ALERTA: degradação vermelhos ≥3pp detectada"
        fi
    fi

    if [[ "$DELTA_AMBER" -ge 5 ]]; then
        DEGRADED_AMBER="true"
        log "ALERTA: ≥5 novos amarelos (delta=${DELTA_AMBER})"
    fi

    if [[ "$IS_MONDAY" == "true" ]]; then
        SHOULD_POST="true"
        POST_TYPE="weekly"
        log "Segunda-feira — relatório semanal será postado"
    elif [[ "$DEGRADED_RED" == "true" || "$DEGRADED_AMBER" == "true" ]]; then
        SHOULD_POST="true"
        POST_TYPE="alert"
        log "Degradação detectada — alerta será postado"
    else
        log "Estável ou melhora — silencioso (sem post)"
    fi
fi

# ── Salvar snapshot atual ─────────────────────────────────────────────────────
python3 - << PYEOF
import json

with open("${SNAPSHOT_FILE}") as f:
    data = json.load(f)

snap = {
    "date":         "${NOW_DATE}",
    "timestamp":    "${NOW_ISO}",
    "green":        ${GREEN},
    "amber":        ${AMBER},
    "red":          ${RED},
    "not_analyzed": ${NOT_ANALYZED},
    "total":        ${TOTAL},
    "post_type":    "${POST_TYPE}"
}
data["snapshots"].append(snap)

# Manter máximo 90 snapshots (~3 meses)
if len(data["snapshots"]) > 90:
    data["snapshots"] = data["snapshots"][-90:]

with open("${SNAPSHOT_FILE}", "w") as f:
    json.dump(data, f, indent=2)

print("Snapshot salvo.")
PYEOF
log "Snapshot salvo em $SNAPSHOT_FILE"

# ── Encerrar se silencioso ────────────────────────────────────────────────────
if [[ "$SHOULD_POST" == "false" ]]; then
    log "Modo silencioso — encerrando sem post Discord."
    rm -f /tmp/yoast_health_query_eggbev.sh /tmp/_yoast_scp.exp /tmp/_yoast_ssh.exp
    log "=== Concluído (silencioso). verde=${GREEN} amarelo=${AMBER} vermelho=${RED} n/a=${NOT_ANALYZED} ==="
    exit 0
fi

# ── Formatar mensagem Discord ─────────────────────────────────────────────────
DATE_DISPLAY="$(date +"%d/%m %Hh")"

DISCORD_MSG=$(python3 - << PYEOF
import json

post_type    = "${POST_TYPE}"
date_display = "${DATE_DISPLAY}"
total        = ${TOTAL}
green        = ${GREEN}
amber        = ${AMBER}
red          = ${RED}
not_analyzed = ${NOT_ANALYZED}
is_first     = "${IS_FIRST_RUN}" == "true"
delta_green  = ${DELTA_GREEN}
delta_amber  = ${DELTA_AMBER}
delta_red    = ${DELTA_RED}

# Percentuais
def pct(n, t):
    return round(n * 100 / t) if t > 0 else 0

g_pct  = pct(green, total)
a_pct  = pct(amber, total)
r_pct  = pct(red, total)
na_pct = pct(not_analyzed, total)

# Cabeçalho
headers = {
    "baseline": f"📊 **[YOAST] Baseline eggbev ({date_display})**",
    "weekly":   f"📅 **[YOAST] Relatório semanal eggbev ({date_display})**",
    "alert":    f"⚠️ **[YOAST] ALERTA degradação — eggbev ({date_display})**",
}
header = headers.get(post_type, f"📊 **[YOAST] Saúde readability eggbev ({date_display})**")

lines = [
    header,
    "",
    f"Total posts publicados: **{total}**",
    f"🟢 Verdes (≥71): {green} ({g_pct}%)",
    f"🟡 Amarelos (41–70): {amber} ({a_pct}%)",
    f"🔴 Vermelhos (≤40): {red} ({r_pct}%)",
    f"⚪ Não analisados: {not_analyzed} ({na_pct}%)",
]

# Variação (não mostrar no baseline)
if not is_first:
    delta_parts = []
    if delta_red > 0:
        delta_parts.append(f"+{delta_red} vermelho(s) ⬆️")
    elif delta_red < 0:
        delta_parts.append(f"{delta_red} vermelho(s) ⬇️")
    if delta_amber > 0:
        delta_parts.append(f"+{delta_amber} amarelo(s) ⬆️")
    elif delta_amber < 0:
        delta_parts.append(f"{delta_amber} amarelo(s) ⬇️")
    if delta_green > 0:
        delta_parts.append(f"+{delta_green} verde(s) ⬆️")
    elif delta_green < 0:
        delta_parts.append(f"{delta_green} verde(s) ⬇️")

    if delta_parts:
        lines.append("")
        lines.append("Variação vs ontem: " + ", ".join(delta_parts))
    else:
        lines.append("")
        lines.append("Variação vs ontem: sem mudança significativa ✅")

# CTA
lines.append("")
if post_type == "alert":
    lines.append("💬 Para listar URLs problemáticas, peça no <#1496267571543019653>")
else:
    lines.append("💬 Para listar URLs por cor, peça no <#1496267571543019653>")

print(json.dumps({"content": chr(10).join(lines)}))
PYEOF
)

log "Postando no Discord (tipo=${POST_TYPE})..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "$DISCORD_MSG" \
    --max-time 15)

if [[ "$HTTP_CODE" == "204" ]]; then
    log "Discord: OK (HTTP 204)"
else
    log "AVISO: Discord retornou HTTP ${HTTP_CODE} — verificar webhook"
fi

# ── Cleanup ───────────────────────────────────────────────────────────────────
rm -f /tmp/yoast_health_query_eggbev.sh /tmp/_yoast_scp.exp /tmp/_yoast_ssh.exp

log "=== Concluído (post_type=${POST_TYPE}). verde=${GREEN} amarelo=${AMBER} vermelho=${RED} n/a=${NOT_ANALYZED} total=${TOTAL} ==="
