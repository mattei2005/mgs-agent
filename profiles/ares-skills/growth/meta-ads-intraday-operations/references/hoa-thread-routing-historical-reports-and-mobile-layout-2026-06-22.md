# HOA thread routing, historical reports and Discord layout — 2026-06-22

## Context

Rodolfo split the OpenzedFinanzas operation thread into separate fixed threads because intraday posts every 30 minutes and accumulates too much noise for HOA/manager reports.

```text
Stream    | Thread pattern
----------|------------------------------------------------
Intraday  | OpenzedFinanzas ES-CC-ES - <MM-DD> - Intraday
HOA       | OpenzedFinanzas ES-CC-ES - <MM-DD> - HOA
```

For the 2026-06-20 operation:

```text
Intraday thread | 1517682975234326729
HOA thread      | 1518648967360024757
```

## Operational rules

1. Keep high-frequency intraday output separate from HOA.
2. HOA wrapper should post to the HOA thread, not the intraday thread.
3. Add all media buying managers plus Geizian to the HOA thread before posting historical/full reports.
4. Validate thread membership with `GET /channels/{thread_id}/thread-members/{user_id}` returning `200` before reporting success.
5. If Discord returns `429` while adding several users, wait and retry the failed user; do not report that user as added until verified.
6. For historical HOA requests, generate reports with an explicit account-date and checkpoint time. Use `22:00` in account timezone for a complete past-day summary unless Rodolfo specifies a different checkpoint.
7. For “today”, use the live/current HOA checkpoint.

## Commands/patterns

Add a thread member:

```bash
/root/mgs-agent/scripts/discord-add-thread-member.sh \
  --profile ares \
  --thread <THREAD_ID> \
  --user <USER_ID>
```

Historical HOA generation requires the script to support:

```bash
/root/mgs-agent/scripts/ares-meta-hoa-manager.py \
  --operation-id OpenzedFinanzas-CC-ES \
  --account-id 1356770869843984 \
  --account-tz Europe/Madrid \
  --always-output \
  --report-date YYYY-MM-DD \
  --checkpoint-time 22:00
```

The profile wrapper should accept and forward `"$@"` so manual date arguments work:

```bash
/root/.hermes/profiles/ares/scripts/ares-meta-hoa-manager.sh \
  --report-date 2026-06-20 \
  --checkpoint-time 22:00
```

## Discord mobile layout pitfall

Rodolfo corrected that the intraday table looked “feia” when it split into `Parte 1 de 3`, `Parte 2 de 3`, etc. Root cause: too-wide columns (`REC-YYYYMMDD-HHMM-001`, long campaign names, long reasons) exceeded Discord/mobile usable width and forced ugly chunking.

Prefer mobile-first compact columns for recurring cron reports:

```text
REC    | Campanha         | PG       | Início     | Spend | MO | CPMO | Ação     | Motivo          | Status
-------|------------------|----------|------------|-------|----|------|----------|-----------------|-------
REC001 | Elena ES ESP 013 | pg_22091 | 20/06/2026 | 14.41 | 4  | 3.6  | OBSERVAR | Learning<3d; R2 | ACTIVE
```

Guidelines:

- Use `REC001` in display; keep full `REC-YYYYMMDD-HHMM-001` in audit JSON.
- Compact campaign display to first name + country + language + sequence, e.g. `Elena ES ESP 013`; keep raw campaign name in audit JSON.
- Compact reasons to action/rule indicators, e.g. `Learning<3d; R2`; keep long reason in audit JSON.
- Before posting a recurring report, run the Discord poster in dry-run when practical and check `chunks=1` or at least balanced chunks.
- Never let the helper split a fenced `text` table in the middle; use smaller table blocks with repeated headers if splitting is unavoidable.

## REPORT-INFRA pitfall during these changes

Ares must not use `ares-discord-post-with-thread.py` for `[REPORT-INFRA]` without a `--thread-id`, because it creates a thread in the infra/alert channel. Use:

```bash
/root/mgs-agent/scripts/ares-report-infra.sh
```

Validate with:

```bash
printf '[REPORT-INFRA] test\n' | /root/mgs-agent/scripts/ares-report-infra.sh --dry-run
```
