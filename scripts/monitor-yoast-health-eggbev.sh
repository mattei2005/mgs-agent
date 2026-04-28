#!/usr/bin/env bash
# =============================================================================
# monitor-yoast-health-eggbev.sh — Monitor de saúde Yoast (SEO + Readability)
#
# Varre TODOS os posts publicados do eggbev via SQL na wp_yoast_indexable.
# Reporta DUAS métricas em paralelo:
#   - SEO          → primary_focus_keyword_score
#   - Readability  → readability_score
#
# Thresholds Yoast padrão (ambas as métricas):
#   ≥71 verde | 41-70 amarelo | ≤40 vermelho | NULL não analisado
#
# Lógica de postagem:
#   - Primeira execução (sem snapshot anterior) → baseline sempre
#   - Segunda-feira                             → relatório semanal sempre
#   - Degradou significativamente em QUALQUER métrica (OR):
#       * ≥3pp a mais de vermelhos (vs total do dia anterior)
#       * OU ≥5 novos amarelos (absoluto)
#   - Estável ou melhorou em AMBAS                → silencioso (sem post)
#
# Canal destino: Alerts Yoast Channel (via webhook 1Password)
# Estado:   /root/mgs-agent/data/yoast-health-eggbev-snapshots.json
# Log:      /root/mgs-agent/logs/monitor-yoast-health-eggbev.log
#
# Arquitetura: cron Linux standalone (não Hermes interno)
# Substitui:   monitor-yoast-readability-eggbev.sh (deprecated 2026-04-26 — em scripts/deprecated/)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
SNAPSHOT_FILE="${BASE_DIR}/data/yoast-health-eggbev-snapshots.json"
OLD_SNAPSHOT_FILE="${BASE_DIR}/data/yoast-readability-eggbev-snapshots.json"
LOG_PREFIX="monitor-yoast-health-eggbev"

# Carregar env (OP_SERVICE_ACCOUNT_TOKEN etc)
# shellcheck source=/dev/null
set -a
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a

NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
NOW_DATE="$(date +%Y-%m-%d)"
DAY_OF_WEEK="$(date +%u)"  # 1=Mon ... 7=Sun

log() { echo "[$(date -Iseconds)] ${LOG_PREFIX}: $*"; }

log "=== Iniciando monitor-yoast-health-eggbev ==="
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

WEBHOOK_URL="$(op_get_retry 'Discord Webhook - Alerts Yoast Channel' 'MGS Conteúdo' 'label=webhook_url')" || true
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
# Roda no S01 (eggbev). Busca SEO + Readability em duas queries separadas.
# Emite "YOAST_DATA:{json}" com ambas as métricas.
cat > /tmp/yoast_health_query_eggbev.sh << 'EOFREMOTE'
#!/bin/bash
# Executado remotamente no S01 via SSH.
# Consulta wp_yoast_indexable para SEO e Readability.
# Emite "YOAST_DATA:{json}" no stdout.

python3 - << 'PYEOF'
import subprocess, json, sys

WP_PATH = "/home/runcloud/webapps/eggbev"

def classify_scores(sql_output):
    """Classifica rows de (score, count) nos buckets Yoast padrão."""
    green = amber = red = not_analyzed = 0
    for line in sql_output.strip().split("\n"):
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
    return {"green": green, "amber": amber, "red": red, "not_analyzed": not_analyzed}

