# Faithful creative reuse and destination changes

## Active policy override — Rodolfo 1568722979569930414

Resolve `context/meta-creative-copy-policy.md` before treating legacy preservation/individual-review gates as active. For every authorized campaign duplication, opt out only inherited enabled `image_background_gen` on the copy, without another question; preserve the source and every other resource. This explicitly supersedes this reference's earlier no-waiver requirement only for that feature. Do not rely on a still-enabled immutable creative/post, defaults, or relocated UTMs as compliance. Ares owns implementation and execution; Zeus coordinates and verifies without a parallel writer. Human browser control is not a prerequisite for the now-authorized opt-out API recovery.

Use this reference when a faithful clone must keep source media, copy and feature configuration while writing new tracking directly into Website URL. It is a documentation and diagnostic checklist, not authorization to disable a feature, add a catalog, change identity, create extra test objects or weaken QA.

## Establish the contract at the correct object level

- Separate campaign/adset creation, ad creation, reusable media (`video_id` / `image_hash`), AdCreative identity, post identity, individual feature enrollment and effective eligibility. Fresh campaign creation does not by itself bypass creative validation.
- The official Video and Carousel Ads guide documents creation from an existing video ID. Reusing the same media does not require retaining the same technical creative ID.
- The AdCreative update operation lists account_id, adlabels, name and status; a Field enum containing link_url does not make destination mutable on an existing creative node. Consult endpoint-specific writable parameters, not a generic SDK field list.
- For a video creative, inspect `object_story_spec.video_data.call_to_action.value.link`; for link ads inspect `object_story_spec.link_data.link`; inspect `asset_feed_spec.link_urls` where the subtype uses asset feeds. A top-level link_url example is not proof that it replaces every nested destination subtype.

## Native Ad Copies semantics

- Supply overrides under `creative_parameters`. Passing degrees_of_freedom_spec beside that parameter is not the documented nesting.
- Overrides replace complete top-level values, not individual nested leaves. If replacing object_story_spec or degrees_of_freedom_spec, construct the complete required value and validate all required source settings afterward.
- Omitting a block in native copy means inheritance; omitting it in fresh standalone creation can mean defaults. These are not equivalent experiments.
- Inspect the installed transport and the attempt journal before treating a community workaround as new. If correct nesting and normalization were already used, the same snippet is not evidence for another live retry.

## Enrollment is not eligibility, but neither may be silently waived

- The official Advantage+ Creative guide says ineligible OPT_IN features can be removed and deprecated standard_enhancements fields can still appear in GET responses. A GET payload is not automatically a valid create payload.
- The Generative AI API guide limits image_background_gen to catalog product images; Meta Business Help explicitly says background generation is unavailable for video ads. A legacy OPT_IN on a video therefore does not prove that background generation is actually rendering.
- Check feature-specific preview transformation_spec and applicable placements. Preserve the difference between source configuration, eligible transformation and actual rendered output.
- Read screenshots literally. Video effects, video touch-ups and image background generation must not be equated without a documented/API mapping. A summary listing enhancements does not establish every individual toggle's state.
- Do not use ineligibility as implicit approval to change enrollment. If the acceptance contract requires retaining that configured state, preserve the requirement or surface the exact conflict; do not silently substitute OPT_OUT, defaults, a new catalog or relocated UTMs.

## Evidence for a complete manual control

When Rodolfo explicitly directs the control to an existing pending original request, use its verified first eligible slot rather than proposing another diagnostic campaign. Bind the control to the original account, source, request, campaign/adset IDs, approved budget/bid/tracking and shared writer hold. A paused campaign/adset with no ads is an incomplete request, not an existing ad whose URL can simply be edited: materialize only its missing authorized ad layer, keep it paused during QA, and do not replay campaign/adset creation or silently alter enrollment. This explicit redirection supersedes only the abandoned diagnostic target; it does not authorize unrelated production changes.

Before proposing or requesting authorization to edit a historical canary, reconcile its exact immutable ID against the deletion/request journal and perform a fresh live status read. A past PAUSED receipt is not current availability. If the target is DELETED, withdraw the stale proposal, report the mistake and zero writes, and obtain explicit authorization for any replacement copy or different target; do not silently restore, recreate, reuse a retired number, or substitute a pending production shell. A later approval to edit the named existing canary does not authorize its recreation.

Require the same saved object to demonstrate new Website URL tracking and the required source feature configuration together. A manual copy that preserves the old creative/post and old tracking proves reuse, not the changed-destination case. A screenshot with source campaign tracking or mismatched campaign/adgroup codes is not proof that new tracking was fully validated. Report that evidence gap without claiming the UI cannot do it or asking the manager to repeat already-provided context.

## UI gate and readback interpretation

