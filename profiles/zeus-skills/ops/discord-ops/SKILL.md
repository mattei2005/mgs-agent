---
name: discord-ops
description: "Operações do ecossistema de agentes MGS (Zeus/Atena): comunicação inter-agente via Discord, diagnóstico e reinicialização de gateway, versionamento de profiles (SOUL.md, skills) via git, roles managed, e hook git post-commit com notificação via webhook. Cobre IDs de canais/bots, DISCORD_ALLOW_BOTS, TTY check, sessão stale, rate limit, Message Content Intent, symlink pitfall e ciclo cron de sync."
tags: [discord, inter-agent, messaging, webhook, hook, git, roles, infra, notification, hermes, agent, restart, versioning, soul, profile, systemd, cron]
related_skills: [log-monitor-discord-alert, wp-plugin-mass-operation, hermes-update]
---


## Progressive disclosure — mandatory

1. Identify the exact branch below before loading details.
2. Load one primary reference first.
3. Load another reference only when the first requires it or live evidence changes the branch.
4. Never load every reference, the full catalog, or broad source ranges “for context.”
5. For repeated lookups, search the exact symbol/path and aggregate results before returning them to model context.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Routing index

- **Referências recentes** → `references/router-01-refer-ncias-recentes.md`
- **Recent operational references** → `references/router-02-recent-operational-references.md`
- **User-facing response hygiene** → `references/router-03-user-facing-response-hygiene.md`
- **Message deletion / repost by channel ID** → `references/router-04-message-deletion-repost-by-channel-id.md`
- **App-rate-limit channel scope (B001–B010)** → `references/router-05-app-rate-limit-channel-scope-b001-b010.md`
- **SEÇÃO A — Comunicação Inter-Agente (Zeus → Atena)** → `references/router-06-se-o-a-comunica-o-inter-agente-zeus-atena.md`
- **SEÇÃO B — Roles Managed (não deletáveis via API)** → `references/router-07-se-o-b-roles-managed-n-o-delet-veis-via-api.md`
- **SEÇÃO C — Hook git post-commit com notificação Discord** → `references/router-08-se-o-c-hook-git-post-commit-com-notifica-o-discord.md`
- **SEÇÃO D — Diagnóstico, Cron Scheduler e Reinicialização de Agente (Gateway Hermes)** → `references/router-09-se-o-d-diagn-stico-cron-scheduler-e-reinicializa-o-de-agente-gat.md`
- **SEÇÃO F — Threads: Ciclo de Vida, Tokens e Leitura de Histórico** → `references/router-10-thread-lifecycle-history.md`
- **SEÇÃO G — Importar histórico de thread antiga por link/ID** → `references/router-11-se-o-g-importar-hist-rico-de-thread-antiga-por-link-id.md`
- **SEÇÃO E — Versionamento e Edição de Profiles (SOUL.md, config.yaml, skills)** → `references/router-12-se-o-e-versionamento-e-edi-o-de-profiles-soul-md-config-yaml-ski.md`
- **SEÇÃO E — Versionamento e Edição de Profiles (SOUL.md, config.yaml, skills)** → `references/router-13-se-o-e-versionamento-e-edi-o-de-profiles-soul-md-config-yaml-ski.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Reduce tool output above roughly 5 KB before any additional broad lookup.
- Preserve exact procedures in topical references; keep this `SKILL.md` as the routing layer.
- Validate the real result before reporting success.
