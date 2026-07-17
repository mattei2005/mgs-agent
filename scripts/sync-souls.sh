#!/bin/bash
# Sync SOUL.md + MGS-specific skills from Hermes profiles to mgs-agent for versioning
# Runs every 5 min via crontab: */5 * * * * /root/mgs-agent/scripts/sync-souls.sh
set -euo pipefail

PROFILES_DIR="/root/.hermes/profiles"
TARGET_DIR="/root/mgs-agent/profiles"
mkdir -p "$TARGET_DIR"

# ── SOUL.md sync ───────────────────────────────────────────────────────────
for agent in zeus atena ares; do
    SOURCE="$PROFILES_DIR/$agent/SOUL.md"
    TARGET="$TARGET_DIR/$agent-soul.md"
    if [ -f "$SOURCE" ] && [ "$SOURCE" -nt "$TARGET" ]; then
        cp "$SOURCE" "$TARGET"
        echo "$(date -Iseconds) synced $agent SOUL"
    fi
done

# ── Config.yaml sync (Zeus + Atena + Ares) ─────────────────────────────────
# Adicionado 2026-04-27 (Item 23) — sincroniza configs do Hermes
# Mantem permissao 600 no destino
for agent in zeus atena ares; do
    SOURCE="$PROFILES_DIR/$agent/config.yaml"
    TARGET="$TARGET_DIR/$agent-config.yaml"
    if [ -f "$SOURCE" ] && { [ ! -f "$TARGET" ] || [ "$SOURCE" -nt "$TARGET" ]; }; then
        cp "$SOURCE" "$TARGET"
        chmod 600 "$TARGET"
        echo "$(date -Iseconds) synced $agent config"
    fi
done

# ── Skills MGS-específicas sync ────────────────────────────────────────────
# Zeus: ops/ (skills de infra e deploy MGS)
mkdir -p "$TARGET_DIR/zeus-skills"
rsync -a --delete \
    "$PROFILES_DIR/zeus/skills/ops/" \
    "$TARGET_DIR/zeus-skills/ops/" \
    && echo "$(date -Iseconds) synced zeus skills/ops"

# Zeus: growth/ MGS específicas usadas por governança/monitoramento.
# Não sincronizar a categoria growth inteira; preservar apenas as skills customizadas
# refatoradas e validadas nesta operação.
mkdir -p "$TARGET_DIR/zeus-skills/growth"
for skill in meta-utility-template-approval meta-app-rate-limit-monitor segurador-page-health-monitor meta-ads-api-operations; do
    if [ -d "$PROFILES_DIR/zeus/skills/growth/$skill" ]; then
        rsync -a --delete \
            "$PROFILES_DIR/zeus/skills/growth/$skill/" \
            "$TARGET_DIR/zeus-skills/growth/$skill/" \
            && echo "$(date -Iseconds) synced zeus skills/growth/$skill"
    fi
done

# Zeus: canonical productivity workspace router with MGS Google fail-closed adapters.
if [ -d "$PROFILES_DIR/zeus/skills/productivity/productivity-workspace-apis" ]; then
    mkdir -p "$TARGET_DIR/zeus-skills/productivity"
    rsync -a --delete \
        "$PROFILES_DIR/zeus/skills/productivity/productivity-workspace-apis/" \
        "$TARGET_DIR/zeus-skills/productivity/productivity-workspace-apis/" \
        && echo "$(date -Iseconds) synced zeus skills/productivity/productivity-workspace-apis"
fi

# Atena: wordpress/ + devops/ (skills WP e deploy MGS-específicas)
mkdir -p "$TARGET_DIR/atena-skills"
for category in wordpress devops; do
    if [ -d "$PROFILES_DIR/atena/skills/$category" ]; then
        rsync -a --delete \
            "$PROFILES_DIR/atena/skills/$category/" \
            "$TARGET_DIR/atena-skills/$category/" \
            && echo "$(date -Iseconds) synced atena skills/$category"
    fi
done

# Atena: OpenHands skill customizada por política MGS de custo/provider.
# Não sincronizar a categoria inteira autonomous-ai-agents para evitar vendor skills enormes.
if [ -d "$PROFILES_DIR/atena/skills/autonomous-ai-agents/openhands" ]; then
    mkdir -p "$TARGET_DIR/atena-skills/autonomous-ai-agents"
    rsync -a --delete \
        "$PROFILES_DIR/atena/skills/autonomous-ai-agents/openhands/" \
        "$TARGET_DIR/atena-skills/autonomous-ai-agents/openhands/" \
        && echo "$(date -Iseconds) synced atena skills/autonomous-ai-agents/openhands"
fi

# Ares: growth/ (skills de aquisição paga, criativos e operações ads MGS)
mkdir -p "$TARGET_DIR/ares-skills"
if [ -d "$PROFILES_DIR/ares/skills/growth" ]; then
    rsync -a --delete \
        "$PROFILES_DIR/ares/skills/growth/" \
        "$TARGET_DIR/ares-skills/growth/" \
        && echo "$(date -Iseconds) synced ares skills/growth"
fi

# Canonical Google Workspace route for Atena and Ares.
# These profile-local skills replace the generic personal-auth flow with the
# mgs-core-prod Service Account contract and fail-closed compatibility scripts.
for agent in atena ares; do
    if [ -d "$PROFILES_DIR/$agent/skills/productivity/google-workspace" ]; then
        mkdir -p "$TARGET_DIR/$agent-skills/productivity"
        rsync -a --delete \
            "$PROFILES_DIR/$agent/skills/productivity/google-workspace/" \
            "$TARGET_DIR/$agent-skills/productivity/google-workspace/" \
            && echo "$(date -Iseconds) synced $agent skills/productivity/google-workspace"
    fi
done

# Ares: skills ops MGS compartilhadas, sincronizadas seletivamente.
# Não sincronizar a categoria ops inteira: preservar apenas as skills operacionais
# que foram auditadas/refatoradas e precisam de mirror versionado.
for agent in ares; do
    mkdir -p "$TARGET_DIR/$agent-skills/ops"
    skills=(discord-ops log-monitor-discord-alert)
    for skill in "${skills[@]}"; do
        if [ -d "$PROFILES_DIR/$agent/skills/ops/$skill" ]; then
            rsync -a --delete \
                "$PROFILES_DIR/$agent/skills/ops/$skill/" \
                "$TARGET_DIR/$agent-skills/ops/$skill/" \
                && echo "$(date -Iseconds) synced $agent skills/ops/$skill"
        fi
    done
done
