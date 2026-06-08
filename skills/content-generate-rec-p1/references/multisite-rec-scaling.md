# Multi-site REC scaling and duplicate-content control

Use this when Rodolfo wants to publish the same credit card REC across multiple MGS sites/countries/domains.

## Core principle

Reuse **facts**, not finished copy.

The same card can appear on several MGS sites, but each domain should receive a distinct editorial package. This reduces SEO duplicate-content risk while keeping financial claims accurate and sourced.

## Reusable layer

Safe to reuse across sites when still current:

- Official source URLs
- APR, annual fee, fees, credit limit, eligibility facts
- Benefit list, short tags, descriptor
- Card image if accurate and rights/quality are acceptable
- Competitor set as a starting point
- Internal card cache entry

## Must vary per site

Generate uniquely per domain/template/audience:

- Post title
- Meta description
- Opening paragraph/subtitle
- Benefit explanations
- Comparative table wording and, when possible, competitor emphasis
- “Who is this card best for” positioning
- Closing paragraph
- Featured image scene if volume is high

Do not publish identical HTML/body copy across sites.

## Fingerprint enforcement

The runner now uses:

```bash
/root/mgs-agent/scripts/rec-fingerprint.py
```

Behavior:

1. Normalize candidate HTML into plain lowercase text.
2. Build 5-word shingles.
3. Compare against stored fingerprints for the same `card_slug` on other sites.
4. Warn when similarity is above threshold (`0.35` default).
5. Store the final published fingerprint with `--store` after publish.

Runner output path:

```text
validation.duplicate_fingerprint.status
validation.duplicate_fingerprint.max_similarity
validation.duplicate_fingerprint.comparisons[]
```

If status is `WARN_SIMILAR`, Atena must not claim duplicate-control is clean. For now the runner warns but does not block publish; for high-volume rollout, convert the warning into a hard fail or rewrite pass.

## Recommended same-card-multisite behavior

For a future `same-card-multisite` flow:

1. Build or refresh one factual cache entry from official URLs.
2. For each target site, load that site's template and audience/country settings.
3. Generate a fresh article body using the shared facts.
4. Compute a text fingerprint/similarity score against existing MGS REC bodies for the same card.
5. If similarity is too high, rewrite title/intro/benefit prose/table/conclusion before publishing.
6. Report shared facts + per-site unique fields in the final summary.

## Official-source handling

When the official URL is thin, ask for or discover supporting official URLs before writing. For Marbles, `/marbles-card/` was insufficient; the better source set was homepage + features + product-summary.

If official pages do not expose a clean card image, fallback image search is acceptable, but report the tier/domain and mark for editorial review.

## Plagiarism framing

- Copying bank text verbatim is the real plagiarism/legal risk; always paraphrase and keep factual claims anchored to official terms.
- Reusing our own text is not classic plagiarism, but it is an SEO duplicate-content risk.
- The target is “same facts, unique article.”
