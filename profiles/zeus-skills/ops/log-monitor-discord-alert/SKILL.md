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

- **Hostinger provider metrics versus local health/DR/cron signals, performance and native read-only trust gate** → skill `hostinger-vps-operations`, then its **Process routing and performance** route. Keep the local 5-minute health monitor and deterministic business/DR jobs; provider `running`/historical metrics are supplementary predicates, not replacements. Do not add repeated standalone MCP/1Password bootstraps, new jobs or altered cadence merely to adopt MCP; migrations require equivalent-predicate/failure/credential validation within an authorized scope.
- **Fila comum PC1/timeout, consumidor durável, gates e recibos de retomada** → `references/common-automation-continuity.md`
- **Quando usar** → `references/route-pack-01.md`
- **Convenção de canal Discord por tipo de alerta → Template do script monitor** → `references/route-pack-02.md`
- **Cron entry → Atualizar infra-inventory.json** → `references/route-pack-03.md`
- **Alocação global de minuto, baselines densas e prevenção de colisão entre agentes/schedulers** → `/root/mgs-agent/context/cron-scheduling-policy.md`
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

- **DR SLA: origem correta, dedupe, recuperação e readback sem repost** → `references/stateful-dr-sla-alerts.md`
- **RunCloud: coleta, orçamento de API, cooldown, cadência e avaliação SSH/API híbrida** → `references/runcloud-initial-monitoring.md`
- **SHEIN D-1 e cinco rodadas intraday: estado/nonce por slot, lock compartilhado, UI Today e validação sem publicação antecipada** → `references/shein-daily-and-intraday-reports.md`
- **SMS Funnel: saldo monetário, billing por canal e conferência independente API × dashboard autenticada** → `references/sms-funnel-wallet-readback.md`

## MGS transport and telemetry invariants

