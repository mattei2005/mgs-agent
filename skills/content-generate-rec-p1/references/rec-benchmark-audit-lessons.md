# REC benchmark audit lessons — runner, image override, timing, cost

Use this reference when auditing REC benchmark threads or debugging fast-path REC behavior after a user compares multiple draft runs.

## What to verify from Discord threads

For each thread, import/read the thread and verify the original prompt, not only the agent summary:

- Was the post created as `draft`, not published?
- Did the agent call `/root/mgs-agent/scripts/mgs-rec-runner.py` directly?
- Did the exact CLI include required flags (`--site`, `--card`, `--status`, `--source-url`)?
- If the user supplied an image, did the exact CLI include `--card-image-url <direct image url>`?
- Did the summary include `duration_sec`, `timings_sec`, `card_selection`, Post ID/edit link, Yoast, images, artifact audit and cost?
- Did the import show any Zeus message in an Atena content thread? If yes, distinguish requested admin intervention from accidental routing/loop.

## Manual image override pitfall

Atena may try to pass manual image URLs via environment variables such as `MGS_MANUAL_CARD_IMAGE_URL` or `MGS_CARD_IMAGE_URL`. That does **not** prove the manual-image path unless the runner supports those env vars.

Current benchmark pass condition:

```text
Expected manual image run
-------------------------
Runner CLI must include: --card-image-url "https://...direct-image.jpg"
card_selection.mode should be manual_card_image_url
card_selection.source should match the user-supplied URL
LazyBlock card image and featured generation should derive from that image
```

If the final summary says `auto_ranked_card_image`, the manual benchmark failed even if the draft was created successfully.

## Automatic image quality pitfall

A successful image upload is not enough. For LazyBlock card images, prefer:

1. official issuer card-only/isolated asset;
2. trusted third-party card-only/isolated asset;
3. cropped/normalized user-supplied direct image;
4. contextual payment/app/hand/phone/banner image only as fallback with explicit caveat.

Images containing a phone screen, app UI, hand/person, coffee shop scene, YouTube thumbnail, promo banner, or contactless lifestyle photo should be reported as poor LazyBlock candidates even when they pass dimensions/aspect validation.

## Cache-miss and official-source quality

A cache-miss is acceptable only if the runner can extract or receive minimum facts without Anthropic/Claude. If official pages are geo/bot blocked or contain error pages, report that the draft is operationally created but editorially weak.

Minimum facts to confirm or request before publication-quality output:

- annual fee;
- APR/representative APR when available;
- 2–4 real benefits/features;
- official source URL and any alternative source URLs used.

Do not treat fallback filler such as `N/A`, `Check terms`, or generic benefits as publication-ready.

## Timing interpretation

Use both runner duration and thread elapsed time:

```text
thread_elapsed = final_agent_message_timestamp - original_user_message_timestamp
overhead = thread_elapsed - runner_duration
```

Benchmark interpretation:

- under 2 minutes thread elapsed: pass for operational fast path;
- 2–3 minutes: acceptable if image fallback or Yoast scoring dominates;
- over 3 minutes: investigate `timings_sec`;
- if `yoast_score` is ~30–40s, it is likely the main bottleneck, not content generation.

Also check telemetry consistency: `instrumented_total` should not materially exceed `duration_sec`. If it does, report a timing instrumentation bug.

## Cost reporting

Atena's runner summary may show only runner/image cost. For executive reporting, also estimate agent-session token cost when available. Label it clearly as operational/Sonnet-equivalent if the provider is OAuth/included billing.

Report both:

```text
runner/img cost       | direct pipeline estimate
agent session cost    | model/session operational estimate
combined estimate     | runner/img + agent session
```

Do not let a report claim `US$0.03 total` if the agent session itself consumed meaningful model tokens.
