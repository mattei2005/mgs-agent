---
name: hermes-agent-ops
description: "Operações de manutenção dos agentes Hermes (Zeus, Atena): diagnóstico e reinicialização de gateway, versionamento de profiles (SOUL.md, config.yaml, skills) via git. Cobre sessão Discord stale, rate limit, Message Content Intent, symlink pitfall, e ciclo cron de sync."
tags: [hermes, agent, restart, versioning, soul, profile, git, cron, systemd]
related_skills: [inter-agent-messaging, discord-ops]
---

# Hermes Agent Ops — Restart, Diagnóstico e Versionamento

## SEÇÃO A — Diagnóstico e Reinicialização de Agente

### Quando usar
- Agente está online (processo rodando) mas não responde no Discord
- Mensagens não aparecem como `inbound message` no log
- Agente travou em loop de rate limit
- Usuário relata silêncio após período de alta atividade

### Sintomas típicos

| Sintoma | Causa provável |
|---------|---------------|
| Processo rodando, Discord conectado, mas sem `inbound message` | Sessão stale OU Message Content Intent desabilitada |
| Múltiplos `Retrying request` (waits 21s, 45s, 56s) | Rate limit Anthropic |
| Gateway reiniciou mas parou de receber após reconexão | Sessão zumbi pós-restart |

### Diagnóstico

```bash
# 1. Verificar processo
ps aux | grep -E "hermes.*atena|hermes.*zeus" | grep -v grep

# 2. Últimas linhas do log
tail -30 /root/.hermes/profiles/atena/logs/agent.log

# 3. Checar chegada de mensagens
grep "inbound message" /root/.hermes/profiles/atena/logs/agent.log | tail -5

# 4. Loop de rate limit?
grep -E "Retry|inbound|response ready|ERROR" /root/.hermes/profiles/atena/logs/agent.log | tail -20
```

**Sessão stale confirmada quando:** processo vivo, log mostra `Connected as Atena#2956`, mas nenhum `inbound message` novo após mensagens enviadas.

### Reinicialização

```bash
pkill -f "hermes -p atena gateway run"
sleep 2 && ps aux | grep "atena" | grep -v grep   # confirmar morte
# Reiniciar com terminal(background=true)
sleep 5 && tail -10 /root/.hermes/profiles/atena/logs/agent.log
```

Confirmar sucesso: `Connected as Atena#2956` + `✓ discord connected` + `Gateway running with 1 platform(s)`

### Causa raiz difícil: Message Content Intent

Se após reinicialização o agente **continua sem receber**: verificar no Discord Developer Portal:
1. https://discord.com/developers/applications → aplicação do bot
2. Aba **Bot** → **Privileged Gateway Intents** → confirmar **Message Content Intent** habilitada

### Patch local `busy_input_mode` em gateway

Patch em `/root/.hermes/hermes-agent/gateway/run.py` que faz `busy_input_mode: queue` funcionar em gateway mode. Quando o Hermes for atualizado:
1. Verificar: `grep "PATCH (MGS Digital Corp)" /root/.hermes/hermes-agent/gateway/run.py`
2. Se não estiver: `patch -p1 < /root/mgs-agent/patches/hermes/busy_input_mode_queue_gateway.patch`
3. Restart: `systemctl restart zeus-gateway atena-gateway`

Issue upstream: https://github.com/NousResearch/hermes-agent/issues/14905

### Pitfalls (restart)

- **Não usar `nohup/disown/&`** em terminal foreground — usar `terminal(background=true)`
- **Sessão zumbi é silenciosa** — Discord mostra online mas sem eventos; detectável só pelo log
- **`pkill` pelo padrão exato** — `pkill -f "hermes -p atena gateway run"` para não matar outros perfis
- **`config.yaml` sobrescreve `.env` para `allowed_channels`** — se `discord.allowed_channels` estiver vazio, agente ignora TODAS as mensagens. Fix: `allowed_channels: '1496267571543019653'` no `config.yaml`
- **Mensagens de bots ignoradas por padrão** — `DISCORD_ALLOW_BOTS=mentions` no `.env` do agente destino; com `mentions`, incluir `<@BOT_ID>` no texto
- **Profile `.env` real está em `/root/.hermes/profiles/{agent}/.env`** — nunca `/root/.hermes/.env` (é template)
- **Instância em terminal interativo (`pts/N`)** — output vai para aquele terminal, não para agent.log; detectar via coluna TTY no `ps aux`
- **Múltiplas instâncias conflitam** — verificar PID file antes de reiniciar; `Another gateway instance is already running`

