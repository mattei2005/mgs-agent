---
name: log-monitor-discord-alert
description: "Monitoramento MGS com alertas Discord: template genérico de monitor de log (START/OK padrão), monitor de restarts de services systemd (zeus-gateway, atena-gateway, mgs-autocommit), e monitor de skills MGS sem REPORT-INFRA no inventário. Inclui state file JSON, anti-spam, resolução automática, padrão cron, set-a env export para cron, e padrão seguro para crontab. Referências: meta-app-roles-b011-sheet-gid-2026-07-04.md (B011 separado + gid 542936436), shell-env-crontab-patterns.md (set-a, crontab safety), mgs-audit-2026-05-02.md (auditoria 130 arquivos)."
tags: [monitoring, discord, cron, logs, alerting, bash, systemd, restart, infra, inventory, skills, report-infra, env-export, shell]
related_skills: [wp-plugin-mass-operation, discord-ops]
---

# Monitor de Log com Alerta Discord

## Progressive disclosure — mandatory

1. Identify the exact branch below before loading details.
2. Load one primary reference first.
3. Load another reference only when the first requires it or live evidence changes the branch.
4. Never load every reference, the full catalog, or broad source ranges “for context.”
5. For repeated lookups, search the exact symbol/path and aggregate results before returning them to model context.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Routing index

- **Quando usar** → `references/router-01-quando-usar.md`
- **Convenção de canal Discord por tipo de alerta** → `references/router-02-conven-o-de-canal-discord-por-tipo-de-alerta.md`
- **Estrutura do sistema** → `references/router-03-estrutura-do-sistema.md`
- **State file inicial** → `references/router-04-state-file-inicial.md`
- **Template do script monitor** → `references/router-05-template-do-script-monitor.md`
- **Cron entry** → `references/router-06-cron-entry.md`
- **Validação pós-criação** → `references/router-07-valida-o-p-s-cria-o.md`
- **Triage operacional de alertas já disparados** → `references/router-08-triage-operacional-de-alertas-j-disparados.md`
- **Atualizar infra-inventory.json** → `references/router-09-atualizar-infra-inventory-json.md`
- **Pitfalls** → `references/router-10-pitfalls.md`
- **SEÇÃO B — Monitor de Restarts de Services Systemd** → `references/router-11-se-o-b-monitor-de-restarts-de-services-systemd.md`
- **SEÇÃO C — Monitor de Skills MGS sem REPORT-INFRA** → `references/router-12-se-o-c-monitor-de-skills-mgs-sem-report-infra.md`
- **SEÇÃO D — Hardening de Monitors em Produção (checklist obrigatório)** → `references/router-13-se-o-d-hardening-de-monitors-em-produ-o-checklist-obrigat-rio.md`
- **SEÇÃO E — Bug History: Regras Universais para Monitors com State File** → `references/router-14-se-o-e-bug-history-regras-universais-para-monitors-com-state-fil.md`
- **SEÇÃO F — Cron Control Plane e Smoke Tests** → `references/router-15-se-o-f-cron-control-plane-e-smoke-tests.md`
- **Exemplo real — monitor-auto-push.sh** → `references/router-16-exemplo-real-monitor-auto-push-sh.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Reduce tool output above roughly 5 KB before any additional broad lookup.
- Preserve exact procedures in topical references; keep this `SKILL.md` as the routing layer.
- Validate the real result before reporting success.
