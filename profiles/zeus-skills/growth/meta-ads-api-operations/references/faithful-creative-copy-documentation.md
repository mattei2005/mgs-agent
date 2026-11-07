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
