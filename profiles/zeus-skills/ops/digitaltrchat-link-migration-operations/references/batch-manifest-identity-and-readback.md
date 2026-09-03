# Batch manifests, identity reconciliation, and readback

Use this reference for multi-Page URL migrations after the Page list and canonical catalog have been authorized.

## 1. Freeze the current source state

1. Re-read the approved spreadsheet after any user-reported correction; never reuse an earlier local snapshot.
2. Preserve the raw spreadsheet values in `sheet-scope.json`.
3. Build a separate `identity-scope.json` that records:
   - DTR Page ID;
   - raw spreadsheet Facebook Page ID;
   - exact live DTR Facebook Page ID;
   - Page name;
   - imported-account/segurador ID;
   - spreadsheet classification;
   - requested classification and its authority;
   - any reconciliation performed.
4. A new explicit classification correction from Rodolfo wins an older spreadsheet value. Preserve the discrepancy, use the correction only for the authorized scope, and capture the stale spreadsheet value for canonical reconciliation; do not silently edit the spreadsheet.

## 2. Reconcile identity safely

- Use internal DTR Page ID as the primary key and require an exact live Facebook Page ID before writing.
- Parse the selected Page/sidebar identity as distinct fields; do not rely on loose substring matching that can collide with another ID.
- Spreadsheet software may render long Facebook Page IDs in scientific notation and destroy their textual precision. Never convert that display back to an integer or guess the missing digits. Preserve the raw cell, obtain the exact ID from the live DTR Page, cross-check Page name plus DTR Page ID, and mark the manifest identity source as `live_dtr_reconciled_sheet_format_loss`.
- Normalize Page names to Unicode NFC only for comparison. Preserve the original strings in backups and never rewrite the live Page name because composed and decomposed accents compare differently byte-for-byte.
- If DTR ID, Page name, and exact live Facebook Page ID cannot be reconciled unambiguously, skip only that Page.

## 3. Select the real imported account

Enumerate every `a.account_switch[data-id]`, switch with `/social_accounts/fb_rx_account_switch`, reload Bot Manager, and map each Page to its imported-account ID. Deduplicate repeated desktop/mobile DOM entries by `(account_id, normalized_name)`, not by display name alone: DTR can contain two distinct imported-account IDs with the same segurador name. A Page absent from that inventory may be disconnected rather than nonexistent. Do not connect it or install a template under URL-migration authorization.

Resolve action settings and Flow Builder independently when duplicate account names exist:

- **Action account:** the Bot Manager Page list must contain exactly one row whose DTR Page ID, Facebook Page ID, and normalized Page name all match the authorized Page.
- **Flow account:** probe every same-name account for the exact `Auto Principal Drip` edit row. Collapse repeated visibility of one logical flow by `(edit_href, graph_hash)`; two account hits with the same pair are one flow, while different edit records or hashes are a real ambiguity.
- The action-account ID and flow-account ID may differ in a legacy duplicate-account layout. That alone is not an identity conflict when the Page IDs, direct editor identities, edit URL, and graph hash reconcile. Never choose an account merely because its display name is unique or appears first.

Bot Manager action links are hydrated asynchronously and may be hidden inside collapsed panels. Select the exact `li.page_list_item`, wait for `/messenger_bot/get_page_details`, then extract the direct `/messenger_bot/edit_bot/<id>/1/getstart` and `/nomatch` routes. A hidden edit anchor is not evidence that the editor is absent. Stale anchors from the previously selected Page can survive briefly: open each direct route read-only and require hidden `page_table_id == DTR Page ID` plus `page_id == Facebook Page ID`; on mismatch, reload/reselect and retry before classifying the Page. Never save through a stale editor identity.

For large batches, preserve the exact authorized Page list as an ordered, deduplicated target artifact before discovery. Reuse one authenticated browser context per DTR login/imported account for **read-only** account mapping and qualification, but preserve Page-level manifests and independent post-write contexts. Read-only session reuse reduces login/UI overhead; it must not weaken Page identity checks, pre-write drift checks, rollback isolation, or readback independence.

Persist each fully qualified Page manifest immediately, before moving to the next Page. If the foreground qualification is interrupted or times out, resume only from manifests whose Page identity, status and hashes read back exactly; re-enumerate the live target inventory and process only the missing Pages. Do not open production writes until the resumed qualification again yields a complete, disjoint partition of the requested set.

Before any production write, build a disjoint disposition partition whose union equals the exact requested set. Typical buckets are `qualified`, `incomplete N/28`, `flow absent`, `ignore-list`, `blocked/on-hold`, `disconnected/not listed live`, and `identity conflict`. Fail closed if a Page appears in more than one bucket or the bucket totals do not exhaust the requested list.

## 4. Qualify the flow from structure

For a full-flow-qualified batch, require:

- exactly one `Auto Principal Drip`;
- 28 timed `Sequence Single` branches;
- semantic URL coverage M0 through M28;
- a fully reachable graph.

