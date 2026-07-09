# Dedicated operational audit channels for daily business monitors (2026-07-09)

## Context

Rodolfo approved a daily read-only DTR↔SmartBidding match-audit monitor after Phase 1 closure and provided a dedicated Discord channel:

```text
channel_id = 1524631647151198218
channel_name = bot-dashsb-relacao-paginas
```

This is an example of a business/ops control monitor, not an infrastructure alert.

## Rule

When creating recurring monitors whose output is business state (DTR↔SB match, page status quantities, operational divergence lists, finance status, content production status), prefer a dedicated operational channel over `#alerts-infra`.

Use `#alerts-infra` for:

- script/cron/service failures;
- REPORT-INFRA;
- broken credentials/runtime;
- infra drift requiring Zeus attention.

Use a dedicated operational channel for:

- daily read-only audit summaries;
- status quantities/trends;
- divergence lists for operators;
- persistent dashboards/briefings that Rodolfo wants to watch without polluting infra.

## Monitor design pattern

1. Start read-only.
2. Apply business ignore/exclusion gates before reporting pending/actionable rows.
3. Include an executive summary and status-count block.
4. Report only actionable divergences in detail; keep full JSON/CSV locally.
5. Use state to distinguish `new`, `persistent`, and `resolved` issues.
6. Do not autocorrect until the report has proven stable and Rodolfo explicitly approves the autocorrection class.
7. Validate channel access with the bot before enabling cron.
8. Add `flock`, docs/CRONS update, infra inventory update, and REPORT-INFRA.

## Report shape example

```text
DTR x Dash — auditoria diária

Resumo
Total DTR ativo
Total Dash SB
Páginas em ambos
OK match
Divergências atuais
Novas divergências
Resolvidas desde ontem
Ignoradas globalmente
Só DTR
Só Dash SB

Status Dash SB
Broadcast
Campaign
On-hold
Blocked
Ready
Restricted ativo
```

## Pitfalls

- Do not post recurring business summaries to `#alerts-infra` just because the job is a cron.
- Do not let a script-only/no-agent cron dump raw stdout into a user thread. Use a wrapper that posts a clean message to the intended channel and logs full output locally.
- Do not treat the first noisy dry-run as final signal if the collector was intentionally scoped/limited; run full scope before interpreting operational counts.
