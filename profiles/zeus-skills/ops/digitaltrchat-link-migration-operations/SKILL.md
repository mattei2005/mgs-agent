---
name: digitaltrchat-link-migration-operations
description: Use when auditing DTR Page inventory or Auto Principal Drip installation, reconciling DTR with Smart Bidding from a Sheet, performing canonical URL migrations, or remediating an incomplete flow with an explicitly authorized Saved Template.
version: 1.7.4
tags: [mgs, digitaltrchat, chatpion, url-migration, openzed, messenger]
related_skills: [digitaltrchat-drip-flow-builder, google-drive-agent-automation]
triggers:
  - DigitalTRChat link migration
  - trocar links Auto Drip
  - Openzed country vertical language
  - Get Started No Match Persistent Menu URLs
  - mass URL replacement in ChatPion
  - install approved Saved Template after incomplete Drip audit
  - install template by Page ID and segurador
  - reconcile DTR Page IDs with Smart Bidding from a Sheet
  - audit whether Auto Principal Drip is installed per Page
  - connect an exact disconnected DTR Page batch before Auto Scan
  - trigger or retrigger Subscriber Manager Auto Scan for an exact Page batch
---

# DigitalTRChat Link Migration Operations

Perform controlled Page-level URL migrations without changing messages, schedules, topology, locale, button text, or unrelated settings.

For Flow Builder mechanics, also load `digitaltrchat-drip-flow-builder`. This skill governs the migration plan, Page classification, eligibility, canonical catalog, cross-surface consistency, and validation.

## Required supporting material

- `references/openzed-country-vertical-language.md` — canonical Openzed classification, catalog patterns, DTR route details, the approved legacy Keitaro `card.`/`tarjeta.` → Smart Routing mapping, and the 2026-07-21 pilot discovery.
- `references/batch-manifest-identity-and-readback.md` — reusable batch manifest, Unicode/long-ID identity reconciliation, variable image-click coverage, rollback, and independent readback procedure.
- `references/saved-template-installation-after-incomplete-flow-audit.md` — authorized remediation path when an incomplete/absent Drip must be replaced by an approved Saved Template; includes complete per-login template inventory, actual-login partitioning, blocker rechecks, exact ignore-list identity matching, disconnected-Page handling, resumable backups, login-safe concurrency, canary/readback, Openzed 21/07 EN/ES signatures, and column-I completion rules.
- `references/utm-medium-only-migration-and-exact-login-resolution.md` — validated narrow migration for changing only `utm_medium` across Get Started and existing Drip URLs, including exact-login discovery when a newly added generic-title 1Password item is absent from the resolver map, dynamic occurrence counts, normalized graph hashing, rollback, and fresh-session readback.
- `references/live-reference-page-catalog-and-idempotent-recovery.md` — live source-Page approval gate, resumable qualification, action-editor normalization, and safe recovery when a Flow Builder Save is a no-op or a Page ends in a known partial state.
- `references/multi-login-large-batch-existing-position-migration.md` — validated large-batch pattern for complete preflight, one canary per catalog family, action-only Pages, transaction-safe interruption recovery, second-pass readback, and honest occurrence accounting.
- `references/all-account-url-variance-audit.md` — read-only enumeration of every imported account/Page across exact logins, identity-safe action-route hydration, resumable collection, exact URL signatures, and disjoint missing/variance reporting.
- `references/sheet-driven-dtr-sb-reconciliation.md` — phased Sheet/1Password preflight, exact login+Segurador traversal, DTR Auto Principal Drip presence classification, full-scope SB ID reconciliation, webhook connection canary and stale Meta Page-access diagnosis, exact-batch Subscriber Manager Auto Scan triggering, and report-Sheet contract.
- `scripts/openzed_link_catalog.py` — deterministic catalog generator/validator; run it instead of hand-typing links.
- `scripts/diagnose_dtr_page_access.py` — sanitized Graph gate for a frozen disconnected-Page manifest after a DTR webhook reports an application error or an operator reports manual reconnection; it verifies the current app, account-token binding, exact `/me/accounts` visibility, Page-token binding, and `subscribed_apps` without persisting secrets.

