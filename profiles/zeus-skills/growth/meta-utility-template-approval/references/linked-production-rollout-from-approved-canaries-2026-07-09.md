# Linked Production Template Rollout from Fully Approved Canaries

Session pattern validated 2026-07-09 for SmartBidding Messenger Utility templates.

## Scope gate

1. Read live `Broadcast Template` rows from `/broadcast/Messenger` under `digital-trust + digital-trust-2`.
2. Target only production rows with live `PAGES > 0`.
3. Exclude `Teste-*`, `NAO-USAR`/equivalents, and templates already 20/20 green.
4. Parse the exact `COUNTRY-VERTICAL-LANGUAGE` code from the target name and require a same-code canary source with exactly 20 unique messages, all currently green.
5. For a mass rollout, show the live impact and obtain the required explicit confirmation before writes.

## Mutation rule for this scoped phase

This is an explicit migration exception to the normal red-only repair policy:

- Preserve every existing green slot byte-for-byte.
- Replace only red, purple, and gray slots.
- Source `TEXT + CTA_1` only from the exact same-vertical 20/20-green canary.
- Skip candidates whose normalized visible `TEXT` or `TEXT+CTA` already exists in the destination template.
- Preserve the destination slot's `MESSAGE_ID`, `LINK_1`, `CTA_2`, `LINK_2`, `DESCRIPTION`, `IMAGE`, and `TEXT_2` fields.
- Remove old approval counters only from changed/new slots; never edit approved source copy.
- For linked 10-message templates that must reach 20, add slots 11–20 while cycling the destination's existing exact link/secondary-field sequence. Never import canary links.

## Safe staged execution

1. Build a frozen live plan containing exact row ID, name, pages, message hash, before row, desired messages, source canary, and target phase.
2. Independently validate the plan before POST:
   - source canaries remain 20/20 green;
   - all targets have `PAGES > 0`;
   - all retained green slots are unchanged;
   - all changed copies come from the matched canary;
   - existing link slots are unchanged;
   - added slots follow the destination link cycle;
   - 20 unique visible texts and `TEXT+CTA` pairs result.
3. Select one low-blast-radius production target per vertical. Include any special 10→20 case in this canary phase so link cycling is exercised early.
4. Backup the full row immediately before each POST.
5. POST the complete template payload with only `MESSAGES` changed.
6. Re-fetch live rows and validate exact content/CTA/link readback before recording success.
7. After all production canaries pass, apply the remainder.
8. Trigger `Run Approvals` only after all target rows have clean content/link readback.

## Resumability and retry pattern

Mass jobs must be restartable:

- Append one durable run record after each template passes readback (`template`, row ID, before/after hashes, backup, replaced/added counts, phase, validation status).
- On rerun, skip templates already recorded as validated and continue only pending names.
- On transient HTTP 5xx, retry the same exact payload once after a short delay. If it still fails, stop; do not continue blindly.
- Never restart from the first template after a partial run without the validated-skip guard.

## Approval validation pitfall

Approval counters are asynchronous. After the first approval call, identical approved hashes may update status counters in other templates, so a full `MESSAGES` hash that includes `APPROVED`, `REJECTED`, `INVALID_FORMAT`, or `ERROR` can drift even when content is untouched.

Before each approval and in final deployment validation, compare the immutable core only:

- `MESSAGE_ID`
- `TEXT`
- `CTA_1`
- `LINK_1`

Use status counters only for a separate approval-state report. HTTP 202 means the approval request was accepted, not that Meta/Ciro finished processing it.

## Closure checks

- Every target has a full backup.
- Every target returns the planned 20-message content/CTA/link set by live readback.
- Source canaries still read 20/20 green.
- Every approval endpoint call was accepted; report final approval colors as asynchronous/in progress.
- Record production usage in `data/utility-message-bank.json` and rollout history in `data/sb-utility-rollout-tracker.json`.
- Update audit/inventory for modified operational data.

## Validated example

The 2026-07-09 rollout staged 11 production canaries, resumed safely after a bounded transient retry, then completed the remaining targets. The key proof was live immutable-core readback for every target plus accepted approval requests—not the immediately visible color totals, which continued changing asynchronously.