Treat current tracking labels as evidence, not infallible structure. A copied legacy flow can have a structurally valid initial M0 CTA whose URL is incorrectly labeled as NM. If M1–M28 are complete and exactly one initial HTTP CTA remains, derive M0 from its graph position between `Start Bot Flow` and the first timed sequence, record that inference in the manifest, and replace it with canonical M0. Never infer M0 from a hardcoded node ID across templates and never use the bad NM URL to reclassify the Page.

Do not hardcode Generic Template image-click counts. Valid copied templates have differed by locale/account (for example, 14 versus 15 `imageClickDestinationLink` values). Inventory every existing HTTP button and image-click URL, map each by `utm_content`, and require post-write URL count to equal the exact pre-write scoped count. Never create a missing image-click destination.

## 5. Manifest and backup contract

Create one directory per Page containing:

- raw flow and sanitized summary;
- Get Started/No Match controls;
- Persistent Menu controls;
- a manifest with every `node_id + field + semantic label + before + after` replacement;
- source and classification authority;
- hashes of all before artifacts;
- rollback material.

Validate the generated catalog before the first write. Confirm the approved host/path, `utm_medium`, `utm_content`, literal `#PAGE_ID#`, absence of `utm_term`, and absence of manually inserted subscriber suffixes.

## 6. Apply sequentially

1. Re-read live identity and current URL values; abort that Page on drift.
2. Apply Flow Builder URL fields and save once.
3. Apply Get Started M0, No Match NM, and the first default Persistent Menu Web URL as M0.
4. Accept only the platform-added `&subscriber_id=#SUBSCRIBER_ID_REPLACE#` on Get Started/No Match; never inject it into the catalog, Flow Builder, or Persistent Menu.
5. Reload every surface before continuing.
6. Stop the batch on an unrolled-back mismatch; do not stack repairs across Pages.

A Flow Builder Save can occasionally be a no-op even though the editor accepted the in-memory change. After Save, reload and classify the graph as exactly one of: `before`, `target`, or `mixed/unknown`. If it is `target`, accept only after normal independent readback. If it is exactly `before`, no partial side effect occurred: revalidate `xitFlowBuilderData.page_table_id`, the prepared graph hash and the allowed field diff, then a single canonical `flowbuilder_submit` fallback may be used. If it is mixed/unknown, stop and restore or escalate; never replay blindly. Preserve failed attempts and recovery evidence instead of overwriting them.

For a known partial Page, recovery must be idempotent: accept each surface only when it equals either the frozen before value or the approved target, write only the missing surfaces, and reject any third value as live drift. A rollback response failure is not proof of rollback failure or success; read back every surface and reconcile the actual state before the next action.

## 7. Independent verification

Open a fresh browser context and collect new after-state files. Verification must prove:

- every manifest replacement equals its target;
- all non-URL graph fields equal the before graph;
- node count, reachability, sequence delays, messages, images, buttons, and connections are unchanged;
- Get Started/No Match differ only by the canonical destination plus an allowed platform suffix;
- Persistent Menu equals M0 exactly without the suffix;
- host/path, medium, content labels, and placeholders are correct;
- total verified URLs equal the manifest count.

When comparing HTML control inventories across independent browser sessions, normalize away runtime-only UI artifacts: generated `ajax-upload-id-*` fields, anonymous modal/search controls, selector option-text ordering, visibility, and hydrated display text. Compare stable business fields (`tag`, stable `id`/`name`, `type`, `value`, `checked`, `disabled`) and the authorized URL fields separately. Key controls by stable `id`/`name`, never by DOM/list position: a business textarea can remain present with the same value while toggling from visible to hidden, shifting every later field index and creating a false mismatch. Require the baseline business IDs and values to remain present; ignore visibility/order only after that keyed comparison succeeds. In particular, classic action editors can hydrate hidden inactive controls whose `name` contains `post_id_` with the first dynamically ordered option; after proving the active button type is still `web_url`, exclude those inactive selector values from equality checks. Do not generalize that exclusion to active selectors or other business fields. Do not treat browser-generated IDs or hydration order as production drift.

For URL parsing, temporarily replace the complete `#PAGE_ID#` token with a sentinel before parsing because `#` starts a fragment. Verify the original production string still contains the literal token.

## 8. Report

Report requested, eligible, actually changed, already canonical, skipped, exact skip reasons, URL counts by surface, structural invariants, readback result, classification/identity reconciliations, backup path, and rollback count. Keep these counts distinct:

- **eligible/final-valid** — all Pages that passed qualification and final readback;
- **actually changed** — Pages and URL occurrences whose before/after values differ;
- **already canonical** — qualified Pages that required zero writes but were independently validated;
- **skipped** — a disjoint, exhaustive breakdown whose total reconciles to the requested list.

For a large list, provide the exact changed Page IDs and exact IDs for exceptional skip buckets such as absent, ignored, disconnected, or identity conflict. A large homogeneous remainder such as `incomplete 15/28` may be summarized by count when the original requested list plus the explicit changed/exception lists makes the remainder unambiguous; preserve the full machine-readable disposition artifact in the backup.

Distinguish user-reported manual work from changes Zeus actually verified or executed. Never inflate a zero-diff validation into a write, and never report the final canonical URL count as though every occurrence changed in the current run.