## Non-negotiable model

A DTR login is only a credential/container. It is **not** reliable evidence of a Page's country, vertical, or language. Current URLs and template assignments are legacy state and may already be wrong.

When Rodolfo asks whether a template is installed **on a DTR Page**, interpret that as presence of exactly one fully hydrated `Auto Principal Drip` row in that Page's DTR Flow Builder. Never answer that question from Smart Bidding's `BROADCAST_TEMPLATE_ID`/`BROADCAST_TEMPLATE_NAME`: those fields describe a separate SB Broadcast Template surface. Require full Flow Builder pagination before calling the template absent, and keep `no flow`, `other flow`, `duplicate Auto Principal Drip`, and `disconnected Page` as separate outcomes.

For Sheet-driven DTR↔SB inventories, run credential closure as an explicit first phase: read the exact tab through the canonical Service Account, preserve every row occurrence, resolve each unique `User` to a password-bearing 1Password item, and stop with the exact missing/incomplete identities when that is the authorized phase boundary. A duplicate username with different passwords must be resolved by isolated live-login probes; never choose a credential from title similarity or expose password values/hashes. An app-scoped audit is complete only when every selected Sheet Segurador resolves to exactly one DTR account: if any account is missing or ambiguous, label Page totals as **observed in resolved accounts**, report the Sheet-declared unobserved scope separately, and never present the result as the complete app population. Follow `references/sheet-driven-dtr-sb-reconciliation.md`.

For every DTR↔SB Page reconciliation, treat the exact global Facebook `FB_PAGE_ID` as the immutable identity. Build the SB denominator from the live `Accounts > Messenger > Page` site multiselect with **all current sites under both `Digital trust` and `Digital trust 2`**; when `/company` omits a site exposed by the UI, the captured UI Page request wins. Never classify a Page as absent from SB from a company-derived subset. Only after one unique large-ID match may the workflow compare or repair the mutable small `PAGE_ID`, `UTM_CAMPAIGN`, name, login, profile, status, or connection state.

When Rodolfo asks for a full rescan “from zero” or says not to ignore `On-hold`/`Blocked`, rebuild the population from fresh Sheet, DTR and full-scope SB reads instead of reusing a prior problem list or saved dataset as the denominator. Backups and resumable journals remain mandatory safety evidence, but they are not population authority. Audit every current status: `On-hold` and `Blocked` are workflow states, not proof that a Facebook Page is currently down. A status-level instruction to include those rows in the audit does **not** silently remove a canonical global-ignore entry; inspect ignored Pages for recovery when requested, but require an exact explicit override/removal before connecting, scanning, registering or scheduling one.

For every disconnected Page in such a rescan, first run the exact current-app `/me/accounts` gate. A visible exact large ID is an online connection candidate; an absent ID requires the AdsPower `facebook.com/<FB_PAGE_ID>` liveness check. An explicit unavailable-content result is a down/blocked disposition, while a Page that opens but remains absent from `/me/accounts` is an access/tasks blocker—not a connection candidate. After any successful connection, refresh the DTR inventory before comparing or repairing the mutable small ID.

For a named Segurador batch spanning multiple app generations, resolve every name against the current active Sheet before building one cross-app manifest, then join each DTR Page to SB by exact `FB_PAGE_ID` and compare the effective SB login (`USER_LOGIN`, falling back to `LOGIN`) with the current Sheet/DTR login. Unless Rodolfo has established which source is authoritative, login drift remains an identity/structure blocker. When Rodolfo explicitly declares the current Sheet logins correct, log into DTR with those exact Sheet credentials and treat a mismatching SB login as stale metadata: preserve `LOGIN`/`USER_LOGIN`, Page name, and every unrelated SB field while changing only the authorized `PAGE_ID + UTM_CAMPAIGN`. A unique exact `FB_PAGE_ID` proves the Page for this narrow repair; Page-name drift is then a preserved diagnostic, not permission to rename the SB row. Stop instead when the large ID is absent/duplicated, the Sheet/DTR account is unresolved, or identity depends only on a name/small ID. A requested name that exists only as a historical removed/Blocked Page is zero current operational scope, not a near-match insurer. Follow the named cross-app procedure in `references/sheet-driven-dtr-sb-reconciliation.md`.

