# Live reference Page catalog and idempotent recovery

Use this reference when Rodolfo designates one live DTR Page as the source of truth for a different segurador, or when a URL migration needs safe recovery after a UI Save/no-op or a partially completed Page.

## Source-Page approval protocol

1. Resolve the exact source DTR login and imported-account ID; do not infer the container from the target login.
2. Enumerate the source account's Page list live. Treat the first UI row as “newest” and corroborate it with the greatest internal DTR Page ID. If they disagree, stop for clarification.
3. Open Get Started and No Match directly and require `page_table_id == DTR Page ID` plus `page_id == Facebook Page ID`.
4. Open the exact `Auto Principal Drip` yellow Edit route and parse `window.data`.
5. Extract every business URL occurrence from Button values and Generic Template `imageClickDestinationLink`; map labels without using node IDs or canvas order.
6. Validate node reachability, label coverage, host/path, tracking parameters and literal placeholders.
7. Show Rodolfo the exact Get Started, No Match and AutoDrip catalog. Make explicit that this phase is read-only.
8. Freeze the source Page identity, observation time, catalog and hashes only after Rodolfo approves it. His approval authorizes only the named target population and surfaces.

## Surface-scope rule

Persistent Menu is part of the default full migration unit, but an explicitly confirmed narrower list wins. If Rodolfo confirms only AutoDrip, Get Started and No Match, do not mutate Persistent Menu. Record it as `out_of_scope_unchanged`; never claim it was backed up or validated unless it actually was.

## Resumable qualification

For a large read-only preflight, write each Page's flow backup, action-state backup and manifest atomically as soon as that Page qualifies. On interruption:

- re-enumerate the exact live imported account;
- require the same ordered, deduplicated DTR/FB Page identity set;
- load only manifests marked qualified whose Page identity and files read back;
- process only missing Pages;
- rebuild and validate the complete disposition summary before any production write.

A partial qualification is not authorization to start a partial batch.

## Action-editor comparison

Compare business controls by stable `id`/`name`, not array index. Normalize away visibility and DOM ordering only after proving every baseline business control is still present with the same tag/type/value/checked/disabled state, except the explicitly authorized URL. A textarea may toggle hidden while retaining its exact value; index-based comparisons misclassify that as content drift.

## Flow Save outcome classification

After changing only authorized URL fields in the Rete graph:

1. Save once through the validated UI route.
2. Reload immediately and compare the full graph with the frozen before graph and prepared target graph.
3. Classify the result:
   - `target`: continue to independent readback;
   - `before`: the UI Save was a proven no-op;
   - `mixed/unknown`: stop, do not replay.
4. Only for exact `before`, revalidate `window.xitFlowBuilderData.page_table_id`, builder identity, prepared graph hash, topology and allowed field diff. Then one direct canonical POST to `visual_flow_builder/flowbuilder_submit` may be used with the same prepared graph.
5. Reload again and require exact target fields plus normalized non-URL graph equality.

Do not infer persistence from a click, toast, HTTP response or missing response alone. Readback is authoritative.

## Partial-state recovery

Before recovery, independently classify each surface as exactly `before`, `target`, or `third value`:

- `before`: eligible for the missing authorized write;
- `target`: do not resubmit;
- `third value`: live drift; stop.

Write only missing surfaces. If a rollback request reports an error, read back the actual graph and action editors before deciding whether rollback succeeded. Preserve each failed attempt under a distinct artifact name, then keep the final independent readback separately.

## Validated boundary

This pattern was exercised on a multi-Page existing-position migration where every target flow had M0–M15. The successful path preserved the 82-node/81-edge topology, changed only existing URL occurrences, recovered one known partial Page idempotently, recovered one UI Save no-op after a complete readback-confirmed rollback, and finished with a fresh independent readback for every Page. Do not generalize the observed node or URL counts; inventory them per batch.
