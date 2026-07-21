---
name: digitaltrchat-link-migration-operations
description: Use when auditing, piloting, or performing canonical URL migrations across DigitalTRChat Auto Principal Drip, Get Started, No Match, and Persistent Menu, especially when a login contains mixed countries or languages.
version: 1.0.0
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
- `scripts/openzed_link_catalog.py` — deterministic catalog generator/validator; run it instead of hand-typing links.

## Non-negotiable model

A DTR login is only a credential/container. It is **not** reliable evidence of a Page's country, vertical, or language. Classify every Page independently from a live pre-write URL.

Primary evidence is `utm_term`; corroborate with `utm_content`. Mixed EN/ES and mixed countries inside one login are expected. If the signals conflict or are missing, stop instead of guessing from the login email, Page name, or hostname alone.

The new canonical Openzed URLs intentionally omit `utm_term`. Capture the classification and evidence before replacement because that signal will not exist afterward.

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

If a template field already contains `#SUBSCRIBER_ID_REPLACE#`, preserve it unless Rodolfo explicitly authorizes removal. Preserve literal `#PAGE_ID#` exactly. Never infer or invent tracking parameters absent from both the approved catalog and the existing field.

## Eligibility discovery before any write

1. Resolve the exact approved DTR login from 1Password without exposing credentials.
2. Enumerate every imported Facebook account and Page in that login.
3. Reconcile the global ignore list and any explicit Page exclusions.
4. Read back Page name, Facebook Page ID, and DTR Page ID.
5. Open `/visual_flow_builder/flowbuilder_manager/<DTR_PAGE_ID>/1`.
6. Require exactly one `Auto Principal Drip` row with the yellow `Edit` action and a separate red `Delete` action.
7. If no flow exists, mark the Page ineligible. A URL-replacement request does **not** authorize installing a saved template or creating a flow.
8. Back up the graph, Get Started, No Match, and Persistent Menu values.
9. Inventory existing labels and graph reachability before selecting a catalog.

If fewer Pages are eligible than requested, stop before production writes and obtain authorization for the reduced scope. Do not silently substitute Pages or expand into template installation.

## Legacy flow boundary

A link migration changes destinations only. If a legacy flow contains M0–M15, update only M0–M15. Never add M16–M28, retime messages, rename postbacks, or alter topology under link-replacement authorization.

The expected post-write URL count must equal the pre-write scoped URL count. Node count, connections, reachability, schedule, messages, button labels/types, and images must remain unchanged.

## Safe execution sequence

1. Run `python3 scripts/openzed_link_catalog.py --validate`.
2. Build a target manifest: login, imported account ID, Page name, DTR/FB IDs, classification evidence, existing labels, chosen catalog, and all four surface routes.
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
- classification and evidence per Page;
- pre/post URL counts by surface;
- exact labels migrated;
- graph node/reachability invariants;
- independent readback method;
- Pages skipped and why;
- whether any legacy flow remained M0–M15;
- backup/rollback availability;
- every partial failure without disguising it as success.

Never claim the account was fully migrated when the authorization was only a pilot or when Pages lacked the prerequisite flow.