The Smart Bidding direct campaign read endpoint may omit `LOGIN`/`USER_LOGIN` even when the list endpoint exposes an effective login derived from the Messenger user. Never classify the blank direct-read field as owner drift and never make direct-item login equality a write-success gate. Freeze `MESSENGER_USER_ID` plus the effective list login before mutation, verify the immutable Messenger user ID and all unrelated editable fields after mutation, and validate the final effective login from a fresh list read. If the list login normalizes to the explicit authoritative Sheet/DTR login while `MESSENGER_USER_ID` remains unchanged, record it as derived metadata normalization rather than an ownership mutation.

For an exact disconnected-Page connection batch, require one live webhook canary per imported account before the remaining writes and a fresh all-connected gate before Auto Scan. Treat HTTP 200 with application `status=0` as failure, stop that account's batch, and use the Meta app/account/Page-token decision tree in `references/sheet-driven-dtr-sb-reconciliation.md`; never continue with only the reachable subset unless Rodolfo explicitly authorizes that reduced population. Before calling the current Meta app deleted, reconcile the exact current generation/app ID against fresh canonical monitor evidence and a direct Graph check: a healthy current app plus DTR's `Application has been deleted` response points to the DTR account's stale application/OAuth binding until token diagnostics prove otherwise. Replacing or reconnecting that binding changes credentials/tokens, so Page-connect authorization does not cover it; obtain the Critical Subset confirmation before the OAuth repair. When a follow-up refers to a previously disclosed cohort with pronouns—such as “fix the Page IDs, connect them and run Auto Scan”—bind the writes to that frozen mismatch cohort, not to every disconnected Page in the app. Keep correct-ID disconnected Pages and unresolved insurer scope outside the target set unless Rodolfo names them separately. A current direct statement that a Page is `Blocked` is a canonical exclusion decision: add or update its exact `FB_PAGE_ID` in the global ignore list, validate one unique readback entry, and rebuild the requested/eligible/excluded denominator before any retry. If Rodolfo also asks for Smart Bidding parity, require one unique SB row by exact `FB_PAGE_ID`, back up the full editable row, write only `STATUS=Blocked`, and prove every other editable field unchanged in fresh readback before updating the ignore list. Named Blocked Pages are an explicit scope reduction: after rebuilding the exact denominator, continue the remaining eligible Pages under the original connect/Auto Scan authorization instead of asking again or processing any blocked Page.

When Rodolfo explicitly authorizes a best-effort batch and says to skip isolated problems without stopping, quarantine each failure at the narrowest safe unit—Page first, imported account only when account switching fails, login only when authentication fails—and continue every independent eligible unit. Retry and read back each failed Page once before classifying it unresolved. Do not use best-effort authorization to expand into OAuth/token repair, Smart Bidding row creation, Page renaming, Blocked/global-ignore override, or any other separate scope; report the exact skipped identity and diagnosed blocker after the remaining batch finishes.

When Rodolfo asks to connect and scan **every Page in an already-disclosed problem list**, that frozen list is the execution denominator—not only Pages changed, newly connected, or represented in the current SB repair plan. Reapply the current global-ignore list, revalidate each exact DTR identity and connection, then submit Auto Scan once for every connected member, including Pages already connected, previously scanned, or missing from Smart Bidding. Under explicit best-effort authorization, refresh the Graph access gate for disconnected Pages, skip exact IDs still absent from `/me/accounts`, and continue the connected remainder; never replay a deterministic webhook failure merely to make the attempt count look complete.

For Openzed, classify every Page from Rodolfo's approved spreadsheet `openzed` (`180vUUBqQOoJM1oHEAj1VBCA-OuLCfAHgz-aRND3cuik`): match the exact row by internal DTR Page ID, cross-check the Facebook Page ID, and select the canonical catalog from the explicit `vertical`, `pais`, and `lingua` fields. A current explicit correction from Rodolfo takes precedence. The catalog defaults to `utm_medium=g003-d`, but an explicit Page/user/gestor mapping from Rodolfo may override it; record that override per Page in the manifest and generate it with `openzed_link_catalog.py --utm-medium`, never by ad-hoc string replacement.

