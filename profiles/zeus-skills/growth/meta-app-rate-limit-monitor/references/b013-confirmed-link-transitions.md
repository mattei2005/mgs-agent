# B013 — Coverage and confirmed connection transitions

## Procedure

1. **Freeze the requested scope and channel history.** Resolve the active B013 generation and destination from the registry. Read every current Service Account `NO APP` assignment, including marked rows; count blank mandatory identities and duplicate composed `User × Segurador` keys before accepting the target list. Preserve repeated bot logins. Fetch the requested time window completely and assemble native card families with every continuation message.
2. **Reconstruct inventory separately from movements.** Parse six-column current-user/confirmed-removal tables and three-column movement tables as different schemas. Carry the current section across split messages; a continuation need not repeat its heading. Reconstruct each family's inventory as current plus confirmed-unlinked identities, then compare adjacent families. Count affected profiles separately from repeated movement occurrences. This distinguishes actual Sheet-scope growth from a read recovery mislabeled as an addition.
3. **Verify every target against live sources.** Group by exact DTR login item resolved through its username. Capture credential-free per-login account inventories and medium result batches. Require each assigned identity to appear in the authenticated DTR inventory, a successful exact account switch, matching active identity, a fresh Meta `debug_token` verdict and coherent Sheet marker. Re-read the canonical Sheet at closure to identify genuine concurrent allocation changes. A healthy app aggregate is not proof that every account is connected.
4. **Reconcile exclusions before page-level probes.** Check available page IDs against `data/mgs-global-page-ignore-list.json` before investigating a subscription-count gap. Skip ignored FB page IDs in individual Graph probes; never subscribe or reactivate retired pages to equalize counters. Keep ignored-page metadata separate from genuine missing subscriptions and ambiguous HTTP failures.
5. **Reproduce the classifier before editing.** Trace the actual movement predicate through `main()`. Exercise confirmed→unknown→same-confirmed and distinct equal-count events in isolated tests, with browser, Sheet, Discord and investment-enrichment side effects replaced. Historical `item_check_failed` proves a failed check, not a specific timeout, credential failure or Meta disconnection; label the underlying historical exception unavailable when later snapshots overwrote it.
6. **Stage and validate the whole change.** Publish helper definitions and call sites together. Run new transition tests, existing B013 regressions, Bash syntax and embedded-Python compilation. Back up script/state with verified hashes; publish atomically under the canonical B013 lock. Preserve healthy baselines, channel, cadence and credentials.
7. **Exercise real execution and read back.** Capture a complete real DTR/Graph cycle and fresh SA parity. Record the exact script hash and observation window in each receipt; distinguish a complete live cycle from narrow post-deployment probes and a replay of previously observed results. A replay is a regression check, never a fresh source read. Reconcile any source revision between these validations instead of claiming that an earlier cycle exercised later code.
8. **Close without creating more noise.** In a check-only audit, do not force a new manager-facing alert; verify ordinary delivery only when a genuine scheduled change occurs. Preserve historical misleading messages unless deletion was explicitly double-confirmed. Report coverage, linked/unlinked/unknown counts, named gaps, the proven classification defect, the correction and remaining human action. State clearly that the fix governs future classification, not the wording of old reports.

## Connection-state decision rules

- Keep `verdict`, token diagnostics and page observations fresh. Replace the current observation rather than merging stale successful fields into an unknown result.
- Persist only separate `last_confirmed_verdict`, `last_confirmed_link_status` and `last_confirmed_at` continuity metadata across inconclusive reads. Seed legacy confirmed snapshots from actual evidence; a legacy unknown without positive history must not invent a previous removal.
- Emit a connection movement only for a confirmed linked↔unlinked edge. `linked → item_check_failed/unknown → linked` is a technical recovery, not `USUÁRIOS ADICIONADOS`; an already-unlinked profile recovering from an unknown read is not a fresh removal. Diagnostic changes inside one confirmed verdict are silent.
- Preserve the new-Sheet-target alert even when its initial validation is unknown, plus genuine removals, reconnections and scope retirement/re-entry. Describe `not_monitored → linked` as a new monitoring assignment, not proof that Meta just created or added the user.
- Deduplicate exact composed identities, transition direction and current failure identities. `changes=N failures=M` alone can suppress a different legitimate target with equal counts.

## Regression and execution checks

Require tests for confirmed→unknown→same-confirmed, legacy unknown migration, fresh diagnostic replacement, genuine removal/reconnection, new Sheet targets, scope retirement/re-entry, same-verdict diagnostic changes, distinct equal-count events and ignored-page probe exclusion.

```bash
bash -n /root/.hermes/profiles/zeus/scripts/b013-dtr-link-watch.sh
"${MGS_B013_DTR_PYTHON:-/root/.local/share/mgs/sb-venv/bin/python}" \
  -m unittest discover -s /root/mgs-agent/tests -p 'test_b013*.py'
```

Inspect the current test tree rather than freezing a historical passing-test total. Focused files are `test_b013_confirmed_transitions.py`, `test_b013_profile_removal_alert.py` and `test_b013_sheets_transport.py`.

Use a silent tracked process when the observed full run plus canonical lock wait can exceed the actual foreground tool cap. Consume the terminal result before closure. A wait-window timeout is not a failed monitor and never authorizes another overlapping launch or replayed alert.
