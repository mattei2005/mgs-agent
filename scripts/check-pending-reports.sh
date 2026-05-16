#!/bin/bash
# check-pending-reports.sh — Detecta skills MGS sem REPORT-INFRA no inventário
# Cron: */15 * * * * /root/mgs-agent/scripts/check-pending-reports.sh >> /root/mgs-agent/logs/check-pending-reports.log 2>&1

set -euo pipefail

BASE_DIR="/root/mgs-agent"
STATE_FILE="${BASE_DIR}/data/pending-reports-state.json"
INVENTORY_FILE="${BASE_DIR}/data/infra-inventory.json"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

# Carregar variáveis de ambiente (incluindo OP_SERVICE_ACCOUNT_TOKEN)
set -a
# shellcheck source=/dev/null
source "/root/mgs-agent/.env" 2>/dev/null || true
set +a

# Buscar webhook via 1Password (canal Zeus — alerta operacional ao Zeus, não infra)
WEBHOOK_URL=$(op item get "Discord Webhook - Zeus Channel" --vault "MGS Conteúdo" --fields label=webhook_url 2>/dev/null || true)

if [[ -z "$WEBHOOK_URL" ]]; then
    echo "${LOG_PREFIX} ERRO: Não foi possível obter WEBHOOK_URL do 1Password. Abortando."
    exit 1
fi

# Mention do Rodolfo para push notification
ZEUS_MENTION="<@344196393512075265>"

# Inicializar state file se não existir
if [[ ! -f "$STATE_FILE" ]]; then
    echo '{"alerted": {}, "resolved": {}}' > "$STATE_FILE"
    echo "${LOG_PREFIX} State file criado: ${STATE_FILE}"
fi

# Diretórios de skills MGS-específicos a monitorar
# Zeus: ops/
# Atena: wordpress/, devops/
declare -A SKILL_DIRS
SKILL_DIRS["zeus"]="/root/.hermes/profiles/zeus/skills/ops"
SKILL_DIRS["atena_wp"]="/root/.hermes/profiles/atena/skills/wordpress"
SKILL_DIRS["atena_devops"]="/root/.hermes/profiles/atena/skills/devops"

# Mapear agent real para cada dir key
declare -A DIR_AGENT
DIR_AGENT["zeus"]="zeus"
DIR_AGENT["atena_wp"]="atena"
DIR_AGENT["atena_devops"]="atena"

# Carregar inventário
INVENTORY=$(cat "$INVENTORY_FILE")

# Extrair skills registradas no inventário (por agente)
get_inventory_skills() {
    local agent="$1"
    echo "$INVENTORY" | python3 -c "
import json, sys
d = json.load(sys.stdin)
skills = d.get('skills_hermes', {}).get('$agent', [])
for s in skills:
    print(s.get('name', ''))
" 2>/dev/null || true
}

ZEUS_INVENTORY_SKILLS=$(get_inventory_skills "zeus")
ATENA_INVENTORY_SKILLS=$(get_inventory_skills "atena")

# Carregar state atual
STATE=$(cat "$STATE_FILE")
NOW=$(date +%s)
ANTISPAM_SECONDS=86400  # 24h

PENDING_SKILLS=()
RESOLVED_SKILLS=()

