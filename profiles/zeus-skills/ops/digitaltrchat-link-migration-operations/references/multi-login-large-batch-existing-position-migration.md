# Large multi-login existing-position migrations

Use this reference when a URL audit becomes an explicitly authorized migration spanning many Pages, multiple DTR logins/imported accounts, more than one destination catalog, and a mixture of Pages with and without an installed Auto Principal Drip.

## Validated production case — 2026-09-03/04

Rodolfo authorized migrating every Page in a previously reconciled five-login audit whose live legacy routes matched the approved Keitaro families:

- `card.openzed.com` or `card.wavesbee.com` → `US-CC-EN` → full `sr.openzed.com` catalog;
- `tarjeta.openzed.com` or `tarjeta.wavesbee.com` → `US-CC-ES` → full `srf.openzed.com` catalog.

The frozen population contained 116 exact DTR/FB Page identities:

- 67 `US-CC-EN`;
- 49 `US-CC-ES`;
- 110 Pages with an existing M0–M15 Auto Principal Drip plus Get Started and No Match;
- 6 Pages with Get Started and No Match but no Auto Principal Drip.

Rodolfo was shown that partition before authorizing “todas”. That authorization covered existing URL positions only: the six action-only Pages received Get Started/No Match changes, but no flow was created; Persistent Menu and every unrelated field remained out of scope.

Evidence artifacts:

- executor: `/root/mgs-agent/scripts/dtr-legacy-keitaro-smart-routing-migration.py`;
- transactional backup/readback root: `/root/mgs-agent/backups/dtr-legacy-keitaro-smart-routing-20260903T230557-0400/`;
- final summary: `final-summary.json` inside that root.

These paths are historical evidence, not a generic command to replay against a future population.

## Full-batch preflight before any write

1. Materialize one ordered, deduplicated scope artifact from the approved audit. Require unique DTR Page IDs and preserve login, imported-account ID/name, Page name, Facebook Page ID, old routes, classification authority, expected surfaces, and source hash.
2. Validate every destination catalog deterministically before opening DTR write state.
3. Re-enumerate each exact login and imported account live. Require every Page identity to match DTR Page ID + Facebook Page ID + normalized Page name.
4. Read and back up Get Started/No Match controls for every Page. For every expected flow, back up the full graph and prove reachability/topology; for every action-only Page, prove that Auto Principal Drip is still absent.
5. Accept a pre-write surface only when it is exactly the frozen audit value or already equals the approved target. A third value is drift. A flow must be wholly `before` or wholly `target`; a mixed graph is not safe to replay.
6. Persist each Page manifest atomically, but do not start production until the complete authorized set reconciles. A partial qualification is not a partial write authorization.

## Structural M0 inference for legacy M0–M15 flows

The old Keitaro flow can contain one initial Fineasier URL whose text looks like No Match, followed by M1–M15. Do not map that initial URL to canonical NM merely from its legacy string.

- Build graph reachability from the unique `Start Bot Flow`.
- Identify the unique HTTP CTA reachable before traversing any `New Sequence` or `Sequence Single` node.
- Record that node as M0 with authority `structural_start_path_before_sequence`.
- Require the remaining 15 URL positions to map unambiguously to M1–M15 from matching path/query semantics.
- Require exactly 16 existing flow URL occurrences and preserve the graph depth; never add M16–M28 under link-replacement authorization.

## Canary matrix and transaction order

A large batch with more than one destination family needs one successful canary per distinct catalog family. In the validated case, one EN Page proved `sr.openzed.com` and one ES Page proved `srf.openzed.com` before the remainder advanced.

For every Page, use this transaction:

1. fresh pre-write identity and drift readback;
2. existing Flow Builder URLs, one Save, then immediate reload;
3. Get Started M0, Update, then reload;
4. No Match NM, Update, then reload;
5. close the write context;
6. open a fresh authenticated context and independently verify the complete Page;
7. persist the Page result before advancing.

Accept the DTR-appended `subscriber_id=#SUBSCRIBER_ID_REPLACE#` suffix only on Get Started/No Match when the canonical base is exact. Never inject it into Flow Builder URLs.

## Interrupted-run recovery

A process timeout or lost wrapper result is not proof that the current Page is unchanged or failed. Before retrying:

1. read back Flow, Get Started, and No Match in a fresh context;
2. classify each surface independently as exact `before`, exact `target`, or `third value`;
3. if Flow is wholly target and Actions are before, do not resubmit Flow—write only the missing Actions;
4. if a surface is a third value or the flow is mixed, stop and reconcile/restore;
5. independently verify the Page after the missing-only recovery.

Validated case: Page `3250` lost the wrapper after Flow Save. Fresh readback proved all 16 flow positions at target while both Actions remained at their frozen before values. Missing-only recovery updated the two Actions, preserved the flow, and passed the later 116-Page readback.

## Final second-pass readback

Per-Page post-write verification is necessary but not the batch closure gate. After all Page transactions finish, run a second fresh-session readback across the complete authorized set and require:

- exact target host/path/parameters for every scoped URL occurrence;
- action-editor DTR/FB identity match;
- action business fields unchanged except URL;
- full non-URL graph equality to the backup;
- topology/reachability unchanged per Page;
- action-only Pages still have no flow;
- omitted surfaces remain explicitly out of scope;
- requested, applied, and verified Page totals reconcile exactly.

The validated run finished 116/116 applied and 116/116 verified, with 1,760 flow URL occurrences and 232 Action URLs changed, zero final failures, zero rollback Pages, and zero Persistent Menu writes.

## Honest occurrence accounting after interruption

A Page can reach the approved target before its process writes an `apply-result.json`. Therefore, summing recorded write calls can undercount real before→after changes.

Report both when they differ:

- **recorded write occurrences** — mutations represented in completed executor result files;
- **verified before→target occurrences** — frozen manifest values proven to differ from the final independently read target.

Count a change as verified before→target only when the pre-write manifest is intact, the final surface equals the approved target, and all non-URL invariants pass. Preserve the interrupted Page ID and recovery evidence instead of inflating or hiding the discrepancy. In the validated case, executor result files recorded 1,744 flow writes, while manifests plus final readback proved 1,760 actual flow occurrence changes; the 16-occurrence difference was Page `3250`.
