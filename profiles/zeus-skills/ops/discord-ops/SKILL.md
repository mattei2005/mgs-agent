---
name: discord-ops
description: "Operações do ecossistema de agentes MGS (Zeus/Atena): comunicação inter-agente via Discord, diagnóstico e reinicialização de gateway, versionamento de profiles (SOUL.md, skills) via git, roles managed, e hook git post-commit com notificação via webhook. Cobre IDs de canais/bots, DISCORD_ALLOW_BOTS, TTY check, sessão stale, rate limit, Message Content Intent, symlink pitfall e ciclo cron de sync."
tags: [discord, inter-agent, messaging, webhook, hook, git, roles, infra, notification, hermes, agent, restart, versioning, soul, profile, systemd, cron]
related_skills: [log-monitor-discord-alert, wp-plugin-mass-operation, hermes-update]
---


## Progressive disclosure — mandatory

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Operational route packs

- **Referências recentes → Escopo por agente/thread antes de reportar pendências** → `references/route-pack-01.md`
- **Mentions cross-agent em canal de outro agente → Challenges por IP de datacenter em fluxos Ares** → `references/route-pack-02.md`
  - Cutover de política em sessão nova, sem produção, com readback de `state.db` → `references/cross-agent-session-policy-cutover.md`
- **Recuperar e consolidar continuidade de thread grande → Novo agente Discord/Hermes — bootstrap de bot, token e service** → `references/route-pack-03.md`
- **Enviar arquivos grandes/anexos no Discord → Formato REPORT-INFRA (Atena/Ares → Zeus)** → `references/route-pack-04.md`
- **Excluir alertas/mensagens em lote com HTTP 429** → `references/discord-batch-message-deletion-rate-limits.md`
- **Processamento Zeus de REPORT-INFRA** → `references/route-pack-05.md`
- **Processamento Zeus de REPORT-INFRA com cron Hermes de outro profile → Alternativa Operacional** → `references/route-pack-06.md`
- **SEÇÃO C — Hook git post-commit com notificação Discord → Política MGS de tool progress no Discord** → `references/route-pack-07.md`
- **Gateway routing/restart incident reference → Channel permission overwrites and narrow delegation** → `references/route-pack-08.md`
- **Adding a user to a private Discord thread → Separar canais privados/diretoria e canais de equipe → Usuário autorizado silencioso por drift entre registry/config/.env → Diagnóstico de título ruim em auto-thread** → `references/route-pack-09.md`
- **Regra MGS: renomear thread nova uma vez; nunca renomear thread já aberta → Pitfall crítico: função segura pode estar sobrescrita por duplicata posterior** → `references/route-pack-10.md`
- **Correção preferida: título IA uma vez após a primeira resposta → Patch local `busy_input_mode` em gateway** → `references/route-pack-11.md`
- **Pitfalls (restart) → Aviso antes de thread ficar oculta por auto-archive** → `references/route-pack-12.md`
- **Threads antigas continuam abertas na sidebar de usuários adicionados → SEÇÃO E — Versionamento e Edição de Profiles (SOUL.md, config.yaml, skills)** → `references/route-pack-13.md`
- **Quando usar → Solução implantada em produção — cópia periódica via cron** → `references/route-pack-14.md`
- **Diagnóstico rápido: symlink vs arquivo real no git → Política de extensão de skills** → `references/route-pack-15.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
