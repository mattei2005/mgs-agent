# Meta Support — declared enrollment without a visible background control

Status: prepared locally; not submitted. No approval to open a support conversation is implied by this draft.

## Question

Why do existing non-catalog creatives return `creative_features_spec.image_background_gen.enroll_status=OPT_IN` while the same ad's background-generation preview says `ineligible` and its manual Advantage+ creative editor does not expose Generate backgrounds?

## Minimal reproducible read-only case

- Account ID: `1414197490675732`
- Ad ID: `120252369595910326`
- Creative ID: `1109183188671446`
- Media: image/link creative; no returned product_set_id or catalog template.
- GET the ad or the creative with `degrees_of_freedom_spec`.
- Observed: `image_background_gen=OPT_IN`; `video_auto_crop=OPT_IN` also returned on this image-only creative.
- GET the ad's previews with `ad_format=MOBILE_FEED_STANDARD` and `creative_feature=image_background_gen`.
- Observed: HTTP200, named transformation reports `ineligible`.
- Manual editor path: Ad → Edit → Ad creative → Advantage+ creative enhancements → Edit → full Advantage+ creative panel.
- Observed: other feature controls present; Generate backgrounds absent.
- Direct creative reads had `facebook-api-version` response headers `v26.0` and `v27.0`, respectively, with the same two enrollment flags. Production API configuration was not changed.

## Control case

- Account ID: `787796726891306`
- Ad ID: `120255415667870547`
- Creative ID: `2396702827814984`
- Video creative returns image_background_gen OPT_IN and image_touchups OPT_IN, despite documented image-only applicability; background preview reports ineligible.

## Clarifications requested

1. Are the returned enrollments stored choices, inherited/default bundle values, or eligibility-agnostic read expansion? Which read identifies their provenance and effective applicability?
2. Does the ineligible result confirm non-application for the requested placement, and what is the authoritative mapping between this enrollment and the current editor's displayed controls?
3. How should a faithful copy of an existing source normalize an ineligible inherited enrollment without losing other enhancements? Previous create/copy materialization rejected resubmitted image_background_gen OPT_IN without product_set_id with code100/subcode3858293.

## Sources and evidence

- https://developers.facebook.com/docs/marketing-api/reference/ad-creative-feature-details/
- https://developers.facebook.com/documentation/ads-commerce/marketing-api/creative/advantage-creative/get-started
- https://developers.facebook.com/documentation/ads-commerce/marketing-api/creative/generative-ai-features
- https://www.facebook.com/business/help/981940746195135
- Sanitized local reads: readback-v26.0.json; readback-v27.0.json; direct-creative-version-proof.json.
- Actual manual-editor screenshots retained in `/root/mgs-agent/reports/manual10-background-1569376234008354837/`.

No access token, cookie, password, private preview URL or credential is included. The case requests an explanation; it does not authorize Meta or an agent to modify campaigns.
