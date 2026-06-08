# REC runner telemetry and taxonomy cache

Session learning from Zeus/Atena speed audit, 2026-05-17.

## Problem

Recent REC sessions showed article production taking 5–10 minutes even when the deterministic runner itself completed in about 66–70s. The old runner output only explained about 12–13s of work:

```text
Case                  Total runner   Instrumented   Unattributed
Barclaycard Avios     65.99s         12.41s         53.58s / 81.2%
Marbles Credit Card   69.63s         12.93s         56.70s / 81.4%
```

Article generation was not the bottleneck: local generation was ~0.03s, featured Gemini was ~8.3–8.5s, and image uploads were ~2s each. The hidden time was likely WordPress REST/taxonomy/create/Yoast/cache/verify plus agent-side QA/repair loops.

## Durable fix pattern

When auditing REC speed, instrument the runner itself rather than inferring from external logs.

Add per-stage `timings_sec` fields around:

```text
config_load_sec
card_cache_lookup_sec
reference_fetch_sec
reference_extract_llm_sec
article_api_sec or article_local_generate_sec
validate_pre_upload_sec
card_image_discovery_sec
card_image_upload_sec
featured_generate_sec
featured_local_validate_sec
featured_upload_sec
validate_final_sec
duplicate_fingerprint_check_sec
seo_fields_sec
wp_resolve_terms_sec
wp_create_post_sec
wp_update_yoast_sec
yoast_score_sec
cache_save_sec
public_verify_sec
artifact_cleanup_sec
duplicate_fingerprint_store_sec
unattributed_sec
instrumented_total_sec
```

`unattributed_sec` is mandatory during speed work. It tells whether the measurement is complete or still hiding the real bottleneck.

## Taxonomy cache pattern

WordPress taxonomy resolution is stable for repeated tags like `rec`, `cc`, `gb`, `lang_en`, `atena_agent`, default category, and recurring card tags. Avoid sequential REST calls on every REC.

Use a local cache file:

```text
/root/mgs-agent/data/wp-term-cache.json
```

Cache key shape:

```text
<site_key>:<taxonomy>:<normalized human-readable name>
```

Examples:

```text
eggbev:categories:credit card
eggbev:tags:rec
eggbev:tags:lang_en
eggbev:tags:barclaycard avios credit card
```

Cache value should include at least:

```json
{
  "id": 212,
  "name": "Credit Card",
  "slug": "credit-card",
  "site_key": "eggbev",
  "taxonomy": "categories"
}
```

Operational behavior:

1. Load cache once near runner start.
2. On hit, return cached `id` without calling `resolve-term.sh`.
3. On miss, call `resolve-term.sh`, parse the term ID, store in cache, then continue.
4. Preserve the existing `term_exists` tolerance: if WordPress returns HTTP 400 but includes a `term_id`, parse and cache that ID.
5. Save the cache atomically after term resolution.
6. Return `term_cache: {cache_hits, cache_misses}` in the runner JSON.

Validation observed:

```text
First resolve_terms() call   9 misses, cache saved
Second resolve_terms() call  9 hits, 0 misses
```

## Reporting standard for speed audits

When reporting to Rodolfo, separate three numbers:

```text
1. Agent/thread elapsed time       Full conversation/pipeline time, includes QA/repair/manual loops.
2. Runner duration_sec             Deterministic pipeline execution time.
3. Instrumented vs unattributed    Whether the runner measurement actually explains the duration.
```

Recommended SLA framing:

```text
REC with official URL + cache/facts       90s–2min
REC with image fallback                   2–3min
REC with real visual repair               up to 4–5min
Normal REC >5min                          operational incident
8min+                                     unacceptable before scaling P1/REC+P1/SEO
```

## Benchmark after patch

After changing runner telemetry/cache, run at least one `status=draft` benchmark with a complete REC request and inspect:

```text
duration_sec
unattributed_sec
instrumented_total_sec
term_cache.cache_hits
term_cache.cache_misses
wp_resolve_terms_sec
wp_create_post_sec
wp_update_yoast_sec
yoast_score_sec
cache_save_sec
public_verify_sec
```

Do not declare REC throughput solved from a dry-run alone. Dry-run validates code path and cache mechanics, but only a real draft publish measures WordPress/Yoast/public verification latency.

## Pitfalls

- Do not continue diagnosing REC slowness from coarse logs if the runner lacks timing fields. Add ticks to the runner first.
- Do not treat `mgs-rec-api` connection refused as a blocker for runner tests; the runner can fall back to deterministic local generation. Report the warning, but continue unless the benchmark specifically needs API-local generation.
- Do not expose credentials while checking WordPress timings. Show item names and lengths only if credential lookup is relevant.
- Do not start REC+P1/P1/SEO scale work until REC normal path is consistently within SLA and `unattributed_sec` is small enough to trust the breakdown.
