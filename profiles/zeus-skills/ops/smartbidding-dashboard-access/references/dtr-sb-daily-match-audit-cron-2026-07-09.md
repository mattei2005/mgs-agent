# DTR↔SB daily match audit cron — dedicated channel and report shape (2026-07-09)

## Context

After Phase 1 was closed, Rodolfo requested a recurring daily audit to keep DigitalTRChat/Bot and SmartBidding Dash aligned for pages that exist in both systems. He also asked to include status/page quantities in the report and provided a dedicated Discord channel:

```text
channel_id = 1524631647151198218
channel_name = bot-dashsb-relacao-paginas
```

## Durable workflow

Create/maintain this as an operational monitor, not an infra alert:

1. Run once per day, early morning ET, with `flock`.
2. Read-only first; do not auto-correct SB/DTR divergences until the report has proven stable for several days and Rodolfo explicitly approves autocorrection rules.
3. Source live data, not stale Sheets:
   - DTR/Bot active users/pages from the validated DTR collector.
   - SB `Accounts > Messenger > Page` full scope across `digital-trust + digital-trust-2` child publishers.
4. Apply `/root/mgs-agent/data/mgs-global-page-ignore-list.json` before matching or counting pending/actionable rows.
5. Match primarily by large `FB_PAGE_ID`; validate `LOGIN`, `PAGE_ID/PG`, and `UTM=pg_<PAGE_ID>`.
6. Report only concise summary + actionable divergences in Discord; keep full JSON/CSV locally under `/root/mgs-agent/reports/`.

## Report shape Rodolfo approved

Include both match health and SB page status counts:

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

Problemas — primeiras linhas
FB_PAGE_ID | PG DTR | PG SB | Status SB | Login DTR | Login SB | Problema
```

Silence/verbosity rule: if there is no actionable divergence, post only the compact summary/status block; do not dump long tables.

## Validated implementation from session

Files created:

```text
/root/mgs-agent/scripts/dtr-sb-daily-match-audit.py
/root/mgs-agent/scripts/dtr-sb-daily-match-audit.sh
```

Root crontab entry:

```text
20 6 * * * flock -n /var/lock/dtr_sb_daily_match_audit.lock /root/mgs-agent/scripts/dtr-sb-daily-match-audit.sh >> /root/mgs-agent/logs/dtr-sb-daily-match-audit-cron.log 2>&1
```

Validation performed:

- Discord channel GET via Zeus bot returned `200`, name `bot-dashsb-relacao-paginas`.
- Python `py_compile` OK.
- Shell `bash -n` OK.
- Small dry-run (`--limit-users 1 --limit-accounts 1 --dry-run --no-post`) executed successfully.
- `docs/CRONS.md` and `infra-inventory.json` were regenerated after cron creation.

## Pitfalls

- Never gate full SB child scope on a fixed publisher count (for example, `publishers >= 56`). Publishers can be legitimately added/removed. Validate the live `/company` response structurally: both `digital-trust` and `digital-trust-2` must be present with non-empty publisher lists, consume every returned child publisher, and retain the Messenger-row floor as the volume sanity check. Ensure Playwright/browser cleanup runs in `finally` so a scope exception does not emit a secondary `Event loop is closed` traceback.
- Do not put this report in `#alerts-infra`. It is operational DTR/SB state, not infrastructure failure.
- Do not compare Sheet row counts as if they were live pending work; live SB/DTR + global ignore gate wins.
- Do not treat `SB sem DTR` as automatically deletable/blockable. This cron reports divergences; cleanup still requires the relevant validated workflow and Rodolfo's decision unless an explicit safe autocorrect rule is approved later.
- For first runs, expect high noise if DTR scope is incomplete or intentionally limited. Full daily cron must run the full DTR active-user scope before interpreting counts.