- Treat an Existing campaign selector warning about a different catalog as evidence of that UI gate, not proof of actual source/target catalog IDs. Compare campaign/adset promoted objects and creative configuration before diagnosing a dropped catalog; never add a catalog or disable enrollment merely to make the selector accept the target.
- A fresh-ad editor can preselect an unrelated default Page. Verify the exact required source Page before entering media/copy or publishing; search by both immutable ID and exact name when the picker is empty. A missing human-session Page does not imply missing System User/API access. Discard only the task-owned unpublished draft, never global drafts or existing objects, and verify the target and source afterward.
- Meta thumbnail image locators can rotate between GETs while the bytes remain identical. Compare immutable creative/video/post IDs, all substantive settings and, when image_url is the only delta, fetch both locators privately and compare image bytes by SHA-256. Record the raw delta and byte evidence; do not silently ignore media changes or declare an anomaly from a rotating locator.

## Post-creation feature normalization

Verify preserved enrollments with a fresh postprocessing read, not only the immediate creation/readback snapshot. Meta can initially echo inherited legacy OPT_IN fields and later omit them while the source still returns them. Keep both observations; absence proves loss of verification, not necessarily that the rendering feature is disabled. The permanent image_background_gen exception does not authorize accepting missing image/video/product features. Hold activation for an unresolved material delta unless it is safely restored/proven or the proper authority explicitly accepts that new delta; never weaken QA to make the batch pass.

### Resume after explicit acceptance of missing fields

1. Read the exact approval and its preceding question from the real origin. Validate human identity, account, request and the enumerated uncertainty. A short affirmative can approve a clear pending question; do not require the person to repeat budgets, tracking or the already-authorized background opt-out.
2. Freeze a typed receipt binding the original request/account, source digest, creation/target manifest digests, execution clock, campaign/adset/ad/creative IDs, source lineage, effective creative payload digest and exact accepted absent fields. Keep both manifests unchanged. In the current executor, `ares_campaign_v3.reviewed_copy_omissions.binding` builds this binding, `validate` checks the live dialogue and registered receipt, and `policies/reviewed-copy-feature-omissions.json` indexes grants by request/account/approval. Use the reusable mechanism instead of cloning a hardcoded historical adapter for each new approval.
3. Apply the receipt only in the normal request's QA context. Tolerate only the specifically approved absence on those existing creative IDs; reject explicit enrollment mismatches, unapproved omissions, changed payloads/IDs/clock, different accounts and unregistered requests. Leave the ordinary comparator strict outside the verified context. Acceptance of uncertain API return is not a feature-toggle write and is not proof of literal feature fidelity.
4. Have the single shared-code integrator validate each account's receipt and notify its existing writer. Preserve dispatches installed by concurrent authorized work. Cover negative cases for wrong account, changed IDs/lineage/payload/seals/clock/dialogue, extra omissions and explicit OPT_OUT before handing back execution; do not open another account transaction to test the mechanism.
5. Resume the original input with the normal runner: `python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input ORIGINAL_INPUT --dry-run`, then the same command with `--confirm-execute` instead of `--dry-run`. The registered receipt is loaded from the same request automatically; do not inject a legacy background descriptor or `APPROVED_RESUME` context into this route. Resume only post-processing/activation when materialization is already complete.
6. Independently GET the persisted campaign/adset/ad IDs after activation; do not infer live state from a completion label or the executor's message. Aggregate and reconcile unique IDs and full hierarchy counts per account. Verify budgets/caps, media/video identity, copy/CTA, source lineage, background OPT_OUT, configured status and each ad's effective_status. Parse every Website URL and match its campaign/adgroup tokens to that exact destination slot, not merely to a nonempty UTM; verify url_tags is empty when tracking belongs entirely in Website URL. Save projected response bodies before local assertions so a comparison failure can be diagnosed without repeating successful provider reads. Compare source integrity against a fresh pre-mutation boundary as well as the historical snapshot; an old budget difference alone does not attribute a source change to the recovery.
7. Keep raw fidelity findings separate from acceptance: record explicit enrollment mismatches, missing fields and the exact request-bound approval independently. Declare completion under the approved omissions only after the remaining invariants and live activation pass; never turn that into a claim of literal feature equality or a global waiver. When confirming a permanent rule, inspect the central builder/planner, resume and QA/activation consumers and run its preservation tests, including no source mutation and no changes to unrelated features.
8. Report the working result first and follow Rodolfo's requested numbered questions in order; place compact account bullets inside the relevant point. Say that background was the only feature explicitly disabled by the executor when that is what the evidence proves, and retain one concise caveat for accepted unconfirmed fields. State configured/effective ACTIVE precisely; do not claim actual delivery, impressions or spend without that evidence. Do not repeat an already-resolved approval question, wake an existing writer for another ACK, or start a parallel execution merely to verify completion.

### Recover complete inventories efficiently

