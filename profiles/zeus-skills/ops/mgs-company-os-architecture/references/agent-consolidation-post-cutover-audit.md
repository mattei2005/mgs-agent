# Agent consolidation: post-cutover audit and normalization

Use after two operational agents are merged into one identity with internal modules, or when Rodolfo asks whether the merged design still matches the agent's real operating history.

## 1. Validate the operating model from direct evidence

1. Read the named Discord thread/source first; do not substitute session history.
2. Compare its claims against the live SOUL, operational map, authorization registry, service/runtime, active skills, data inventory and rollback state.
3. Separate architectural findings from runtime incidents. An old restart, paused compatibility job or available Hermes update does not by itself invalidate the consolidation.
4. Judge the design by lifecycle continuity: a merged agent is useful when it owns one shared state from intake/creation through campaign, performance and learning, while modules and sensitive gates remain explicit.

## 2. Permission semantics after a merge

Do not infer that internal modules require different user lists. A single agent may intentionally authorize the same people across modules.

- Read the executable authorization registry per user.
- Treat Rodolfo's explicit role correction as authoritative.
- Record whether access is intentionally broad or segmented.
- Keep sensitive gates independent from general agent access: budget, billing, credentials, token/app permissions, pixel/CAPI and out-of-playbook production.
- Do not propose narrowing permissions merely because the architecture has multiple modules.

MGS Ares decision captured in 2026-07: Kelly is also a campaign manager; all authorized Ares users may operate Creative Ops; Geizian operates Creative Ops and Campaign Ops. The registry should state this directly so future audits do not reinterpret it.

## 3. Naming drift in migrated creative data

For legacy `P_ORIENT` values, classify from the real asset, not the old filename:

```text
PV  person, vertical/story
NV  no person, vertical/story
PH  person, square/feed or horizontal
NH  no person, square/feed or horizontal
```

Procedure:

1. Inventory every affected active file read-only.
2. Extract real dimensions and person presence; do not map `NS` mechanically without evidence.
3. Build `old local name → new local name` and `old Drive name → new Drive name` separately because historical local prefixes may differ from current Drive names.
4. Resolve every Drive file by stable ID; GET current name, parent, dimensions and `capabilities.canRename`.
5. Check the target name for sibling collisions before write.
6. Back up local files and the canonical inventory with hashes.
7. Rename Drive objects by ID and validate each with GET. On partial failure, roll back every successful rename before touching local state.
8. Rename local files while verifying content hashes are unchanged.
9. Update only the current canonical inventory. Preserve historical reports/audits with the old name; append a new trace containing both names.
10. Keep migrated assets fail-closed (`ares_eligible=false`) until their independent Meta × Drive reconciliation is complete.
11. Validate no active READY filename or canonical inventory record still uses the legacy code.

If an authorized credential path fails, an alternate authorized identity may be used only after proving the exact file capability and completing per-file readback. Record the failed path and successful fallback without exposing credentials.

## 4. Close documentation debt

After successful consolidation:

- update stale profile descriptions so campaign channel names are not confused with ownership of external systems;
- make the main operational skill the canonical home of guardrails;
- retain old skill names only as thin compatibility redirects when links may still exist;
- mark the migration plan completed instead of leaving a pre-cutover status;
- keep live and versioned SOUL/skills byte-identical;
- regenerate infra inventory, append authorization/data audit events and publish one REPORT-INFRA.

## 5. Completion evidence

Report at minimum:

- source thread inspected;
- module ownership and user-scope decision;
- service/rollback state;
- affected-file count and classification evidence;
- collision count;
- Drive and local rename readback counts;
- inventory before/after and eligibility state;
- mirror comparisons;
- failures/fallbacks;
- REPORT-INFRA message ID.
