# REC top viewability and subtitle diagnosis

Use when AdOps attributes poor `rec_top` performance to fast scrolling, missing subtitles, or title/CTA layout.

## First resolve the layout question

When the owner says the ad appears before/after the subtitle or differs from a reference site, compare that exact spatial order first: title → ad container → subtitle → CTA. Use the same device and traffic parameters on both pages, inspect actual inserted nodes and geometry, and state any no-fill or missing-slot limitation. Do not replace a placement check with a broad viewability/revenue investigation or demand GAM reports to answer DOM order. Keep the user-facing answer short; only expand into performance causality if that remains the actual question.

## Separate mechanisms from demonstrated causes

- Google display viewability normally requires at least 50% of the creative in the viewport for one continuous second; large-format exceptions exist. Cite https://support.google.com/admanager/answer/4524488 and https://support.google.com/admanager/answer/6123466. Google specifically notes that immediate scrolling and late lazy loading can reduce top-slot viewability.
- Treat "a subtitle can retain attention" as a test hypothesis, not a guarantee. Additional text can move inventory or CTAs below the fold. A successful request, subtitle presence, or a synthetic browser screenshot does not establish real-user exposure, auction competition, RPM/RPS, or ROI causality.
- Ask for the underlying GAM report when screenshots only contain narrative conclusions. Break out exact ad-unit, hour/date/timezone, device, country, traffic source and size. Request measurable/viewable counts and Active View % viewable, exposure time when available, requests, unfilled/fill, eCPM and revenue. Compare viewable impressions against measurable impressions, not all requests/impressions. RPS/ROI additionally require session and media-cost data. Use a controlled experiment for a causal subtitle claim; observational before/after remains confounded by audience, demand and campaign changes.

## Reproduce the actual serving path

1. Distinguish the six site destinations, bare URLs and source-tagged URLs. Preserve the exact traffic parameters; source/device selects different rules.
2. Use a fresh foreground context per site with coherent mobile user agent/client hints, platform, touch and viewport. A narrow desktop viewport can request `desk` units instead of the intended `mob` units and invalidate the comparison. Read back runtime `device`, not only CSS width.
3. Read subtitle text and geometry, but also inspect screenshots and overlays. `display:block`, `visibility:visible`, and nonzero geometry do not prove that text is readable under a blur/rewarded modal. Current subtitle presence does not reconstruct a past debug session.
4. Project only safe wrapper fields. Check `requester.rewardedAdsMapping` names, targeting and `lazyAdTop`, plus declared/requested/filled GPT slots. A rewarded gate configured with `lazyAdTop=true` can hold top-ad insertion until the gate is released. Zero slots before interaction is not sufficient evidence of a broken wrapper.
5. For a bounded authorized QA probe, capture state before and after a physical click on the gate's own play/unlock button; do not click an advertiser creative. Animated CTAs can fail locator stability checks: use bounding box plus `elementFromPoint()` and a physical pointer click, not production CSS changes or a forced hidden-element click. Save the before-state before interaction so a timeout is recoverable.
6. Observe fallback/no-fill separately from a filled impression. If the REC top slot is requested only after the gate flow, record that ordering and exact ad-unit path. Do not describe time from first rewarded request to top request as full page-load latency, and do not extrapolate a datacenter no-fill result to actual audience fill/viewability.
7. Append each batch to a durable JSONL artifact, deduplicate/count in code and verify requested coverage. Keep per-destination checks separate from representative end-to-end gate probes.

## Reporting

Lead with: plausible mechanism versus unproven diagnosis. Report current subtitle state, any confirmed gate/timing interaction, unavailable historical/rendering evidence and unavailable real-user metrics. Keep production untouched unless a separate bounded change is authorized. Do not fabricate viewability, RPM, ROI, creative IDs or a guaranteed revenue gain.
