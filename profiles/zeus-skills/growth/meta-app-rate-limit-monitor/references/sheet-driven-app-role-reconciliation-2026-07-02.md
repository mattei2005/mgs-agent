# Sheet-driven app role reconciliation — July 2026 correction

## Rodolfo's correction

The Google Sheet maintained by Ially is the operational intent layer for B001–B010 app roles. The cron should use it as the reconciliation guide, not treat every missing user as a persistent incident.

Scenario: a segurador/developer profile has account problems. Pages are migrated to another profile, the old row is deleted from the sheet, and the new row is added. Ially may add a note only for human context; the note is informational and should not drive alerting.

## Rule

```text
Planilha atualizada pela Ially = intended state.
Meta /roles = runtime state.
Cron = auditor/reconciler between the two.
```

If a segurador/profile was removed from the sheet because of a planned migration, remove it from `Removidos acumulados` rather than keeping it as an active alert.

If a new row is added for the same segurador/app, match using normalized `Segurador × NO APP` and link it to the correct app/channel.

## Human-error feedback loop

If Ially adds a row for a segurador but forgets to fill `NO APP`:

- the cron cannot reconcile that segurador to a specific app/channel;
- the old/current mismatch can remain visible as `Removidos acumulados`;
- Ially sees the channel and corrects the missing app assignment;
- next cron matches `Segurador × NO APP` and clears the accumulated removal if runtime is consistent.

This is expected and useful: the channel acts as a visual QA loop for planilha mistakes.

## Alerting semantics

```text
Case                                                   Meaning / action
-----------------------------------------------------  -----------------------------------------
Removed from Meta roles, still assigned in sheet       Critical: unexpected runtime removal.
Deleted from sheet due planned migration               Housekeeping: remove from accumulated alert.
New sheet row with same segurador and NO APP set       Reconcile/link to app; clear old if consistent.
New sheet row missing NO APP                           Surface mismatch until Ially fills app.
Observation column mentions migration/name change      Informational only; do not alert from notes alone.
```

## Implementation note

Use sheet assignment (`NO APP`, column L) as the app binding; ignore migration/status column by default unless Rodolfo explicitly asks. Normalize names for matching, but keep human-facing display from the sheet fields used in alerts.