Never use `utm_term` as classification authority. Rodolfo confirmed that it may contain human error inherited from copied/imported flows. Use `utm_term`, domains, login labels, Page names, and assigned template strings only to document legacy discrepancies. Use `utm_content` only to map each existing URL to its semantic position (M0, NM, or M1–M28), not to decide country/language.

**Explicit legacy-route exception:** for the exact audited Openzed/Wavesbee Keitaro families approved by Rodolfo, `card.` identifies `US-CC-EN` and selects the full `sr.openzed.com` catalog, while `tarjeta.` identifies `US-CC-ES` and selects the full `srf.openzed.com` catalog. These old routes are classification markers, not working Smart Routing destinations. Follow `references/openzed-country-vertical-language.md`; replace the complete semantic catalog rather than swapping only the hostname, and do not generalize the exception to other populations or hosts.

## Zuout legacy URLs → Smart Routing classification

For the Zuout DTR migration authorized by Rodolfo, every family marker is read from the exact **Get Started** URL—not from Auto Principal Drip:

- `card.zuout.com/MG2yq6t3` → `US-CC-EN`;
- `card.zuout.com/V1R6LXHz` → `GB-CC-EN`;
- `tarjeta.zuout.com/yfH8xtHt` → `US-CC-ES` on `finanzas.zuout.com`.

Use Sheet `1blCvjbHqU8SxFhP7B-77YLy9-wJ3rieJbYYSmkVrRwM` as the direct source catalog: gid `794022544` for US-CC-EN, gid `1111511336` for GB-CC-EN, and gid `1670618379` for US-CC-ES. Column A is the semantic position and column D is the legacy short path. Do not classify from the Auto Drip M0 URL and do not infer a family merely from the host.

The US catalogs intentionally reuse short path codes after M15, so a short code alone is not a unique message key. Resolve each live occurrence by `utm_content` (`m0`, `nm`, `m1`–`m28`), then cross-check that semantic position against the exact column-D path before replacing only the host/path with the corresponding route: `zu-us-cc-en-drip-*`, `zu-gb-cc-en-drip-*`, or `finanzas.zuout.com/zu-f-us-cc-es-drip-*`. Preserve every tracking parameter, literal placeholder, duplicate occurrence, message, schedule, topology and non-URL field. Get Started/No Match may retain the DTR-appended subscriber suffix after normal UI save. If Get Started is not one of the exact markers, or any legacy occurrence conflicts with the selected catalog, fail closed instead of guessing.

If the spreadsheet row is absent, duplicated, ID-mismatched, or internally ambiguous, stop and reconcile instead of guessing. The new canonical Openzed URLs intentionally omit `utm_term`, so the pre-write manifest must preserve the spreadsheet row identity and the legacy before-state separately.

## Live DTR reference-Page approval gate

When Rodolfo explicitly names a source segurador and asks Zeus to use its newest Page as the destination reference, use a two-stage gate instead of treating the first instruction as write authorization:

1. resolve and activate the exact source login/imported account;
2. identify the newest Page as the first Page in the live DTR list and corroborate it with the greatest internal DTR Page ID when possible; stop on disagreement rather than guessing;
3. read Get Started, No Match and every existing Auto Principal Drip URL without saving;
4. verify source Page identity, full graph reachability, semantic labels, URL occurrences and literal placeholders;
5. send the exact observed catalog to Rodolfo and explicitly state that no target Page has been changed;
6. wait for Rodolfo to approve that catalog; only that later approval authorizes the named target batch;
7. freeze source account/Page IDs, observation time, catalog and hashes in the batch manifest.

A Rodolfo-approved live reference Page is destination authority only for the exact named migration scope. Record it as an explicit override when it conflicts with legacy login labels, current target URLs or spreadsheet classification; do not silently promote it to a global catalog.

## Migration surfaces

The default complete consistency unit is:

- `Auto Principal Drip`: replace every existing URL according to its current semantic label.
- `Get-started Template`: use canonical M0.
- `No Match Template`: use canonical NM.
- `Persistent Menu`: locale `default`, first-level Web URL item, use canonical M0.