- Before buying API capacity or reducing monitoring frequency, map each monitored predicate to its authoritative source and budget the complete collection workload. Prefer approved direct guest reads for host-local facts when they preserve the required evidence; retain provider reads for control-plane facts that local files cannot prove. A transport change must preserve unknown-state handling, alert semantics and the approved coverage.
- Prove integration at the consumer, not at credential storage: an SSH key in 1Password or a successful interactive SSH login does not migrate an API-based monitor. Verify the runner's actual transport and exercise its exact deployed command before describing the new path as active.
- For monitors posting to a Discord channel already reachable by an authenticated MGS bot, prefer direct Discord API delivery with that bot. Do not add a recurring 1Password lookup merely to retrieve a webhook.
- Keep 1Password only for secrets genuinely required by the monitored operation, not for alert transport when local bot authentication already exists.
- Alert delivery should remain independent of the dependency being monitored when practical; for example, a 1Password rate-limit monitor must alert through Discord bot auth rather than a 1Password-resolved webhook.
- State-file inventory monitors must label only what they actually prove: filesystem-versus-inventory comparison means “item not inventoried,” not “missing REPORT-INFRA.” Require two consecutive missing snapshots before alerting, suppress a candidate that reappears, keep resolution open across failed delivery, close only after HTTP 2xx, and cite an item-specific Git change rather than the latest global inventory commit. Detailed fixture/state pattern: `references/route-pack-06.md`.
- When a source monitor changes an embed title, classification, or field contract, update every downstream consumer in the same change—primary explainer, independent completeness watchdog, fallback renderer and tests. Do not depend on one exact legacy title: accept the versioned known-title set plus a constrained `Hermes Agent —`/field contract. Preserve source→reply for a single fresh alert. When repairing multiple historical orphans after a catch-up request, publish one consolidated summary by default instead of flooding one reply per source; preserve exact source IDs and deleted/replacement message IDs in state/audit, then read back one replacement and zero old messages.
- Test direct delivery with an isolated mock HTTP endpoint and token override before sending a real smoke message. Verify authorization, destination, payload schema, state transition, retry after failed HTTP delivery, transient-disappearance suppression, item-specific evidence, and absence of secrets in stdout/stderr.
- For SMS Funnel balance questions, distinguish the monetary wallet shown as `SALDO GERAL DA CONTA` / `Saldo único para todos os produtos` from `/api/user-credits-info.credits`. A zero in that credits field does not prove an empty wallet; reconcile against the current wallet/dashboard source before reporting zero balance or requesting a recharge. If API and dashboard differ, report the exact source and unit for each; do not infer that contracted-minus-sent is usable wallet balance. A dashboard screenshot proves its displayed value, not a fresh live API read. Existing credits-based monitoring is not validated as monetary-wallet monitoring until its source is reconciled. For a live read, use the canonical helper's internal login/1Password flow, then authenticated GET `/api/wallet/balance` and GET `/api/wallet/billing` on `https://web2.smsfunnel.com.br`. These are the current dashboard WalletService routes, discoverable in the public JS at `https://app2.smsfunnel.com.br/` (the old web2 HTML root redirects there). Validate `currency == BRL`; `available_micros`, `balance_micros` and `held_micros` are integer millionths of BRL: divide by 1,000,000 using Decimal. Billing values `sms: wallet` and equivalent channels prove which channels use the monetary wallet; a zero legacy `credits` is not an empty wallet for those channels. Never print login responses, tokens or credentials. Distinguish a verified API wallet read from an authenticated browser read, and do not imply a skill update deployed the monitor fix.
- For SMS Funnel three-day sends/spend reports, use the last three completed calendar days, excluding the current partial bucket from `/api/daily-sents`. Reconcile that sum with `/api/analytics/funnel-performance` and its live `sms_unit_cost`/`total_cost`. The analytics date bounds are timestamp-inclusive: date-only end values mean midnight, same-date start/end returns zero, and next-day midnight can double-count a boundary send in adjacent daily queries. Query explicit `00:00:00` through `23:59:59` for each complete day or aggregate window; never assume a next-date end is exclusive. Credentials stay inside the canonical SMS helper/1Password flow and never appear in output.
- Separate fixed, conditional, event-driven, and on-demand credential consumption. Do not present a conditional lookup as a fixed daily cost.
- Report only telemetry emitted by the runtime. If logs expose API-call counts but not token counts, report calls/responses and explicitly omit token or pay-per-token estimates instead of inventing averages.
- For total Hermes usage, prefer profile-local `state.db` (`sessions` + `session_model_usage`) over gateway-only `response ready` logs: the latter omit CLI/oneshot, cron, tool, and subagent activity and can create a false zero. Sum runtime-provided calls/tokens/cache/billing, fail closed on unreadable active-profile databases, and flag sessions whose `first_seen` predates a `last_seen`-based cutoff as boundary-aggregated rather than exact-window telemetry. Detailed query and fixture pattern: `references/yoast-gpt56-housekeeping-2026-07-11.md`.
- For scripted `hermes -z` resolvers, stdout is final-response-only by CLI contract. If a teardown path returns nonzero after producing non-empty final stdout (observed `rc=-6`), preserve and deliver that final response; nonzero with empty stdout remains an error. Test both branches with `CompletedProcess`, then verify the actual Discord reply reference, empty `content`, embed, and zero mentions.
- High-cardinality Discord alerts must be organized at the renderer/source as a compact aligned monospace table: one row per comparable entity, contextual columns, bounded width, and `+N` summaries for omitted rows or IDs. Do not emit long nested bullet lists with repeated CTA/message prose. Validate the renderer with a realistic fixture before the next production cycle; the detailed pattern is in `references/route-pack-03.md`.
- For large MGS isolated DR drills, end the temporary ciphertext/container lifecycle before profile expansion and validate profiles in sequential temporary sandboxes. Budget archive-header expanded sizes, the largest SQLite staging copy and a reserve before each stage; preserve all hash/CRC, SQLite, knowledge and finance checks. A larger terminal timeout does not override the transport's real window: use a silent tracked process when prior runtime exceeds that window, and resume interrupted drills only through the canonical verified-input procedure in `vps-maintenance-and-backup-governance`. Preserve interrupted evidence until exact-target cleanup confirmation; do not call the recurrence recovered if that residue leaves the next drill without headroom.
- For destructive housekeeping, verify behavior in a temporary fixture first: canonical file preserved, latest backup per family preserved, singleton family preserved, and only eligible older backups removed.

