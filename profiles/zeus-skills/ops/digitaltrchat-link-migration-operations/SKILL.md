---
name: digitaltrchat-link-migration-operations
description: Use when auditing, piloting, or performing canonical URL migrations across DigitalTRChat Auto Principal Drip, Get Started, No Match, and Persistent Menu, especially when a login contains mixed countries or languages.
version: 1.2.5
tags: [mgs, digitaltrchat, chatpion, url-migration, openzed, messenger]
related_skills: [digitaltrchat-drip-flow-builder, google-drive-agent-automation]
triggers:
  - DigitalTRChat link migration
  - trocar links Auto Drip
  - Openzed country vertical language
  - Get Started No Match Persistent Menu URLs
  - mass URL replacement in ChatPion
---

# DigitalTRChat Link Migration Operations

Perform controlled Page-level URL migrations without changing messages, schedules, topology, locale, button text, or unrelated settings.

For Flow Builder mechanics, also load `digitaltrchat-drip-flow-builder`. This skill governs the migration plan, Page classification, eligibility, canonical catalog, cross-surface consistency, and validation.

## Required supporting material

- `references/openzed-country-vertical-language.md` — canonical Openzed classification, catalog patterns, DTR route details, and the 2026-07-21 pilot discovery.
- `references/batch-manifest-identity-and-readback.md` — reusable batch manifest, Unicode/long-ID identity reconciliation, variable image-click coverage, rollback, and independent readback procedure.
- `scripts/openzed_link_catalog.py` — deterministic catalog generator/validator; run it instead of hand-typing links.

## Non-negotiable model

A DTR login is only a credential/container. It is **not** reliable evidence of a Page's country, vertical, or language. Current URLs and template assignments are legacy state and may already be wrong.

For Openzed, classify every Page from Rodolfo's approved spreadsheet `openzed` (`180vUUBqQOoJM1oHEAj1VBCA-OuLCfAHgz-aRND3cuik`): match the exact row by internal DTR Page ID, cross-check the Facebook Page ID, and select the canonical catalog from the explicit `vertical`, `pais`, and `lingua` fields. A current explicit correction from Rodolfo takes precedence. The catalog defaults to `utm_medium=g003-d`, but an explicit Page/user/gestor mapping from Rodolfo may override it; record that override per Page in the manifest and generate it with `openzed_link_catalog.py --utm-medium`, never by ad-hoc string replacement.

Never use `utm_term` as classification authority. Rodolfo confirmed that it may contain human error inherited from copied/imported flows. Use `utm_term`, domains, login labels, Page names, and assigned template strings only to document legacy discrepancies. Use `utm_content` only to map each existing URL to its semantic position (M0, NM, or M1–M28), not to decide country/language.

If the spreadsheet row is absent, duplicated, ID-mismatched, or internally ambiguous, stop and reconcile instead of guessing. The new canonical Openzed URLs intentionally omit `utm_term`, so the pre-write manifest must preserve the spreadsheet row identity and the legacy before-state separately.

## Migration surfaces

Treat these as one consistency unit while preserving their distinct semantic destinations:

- `Auto Principal Drip`: replace every existing URL according to its current semantic label.
- `Get-started Template`: use canonical M0.
- `No Match Template`: use canonical NM.
- `Persistent Menu`: locale `default`, first-level Web URL item, use canonical M0.

Map existing `utm_content` labels directly:

- suffix `_m0-1` → M0;
- suffix `_nm` → NM;
- suffix `_m1-1`…`_m28-1` → same-number message.

Do not force an existing M0 flow button to NM because an older baseline expected an initial block to equal No Match. The canonical migration model has separate M0 and NM destinations.

For the Openzed canonical migration, do not manually carry `#SUBSCRIBER_ID_REPLACE#` from a legacy URL into the target catalog string; Rodolfo confirmed that preserving it is not a requirement. Enter the exact approved catalog destination. The normal DigitalTRChat Get Started and No Match editors may append `&subscriber_id=#SUBSCRIBER_ID_REPLACE#` automatically on save; accept that platform-enforced suffix when the canonical base matches exactly, but do not add it to Flow Builder or Persistent Menu URLs and do not use a lower-level bypass to fight normal UI behavior. Preserve the literal `#PAGE_ID#` from the canonical catalog and never add any other tracking parameter.

## Eligibility discovery before any write