If Rodolfo explicitly enumerates and confirms a narrower surface subset, that exact subset is authoritative. Do not expand it to Persistent Menu or another omitted surface. Record every omitted surface as `out_of_scope_unchanged`, and never imply it was backed up, migrated or validated when it was not.

Within whichever surface set is authorized, preserve each destination's distinct semantic role.

Map canonical `utm_content` labels directly:

- suffix `_m0-1` → M0;
- suffix `_nm` → NM;
- suffix `_m1-1`…`_m28-1` → same-number message.

Legacy copied flows may omit the `m` in numbered query labels (`..._1-1`…`..._28-1`) while the destination path still contains `/...-drip-mN-1/`. Accept that legacy form only when the numeric suffix and path number agree; record both signals in the manifest. A path/query number conflict is a structural divergence and makes the Page ineligible. Treat M0 and NM as recognized out-of-scope business URLs when the current authorization covers only M1–M28; do not misclassify them as unmapped HTTP noise.

Do not force an existing M0 flow button to NM because an older baseline expected an initial block to equal No Match. The canonical migration model has separate M0 and NM destinations.

For the Openzed canonical migration, do not manually carry `#SUBSCRIBER_ID_REPLACE#` from a legacy URL into the target catalog string; Rodolfo confirmed that preserving it is not a requirement. Enter the exact approved catalog destination. The normal DigitalTRChat Get Started and No Match editors may append `&subscriber_id=#SUBSCRIBER_ID_REPLACE#` automatically on save; accept that platform-enforced suffix when the canonical base matches exactly, but do not add it to Flow Builder or Persistent Menu URLs and do not use a lower-level bypass to fight normal UI behavior. Preserve the literal `#PAGE_ID#` from the canonical catalog and never add any other tracking parameter.

## Manager/owner reassignment coupling

When Rodolfo changes a site's responsible manager/medium rather than asking for an isolated URL edit, treat the request as one cross-system attribution transaction:

1. Freeze the exact named domains, old manager tag, new manager tag/person, SB template IDs and live Page population before writing.
2. Migrate every existing authorized DTR occurrence across the approved status partitions without creating missing surfaces. Count old values dynamically; an explicit instruction to make **every current medium** the new value authorizes mixed legacy values, but still preserves every other URL byte.
3. Update every URL-bearing field in the matching SB Broadcast Template messages. If the template display name embeds the old medium/person, renaming `NAME` is a separate metadata write: obtain explicit scope, back up the full row, change only `NAME`, require the normalized full-row hash with `NAME` replaced by a sentinel to remain equal, and verify the messages and media are unchanged in a fresh session.
4. Update `data/finance-gam-revenue-rules.json → site_owner_manager` for every named domain variant so missing/invalid future media fall back to the new owner. Supersede the active `finance.revenue.gam.manager-attribution` knowledge-registry record rather than leaving two active decisions.
5. Run the finance mapping tests, knowledge validation/regression, inventory and REPORT-INFRA closure required by the data changes. Keep dashboard backups and canonical-data rollback material separate.

A successful DTR/SB write is not completion when the canonical finance owner still points to the old manager; conversely, do not rewrite historical closed reporting periods unless Rodolfo explicitly scopes that separate financial restatement.

## Read-only all-account URL variance audits

When Rodolfo gives exact DTR logins and asks whether URLs differ, enumerate every imported account and Page before comparing. Build exact per-surface and combined URL signatures, but keep `flow absent`, `action settings absent`, identity conflict, zero-Page account and zero-account login outside the variance bucket. Do not call a minority signature wrong without an approved destination authority.

Action links are asynchronously hydrated and can remain stale from the previous Page even after a successful click. Every collected Get Started/No Match route must pass direct-editor DTR Page ID and Facebook Page ID readback. Persist results per completed account so long foreground scans can resume safely. Follow `references/all-account-url-variance-audit.md` for the full collection, signature and reporting contract.

## SB-template-driven cross-login scope