### Logs úteis

```
/root/.hermes/profiles/atena/logs/agent.log   # Atividade principal
/root/.hermes/profiles/atena/logs/errors.log  # Erros e warnings
/root/mgs-agent/logs/generate-rec.log          # Log do pipeline REC
/root/mgs-agent/logs/events-audit.jsonl        # Audit trail de eventos
```

---

## SEÇÃO B — Versionamento de Profiles (SOUL.md, config.yaml, skills)

### Quando usar
- SOUL.md de algum agente precisa de backup remoto / histórico git
- Novo agente criado e precisa ter SOUL.md rastreado
- Skills MGS-específicas precisam ser versionadas no repo

### ⚠️ PITFALL CRÍTICO: Symlink NÃO versiona conteúdo

```bash
ln -s /root/.hermes/profiles/zeus/SOUL.md /root/mgs-agent/profiles/zeus-soul.md
git add profiles/zeus-soul.md
# git armazena O APONTADOR (mode 120000), não o conteúdo
git show HEAD:profiles/zeus-soul.md → /root/.hermes/profiles/zeus/SOUL.md
```

Mudanças no SOUL.md real **não aparecem em `git diff`**, não disparam auto-push. Testado e confirmado em 2026-04-24.

### Solução implantada em produção — cópia periódica via cron

Script `/root/mgs-agent/scripts/sync-souls.sh` sincroniza SOUL.md + skills MGS-específicas:

```bash
#!/bin/bash
set -e

PROFILES_DIR="/root/.hermes/profiles"
TARGET_DIR="/root/mgs-agent/profiles"
mkdir -p "$TARGET_DIR"

# SOUL.md sync (mtime check)
for agent in zeus atena; do
    SOURCE="$PROFILES_DIR/$agent/SOUL.md"
    TARGET="$TARGET_DIR/$agent-soul.md"
    if [ -f "$SOURCE" ] && [ "$SOURCE" -nt "$TARGET" ]; then
        cp "$SOURCE" "$TARGET"
        echo "$(date -Iseconds) synced $agent SOUL"
    fi
done

# Skills MGS-específicas sync (rsync com --delete)
mkdir -p "$TARGET_DIR/zeus-skills"
rsync -a --delete \
    "$PROFILES_DIR/zeus/skills/ops/" \
    "$TARGET_DIR/zeus-skills/ops/" \
    && echo "$(date -Iseconds) synced zeus skills/ops"

for category in wordpress devops; do
    if [ -d "$PROFILES_DIR/atena/skills/$category" ]; then
        rsync -a --delete \
            "$PROFILES_DIR/atena/skills/$category/" \
            "$TARGET_DIR/atena-skills/$category/" \
            && echo "$(date -Iseconds) synced atena skills/$category"
    fi
done
```

**Crontab:** `*/5 * * * * /root/mgs-agent/scripts/sync-souls.sh >> /root/mgs-agent/logs/sync-souls.log 2>&1`

**Destinos no git:**
- `profiles/zeus-soul.md` / `profiles/atena-soul.md` — SOUL.md dos agentes
- `profiles/zeus-skills/ops/` — skills operacionais MGS do Zeus
- `profiles/atena-skills/wordpress/` e `atena-skills/devops/` — skills MGS da Atena

**Por que rsync para skills (não `-nt`):** SOUL.md é 1 arquivo — mtime é suficiente. Skills são árvores de diretórios — `rsync -a --delete` detecta adições, modificações e deleções. O `--delete` propaga remoções.

### Diagnóstico rápido: symlink vs arquivo real no git

```bash
# mode 120000 = symlink (errado), 100644 = arquivo real (correto)
git ls-files -s profiles/

# Ver o que git armazenou como conteúdo
git show HEAD:profiles/zeus-soul.md

# Teste definitivo
echo "x" >> /root/.hermes/profiles/zeus/SOUL.md
git -C /root/mgs-agent diff  # vazio se symlink, diff real se arquivo
```

### Adicionar novo agente ao sync

1. Adicionar no loop `for agent in zeus atena NOVO_AGENTE`
2. Adicionar bloco rsync para categorias de skills do novo agente
3. Rodar manualmente uma vez para criar o arquivo inicial
4. Confirmar cron: `crontab -l | grep sync-souls`

### Política de extensão de skills

Se nova skill MGS-específica for criada em categoria não coberta (ex: `zeus/skills/data-science/`), adicionar ao bloco rsync do script E reportar via `[REPORT-INFRA]`. Skill fora do sync = não versionada = sem rastreabilidade.