# Verificar cada diretório de skills
for dir_key in "${!SKILL_DIRS[@]}"; do
    skill_dir="${SKILL_DIRS[$dir_key]}"
    agent="${DIR_AGENT[$dir_key]}"

    [[ ! -d "$skill_dir" ]] && continue

    # Inventário do agente
    if [[ "$agent" == "zeus" ]]; then
        inventory_skills="$ZEUS_INVENTORY_SKILLS"
    else
        inventory_skills="$ATENA_INVENTORY_SKILLS"
    fi

    # Listar skills no filesystem (cada subdiretório com SKILL.md)
    for skill_path in "$skill_dir"/*/SKILL.md; do
        [[ ! -f "$skill_path" ]] && continue
        skill_name=$(basename "$(dirname "$skill_path")")
        skill_full_path=$(dirname "$skill_path")
        skill_key="${agent}:${skill_name}"

        # Verificar se skill está no inventário
        if echo "$inventory_skills" | grep -qx "$skill_name"; then
            # Está no inventário — verificar se estava pendente (resolver)
            was_alerted=$(echo "$STATE" | python3 -c "
import json, sys
d = json.load(sys.stdin)
alerted = d.get('alerted', {})
print(alerted.get('${skill_key}', {}).get('alerted_at', ''))
" 2>/dev/null || true)

            if [[ -n "$was_alerted" ]]; then
                RESOLVED_SKILLS+=("${skill_key}|${skill_full_path}")
                echo "${LOG_PREFIX} RESOLVIDO: ${skill_key} agora está no inventário"
            fi
        else
            # NÃO está no inventário — verificar anti-spam
            last_alerted=$(echo "$STATE" | python3 -c "
import json, sys
d = json.load(sys.stdin)
alerted = d.get('alerted', {})
print(alerted.get('${skill_key}', {}).get('alerted_at', 0))
" 2>/dev/null || echo "0")

            last_alerted=${last_alerted:-0}
            elapsed=$(( NOW - last_alerted ))

            if (( elapsed > ANTISPAM_SECONDS )); then
                PENDING_SKILLS+=("${agent}|${skill_name}|${skill_full_path}|${skill_key}")
                echo "${LOG_PREFIX} PENDENTE: skill '${skill_name}' do agente '${agent}' não está no inventário"
            else
                echo "${LOG_PREFIX} SKIP (anti-spam): ${skill_key} já alertado há $((elapsed/3600))h"
            fi
        fi
    done
done

# Enviar alertas para skills pendentes
if (( ${#PENDING_SKILLS[@]} > 0 )); then
    # Construir mensagem estruturada
    rows=""
    for entry in "${PENDING_SKILLS[@]}"; do
        IFS='|' read -r agent skill_name skill_path skill_key <<< "$entry"
        rows+="${agent} | ${skill_name} | ${skill_path}\n"
    done

    # Postar no Discord
    payload=$(python3 - "$ZEUS_MENTION" "$rows" "${#PENDING_SKILLS[@]}" <<'PY'
import json, sys
mention, rows, count = sys.argv[1], sys.argv[2], sys.argv[3]
print(json.dumps({
  'content': f'{mention} pending report detectado',
  'embeds': [{
    'title': 'Skills sem REPORT-INFRA',
    'color': 15158332,
    'fields': [
      {'name': 'Pendências', 'value': count, 'inline': True},
      {'name': 'Ação', 'value': 'Enviar REPORT-INFRA e atualizar `infra-inventory.json`.', 'inline': False},
      {'name': 'Itens', 'value': f'```text\n{rows[:900]}\n```', 'inline': False},
    ]
  }]
}))
PY
)

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$WEBHOOK_URL")

    if [[ "$HTTP_CODE" == "204" ]]; then
        echo "${LOG_PREFIX} Alerta enviado ao Discord (${#PENDING_SKILLS[@]} skills pendentes)"
        # Atualizar state — marcar como alerted
        for entry in "${PENDING_SKILLS[@]}"; do
            IFS='|' read -r agent skill_name skill_path skill_key <<< "$entry"
            STATE=$(STATE_JSON="$STATE" python3 - "$skill_key" "$NOW" "$skill_name" "$agent" "$skill_path" <<'PY'
import json, os, sys
skill_key, now, skill_name, agent, skill_path = sys.argv[1:6]
d = json.loads(os.environ["STATE_JSON"])
d.setdefault('alerted', {})[skill_key] = {
    'alerted_at': int(now),
    'skill_name': skill_name,
    'agent': agent,
    'path': skill_path,
}
print(json.dumps(d, indent=2))
PY
)
        done
        echo "$STATE" > "$STATE_FILE"
    else
        echo "${LOG_PREFIX} ERRO ao enviar Discord: HTTP ${HTTP_CODE}"
    fi
else
    echo "${LOG_PREFIX} OK — nenhuma skill pendente de REPORT-INFRA"
fi

# Enviar notificações de resolução
if (( ${#RESOLVED_SKILLS[@]} > 0 )); then
    # Deduplicar por skill_key antes de processar
    declare -A RESOLVED_DEDUP
    for entry in "${RESOLVED_SKILLS[@]}"; do
        IFS='|' read -r skill_key skill_path <<< "$entry"
        RESOLVED_DEDUP["$skill_key"]="$skill_path"
    done

    for skill_key in "${!RESOLVED_DEDUP[@]}"; do
        skill_path="${RESOLVED_DEDUP[$skill_key]}"
        # skill_key = "agent:skill_name"
        skill_name="${skill_key#*:}"
        agent="${skill_key%%:*}"

        # Buscar commit mais recente do inventário para evidência
        last_commit=$(cd "$BASE_DIR" && git log --oneline -1 -- data/infra-inventory.json 2>/dev/null | awk '{print $1}' || echo "N/A")

        payload=$(python3 - "$skill_name" "$agent" "$last_commit" <<'PY'
import json, sys
skill_name, agent, last_commit = sys.argv[1:4]
print(json.dumps({
  'content': '',
  'embeds': [{
    'title': 'Pending report resolvido',
    'color': 3066993,
    'fields': [
      {'name': 'Skill', 'value': f'`{skill_name}`', 'inline': True},
      {'name': 'Agent', 'value': f'`{agent}`', 'inline': True},
      {'name': 'Inventário', 'value': f'commit `{last_commit}`', 'inline': False},
    ]
  }]
}))
PY
)

        # Persistir remoção do state ANTES de enviar (idempotência)
        STATE=$(STATE_JSON="$STATE" python3 - "$skill_key" "$skill_name" "$agent" <<'PY'
import json, os, sys, datetime
skill_key, skill_name, agent = sys.argv[1:4]
d = json.loads(os.environ["STATE_JSON"])
entry = d.get('alerted', {}).pop(skill_key, None)
d.setdefault('resolved', {})[skill_key] = {
    'resolved_at': datetime.datetime.now(datetime.timezone.utc).isoformat() + 'Z',
    'skill_name': skill_name,
    'agent': agent,
}
print(json.dumps(d, indent=2))
PY
)
        echo "$STATE" > "$STATE_FILE"

        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Content-Type: application/json" \
            -d "$payload" \
            "$WEBHOOK_URL")

        if [[ "$HTTP_CODE" == "204" ]]; then
            echo "${LOG_PREFIX} Resolução enviada para ${skill_key}"
        else
            echo "${LOG_PREFIX} ERRO ao enviar resolução Discord: HTTP ${HTTP_CODE}"
        fi
    done
fi

echo "${LOG_PREFIX} check-pending-reports.sh concluído"