Prefer verified persisted creative IDs and full semantic GETs for those IDs. When a missing slot still requires discovery, paginate the account edge with compact `fields=id,name` pages; the current engine uses a page size of 500. Follow every cursor, retain loop/missing-cursor guards and deduplicate by immutable ID before declaring the inventory complete. A matching name selects only a candidate: fetch its full definition and prove account, media, copy and tracking before reuse. If a large edge read fails, reduce page size without truncating inventory coverage or replaying creation; do not mistake one successful page for complete recovery.

## Portfolio audit of an inherited feature

For a read-only audit of all active SHEIN campaigns, reconcile immutable account-ID sets from `operations/SHEIN-US-DIRECT-accounts.json` and the live engine account profiles; never restrict the audit to configured creation-ready accounts or the current manager. Read each account live, paginate campaign and ad edges completely, validate filtered declared totals when provided, and persist reduced per-account batches before aggregating. Recheck active campaign-ID sets at the end and refresh accounts whose set changed.

The feature belongs to ad creatives, not a campaign-level toggle. For ACTIVE/effective-ACTIVE campaigns, inspect all nondeleted/nonarchived ads and state that scope. Classify explicit OPT_IN as enabled, all explicit OPT_OUT as disabled, mixed states separately, and any remaining missing/unknown states as unconfirmed. Do not call a missing field disabled; cross-check missing states on the direct creative nodes before reporting the limitation. Enrollment is not eligibility or delivery.

Aggregate and reconcile campaign IDs/counts in code. Group campaign numbers by exact account and manager, detect duplicate/nonstandard numbers, and validate that any compressed numeric ranges expand back to the original complete lists. Include accounts with no active campaigns in coverage, keep the output inline unless an attachment was requested, and do not mutate campaigns or reinterpret an audit request as opt-out authorization.

### Preserve scope and evidence when API unknowns require UI verification

1. Persist a durable manifest before opening the browser: exact account/campaign/ad/creative IDs, original API classification, authorization source and required control. Count campaigns, accounts, ads and unique creatives independently in code; creative deduplication can reduce API probes, but its count is not the number of ads in the UI scope. Do not leave the sole resumable manifest in an expiring scratch directory.
2. When Rodolfo directs verification through the already-authenticated PC1 browser, reuse that ordinary Chrome session first; do not open an AdsPower profile merely because the task concerns Meta. A Page creation/access warning is not proof that read-only inspection of the existing ad is blocked: check the exact ad and named setting in the logged-in session before proposing a different profile or another authentication. Bind one representative pending ad to the correct account/profile and validate a read-only inspection path to the exact named setting before expanding to the batch. Opening its editor, seeing an enhancement summary or authenticating a profile is not a confirmed toggle state. Do not present an uncompleted inspection attempt as a proven bulk-automation method.
3. Save per-ad evidence and roll it up through the original campaign classification rules. Preserve unresolved ads and campaigns as unconfirmed; a first-ad result or one account's session does not establish the remaining scope. An asset-permission warning proves that specific gate, not that the website is logged out or that API access is missing.
4. If a protected authentication challenge blocks inspection, route the handoff through `secure-remote-windows-automation` and its interactive-browser reference. Preserve the exact profile, durable manifest, completed/pending counts and next action. Release the desktop lease and distinguish transport recovery from audit progress; never count browser setup as a visually confirmed campaign.
5. Report only verified campaign results, including zero when no exact setting was observed, and keep the API-unknown classification unchanged until evidence resolves it. Do not grant permissions, change credentials, edit or publish ads to unlock a read-only audit.

## Sources and confidence

Primary contract:
- https://developers.facebook.com/documentation/ads-commerce/graph-api/reference/adgroup/copies
- https://developers.facebook.com/blog/post/2025/05/28/you-can-now-change-creative-fields-when-duplicating-ads-with-ad-copies-api/
- https://developers.facebook.com/documentation/ads-commerce/marketing-api/reference/ad-creative
- https://developers.facebook.com/documentation/ads-commerce/marketing-api/reference/ad-account/adcreatives
- https://developers.facebook.com/documentation/ads-commerce/marketing-api/guides/videoads
- https://developers.facebook.com/documentation/ads-commerce/marketing-api/creative/advantage-creative/get-started
- https://developers.facebook.com/documentation/ads-commerce/marketing-api/creative/generative-ai-features
- https://www.facebook.com/business/help/981940746195135

Community nesting example (not a vendor guarantee or proof for a specific account/feature combination):
- https://developers.facebook.com/community/threads/2017633248799556/

Distinguish researched, API-accepted, saved/read-back and common-executor-homologated outcomes. Public SDK fields, third-party validation-only reports, other accounts' success and source-reference copies do not establish the full acceptance contract. Never turn failure of selected routes into universal API impossibility.
