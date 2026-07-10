---
name: discord-ops
description: "Operações do ecossistema de agentes MGS (Zeus/Atena): comunicação inter-agente via Discord, diagnóstico e reinicialização de gateway, versionamento de profiles (SOUL.md, skills) via git, roles managed, e hook git post-commit com notificação via webhook. Cobre IDs de canais/bots, DISCORD_ALLOW_BOTS, TTY check, sessão stale, rate limit, Message Content Intent, symlink pitfall e ciclo cron de sync."
tags: [discord, inter-agent, messaging, webhook, hook, git, roles, infra, notification, hermes, agent, restart, versioning, soul, profile, systemd, cron]
related_skills: [log-monitor-discord-alert, wp-plugin-mass-operation, hermes-update]
---

# Discord Ops — Comunicação Inter-Agente, Roles e Webhooks

## Progressive disclosure — mandatory

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Operational route packs

- **SEÇÃO A — Comunicação Inter-Agente (Zeus → Atena) → Limpeza pós-loop de regras persistidas** → `references/route-pack-01.md`
- **Pedidos operacionais ao Zeus e permissões de canais → Layout de alertas automáticos via webhook** → `references/route-pack-02.md`
- **Pitfall: não quebrar blocos ```text no meio ao dividir mensagens longas → Quando usar** → `references/route-pack-03.md`
- **Cron-worker architecture / provider pinning → Reinicialização** → `references/route-pack-04.md`
- **Causa raiz difícil: Message Content Intent → Logs úteis** → `references/route-pack-05.md`
- **SEÇÃO F — Threads: Ciclo de Vida, Tokens e Leitura de Histórico → SEÇÃO G — Importar histórico de thread antiga por link/ID** → `references/route-pack-06.md`
- **SEÇÃO E — Versionamento e Edição de Profiles (SOUL.md, config.yaml, skills) → Política de extensão de skills** → `references/route-pack-07.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
