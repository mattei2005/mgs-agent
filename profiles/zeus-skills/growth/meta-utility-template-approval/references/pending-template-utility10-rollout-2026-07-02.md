# Pending templates → Utility10 rollout — 2026-07-02

## Context

Rodolfo clarified the correct sequence for Messenger Broadcast Templates that were not part of the first 59-template Utility rollout:

1. Existing pending templates must be converted to **10 Utility-style messages**.
2. For CC templates, reuse the known-approved Utility copy structure from the templates that were reduced to 10 and later expanded to 20; translate/adapt by country/language.
3. Preserve each target template's existing `LINK_1` sequence exactly for the first 10 slots.
4. After updating the message bank, trigger `Run Approvals` so Ciro's system submits the messages to Meta.
5. Then include these templates in the same rollout/tracker process as the original 59 templates: monitor approval status, replace rejected/error/invalid, handle gray/no-status, then progress 10→20→30→40→50.

## Important workflow corrections

- Schedule/hour updates are separate from message-bank conversion. If hours were already fixed, do not touch hours again during Utility10 conversion.
- For templates whose Page rows have `COUNTRY` inconsistent with the template name, use the **template country/vertical code** as the conversion/content routing source, not the Page row's `COUNTRY`.
- Templates with zero current pages should still be converted and may have `Run Approvals` triggered, but their approval ETA is not meaningful until Pages are linked.
- Renaming a template can be part of the same broadcast template update payload. Example: `Openzed - US-CC-EN/EN - AV - g003-d Isliago 2 mensagens` → `NAO USAR - Openzed - US-CC-EN/EN - AV - g003-d Isliago 2 mensagens`.

## Approval ETA rule

Ciro's ETA rule remains:

```text
approval ETA = pages × active_messages × 8 seconds
```

For Utility10:

```text
ETA = pages × 10 × 8s
```

Examples from the session:

```text
2 pages   ≈ 2m
12 pages  ≈ 16m
51 pages  ≈ 1h08m
59 pages  ≈ 1h18m
224 pages ≈ 4h58m
0 pages   = sem ETA útil / sem pages vinculadas
```

## Run Approvals implementation note

The UI path is:

```text
Broadcast Template → open template/messages → Run Approvals → Update/Cancel → Save parent modal
```

When automating, use the authenticated SB broadcast template context, keep backups, update `MESSAGES`, and then trigger the approval endpoint with the real template ID. Validate by readback that:

- target template has exactly 10 messages;
- renamed templates appear under the new name;
- `LINK_1` for the first 10 slots matches the original first 10 links;
- approval trigger returned 2xx for each template.

## Required post-step

After a pending batch is converted to Utility10 and Run Approvals is triggered, add those templates to the same rollout tracker/process as the original 59 templates. Do not leave them as one-off completed work; they need ongoing approval-state monitoring and rollout progression.
