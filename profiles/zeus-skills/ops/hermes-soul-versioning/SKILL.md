---
name: hermes-soul-versioning
description: "Versiona SOUL.md dos agentes Hermes (Zeus, Atena, etc) via cópia periódica para mgs-agent, com auto-push para GitHub. Inclui pitfall crítico de symlink que NÃO funciona."
tags: [hermes, soul, versioning, git, cron, backup]
related_skills: [hermes-profile-versioning]
---

# Versionamento de SOUL.md dos Agentes Hermes

## Quando usar
- SOUL.md de algum agente precisa de backup remoto / histórico git
- Novo agente criado e precisa ter SOUL.md rastreado
- Auditoria de mudanças no comportamento/identidade de um agente

## Por que não usar symlink (PITFALL CRÍTICO)

**Symlink NÃO versiona conteúdo.** Git rastreia o symlink como apontador (mode `120000`), não como arquivo:

```bash
git show HEAD:profiles/zeus-soul.md
# → /root/.hermes/profiles/zeus/SOUL.md   (só o path, não o conteúdo)
```

Consequência: mudanças no SOUL.md real nunca aparecem em `git diff`, auto-push nunca dispara para essas mudanças. Testado e confirmado em 2026-04-24.

## Solução: cópia periódica via cron

Script `/root/mgs-agent/scripts/sync-souls.sh` copia SOUL.md de cada agente para `profiles/` no repo apenas quando o source é mais novo que o destino (`-nt`). Auto-commit watcher detecta a mudança e auto-push vai para GitHub em seguida.

## Estrutura em produção

```
/root/mgs-agent/
├── profiles/
│   ├── zeus-soul.md     (cópia real — não symlink)
│   └── atena-soul.md    (cópia real — não symlink)
└── scripts/
    └── sync-souls.sh
```

Cron: `*/5 * * * * /root/mgs-agent/scripts/sync-souls.sh >> /root/mgs-agent/logs/sync-souls.log 2>&1`

## Script sync-souls.sh

```bash
#!/bin/bash
# Sync SOUL.md from Hermes profiles to mgs-agent for versioning
set -e

PROFILES_DIR="/root/.hermes/profiles"
TARGET_DIR="/root/mgs-agent/profiles"
mkdir -p "$TARGET_DIR"

for agent in zeus atena; do
    SOURCE="$PROFILES_DIR/$agent/SOUL.md"
    TARGET="$TARGET_DIR/$agent-soul.md"

    if [ -f "$SOURCE" ] && [ "$SOURCE" -nt "$TARGET" ]; then
        cp "$SOURCE" "$TARGET"
        echo "$(date -Iseconds) synced $agent SOUL"
    fi
done
```

## Adicionar novo agente

1. Adicionar o nome do agente no loop `for agent in zeus atena NOVO_AGENTE`:
   ```bash
   nano /root/mgs-agent/scripts/sync-souls.sh
   ```
2. Rodar manualmente uma vez: `/root/mgs-agent/scripts/sync-souls.sh`
3. Confirmar que `profiles/NOVO_AGENTE-soul.md` foi criado

## Validação do ciclo completo

1. Editar SOUL.md do agente (adicionar linha trivial)
2. Verificar MD5 divergem: `md5sum /root/.hermes/profiles/zeus/SOUL.md /root/mgs-agent/profiles/zeus-soul.md`
3. Aguardar até 5 min para o cron rodar
4. Verificar `cat /root/mgs-agent/logs/sync-souls.log` — deve mostrar "synced X SOUL"
5. Verificar `tail /root/mgs-agent/logs/auto-commit-watcher.log` — deve mostrar commit `auto: profiles/zeus-soul.md`
6. MD5 devem bater novamente
7. Reverter edição trivial e aguardar próximo tick

## Latência

- Cron roda a cada 5 min (`*/5`)
- Auto-commit watcher tem debounce de 10s
- Total máximo: ~5min 10s entre edição e push no GitHub

## Verificar se cron está ativo

```bash
crontab -l | grep sync-souls
```