def run_query(metric_col):
    sql = (
        f"SELECT COALESCE(i.{metric_col}, -1) AS score, COUNT(*) AS cnt "
        f"FROM wp_yoast_indexable i "
        f"INNER JOIN wp_posts p ON i.object_id = p.ID "
        f"WHERE i.object_type = 'post' "
        f"AND p.post_status = 'publish' "
        f"GROUP BY score ORDER BY score"
    )
    result = subprocess.run(
        ["sudo", "-u", "runcloud", "wp", f"--path={WP_PATH}",
         "db", "query", sql, "--skip-column-names"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        print(f"YOAST_ERROR:{metric_col}:{result.stderr.strip()}", flush=True)
        sys.exit(1)
    return result.stdout

# Query SEO (primary_focus_keyword_score)
seo_raw    = run_query("primary_focus_keyword_score")
# Query Readability (readability_score)
read_raw   = run_query("readability_score")

seo  = classify_scores(seo_raw)
read = classify_scores(read_raw)

# Total: usar o readability como referência (mesmo conjunto de posts)
total = read["green"] + read["amber"] + read["red"] + read["not_analyzed"]

print("YOAST_DATA:" + json.dumps({
    "seo":          seo,
    "readability":  read,
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
log "Executando queries no eggbev via SSH (S03→S01)..."

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
sleep 55
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

# SEO
SEO_GREEN=$(echo        "$SCORES_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['seo']['green'])")
SEO_AMBER=$(echo        "$SCORES_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['seo']['amber'])")
SEO_RED=$(echo          "$SCORES_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['seo']['red'])")
SEO_NA=$(echo           "$SCORES_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['seo']['not_analyzed'])")
# Readability
READ_GREEN=$(echo       "$SCORES_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['readability']['green'])")
READ_AMBER=$(echo       "$SCORES_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['readability']['amber'])")
READ_RED=$(echo         "$SCORES_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['readability']['red'])")
READ_NA=$(echo          "$SCORES_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['readability']['not_analyzed'])")
TOTAL=$(echo            "$SCORES_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])")

log "SEO:         verde=${SEO_GREEN}  amarelo=${SEO_AMBER}  vermelho=${SEO_RED}  n/a=${SEO_NA}"
log "Readability: verde=${READ_GREEN} amarelo=${READ_AMBER} vermelho=${READ_RED} n/a=${READ_NA}"
log "Total posts: ${TOTAL}"

# ── Migração de snapshot antigo ───────────────────────────────────────────────
# Se existir snapshot antigo (só readability), migrar para novo arquivo.
# Não remover o antigo — manter como histórico.
if [[ ! -f "$SNAPSHOT_FILE" && -f "$OLD_SNAPSHOT_FILE" ]]; then
    log "Migrando snapshot antigo (readability-only) para novo formato..."
    python3 - << PYEOF
import json

with open("${OLD_SNAPSHOT_FILE}") as f:
    old_data = json.load(f)

# Criar novo arquivo com meta atualizado
new_data = {
    "_meta": {
        "description": "Histórico diário de saúde Yoast (SEO + Readability) — eggbev. Max 90 snapshots (~3 meses).",
        "site": "eggbev",
        "thresholds": {"green_min": 71, "amber_min": 41, "red_max": 40},
        "created": "${NOW_ISO}",
        "migrated_from": "${OLD_SNAPSHOT_FILE}"
    },
    "snapshots": []
}

# Converter snapshots antigos: flat readability → nested {seo: null, readability: {...}}
for old_snap in old_data.get("snapshots", []):
    new_snap = {
        "date":      old_snap.get("date"),
        "timestamp": old_snap.get("timestamp"),
        "total":     old_snap.get("total", 0),
        "post_type": old_snap.get("post_type", "baseline"),
        "seo":          None,   # sem histórico SEO nos snapshots antigos
        "readability": {
            "green":        old_snap.get("green", 0),
            "amber":        old_snap.get("amber", 0),
            "red":          old_snap.get("red", 0),
            "not_analyzed": old_snap.get("not_analyzed", 0)
        }
    }
    new_data["snapshots"].append(new_snap)

with open("${SNAPSHOT_FILE}", "w") as f:
    json.dump(new_data, f, indent=2)

print(f"Migração OK: {len(new_data['snapshots'])} snapshot(s) convertidos.")
PYEOF
    log "Snapshot migrado para $SNAPSHOT_FILE"
fi

# ── Garantir snapshot file ────────────────────────────────────────────────────
if [[ ! -f "$SNAPSHOT_FILE" ]]; then
    python3 - << PYEOF
import json
data = {
    "_meta": {
        "description": "Histórico diário de saúde Yoast (SEO + Readability) — eggbev. Max 90 snapshots (~3 meses).",
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

# ── Lógica de decisão (OR: alerta se QUALQUER métrica degradar) ───────────────
IS_MONDAY="false"
IS_FIRST_RUN="false"
SHOULD_POST="false"
POST_TYPE="silent"

# Deltas SEO
SEO_DELTA_RED=0
SEO_DELTA_AMBER=0
SEO_DELTA_GREEN=0
# Deltas Readability
READ_DELTA_RED=0
READ_DELTA_AMBER=0
READ_DELTA_GREEN=0

[[ "$DAY_OF_WEEK" == "1" ]] && IS_MONDAY="true"

if [[ "$PREV_RESULT" == "null" ]]; then
    IS_FIRST_RUN="true"
    SHOULD_POST="true"
    POST_TYPE="baseline"
    log "Primeira execução — baseline será postado"
else
    # Extrair prev SEO (pode ser null se snapshot antigo migrado)
    PREV_HAS_SEO=$(echo "$PREV_RESULT" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('true' if d.get('seo') is not None else 'false')
")
    PREV_TOTAL=$(echo "$PREV_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))")

    # ── Readability: sempre temos histórico (migrado ou nativo)
    PREV_READ_RED=$(echo   "$PREV_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('readability',{}).get('red',0))")
    PREV_READ_AMBER=$(echo "$PREV_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('readability',{}).get('amber',0))")
    PREV_READ_GREEN=$(echo "$PREV_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('readability',{}).get('green',0))")

    READ_DELTA_RED=$(( READ_RED - PREV_READ_RED ))
    READ_DELTA_AMBER=$(( READ_AMBER - PREV_READ_AMBER ))
    READ_DELTA_GREEN=$(( READ_GREEN - PREV_READ_GREEN ))

    # ── SEO: só comparar se snapshot anterior tinha SEO
    PREV_SEO_RED=0
    PREV_SEO_AMBER=0
    PREV_SEO_GREEN=0
    if [[ "$PREV_HAS_SEO" == "true" ]]; then
        PREV_SEO_RED=$(echo   "$PREV_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('seo',{}).get('red',0))")
        PREV_SEO_AMBER=$(echo "$PREV_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('seo',{}).get('amber',0))")
        PREV_SEO_GREEN=$(echo "$PREV_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('seo',{}).get('green',0))")
        SEO_DELTA_RED=$(( SEO_RED - PREV_SEO_RED ))
        SEO_DELTA_AMBER=$(( SEO_AMBER - PREV_SEO_AMBER ))
        SEO_DELTA_GREEN=$(( SEO_GREEN - PREV_SEO_GREEN ))
    else
        log "Snapshot anterior sem SEO (migrado) — comparação SEO ignorada nesta run"
    fi

    # ── Verificar degradação: OR entre métricas
    DEGRADED="false"

    # Readability
    if [[ "$PREV_TOTAL" -gt 0 && "$READ_DELTA_RED" -gt 0 ]]; then
        READ_RED_PP=$(python3 -c "print(round(($READ_RED - $PREV_READ_RED) * 100 / $PREV_TOTAL))")
        log "Read variação vermelhos: +${READ_DELTA_RED} posts = +${READ_RED_PP}pp"
        if [[ "$READ_RED_PP" -ge 3 ]]; then
            DEGRADED="true"
            log "ALERTA: Readability — vermelhos ≥3pp"
        fi
    fi
    if [[ "$READ_DELTA_AMBER" -ge 5 ]]; then
        DEGRADED="true"
        log "ALERTA: Readability — ≥5 novos amarelos (delta=${READ_DELTA_AMBER})"
    fi

    # SEO (apenas se havia histórico)
    if [[ "$PREV_HAS_SEO" == "true" ]]; then
        if [[ "$PREV_TOTAL" -gt 0 && "$SEO_DELTA_RED" -gt 0 ]]; then
            SEO_RED_PP=$(python3 -c "print(round(($SEO_RED - $PREV_SEO_RED) * 100 / $PREV_TOTAL))")
            log "SEO variação vermelhos: +${SEO_DELTA_RED} posts = +${SEO_RED_PP}pp"
            if [[ "$SEO_RED_PP" -ge 3 ]]; then
                DEGRADED="true"
                log "ALERTA: SEO — vermelhos ≥3pp"
            fi
        fi
        if [[ "$SEO_DELTA_AMBER" -ge 5 ]]; then
            DEGRADED="true"
            log "ALERTA: SEO — ≥5 novos amarelos (delta=${SEO_DELTA_AMBER})"
        fi
    fi

    if [[ "$IS_MONDAY" == "true" ]]; then
        SHOULD_POST="true"
        POST_TYPE="weekly"
        log "Segunda-feira — relatório semanal será postado"
    elif [[ "$DEGRADED" == "true" ]]; then
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
    "date":      "${NOW_DATE}",
    "timestamp": "${NOW_ISO}",
    "total":     ${TOTAL},
    "post_type": "${POST_TYPE}",
    "seo": {
        "green":        ${SEO_GREEN},
        "amber":        ${SEO_AMBER},
        "red":          ${SEO_RED},
        "not_analyzed": ${SEO_NA}
    },
    "readability": {
        "green":        ${READ_GREEN},
        "amber":        ${READ_AMBER},
        "red":          ${READ_RED},
        "not_analyzed": ${READ_NA}
    }
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
    log "=== Concluído (silencioso). SEO: 🟢${SEO_GREEN}/🟡${SEO_AMBER}/🔴${SEO_RED} | Read: 🟢${READ_GREEN}/🟡${READ_AMBER}/🔴${READ_RED} ==="
    exit 0
fi

# ── Formatar mensagem Discord ─────────────────────────────────────────────────
DATE_DISPLAY="$(date +"%d/%m %Hh")"

DISCORD_MSG=$(python3 - << PYEOF
import json

post_type    = "${POST_TYPE}"
date_display = "${DATE_DISPLAY}"
total        = ${TOTAL}
is_first     = "${IS_FIRST_RUN}" == "true"

# SEO
seo_g  = ${SEO_GREEN};  seo_a  = ${SEO_AMBER};  seo_r  = ${SEO_RED};  seo_na  = ${SEO_NA}
# Readability
read_g = ${READ_GREEN}; read_a = ${READ_AMBER}; read_r = ${READ_RED}; read_na = ${READ_NA}

# Deltas
seo_dr = ${SEO_DELTA_RED};   seo_da = ${SEO_DELTA_AMBER};   seo_dg = ${SEO_DELTA_GREEN}
rd_dr  = ${READ_DELTA_RED};  rd_da  = ${READ_DELTA_AMBER};  rd_dg  = ${READ_DELTA_GREEN}

def delta_str(dr, da, dg, first_seo=False):
    if first_seo:
        return "primeira medição SEO (sem histórico anterior)"
    parts = []
    if dr > 0:  parts.append(f"+{dr} vermelho(s) ⬆️")
    elif dr < 0: parts.append(f"{dr} vermelho(s) ⬇️")
    if da > 0:  parts.append(f"+{da} amarelo(s) ⬆️")
    elif da < 0: parts.append(f"{da} amarelo(s) ⬇️")
    if dg > 0:  parts.append(f"+{dg} verde(s) ⬆️")
    elif dg < 0: parts.append(f"{dg} verde(s) ⬇️")
    return ", ".join(parts) if parts else "sem mudança significativa ✅"

# Cabeçalho
headers = {
    "baseline": f"📊 **[EGGBEV.COM] [YOAST] Baseline ({date_display})**",
    "weekly":   f"📅 **[EGGBEV.COM] [YOAST] Relatório semanal ({date_display})**",
    "alert":    f"⚠️ **[EGGBEV.COM] [YOAST] ALERTA degradação ({date_display})**",
}
header = headers.get(post_type, f"📊 **[EGGBEV.COM] [YOAST] Saúde ({date_display})**")

lines = [
    header,
    f"Total posts publicados: **{total}**",
    "",
    "⚠️ *Cada post conta em ambas as métricas (mesmo post pode ser SEO 🟢 + Read 🔴):*",
    "",
    f"🎯 **SEO:**        {seo_g}🟢 / {seo_a}🟡 / {seo_r}🔴 / {seo_na}⚪",
    f"📖 **Readability:** {read_g}🟢 / {read_a}🟡 / {read_r}🔴 / {read_na}⚪",
]

# Variação (não mostrar no baseline / primeira run SEO)
if not is_first:
    prev_has_seo = "${PREV_HAS_SEO:-false}" == "true"
    lines.append("")
    lines.append(f"Variação SEO vs ontem: {delta_str(seo_dr, seo_da, seo_dg, first_seo=not prev_has_seo)}")
    lines.append(f"Variação Readability vs ontem: {delta_str(rd_dr, rd_da, rd_dg)}")

# CTA
lines.append("")
lines.append("💬 Para listar URLs por cor/métrica, peça no <#1496267571543019653>")

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

log "=== Concluído (post_type=${POST_TYPE}). SEO: 🟢${SEO_GREEN}/🟡${SEO_AMBER}/🔴${SEO_RED} | Read: 🟢${READ_GREEN}/🟡${READ_AMBER}/🔴${READ_RED} total=${TOTAL} ==="
