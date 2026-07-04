# Controlled-write bridge during Meta read-only calibration — 2026-06-19

## Context

Rodolfo clarified the intended operating model for Ares Meta Ads management:

- The strategic goal is to eventually have no human manually managing the account.
- The current phase is still calibration/read-only: Ares should report what it would do, Rodolfo manually acts or declines, and Ares learns/validates.
- Controlled writes can be explicitly approved for specific operational setup tasks, but this does not mean autonomous write is generally enabled.

## Workflow correction

For management reports in `logs-aquisicao`:

```text
Phase                       | Behavior
----------------------------|------------------------------------------------
Current calibration          | recommendation/checkpoint gets a thread
Rodolfo reply                | feito / ignorar / segurar / pausei / reativei / não mexer
Ares next step               | store/audit decision and validate by Meta GET
Future autonomous phase      | execute action, validate, post consolidated log; no per-action thread by default
```

## Scope/state correction

The cron reads the account as the data source, but action/recommendation scope must be explicit.

```text
State/scope                  | Correct behavior
-----------------------------|------------------------------------------------
active_focus                 | include in decision recommendations
manual_hold / saturation     | exclude from reactivation/cut recommendations
paused_by_ares_rule          | keep monitoring for simulated reactivation
outside_active_focus         | read for context, do not recommend action
```

Session example:

```text
Elena Santana / pg_22091     | active_focus
Patricia Flores / pg_22069   | manual_hold due page saturation
```

## Controlled write pattern used

Rodolfo then explicitly approved specific setup writes:

1. Disable Meta automated pause rules created by the human traffic manager.
2. At account midnight, normalize active Elena campaigns to USD25/day, 1 adset, 3 ads, and remove bid cap where Meta accepts it.
3. Create/attempt 15 functional Elena duplicates so the account reaches 20 campaigns total, scheduled between 00:00 and 01:00 Europe/Madrid.

Important distinction: these were explicit controlled writes, not broad autonomous write approval.

## Implementation pattern

Use deterministic scripts with:

- explicit target IDs;
- dry-run first;
- sanitized audit JSON under `/root/mgs-agent/data/ares/meta-ads/audit/controlled-write/`;
- `py_compile` and wrapper `bash -n` validation;
- GET verification after write;
- `[REPORT-INFRA]` for scripts/cron/persistent data;
- never print token values.

Files created in the session:

```text
/root/mgs-agent/scripts/ares-meta-elena-midnight-structure-adjust.py
/root/.hermes/profiles/ares/scripts/ares-meta-elena-midnight-structure-adjust.sh
/root/mgs-agent/scripts/ares-meta-elena-bulk-duplicates.py
```

Dry-run/audit examples:

```text
/root/mgs-agent/data/ares/meta-ads/audit/controlled-write/elena-midnight-structure-adjust-20260619T185020Z.json
/root/mgs-agent/data/ares/meta-ads/audit/controlled-write/elena-bulk-duplicates-20260619T185720Z.json
```

## Pitfalls

- Do not treat "execute this setup write" as permission for autonomous campaign management generally.
- When user says “20 campaigns” but the account has only 5 active campaigns, clarify whether to duplicate, reactivate paused campaigns, or limit to active scope. In this session, the corrected instruction was to duplicate the 5 Elena campaigns to reach 20.
- When creating scheduled campaigns for the next account-day, compute start slots in the account timezone (`Europe/Madrid`) and verify they fall between 00:00 and 01:00 local.
- Meta API rate limits can interrupt bulk creation. Use long bounded backoff and idempotent naming/detection so a resumed run does not create accidental duplicates.
- For Discord handoff to Zeus, mention the Zeus bot explicitly (`<@1496296175014252634>`); a plain message in Zeus channel may not be read/acted on by Zeus.