When Rodolfo defines a DTR migration population by the template installed in **SB → Accounts → Messenger → Page**, treat live SB Page rows as the population source instead of assuming one DTR login or one spreadsheet login list.

1. Query the live `/campaigns/Messenger` dataset across every authorized active publisher in scope.
2. Match the requested `BROADCAST_TEMPLATE_NAME` exactly after trimming outer whitespace; do not merge similarly named country/language variants.
3. Before exclusions, reconcile the baseline count against distinct `ID`, `PAGE_ID`, and `FB_PAGE_ID`. Report duplicate or blank identifiers instead of treating duplicated rows as separate Pages.
4. Produce a full status partition, including `On-hold`, so Rodolfo can compare the live total with his dashboard view before production work starts.
5. Apply execution gates only after baseline reconciliation. `On-hold` is no-write by default; a current explicit authorization that names the On-hold partition may enable a medium/link-only migration while preserving status, schedule and all non-URL fields. `Blocked` remains no-write, and global-ignore records remain no-scan, unless the canonical block/ignore decision is removed or explicitly overridden for that exact Page identity. `Ready`, `Campaign`, `Broadcast`, and Restricted Broadcast remain eligible for audit.
6. Resolve every distinct `LOGIN`/`USER_LOGIN` represented by eligible rows and operate all corresponding DTR containers. A login requested as an example is not the batch boundary when live SB identifies additional logins.
7. Reconcile each SB row to the live DTR Page using DTR Page ID plus Facebook Page ID before editing. Blank login, missing Page, identity mismatch, or duplicate identity is a stop/reconciliation condition.
8. Keep population authority separate from destination authority: SB template membership identifies candidate Pages, while Rodolfo's current explicit URL catalog or the applicable approved classification source determines target URLs.
9. Under a link-replacement authorization, interpret “install/apply the links” as updating existing scoped URL positions. Do not install a Saved Template, create a missing flow, or extend a partial flow unless Rodolfo explicitly authorizes that separate scope.
10. Report an exclusion waterfall: exact-template total → `On-hold` → `Blocked` → structurally/identity ineligible → eligible Pages, plus distinct DTR login count. This waterfall must reconcile back to the exact-template total.

## Eligibility discovery before any write

1. Resolve the exact approved DTR login from 1Password without exposing credentials.
   - Treat the login string as an exact identity boundary. A similarly named item, a missing/extra numeric suffix, or the same site/vertical label is **not** an authorized substitute.
   - If the exact login is absent, do not try a near-match credential against the requested login and do not infer access from a different container. Report the exact missing identity and stop before Page/URL claims or writes.
   - If Rodolfo explicitly corrects the login, restart discovery under the corrected identity; preserve the originally requested value in the manifest.
2. Read the approved Page-classification spreadsheet through the canonical MGS Service Account; never fall back to personal Google auth.
3. Match the candidate by internal DTR Page ID and cross-check the exact Facebook Page ID. Derive the target catalog from `vertical + pais + lingua`. If a long Facebook Page ID is rendered in scientific notation, preserve the raw cell and reconcile the exact value from the live DTR Page; never reconstruct or round it. Normalize Page names to Unicode NFC only for comparison so composed/decomposed accents do not create a false mismatch.
4. Apply the spreadsheet status gate: `Blocked` and `On-hold` are no-write; `Ready`, `Campaign`, `Broadcast`, and Restricted Broadcast remain eligible for audit. Do not infer status from the DTR UI alone when the sheet provides it.
5. Enumerate every imported Facebook account and Page in that login. The Page list can be larger than the first Bot Manager card; inspect the selected segurador's complete Social Accounts/Page inventory and switch segurador when needed.
6. Reconcile the global ignore list and any explicit Page exclusions. Match an ignore record by exact Facebook Page ID, or by the compound fallback `bot_user + page_id_pg`; never treat `bot_user` alone as a Page-level match.
7. Read back Page name, Facebook Page ID, and DTR Page ID from the live DTR account.
8. Open `/visual_flow_builder/flowbuilder_manager/<DTR_PAGE_ID>/1` and wait for the asynchronously populated flow table before concluding it is empty. DataTable pagination can hide `Auto Principal Drip`: select a larger page length such as 100 or paginate every table page, wait for the redraw, and only then classify `flow absent`.
9. Require exactly one `Auto Principal Drip` row with the yellow `Edit` action and a separate red `Delete` action.
10. If no flow exists, mark the flow surface `absent`; a URL-replacement request never authorizes installing a Saved Template or creating a flow. By default the Page remains ineligible for flow migration. Exception: when the disclosed authorized population explicitly includes action-only Pages and Rodolfo confirms that partition, those Pages may remain eligible for Get Started/No Match only. Record the missing flow and exact reduced surface set per Page; do not imply that a flow was migrated or validated. If direct checks prove Get Started, No Match, Auto Principal Drip and Persistent Menu are all absent or contain zero scoped URLs, classify the Page as `zero_surface_validated` with zero writes instead of failing an otherwise exhaustive batch merely because there is nothing to mutate.
11. Back up every authorized surface. The default full unit includes the graph, Get Started, No Match and Persistent Menu; for an explicitly narrower subset, record omitted surfaces as `out_of_scope_unchanged` without claiming a backup or validation.
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