## Cancelamento de uma entrega pendente

- Tratar a dispensa explícita de uma entrega como decisão sobre aquela execução, não como pausa do cron. Resolver o relatório e seu período/slot pelo pedido imediatamente anterior; preservar recorrência, rodadas atuais e outras recuperações. A obrigação de retry não autoriza insistir após cancelamento humano válido.
- Registrar a decisão no pedido durável e no checkpoint, impedir replay da entrega dispensada e conferir o estado efetivo antes de confirmar. Não marcar como entregue ou recuperado; não pedir outra vez a mesma autorização. Distinguir bloqueio preventivo aplicado de cancelamento terminal reconciliado com todos os consumidores.
- Responder em poucas linhas: qual entrega não será enviada e o que permaneceu inalterado. Manter a descoberta restrita ao pedido e seus consumidores, sem transformar uma dispensa pontual em auditoria geral. Receita e cuidados de concorrência: `references/common-automation-continuity.md`, seção **Owner cancellation of one historical delivery**.

## Retentativas adiadas de operações

- Aplicar `context/automation-recovery-policy.md`, decisão Rodolfo `1569191908020981801`: qualquer função autorizada de cron que encontre PC1 ocupado entra em espera/fila persistente com dedupe, executor, checkpoint e retomada verificável. Timeout exige intervalo/backoff e repetição segura da etapa faltante, sem depender de nova lembrança humana. Não fechar o pedido por ocupação, timeout, alerta ou limite de tentativas; preservar pendência e escalar o bloqueio exato. Anti-loop, autenticação, efeito ambíguo e Critical Subset continuam protegidos. Registro sem consumidor/agendamento não comprova fila executável nem retry automático universal.

- Quando Rodolfo pedir para esperar um intervalo e tentar de novo, agendar **uma execução real e única da operação**, não apenas um lembrete; preservar a recorrência existente, o escopo aprovado e o checkpoint. Retomar somente as etapas faltantes após reconciliar efeitos já publicados.
- Classificar colisões por finalidade e recurso, não apenas por frequência: um intake de criativos ou outro trabalho de negócio continua operacional mesmo executando a cada poucos minutos. A exceção de baseline densa vale somente para infraestrutura identificada; frequência alta, sozinha, não libera o minuto.
- Antes de confirmar o horário, validar o instante efetivamente persistido e auditar esse minuto novamente; o tempo gasto no preflight pode deslocar uma agenda relativa. Se for preciso mudar de slot, atualizar o mesmo job e comunicar o horário ajustado, sem criar uma segunda tentativa.
- Separar agendamento validado de recuperação concluída: confirmar brevemente a hora e a entrega na origem; só declarar a operação recuperada depois da execução e do readback do alvo. Ver receita em `references/route-pack-03.md`, seção **Native Hermes one-shot readback**.

## Recuperação de cron após falha transitória

- Antes de refazer login ou editar um script, reexecute uma leitura segura pelo consumidor exato, com o interpreter, wrapper e locks do cron; a sessão pode ter se recuperado e um probe genérico não comprova o fluxo afetado. Respeite gates de autenticação/2FA e não transforme essa leitura em tentativas repetidas de login.
- Separe três aceites: leitura recuperada, operação autorizada concluída com readback e alerta reconciliado pelo watchdog. Um dry-run bem-sucedido não certifica a escrita/entrega nem encerra sozinho o incidente.
- Na resposta, use **Problema / Causa / Recuperação**, distinguindo a falha observada do mecanismo não comprovado. Não apresente retry bem-sucedido como prevenção permanente de recorrência. Receita e exemplo SB em `references/route-pack-03.md`, seção **Recuperação pelo consumidor exato**.

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
