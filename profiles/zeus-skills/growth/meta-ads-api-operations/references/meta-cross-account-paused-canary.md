# Explicit paused cross-account canary

Use only for a specifically authorized technical test that names one destination account, one Page, the budget and `PAUSED`. Normal production stays on the canonical Campaign Engine and its operation registration. Do not broaden a technical canary into a production onboarding/configuration change.

## Freeze and preflight

- Resolve source and target identities with the active operation token. Freeze one real source hierarchy, require complete source adset/ad enumeration, and reject empty-source examples rather than publishing an empty test.
- Before asking the owner about an ambiguity, collect all independently retrievable dependencies together: duplicate Page identities, target account permissions, the source pixel and the target's available pixels. Do not serialize avoidable decision round trips.
- Obtain explicit Page selection and any destination-pixel substitution required by a preserve-the-rest request. Use the existing approved operational token; administrative discovery must not become the campaign writer.
- Materialize source campaign/adset/ad IDs, target account/Page/pixel, one campaign, exact adset/ad cardinality, budget in minor units, status, before inventory and readback criteria in a durable, credential-free manifest. Keep mutation state separately and record intent before each write. Reconcile an existing journal instead of replaying creates.

## Validated direct template route

The official Meta Python SDK exposes destination-account creation edges with `source_campaign_id`, `source_adset_id` and `source_ad_id`; verify the current SDK/schema before using these fields. A same-account Campaign `/copies` route must not be mistaken for a supported destination-account transfer.

1. Build target campaign/adset/ad payloads from the frozen source configuration, changing only authorized destination identity, budget, status and the technical test marker. Source IDs are provenance, never cleanup targets.
2. Use `execution_options=["validate_only"]` for the campaign and each complete creative payload before real creation. Validate-only success is not publication; unexpected real object IDs require reconciliation.
3. For a cross-Page video creative, test existing video and thumbnail references at the exact destination before assuming re-upload is necessary. Preserve original copy, CTA, URL/tags and raw video/thumbnail identity; do not automatically translate or rewrite UTMs to match the destination label.
4. Omit the deprecated outgoing `standard_enhancements` key when required by the current schema, preserving supported individual feature flags. Compare actual flags after asynchronous Meta processing; a successful create is not proof that every optimization setting survived.
5. Create only the destination campaign, adset, creatives and ads, all configured `PAUSED`. After the campaign shell exists, immediately verify account, budget and PAUSED before creating its children. No activation, billing change, pixel sharing, permission grant or additional campaign is implicit.
6. If the backend normalizes a past start time, drops nested targeting controls or changes/removes a creative feature, record the precise requested/returned diff. Make at most a bounded, scoped restoration attempt supported by the API and re-read it. Do not repeatedly write an unsupported field or call the resulting campaign an exact all-fields clone when parity remains unverified.

## Page-backed Instagram race: error 2238011

A newly published ad may move from `IN_PROCESS` to `WITH_ISSUES` while Meta reports that the Page-backed Instagram profile is still being created. Another ad on the same Page may already have passed processing.

- Read the affected ad's `issues_info` and the existing `/{PAGE_ID}/page_backed_instagram_accounts` edge; distinguish a Page-backed ad identity from a separately connected, login-based Instagram account.
- If the Page-backed actor is now present, preserve the same ad and creative IDs and re-submit only the affected ad with the same `creative_id` and `status=PAUSED`. Record intent/result; do not create a duplicate ad or manually create/link another Instagram account to hide the failure.
- Use bounded GET-only polling through `IN_PROCESS`/`PENDING_REVIEW` until the configured/effective status is PAUSED and `issues_info` is absent. Keep the campaign and adset PAUSED throughout. Do not remove Instagram placements as a silent workaround.
- If a creative's supported enhancement flags are subsequently reset, a same-ad creative payload update can restore the authorized flags. Re-read the resulting creative ID and include any replacement in the cleanup inventory; verify the final post-processing values rather than the first response.
- Report initial error, exact recovery and final validation. Pending platform processing is not a fully healthy final state; a persisting hard error remains a blocker.

## Acceptance and future cleanup

Require exact one-campaign/adset/ad cardinality; correct account/Page/pixel/budget/event; PAUSED configured and effective statuses; no ad issues; source IDs/statuses/budget/creative references preserved; unchanged intended copy/video/thumbnail/CTA/links; and explicit reporting of any remaining field normalizations. Never invent zero spend from a missing response: preserve the actual Insights result and distinguish no recorded delivery from an explicit numeric metric.

Inventory created campaign/adset/ad/creative IDs and effective Page post IDs. Separately mark reused source media as protected. A future request to delete the test must not revoke persistent account/Page grants, delete the source campaign/videos or remove audit evidence. Freeze the exact cleanup scope and obtain any required confirmation before destructive cleanup; a future intent is not proof that cleanup has already happened.

### Confirmed cleanup and readback

1. Pre-read every named target and require the exact destination account, campaign/child relationships, creative/story association and Page ownership of each unpublished post. Keep the source campaign/ads/videos, Page, pixels and persistent grants outside the deletion set. Record intent and process ads before adset/campaign, then unreferenced creatives and exact generated Page posts. Never blindly repeat an ambiguous DELETE.
2. Authenticate Page post reads/deletes with an existing Page Access Token derived internally from the approved operational identity when the account token returns code 10 despite granted Page scopes. Keep the derived token only in process memory; do not rotate the production token, create new credentials or grant permissions to make cleanup pass. Use current post fields `id,from,is_published`; the legacy `object_id` projection can return code 12 on modern Graph versions.
3. Require `status=DELETED` for ad/campaign/adset/creative readback; do not relabel ARCHIVED or PAUSED as deletion. Meta may retain deleted ad-object metadata, so successful deletion is not a claim of physical history erasure.
4. A deleted dark post may return code 10 rather than 100/33. Do not treat this ambiguous permission/not-found message alone as proof, and do not loop the same failed GET. Combine the prior successful exact post read, successful DELETE, current Page control read with the same derived token, and fully paginated `/{PAGE_ID}/ads_posts?fields=id,is_published&include_inline_create=true&limit=100` showing the exact target absent. Preserve and verify unrelated Page posts.
5. Compare source configuration semantically while retaining raw before/after evidence. A Meta thumbnail serving URL may rotate between reads: only disregard that particular `video_data.image_url` difference when both the `image_hash` and `video_id` are unchanged. Continue comparing source IDs, statuses, creative/story identities, copy/CTA and destination tracking links literally; never ignore ordinary campaign URLs as volatile.
6. Reconcile existing deleted targets from the journal before resuming a partial cleanup and write only the missing deletion. Verify every target terminal state, target campaign-list absence, source readability/configuration, Page task set and both pixels. For bulk grants promised as preserved, batch-read the exact account `user_tasks` and compare with the grant baseline; catalog membership alone does not prove task parity.
7. Preserve immutable creation proof and write a separate final cleanup/closure proof. Update checkpoint, registry and inventory to the closed state with explicit supersession where needed; retain audit history and report any unrecovered residue honestly.