## Zero-diff and direct-catalog protocol

When Rodolfo provides a Google Sheet as the destination catalog rather than as a Page-classification table:

1. Read the exact spreadsheet ID, `gid`/tab title, and authorized row range through the canonical MGS Service Account; validate Drive edit capability and Sheets HTTP 200 even when the task is read-only.
2. Do not require friendly headers when the range is an ordered link catalog. Validate row labels and cardinality instead: exactly one M0/Get Started row, one NM/No Match row, and the expected numbered Drip rows. Validate every final URL's host, path, tracking parameters, literal `#PAGE_ID#`, uniqueness, and semantic label before comparing it with DTR.
3. Freeze the source tab, row numbers, catalog hash, Page identity, graph, and action settings in the manifest before any writable step.
4. If every scoped live value already matches the catalog, perform **zero writes**. Do not submit identical values merely to satisfy the verb “apply”; redundant saves create avoidable production risk and can trigger platform normalization.
5. Still run a fresh pre-write drift check and an independent new-session readback. Report the Page as `already canonical / validated`, with `actually changed = 0`, rather than claiming the links were applied.
6. Count URL occurrences, not just semantic destinations: one M-number can legitimately appear in both a Button URL and a Generic Template image-click URL. Preserve that exact occurrence count and require every occurrence to match its semantic target.
7. Accept the platform-appended subscriber suffix only on Get Started and No Match when the canonical base is exact. Include the suffix state in readback; never copy it into the Sheet catalog or Flow Builder.

## Safe execution sequence

1. For Openzed catalog migrations, run `python3 scripts/openzed_link_catalog.py --validate`. For a Rodolfo-supplied direct catalog Sheet, use the zero-diff/direct-catalog protocol above instead of forcing the Openzed generator.
2. Build a target manifest: login, imported account ID, Page name, DTR/FB IDs, classification authority, legacy URL discrepancies, existing semantic labels, chosen catalog, and every authorized surface route. Under the default full unit this includes all four routes; under an explicit narrower subset, record omitted routes as out of scope.
3. Create timestamped backups and hashes before opening a writable state.
4. Re-read live values immediately before mutation; abort on drift.
5. Execute at least one Page as canary for every distinct destination catalog/classification family in the batch. A successful EN catalog canary does not validate an ES catalog, and vice versa.
6. Update only the authorized surfaces, one at a time, preserving all non-URL fields. The default full unit order is:
   - Flow Builder URLs, then one global Save;
   - Get Started URL, then Update;
   - No Match URL, then Update;
   - Persistent Menu first-level default Web URL, then Submit.
   Skip and record any explicitly omitted surface rather than touching it.
7. After each save, reload that surface and read back the exact destination. Do not treat a click, toast, or missing network event as persistence. If the UI Save is a proven no-op, use the guarded recovery in `references/live-reference-page-catalog-and-idempotent-recovery.md`; never blindly submit a second write.
8. Open a fresh independent browser session and validate the complete Page.
9. Compare against backup: only scoped URL strings may differ.
10. If a governed tracking sheet has a completion/status field, write `feito` only for Pages whose independent readback passed. Read the exact target cell immediately before the write, update only that Page's range, and read back the entire authorized target set so skipped Pages are proven unchanged.
11. Continue to remaining Pages only after the canary passes. On mismatch, stop and restore from backup rather than stacking fixes.

