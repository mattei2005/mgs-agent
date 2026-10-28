# B013 — Confirmed link transitions and addition-alert audit

## Scope and evidence

- Audit the dedicated B013 channel against every current canonical Service Account `NO APP` occurrence, not the generic `/roles` runner. Freeze composed `User × Segurador` identities, preserve repeated bot logins, collect all native card continuation messages, and distinguish six-column inventory tables from three-column movement tables.
- Reconcile every assigned profile with the authenticated DTR account inventory, exact switched account identity, fresh `debug_token` verdict and Sheet marker. Capture per-login inventories and result batches without tokens or passwords. A valid app and healthy aggregate capability do not prove that every assigned account is linked.
- Separate `not_monitored → linked` (new Sheet monitoring scope) from a confirmed disconnected→linked reconnection. A scope increase can be real even when the profiles were already present in DTR; do not call it a newly created Meta user.

## Confirmed-state invariant

- Keep `verdict` and diagnostic fields as fresh observations; do not merge stale successful `debug_token` or page data into an unknown result.
- Persist only separate `last_confirmed_verdict`, `last_confirmed_link_status` and `last_confirmed_at` continuity metadata across inconclusive reads. Seed legacy confirmed snapshots from their actual verdict; a legacy unknown without positive history must not invent a prior removal.
- Emit membership movements only for confirmed linked↔unlinked edges. `linked → item_check_failed/unknown → linked` is a technical recovery, not `USUÁRIOS ADICIONADOS`; an already-unlinked profile recovered from an unknown read is not a fresh removal. Diagnostic changes inside the same confirmed verdict are silent.
- Preserve the existing new-Sheet-target alert, including a new target whose initial validation is unknown, and preserve genuine removals, reconnections and reassignment/re-entry behavior.
- Deduplicate exact event identities, transition direction and current failure identities. A signature built only from `changes=N failures=M` can suppress a different legitimate target with equal counts.

## Validation and deployment

1. Reproduce the actual state-machine bug through the monitor `main()` before editing; isolate browser/Sheet/Discord/enrichment side effects in tests.
2. Require regressions for linked→unknown→linked, unlinked→unknown→unlinked, legacy unknown migration, fresh diagnostic replacement, real removal/reconnection, new Sheet targets, scope retirement/re-entry, same-verdict diagnostic changes and distinct equal-count events.
3. Stage the complete helper and call-site change, run new and existing B013 tests plus Bash/inline-Python syntax checks, back up script/state with verified hashes, then publish atomically under the existing canonical B013 lock. Never reset healthy account baselines or change credentials, scheduling or channels to repair alert semantics.
4. Exercise a complete real DTR/Graph cycle and compare fresh SA readback, frozen target count, distinct account coverage, account-switch identity, unresolved rows and actual alert delivery. Recheck live scope at closure; do not blame a legitimate concurrent allocation change on the parser.
5. Use a silent tracked process when the observed run plus lock wait can exceed the real foreground tool cap. Consume its terminal result before closing; a wait-window timeout is not a monitor failure and never authorizes overlapping/replayed delivery.
6. Preserve old misleading Discord reports unless deletion was explicitly double-confirmed. Explain that the fix applies to future classification; do not claim historical messages were corrected or republish a manual live alert during a check-only audit.

Implementation: `/root/.hermes/profiles/zeus/scripts/b013-dtr-link-watch.sh`. Focused regressions: `tests/test_b013_confirmed_transitions.py`, `tests/test_b013_profile_removal_alert.py`, `tests/test_b013_sheets_transport.py`.
