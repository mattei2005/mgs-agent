# OpenzedFinanzas cron logging setup — 2026-06-17

Session-specific reference for Ares Meta Ads cron/log configuration.

## Operation

```text
Operation ID | OpenzedFinanzas-CC-ES
Account ID   | 1356770869843984
Account name | OpenzedFinanzas-ES-CC-ES-03
Log channel  | logs-aquisicao / 1516887105543077949
Timezone     | Europe/Madrid
Mode         | dry_run_no_write until Rodolfo approves controlled-write
```

## Cron jobs created

```text
Cron             | Schedule                          | Deliver target               | Job ID
-----------------|-----------------------------------|------------------------------|-------------
Intraday R1-R5   | every 30m                         | discord:1516887105543077949 | aa9e01a5ec4a
Reativar-todas   | 30 18 * * * America/New_York (*) | discord:1516887105543077949 | c6c737070d3f
```

(*) At creation time, `30 18 * * *` EDT maps to 00:30 Europe/Madrid. Re-check DST offsets if scheduler timezone or account timezone changes.

## Log format corrected by Rodolfo

Rodolfo rejected the original wider table and requested this compact table:

```text
OpenzedFinanzas-ES-CC-ES-03 — 2026-06-17 — 21:45 CEST — Reativar-todas Meta — dry-run

PG ID    | País/Vertical | Regra usada    | Status
---------|---------------|----------------|-------
pg_22068 | US / CC       | reativar-todas | PAUSED
pg_22037 | US / CC       | reativar-todas | PAUSED
```

Rules:
- Title: account name + date + time in account timezone + cron type.
- First column: PG ID extracted from campaign name pattern like `(pg_22068)`.
- Second: country from campaign name + operation vertical.
- Third: rule used (`R1`–`R5` or `reativar-todas`).
- Fourth: campaign `effective_status`.
- Keep intraday silent when there are no candidates or errors.

## Implementation files

```text
/root/mgs-agent/scripts/ares-meta-cron-runner.py
/root/.hermes/profiles/ares/scripts/ares-meta-intraday-cron.sh
/root/.hermes/profiles/ares/scripts/ares-meta-reactivate-all-cron.sh
/root/mgs-agent/data/ares/meta-ads/operations/OpenzedFinanzas-CC-ES.json
```

Validation performed in session:
- `py_compile` OK.
- Intraday dry-run: errors=0, candidate_count=0, stdout silent.
- Reativar-todas dry-run: errors=0, candidate_count=10, table emitted in new format.