## Attribute an unexpected Saved Template after a migration

When a Saved Template appears and Rodolfo asks whether Zeus created it, investigate before answering; a similarly named template in the same segurador is not proof of authorship.

1. Capture the active DTR login and segurador, the exact visible title/description, any template identifier, and the displayed relative age. Preserve the screenshot as observation evidence.
2. Separate the product surfaces: a Flow Builder `Save`, Get Started `Update`, or No Match `Update` does **not** by itself mean a Facebook Saved Template was created. Generic form fields containing the word `template` are also not evidence of a Saved Template action.
3. Reconcile the operation's audit event, manifest, apply result, REPORT-INFRA, Git/session history, and actual automation writer. Require evidence of a Saved Template route or an `Upload`, `Create`, `Save as template`, or `Install template` control before attributing creation to Zeus.
4. Inspect the writer's mutation allowlist or source when necessary. A URL-only migration should show writes only to the authorized Flow Builder graph and action editors; absence of Saved Template routes in that writer is stronger evidence than a verbal completion summary.
5. Convert the UI's relative age to an approximate absolute time using a live clock and compare it with the run's `created_at` and `finished_at`. Treat this only as corroboration because relative ages are rounded and screenshots may be delayed.
6. If the operation evidence excludes Saved Templates but the creator cannot be identified, report: `not created by this Zeus operation; concurrent origin unattributed`. Do not guess the actor or classify it as an anomaly without separate evidence.
7. Do not delete, rename, reinstall, or otherwise mutate the unexpected template during attribution; investigation is read-only unless Rodolfo separately authorizes a change.

## Parser hazard: `#PAGE_ID#`

Python and browser URL parsers treat the first `#` in `#PAGE_ID#` as a fragment delimiter, hiding later query parameters. For validation only, replace the complete placeholder with a sentinel such as `PAGE_ID_PLACEHOLDER`, parse, then verify the original still contains exactly one literal `#PAGE_ID#`. Never percent-encode or modify the production placeholder.

## Completion report

Report:

- requested versus eligible Pages, with a disjoint disposition partition that exhausts the exact authorized list;
- actually changed Pages/URL occurrences versus qualified Pages that were already canonical and only validated;
- spreadsheet tab/row, DTR/FB identity match, `vertical + pais + lingua`, and operational status per Page;
- legacy `utm_term`/template/domain discrepancies, explicitly labeled non-authoritative;
- pre/post URL counts by surface;
- exact labels migrated;
- graph node/reachability invariants;
- independent readback method;
- governed-sheet completion cells actually changed, plus readback proving skipped target rows remained unchanged;
- Pages skipped and why;
- whether any legacy flow remained M0–M15;
- backup/rollback availability;
- every partial failure without disguising it as success;
- for any Page-level exception list that mentions Smart Bidding, refresh the live Messenger Page dataset immediately before replying, join each Page only by exact `FB_PAGE_ID`, and print the current SB `STATUS` inline on every listed Page. When the exact join returns zero rows, print the literal label `sem cadastro SB`; never reuse an earlier audit status or infer registration/status from Page name, login, or small PG ID. Preserve the complete requested list and group it by app and segurador for legibility;
- for a connect/Auto Scan result list, print the exact DTR login email once under each Segurador, then every Page with both IDs, current SB status or `sem cadastro SB`, final connection state, `Auto Scan aceito` or the exact skip reason, and the requested DTR subscriber metric. When Rodolfo asks for both numbers or points to the parenthesized value, print the live card literally as `Bot subscriber N (M)`; do not substitute the DataTable `recordsTotal` or omit `M`. Reconcile the list to the summary totals and say `Auto Scan aceito`, not `scan concluído`, unless DTR exposes and the operation verifies a separate completion signal.

Never claim the account was fully migrated when the authorization was only a pilot or when Pages lacked the prerequisite flow.
