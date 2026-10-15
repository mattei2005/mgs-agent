---
name: discord-ops
description: "Operações do ecossistema de agentes MGS (Zeus/Atena): comunicação inter-agente via Discord, diagnóstico e reinicialização de gateway, versionamento de profiles (SOUL.md, skills) via git, roles managed, e hook git post-commit com notificação via webhook. Cobre IDs de canais/bots, DISCORD_ALLOW_BOTS, TTY check, sessão stale, rate limit, Message Content Intent, symlink pitfall e ciclo cron de sync."
tags: [discord, inter-agent, messaging, webhook, hook, git, roles, infra, notification, hermes, agent, restart, versioning, soul, profile, systemd, cron]
related_skills: [log-monitor-discord-alert, wp-plugin-mass-operation, hermes-update]
---

# Discord Ops — Comunicação Inter-Agente, Roles e Webhooks

## Regras de execução e fechamento

- Antes de uma limpeza de mensagens, separar mensagens próprias das de outros autores e conferir as permissões efetivas na thread e no canal pai; conseguir apagar mensagens próprias não comprova `MANAGE_MESSAGES` para as demais. Preservar canais/threads e inventariar os IDs exatos antes de excluir.
- Tratar autorização de limpeza e autorização de alterar permissões como escopos distintos. Se faltar capacidade, registrar o restante e encaminhar a um administrador autorizado pela rota operacional, sem usar a credencial dele nem conceder acesso permanente como atalho. Procedimento em `references/route-pack-02.md`.
- Conferir handoffs por GET, incluindo a mention efetiva do destinatário. Distinguir pedido entregue, trabalho aceito e resultado validado; só este último encerra a pendência. Não transformar REPORT-INFRA em fila de execução nem chamar um handoff confirmado de tarefa concluída.

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
