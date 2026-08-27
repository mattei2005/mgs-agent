---
name: log-monitor-discord-alert
description: "Monitoramento operacional MGS com crons, state files e alertas Discord: transporte direto por bot, anti-spam, resolução, monitores de services/REPORT-INFRA/rate limit/Yoast/uso OAuth, housekeeping seguro, consumo 1Password e validação por fixture/mock antes de produção."
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

- **Quando usar** → `references/route-pack-01.md`
- **Convenção de canal Discord por tipo de alerta → Template do script monitor** → `references/route-pack-02.md`
- **Cron entry → Atualizar infra-inventory.json** → `references/route-pack-03.md`
- **Pitfalls** → `references/route-pack-04.md`
- **SEÇÃO B — Monitor de Restarts de Services Systemd → Fluxo completo esperado** → `references/route-pack-05.md`
- **SEÇÃO D — Hardening de Monitors em Produção (checklist obrigatório) → Exemplo real — monitor-auto-push.sh** → `references/route-pack-06.md`
- **Service Account `op`: rate-limit, migração Business, diagnóstico de consumo e monitor independente do 1Password** → `references/cron-op-rate-limit-mitigation.md`
- **Auditoria completa de consumo 1Password: crons Linux + Hermes de todos os perfis, projeção nominal versus observada e otimização** → `references/1p-full-consumption-audit.md`
- **Yoast eggbev, telemetria GPT-5.6 OAuth, teardown `rc=-6` de oneshots/resolvedores e housekeeping de backups** → `references/yoast-gpt56-housekeeping-2026-07-11.md`
- **Centralização Zeus para Honcho, Google Drive e transporte Discord sem webhook do 1Password** → `references/mgs-runtime-centralization-2026-07-11.md`
- **Filas humanas de aprovação: aging, metadata-only alerts, anti-spam, unknown-state preservation e resumo não bloqueante no REPORT-INFRA** → `references/approval-queue-aging-monitor.md`
- **Auditoria de alertas Discord por janela: embeds completos, agrupamento por incidente, reconciliação com resoluções/live state e anti-spam de guardrail** → `references/discord-alert-history-audit-and-incident-reconciliation.md`
- **Espelhar `Messenger user token invalid` da Smart Bidding com page count, dedupe, outbox e zero mentions** → `references/sb-messenger-token-invalid-monitor.md`

## MGS transport and telemetry invariants

- For monitors posting to a Discord channel already reachable by an authenticated MGS bot, prefer direct Discord API delivery with that bot. Do not add a recurring 1Password lookup merely to retrieve a webhook.
- Keep 1Password only for secrets genuinely required by the monitored operation, not for alert transport when local bot authentication already exists.
- Alert delivery should remain independent of the dependency being monitored when practical; for example, a 1Password rate-limit monitor must alert through Discord bot auth rather than a 1Password-resolved webhook.
- State-file inventory monitors must label only what they actually prove: filesystem-versus-inventory comparison means “item not inventoried,” not “missing REPORT-INFRA.” Require two consecutive missing snapshots before alerting, suppress a candidate that reappears, keep resolution open across failed delivery, close only after HTTP 2xx, and cite an item-specific Git change rather than the latest global inventory commit. Detailed fixture/state pattern: `references/route-pack-06.md`.
- Test direct delivery with an isolated mock HTTP endpoint and token override before sending a real smoke message. Verify authorization, destination, payload schema, state transition, retry after failed HTTP delivery, transient-disappearance suppression, item-specific evidence, and absence of secrets in stdout/stderr.
- Separate fixed, conditional, event-driven, and on-demand credential consumption. Do not present a conditional lookup as a fixed daily cost.
- Report only telemetry emitted by the runtime. If logs expose API-call counts but not token counts, report calls/responses and explicitly omit token or pay-per-token estimates instead of inventing averages.
- For total Hermes usage, prefer profile-local `state.db` (`sessions` + `session_model_usage`) over gateway-only `response ready` logs: the latter omit CLI/oneshot, cron, tool, and subagent activity and can create a false zero. Sum runtime-provided calls/tokens/cache/billing, fail closed on unreadable active-profile databases, and flag sessions whose `first_seen` predates a `last_seen`-based cutoff as boundary-aggregated rather than exact-window telemetry. Detailed query and fixture pattern: `references/yoast-gpt56-housekeeping-2026-07-11.md`.
- For scripted `hermes -z` resolvers, stdout is final-response-only by CLI contract. If a teardown path returns nonzero after producing non-empty final stdout (observed `rc=-6`), preserve and deliver that final response; nonzero with empty stdout remains an error. Test both branches with `CompletedProcess`, then verify the actual Discord reply reference, empty `content`, embed, and zero mentions.
- High-cardinality Discord alerts must be organized at the renderer/source as a compact aligned monospace table: one row per comparable entity, contextual columns, bounded width, and `+N` summaries for omitted rows or IDs. Do not emit long nested bullet lists with repeated CTA/message prose. Validate the renderer with a realistic fixture before the next production cycle; the detailed pattern is in `references/route-pack-03.md`.
- For destructive housekeeping, verify behavior in a temporary fixture first: canonical file preserved, latest backup per family preserved, singleton family preserved, and only eligible older backups removed.

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
