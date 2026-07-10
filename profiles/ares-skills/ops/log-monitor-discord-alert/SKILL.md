---
name: log-monitor-discord-alert
description: "Monitoramento MGS com alertas Discord: template genérico de monitor de log (START/OK padrão), monitor de restarts de services systemd (zeus-gateway, atena-gateway, mgs-autocommit), e monitor de skills MGS sem REPORT-INFRA no inventário. Inclui state file JSON, anti-spam, resolução automática, padrão cron, set-a env export para cron, e padrão seguro para crontab. Referências: shell-env-crontab-patterns.md (set-a, crontab safety), mgs-audit-2026-05-02.md (auditoria 130 arquivos)."
tags: [monitoring, discord, cron, logs, alerting, bash, systemd, restart, infra, inventory, skills, report-infra, env-export, shell]
related_skills: [wp-plugin-mass-operation, discord-ops]
---

# Monitor de Log com Alerta Discord

## Progressive disclosure — mandatory

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Operational route packs

- **Quando usar → State file inicial** → `references/route-pack-01.md`
- **Template do script monitor → Validação pós-criação** → `references/route-pack-02.md`
- **Triage operacional de alertas já disparados → Pitfalls** → `references/route-pack-03.md`
- **SEÇÃO B — Monitor de Restarts de Services Systemd → Fluxo completo esperado** → `references/route-pack-04.md`
- **SEÇÃO D — Hardening de Monitors em Produção (checklist obrigatório) → Exemplo real — monitor-auto-push.sh** → `references/route-pack-05.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
