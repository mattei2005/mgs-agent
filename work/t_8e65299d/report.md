# SHEIN historical review queue maintenance — t_8e65299d

## Result and limits

Installed central scheduling-only representation `WAITING_HUMAN_DECISION`, pinned to unmodified historical runner state and completed Engine checkpoint. The historical request `shein-1565261967260647536-c3` remains `POSTPROCESS_PENDING`, not terminal or approved. Campaigns `120250921178510629` (006) and `120250921178500629` (007) were independently GET-verified PAUSED on account `937846586033361`, with daily budget 3500 and COST_CAP. Review question `1565343225894666345` was read in full: device suggestion omission and unknown-age inclusion still require a human decision. Complete live message history contained only the new original order after that question, no approval/cancellation.

Request `shein-1565747351543480374` now has `dependencies=[]` under the central read-only evaluator. This proves **dependency readiness only**, not media readiness, a real campaign plan or successful creation. The exact original input and historical state hashes are unchanged. The queue job remains WAITING/attempts0 under a durable maintenance hold. No new runner state exists. All 16 selected media lineages remain unreserved. No Meta/Drive mutation, upload, reservation, activation, cancellation, source/manifest/input rewrite or gateway restart was performed.

## Installed safety behavior

- Missing/changed/ambiguous review evidence retains the dependency. Exact historical state and Engine checkpoint digests, campaign IDs/account, completed Engine status, PAUSED readback and material human-review provenance are required.
- Active foreign/unknown writer leases, account process locks, lease-update locks, selected-media ambiguity, shared lineage/checksum/media IDs/filename identity and pending activation/partial QA remain blockers. Reservations are never transferred from an active/nonterminal request.
- Same-request missing-only recovery is not deadlocked by its own persisted lease: exact incoming request/state/phase parity is required, while process/account locks and foreign lease guards remain effective. No lease is released or overwritten.
- Historical decision-wait records cannot be autoexecuted, even if stale. Future review/QA resolution remains the existing human-authorized central route.
- Durable hold/foreground ownership is reloaded inside a per-job dispatch lock. Stale worker snapshots cannot execute or overwrite the handoff. Ares-only takeover validates live authority and immutable original input; it performs scheduling ownership changes only.
- A foreground-owned job is not executed or notified by the worker. After exact terminal QA/readback, the worker may close only scheduling bookkeeping as FOREGROUND_COMPLETE; Ares still delivers the result.

## Verification

Final installed-module regression in the existing full test runtime: **531 passed + 322 passed subtests**, 40 files, no exclusions, no external-network attempts, no module-origin mismatch. Includes 36 new decision-wait/handoff cases and 19 existing queue cases; IMG/VID/core routes remain covered. This is the named regression scope in Zeus context, not a whole-repository or live Ares/Meta write acceptance claim. The unrelated Ares-context fixture follow-up already exists as `t_0bb85547`.

The real installed evaluator returned `dependencies=[]`. Holding the real account lock read-only made it return the historical dependency again (negative PASS). The restarted queue service produced successive natural heartbeats, with attempts0 and hold preserved. Final source/descriptor/skill hashes, original-input/historical-state hashes and exact inventory entry were independently read back. Only the queue worker service was stopped/reloaded; no gateway was touched.

Two tooling invocation mistakes were recovered without side effects: OS python lacked pytest (used existing full runtime, no package install), and a shell helper help probe was initially sent to python (corrected to bash). One multi-hunk patch validation rejected ambiguous context before changing files; corrected patch and final tests passed. No unresolved failure remains in this maintenance's acceptance scope.

## Dry handoff — Ares only

Ares acknowledged exclusive ownership/no new writer in card `t_8f7a90a8` before installation. From the **actual existing Ares profile**, in `/root/mgs-agent`:

1. Recheck original request, authority, effects and installed receipt. Inspect dependency only:

   `PYTHONPATH=/root/mgs-agent/scripts python3 -m ares_campaign_v3.shein_request_queue --inspect /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1565747351543480374/request.json`

2. Claim the dry scheduling handoff through the central route, not by manually clearing fields:

   `PYTHONPATH=/root/mgs-agent/scripts python3 -m ares_campaign_v3.shein_request_queue --take-foreground /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1565747351543480374/request.json`

   Expect FOREGROUND_OWNED and zero campaign writes/media uploads/reservations. Do not impersonate Ares by changing Zeus's profile env. Takeover intentionally rejects Zeus. Read back the same queued job: maintenance_hold absent, dispatch_owner=foreground, unchanged immutable request/clock/attempt counter. Worker stays active but cannot become a second writer or duplicate final delivery.

3. Resume only the original central flow: real prepare-media -> request-ready -> campaign --dry-run -> campaign --confirm-execute. Preserve the same request, 8 groups x2 IMG/texts, USD25/day each (USD200 total), COST_CAP/bid_amount95, original start 2026-10-30 11:45 America/New_York and approved same-day elapsed-start policy. Do not reset the SLA or claim 11:45 was met. Do not modify historical 006/007. Require all media QA, exact IDs/semantics and final ACTIVE readback before delivery.

Do not run this maintenance's work/ helper scripts as an operational route.

## Evidence and rollback

- Live read-only evidence: `work/t_8e65299d/live-readonly.json`
- Final regression: `work/t_8e65299d/regression-final.json`
- Installed source receipt: `work/t_8e65299d/deployment-receipt.json`
- Durable post-reload hold/hash/account-lock proof: `work/t_8e65299d/final-readback.json`
- Rollback snapshots: `work/t_8e65299d/rollback/`
- Inventory: `runtime_artifacts[id=shein-inert-review-queue-t_8e65299d]`
- Audit: task-scoped entries in `logs/events-audit.jsonl`
- REPORT-INFRA: exact existing embed `1565761035963465729`, created through canonical helper, updated in place after the final recovery tests, GET/readback verified. No duplicate post, mention or thread.
- Own skill learning: `meta-ads-api-operations/references/shein-request-queue-decision-waits.md` with router link, saved and read back. No Ares skill changed.

Rollback must keep the durable hold and first reconcile current ownership/effects. Restoring the old queue code is allowed only under coordinated idle maintenance. Never restore stale queued-job snapshots after Ares takeover, rewrite historical state/manifest, release a reservation/lease or delete records as an implicit rollback. No destructive action is authorized here.
