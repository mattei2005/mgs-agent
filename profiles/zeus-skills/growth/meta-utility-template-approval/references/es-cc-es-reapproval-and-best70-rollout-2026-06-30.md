# ES-CC-ES reapproval + best70 rollout — 2026-06-30

Session pattern from the ES Spanish Utility Template rollout after a partial approval probe.

## Situation

A full ES-CC-ES approval template returned a mix of:

```text
APPROVED
REJECTED
blank / no status yet
```

The blank rows were exported as a separate reapproval CSV, submitted again, then read back from a second SB test template.

## Correct workflow

1. Read the original full approval template from SB and update the Sheet tab with raw `STATUS`.
2. Export only rows where `STATUS` is blank/no-status into a fresh dashboard-import CSV with the normal 9 columns only:
   - `MESSAGE ID`
   - `TEXT`
   - `DESCRIPTION`
   - `IMAGE`
   - `CTA 1`
   - `LINK 1`
   - `CTA 2`
   - `LINK 2`
   - `TEXT 2`
3. Keep UTF-8 BOM + CRLF for dashboard import.
4. After the reapproval template is done, read that exact template from SB.
5. Update the original country/language Sheet tab by message ID:
   - set `STATUS=APPROVED` for newly approved rows;
   - preserve/report rejected and still-blank rows for audit;
   - do not infer status from text match alone.
6. Recount the full source tab after update.
7. Select the best 70 from the **updated matching country/language tab** for production install.

## Important routing guard

If the production targets are `ES-CC-ES`, use the updated `ES-CC-ES` approved bank even if the user casually says “aba us-cc-es” while naming ES templates. Treat the named production templates as the stronger route/vertical signal and avoid cross-country/currency mismatch.

Reason: a US Spanish bank can contain `$`/US URL/link/source assumptions, while ES Spanish targets should preserve ES country/currency/template routing.

## Best70 install behavior

For ES-CC-ES rollout into existing production templates:

- select 70 approved messages by commercial appeal/conversion score, not first 70;
- dedupe by visible `TEXT + CTA`;
- preserve zero-width in `TEXT` if already present in the approved bank;
- preserve each target template’s exact `LINK_1` sequence;
- if installing 70 into a target that currently has 60 messages, cycle the target’s existing link sequence in order for rows 61–70 rather than inventing URLs;
- preserve target `CTA_2`/`LINK_2` sequence the same way when present;
- backup each full template row JSON + CSV before POST;
- validate by re-reading `/broadcast/Messenger` and confirming each target has exactly 70 messages.

## Reporting shape

```text
Reapproval template: <name>
Reapproval rows: 36
New approved: 19
Rejected: 5
Still blank: 12
Final source tab: 150 APPROVED / 39 REJECTED / 12 blank
Selected: best 70 approved
Templates updated: 8/8
Validation: SB re-read confirms 70 each
Backups/audit: <paths>
```

## Pitfalls

- Do not overwrite previous approved statuses with blank rows from a reapproval template.
- Do not consolidate by `TEXT` when updating Sheet status; align by `MESSAGE ID` from the reapproval CSV/template.
- Do not run `Run Approvals` automatically after production install unless explicitly requested.
- Do not reuse a US-selected bank for ES production templates when an ES approval bank exists.
