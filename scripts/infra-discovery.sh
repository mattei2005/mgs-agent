#!/bin/bash
# infra-discovery.sh — Regenera /root/mgs-agent/data/infra-inventory.json
# a partir do estado real do sistema.
# Executar sempre que o inventário puder estar desatualizado.
# Output: sobrescreve data/infra-inventory.json com estado atual.

set -euo pipefail

REPO="/root/mgs-agent"
OUT="$REPO/data/infra-inventory.json"
NOW=$(date -Iseconds)

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "=== infra-discovery.sh START ==="

# ── 1. Systemd services ──────────────────────────────────────────────────────
log "Coletando systemd services..."
SERVICES_JSON="[]"
for svc in zeus-gateway atena-gateway mgs-autocommit; do
    STATUS=$(systemctl is-active "${svc}.service" 2>/dev/null || echo "unknown")
    SERVICES_JSON=$(echo "$SERVICES_JSON" | jq \
        --arg name "${svc}.service" \
        --arg status "$STATUS" \
        '. += [{"name": $name, "status": $status}]')
done

# ── 2. Cron jobs (root crontab) ───────────────────────────────────────────────
log "Coletando cron jobs..."
CRONS_JSON="[]"
while IFS= read -r line; do
    [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
    CRONS_JSON=$(echo "$CRONS_JSON" | jq \
        --arg entry "$line" \
        '. += [{"entry": $entry}]')
done < <(crontab -l 2>/dev/null || true)

# ── 3. Scripts em /root/mgs-agent/scripts/ (top-level, excluindo node_modules) ─
log "Coletando scripts..."
SCRIPTS_JSON="[]"
while IFS= read -r fpath; do
    SIZE=$(stat -c%s "$fpath" 2>/dev/null || echo 0)
    MTIME=$(stat -c%Y "$fpath" 2>/dev/null || echo 0)
    MDATE=$(date -d "@$MTIME" -Iseconds 2>/dev/null || echo "unknown")
    SCRIPTS_JSON=$(echo "$SCRIPTS_JSON" | jq \
        --arg path "$fpath" \
        --argjson size "$SIZE" \
        --arg mtime "$MDATE" \
        '. += [{"path": $path, "size_bytes": $size, "modified_at": $mtime}]')
done < <(find "$REPO/scripts" -maxdepth 2 -type f \( -name "*.sh" -o -name "*.php" -o -name "*.js" \) ! -path "*/node_modules/*" | sort)

# ── 4. Skills MGS ────────────────────────────────────────────────────────────
log "Coletando skills..."
SKILLS_JSON="[]"
for profile_dir in /root/.hermes/profiles/*/skills; do
    agent=$(basename "$(dirname "$profile_dir")")
    while IFS= read -r skill_md; do
        skill_path=$(dirname "$skill_md")
        skill_name=$(basename "$skill_path")
        category=$(basename "$(dirname "$skill_path")")
        SKILLS_JSON=$(echo "$SKILLS_JSON" | jq \
            --arg agent "$agent" \
            --arg name "$skill_name" \
            --arg category "$category" \
            --arg path "$skill_md" \
            '. += [{"agent": $agent, "name": $name, "category": $category, "skill_md": $path}]')
    done < <(find "$profile_dir" -name "SKILL.md" 2>/dev/null | sort)
done

# ── 5. Data files relevantes ─────────────────────────────────────────────────
log "Coletando data files..."
DATA_JSON="[]"
for fpath in "$REPO/data"/*.json "$REPO/profiles"/*.md; do
    [[ -f "$fpath" ]] || continue
    SIZE=$(stat -c%s "$fpath" 2>/dev/null || echo 0)
    MD5=$(md5sum "$fpath" 2>/dev/null | awk '{print $1}' || echo "unknown")
    MTIME=$(stat -c%Y "$fpath" 2>/dev/null || echo 0)
    MDATE=$(date -d "@$MTIME" -Iseconds 2>/dev/null || echo "unknown")
    DATA_JSON=$(echo "$DATA_JSON" | jq \
        --arg path "$fpath" \
        --argjson size "$SIZE" \
        --arg md5 "$MD5" \
        --arg mtime "$MDATE" \
        '. += [{"path": $path, "size_bytes": $size, "md5": $md5, "modified_at": $mtime}]')
done

# ── 6. Mu-plugin deploy status ────────────────────────────────────────────────
log "Verificando mu-plugin canônico..."
MU_PATH="$REPO/scripts/mu-plugins/yoast-rest-meta.php"
if [[ -f "$MU_PATH" ]]; then
    MU_MD5=$(md5sum "$MU_PATH" | awk '{print $1}')
    MU_LINES=$(wc -l < "$MU_PATH")
else
    MU_MD5="FILE_NOT_FOUND"
    MU_LINES=0
fi

# ── 7. Montar JSON final ──────────────────────────────────────────────────────
log "Montando JSON final..."
jq -n \
    --arg updated_at "$NOW" \
    --arg mu_md5 "$MU_MD5" \
    --argjson mu_lines "$MU_LINES" \
    --argjson services "$SERVICES_JSON" \
    --argjson crons "$CRONS_JSON" \
    --argjson scripts "$SCRIPTS_JSON" \
    --argjson skills "$SKILLS_JSON" \
    --argjson data_files "$DATA_JSON" \
    '{
        "_meta": {
            "description": "Inventário de infraestrutura compartilhada MGS. Gerado por infra-discovery.sh.",
            "updated_at": $updated_at,
            "generated_by": "infra-discovery.sh"
        },
        "systemd_services": $services,
        "crons": $crons,
        "scripts": $scripts,
        "skills": $skills,
        "data_files": $data_files,
        "mu_plugin_canonical": {
            "path": "scripts/mu-plugins/yoast-rest-meta.php",
            "md5": $mu_md5,
            "lines": $mu_lines
        }
    }' > "$OUT"

log "Inventário salvo em $OUT"
log "Serviços: $(echo "$SERVICES_JSON" | jq 'length') | Crons: $(echo "$CRONS_JSON" | jq 'length') | Scripts: $(echo "$SCRIPTS_JSON" | jq 'length') | Skills: $(echo "$SKILLS_JSON" | jq 'length')"
log "=== infra-discovery.sh DONE ==="
