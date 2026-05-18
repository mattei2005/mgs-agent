# REC speed audit and SLA guidance

Use this reference when Rodolfo/Zeus asks why REC creation is slow, what the bottleneck is, or how to reduce REC runtime.

## Core finding from the 2026-05-17 speed audit

A normal REC should not take 5-8 minutes when the deterministic runner is used correctly. The article text generation itself is not the bottleneck:

- Local deterministic article generation can complete in ~0.03s.
- Cache-HIT dry-run can complete in ~0.3s.
- A recent real runner publish completed in ~66s when provided official facts and a manual card image URL.
- Featured image generation was around ~8s in that run.
- Slow real cases included Amex Cashback at ~344s and American Express Rewards at ~444s, driven by agent/session workflow rather than text generation.

The central operational problem is Atena drifting back into manual agent behavior. If the request says `publique direto` and has site/card/status/source, Atena should not inspect the runner code, browse manually, read large skill sections, or run separate upload/Yoast/image steps unless the runner fails with a specific blocker. The intended shape is: one `mgs-rec-runner.py` command → parse JSON → one final summary.

The main delays are usually outside text generation:

1. Agent/manual ReAct tool-calling instead of one runner call.
2. Missing official URL or missing official facts, forcing research/browser work.
3. Card image discovery/fallback and visual correction after publication.
4. WordPress REST steps: term resolution, post create, Yoast update/scorer, public verification.
5. Post-publication QA/repair loops, especially featured image replacement.

## SLA targets

Use these as operational expectations, not hard guarantees:

| Mode | Conditions | Target |
|---|---|---|
| Fast REC | Official URL/facts supplied, cache hit or direct inputs, runner used once | 90s-2min |
| REC with image fallback | Needs card image search but no browser loop | 2-3min |
| REC with visual QA/repair | Image correction or manual visual review needed | up to 4-5min |
| Above 5min | Only acceptable for external block/real repair | Treat as incident |
| 8min+ | Not acceptable for normal REC | Investigate and report bottleneck |

## Fast request shape

Ask Rodolfo/Raquel for the minimum inputs that let the runner skip browser/search loops:

```text
Atena, publique direto um REC no eggbev.

Tipo: REC
Status: publish
Cartão: [exact card name]
URL oficial: [official issuer URL]
Imagem do cartão: [optional direct image URL]
```

If the card is cache MISS and the official page is hard to extract, additional official facts reduce runtime:

```text
Annual fee: ...
APR: ...
Benefits:
- ...
- ...
- ...
Competitors:
- ...
- ...
```

## Audit procedure

When reviewing a slow REC:

1. Confirm whether `mgs-rec-runner.py` was used or the agent drifted into manual workflow.
2. Read the runner JSON if available and compare `duration_sec`, `steps`, and `timings_sec`.
3. Separate runner time from agent conversation time. A fast runner can become a 5-8min user experience if the agent does extra browsing, code inspection, QA, corrections, or summaries manually.
4. Check Atena's session transcript/log for anti-patterns: `browser_navigate` before runner, `read_file` on the runner/skills during normal publish, standalone `upload-image.sh`/`generate-featured-image.sh`/`update-yoast.sh` outside the runner, or repeated image uploads.
5. Identify whether the path was cache_hit, request_facts_used, or reference extraction/browser fallback.
6. Check if image handling caused extra uploads/regenerations.
7. Check WordPress/Yoast overhead separately from article generation.
8. For benchmark threads, require final evidence fields: `duration_sec`, `timings_sec`, `term_cache`, `steps`, and `warnings`. If Atena creates the post but omits these fields, classify as “post delivery OK; fast-path benchmark not proven.”
9. For draft posts, public URL 404 is expected. Verify via WP REST/edit context and media URLs instead, and call the link a future permalink.
10. Report a table with bottleneck, evidence, and next optimization.

## Optimization backlog

Prioritize these fixes before adding more complex infrastructure:

1. Use deterministic runner by default for every complete REC request; make this a hard execution rule, not a suggestion.
2. For `publique direto` requests, ban pre-runner browser/code-inspection/tool exploration unless the runner returns a specific error requiring it.
3. Require or strongly prefer official URL in normal requests.
4. Use `--card-image-url` when a clean official card image URL is provided.
5. Cache WordPress category/tag IDs per site inside the runner to avoid repeated REST calls. In the 2026-05-17 audit, resolving 9 eggbev terms cold took ~8.51s; the same resolution from `/root/mgs-agent/data/wp-term-cache.json` took ~0.00s. Keep passing `term_cache`/`term_stats` into `resolve_terms`, save the cache after misses, and report cache hits/misses in runner output.
6. Add timing ticks around unresolved WordPress stages: term resolution, create-post, update-yoast, yoast-score, cache-save, public-verify, artifact-cleanup, fingerprint-store. Also compute `unattributed_sec` so any hidden time is visible instead of hand-waved.
7. Do not do image correction after publication unless the card/brand/product is actually wrong.
8. Treat any normal REC above 5 minutes as an incident with a bottleneck report.

## Reporting style for Rodolfo

Be direct and operational. Avoid defending the delay. State whether the delay is acceptable, where time went, and what action reduces it.

When the speed discussion happens in a shared Zeus+Atena thread, keep each agent's role distinct: Atena owns the editorial/pipeline self-assessment; Zeus should add evidence, risk framing, and the concrete operational decision/patch. If Rodolfo asks whether both agents are saying the same thing, answer with an alignment table and explicitly call out any delta instead of restating both messages.

Good summary shape:

```text
REC speed audit

Area                         | Evidence                 | Action
-----------------------------|--------------------------|-------------------------
Article generation            | local generation ~0.03s  | not the bottleneck
Runner dry-run/cache          | ~0.3s                    | cache path is healthy
Real publish runner           | ~66s                     | baseline should be ~2min
WP term resolution            | cold ~8.5s / cached ~0s  | keep term cache active
Image/QA repairs              | extra uploads/corrections| only repair real defects
WordPress/Yoast/tags          | measured per timing tick | optimize slowest stage
```
