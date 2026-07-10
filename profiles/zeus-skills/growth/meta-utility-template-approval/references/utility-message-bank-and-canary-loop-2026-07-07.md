# Utility Message Bank and Canary Approval Loop

Source: Rodolfo workflow corrections, 2026-07-07.

Use this reference for Utility Template canary loops and future production template replacements. The core correction is that approval work must be stateful and bank-driven: do not decide from the current color alone, and do not rely on one-run artifacts.

## Durable bank vs temporary loop state

Maintain two separate files:

```text
/root/mgs-agent/data/utility-message-bank.json
/root/mgs-agent/data/utility-canary-approval-state.json
```

`utility-message-bank.json` is the durable operational history for all future canaries and real/active template replacements. It tracks every unique `TEXT + CTA_1` message hash, observed approval/rejection history, and usage locations.

`utility-canary-approval-state.json` is temporary loop state for the active canary run: gray attempts, current slot hash, ever-green flag, and approval timestamps.

Never let the temporary state be the only source of known approvals.

## Canonical hash

Use a stable hash of normalized visible `TEXT + CTA_1`.

Do **not** include `LINK_1` in the identity hash: links are slot/template/page-specific and must usually be preserved from the target template.

## Bank-first operating rule

Before any template check, replacement, production rollout, or new copy generation:

1. Load the message bank.
2. Check if the candidate message was used before.
3. Check where it was approved/rejected/gray/purple.
4. Prefer approved candidates from the same vertical/country/language.
5. Skip duplicates already present in the target template by `TEXT+CTA`.
6. Avoid generating new messages blindly when the bank has enough approved candidates.

After any check/change:

1. Upsert the current status into the bank before deciding replacements.
2. Record current template, message slot, page/canary context, observed color/status, and timestamp.
3. If installing a replacement, record usage immediately.

## Color semantics in canary loop

Green:

- Register `ever_green=true` for that slot/hash.
- Update `first_approved_at`, `last_approved_at`, `approved_count`.
- Treat as known-good.
- If the same message later appears gray, do **not** replace it.

Gray:

- Gray is not rejection.
- If the current message has ever been green (`ever_green` or bank approved history), keep it and rerun approval if the template is not 100% green.
- If it has never been green, increment `gray_attempt_count` and rerun approval.
- After 3 gray attempts for a never-green message, replace only that message and reset state for the new hash.

Red:

- Replace that message immediately in canary unless Rodolfo explicitly asks to investigate a known-good contradiction first.
- Update `rejected_count` on the same bank record.
- If the message had approved history, mark `mixed_history` / `needs_review` rather than deleting the approval history.

Purple:

- Do not classify as copy failure automatically.
- Treat as diagnostic for page/app/segurador/SB execution unless separate evidence shows format/copy failure.

## Canary cron loop pattern

For a temporary canary run, e.g. 3 hours:

```text
Every 5 minutes:
1. Read all canary templates.
2. Upsert every slot observation into utility-message-bank.json.
3. For each slot:
   - green: lock/keep
   - red: replace only that slot
   - gray never-green: retry approval, replace only after 3 attempts
   - gray ever-green: keep
   - purple: diagnostic
4. Save template only if replacements occurred.
5. Run approval when the template is not yet 20/20 green or replacements occurred.
6. Persist state after every cycle.
7. Stop when all target templates are 20/20 green or the timebox ends.
```

## Future production rollout rule

When canary templates reach 100% green, the next phase is to update the real/active production templates using the known-good bank, preserving target template link-slot order and page/template routing unless Rodolfo explicitly changes it.

For production rollout, do not bulk-replace gray/purple rows based on a single readback. Use the bank and the production-specific gray/purple rules from the main skill.

## Pitfalls

- Do not bulk-replace gray messages on first readback.
- Do not forget that an approved message can temporarily show gray later.
- Do not create disconnected records for the same `TEXT+CTA` when a message later turns red; update the same history.
- Do not reuse rejected messages in the same context unless Rodolfo explicitly chooses to retest.
- Do not include links in the copy identity hash; link preservation is a separate invariant.
