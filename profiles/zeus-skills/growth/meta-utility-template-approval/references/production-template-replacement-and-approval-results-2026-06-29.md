# Production Template Replacement + Approval Result Handling — 2026-06-29

Session lesson from Rodolfo's US-CC-EN rollout in SmartBidding.

## Approval result source

For a Messenger Broadcast Template, the SB backend returns each message inside the template's `MESSAGES` JSON with approval counters:

```text
APPROVED
INVALID_FORMAT
REJECTED
```

Operational classification:

```text
REJECTED > 0        → REJEITADA
INVALID_FORMAT > 0  → INVALID_FORMAT
APPROVED > 0        → APROVADA
else                → PENDENTE
```

Use this instead of manually reading green/red bars from screenshots when authenticated API/runtime access is available.

## Sheet workflow after canary approval

When a canary template returns approval results:

1. Pull the actual template messages from SB, not stale local CSV assumptions.
2. Rename the working approval sheet tab to the combo, e.g. `US-CC-EN`.
3. Ensure all approved/tested rows are present; if Rodolfo manually added row 201 in the dashboard, pull it from SB and add it back to the sheet.
4. Add column `STATUS` after the 9 SB import columns.
5. Classify each row as `APROVADA`, `REJEITADA`, `INVALID_FORMAT`, or `PENDENTE` from backend counters.
6. Create a separate approved-bank tab, e.g. `US-CC-EN Approved 187`.
7. Generate the approved-bank import CSV with only the original 9 columns:

```text
MESSAGE ID,TEXT,DESCRIPTION,IMAGE,CTA 1,LINK 1,CTA 2,LINK 2,TEXT 2
```

Do not include `STATUS` in the SB import CSV.

## Critical correction: preserve target template links exactly

When preparing a CSV to replace messages inside an existing production template, **do not invent or normalize the link rotation**.

Rodolfo used “1 to 15” only as an example. The correct rule is:

```text
Use the exact LINK_1 sequence from the target template, in current MESSAGE_ID order.
Preserve duplicates, `-2` variants, UTM masks, and all URL text exactly.
Repeat that exact sequence if the approved message bank has more rows than the template sequence length.
```

Wrong:

```text
Assume links are mct-001..mct-015 and synthesize them.
Drop `-2` variants.
De-dupe URLs before assigning links.
Apply links from all sites/templates instead of the one requested target template.
```

Right:

```text
1. Pull target production template from SB.
2. Sort its existing messages by MESSAGE_ID.
3. Extract `LINK_1` as an ordered list exactly as-is.
4. Take approved messages from the approved-bank CSV/sheet.
5. Renumber output MESSAGE_ID sequentially from 1.
6. Assign `LINK_1 = exact_link_sequence[(new_id - 1) % len(exact_link_sequence)]`.
7. Keep approved message TEXT/CTA but target-template links.
8. Export UTF-8 BOM CSV for SB import.
```

Validate before delivery:

- output row count equals approved-bank count;
- first N output links exactly match the target template's first N links (where N = min(target link count, output row count));
- row after the sequence wraps to the original first link;
- no generated/synthetic URLs appear;
- CSV has UTF-8 BOM when emojis are present.

## Scope discipline

If Rodolfo points to a screenshot/filter subset and asks for “those templates,” do not export all templates from all sites. Work only on the requested subset or the specific template named. If unclear, ask for the exact template/domain before generating bulk artifacts.

## First-name placeholder lesson

`{{first_name}}` rendering can be empty or literal if Messenger profile sync/User Profile API is not working for a page/app. Until the permission/sync path is confirmed, avoid relying on `{{first_name}}` in production Utility copy. Prefer copy that reads cleanly without personalization.