1. Resolve the exact approved DTR login from 1Password without exposing credentials.
2. Read the approved Page-classification spreadsheet through the canonical MGS Service Account; never fall back to personal Google auth.
3. Match the candidate by internal DTR Page ID and cross-check the exact Facebook Page ID. Derive the target catalog from `vertical + pais + lingua`. If a long Facebook Page ID is rendered in scientific notation, preserve the raw cell and reconcile the exact value from the live DTR Page; never reconstruct or round it. Normalize Page names to Unicode NFC only for comparison so composed/decomposed accents do not create a false mismatch.
4. Apply the spreadsheet status gate: `Blocked` and `On-hold` are no-write; `Ready`, `Campaign`, `Broadcast`, and Restricted Broadcast remain eligible for audit. Do not infer status from the DTR UI alone when the sheet provides it.
5. Enumerate every imported Facebook account and Page in that login. The Page list can be larger than the first Bot Manager card; inspect the selected segurador's complete Social Accounts/Page inventory and switch segurador when needed.
6. Reconcile the global ignore list and any explicit Page exclusions.
7. Read back Page name, Facebook Page ID, and DTR Page ID from the live DTR account.
8. Open `/visual_flow_builder/flowbuilder_manager/<DTR_PAGE_ID>/1` and wait for the asynchronously populated flow table before concluding it is empty.
9. Require exactly one `Auto Principal Drip` row with the yellow `Edit` action and a separate red `Delete` action.
10. If no flow exists, mark the Page ineligible. A URL-replacement request does **not** authorize installing a saved template or creating a flow.
11. Back up the graph, Get Started, No Match, and Persistent Menu values.
12. Inventory existing semantic labels and graph reachability before selecting replacement strings from the already-classified catalog.

### Conditional full-flow qualification

Determine the batch's eligibility mode from Rodolfo's current authorization before writing:

- **Existing-position migration:** a partial legacy flow may be migrated in place; update only its existing semantic positions and preserve its depth.
- **Full-flow-qualified migration:** when Rodolfo says to process only Pages that already have all 28 Drip messages, require one `Auto Principal Drip` plus exactly 28 timed `Sequence Single` branches and semantic coverage through M28. The flow name alone is insufficient. If absent or incomplete, skip the entire Page—including Get Started, No Match and Persistent Menu—and do not install/complete a template.

For the full-flow gate, classify skips precisely as `flow absent` or `incomplete N/28`; do not use total button count as the completeness criterion because M0 and unrelated buttons can inflate it. If Rodolfo preauthorizes “skip ineligible and continue eligible” in the original request, that conditional reduction is already in scope: continue with qualifying Pages without asking again. Otherwise, a discovered reduction still requires the normal scope confirmation.

If fewer Pages are eligible than requested, stop before production writes and obtain authorization for the reduced scope unless the original authorization explicitly preapproved skipping ineligible Pages and continuing with the qualifying subset. Do not silently substitute Pages or expand into template installation.

## Legacy flow boundary

A link migration changes destinations only. If a legacy flow contains M0–M15, update only M0–M15. Never add M16–M28, retime messages, rename postbacks, or alter topology under link-replacement authorization.

The expected post-write URL count must equal the exact pre-write scoped URL count. Do not hardcode the number of `imageClickDestinationLink` fields: copied templates have valid locale/account differences, so inventory and map every existing HTTP image-click destination by semantic label and never create a missing one. Node count, connections, reachability, schedule, messages, button labels/types, and images must remain unchanged.

## Safe execution sequence

1. Run `python3 scripts/openzed_link_catalog.py --validate`.
2. Build a target manifest: login, imported account ID, Page name, DTR/FB IDs, spreadsheet tab/row and `vertical + pais + lingua`, operational status, legacy URL discrepancies, existing semantic labels, chosen catalog, and all four surface routes.
3. Create timestamped backups and hashes before opening a writable state.
4. Re-read live values immediately before mutation; abort on drift.
5. Execute one Page as canary.
6. Update one surface at a time, preserving all non-URL fields:
   - Flow Builder URLs, then one global Save;
   - Get Started URL, then Update;
   - No Match URL, then Update;
   - Persistent Menu first-level default Web URL, then Submit.
7. After each save, reload that surface and read back the exact destination.
8. Open a fresh independent browser session and validate the complete Page.
9. Compare against backup: only scoped URL strings may differ.
10. Continue to remaining Pages only after the canary passes. On mismatch, stop and restore from backup rather than stacking fixes.

## Parser hazard: `#PAGE_ID#`

Python and browser URL parsers treat the first `#` in `#PAGE_ID#` as a fragment delimiter, hiding later query parameters. For validation only, replace the complete placeholder with a sentinel such as `PAGE_ID_PLACEHOLDER`, parse, then verify the original still contains exactly one literal `#PAGE_ID#`. Never percent-encode or modify the production placeholder.

## Completion report

Report:

- requested versus eligible Pages;
- spreadsheet tab/row, DTR/FB identity match, `vertical + pais + lingua`, and operational status per Page;
- legacy `utm_term`/template/domain discrepancies, explicitly labeled non-authoritative;
- pre/post URL counts by surface;
- exact labels migrated;
- graph node/reachability invariants;
- independent readback method;
- Pages skipped and why;
- whether any legacy flow remained M0–M15;
- backup/rollback availability;
- every partial failure without disguising it as success.

Never claim the account was fully migrated when the authorization was only a pilot or when Pages lacked the prerequisite flow.
