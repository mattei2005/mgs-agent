# REC Fast Runner Optimization Notes

Use this reference when optimizing or auditing REC publishing speed/cost, or when Rodolfo asks how to request the next REC so Atena avoids the legacy tool-calling loop.

## Baseline from Amex Cashback Everyday case

Observed legacy Atena/Hermes flow for a normal REC:

- Total session time: ~9m38s.
- Time after publish confirmation: ~7m42s.
- Article API incremental cost: ~$0.027174.
- Legacy reported session estimate: ~$1.2392, but this was an operational/token estimate, not the true incremental API cost under `openai-codex` subscription billing.
- Browser/Playwright was used locally for research/image fallback.
- Published output was valid: HTTP 200, Yoast SEO 88, Readability 90.

Conclusion: the article generation API was not the bottleneck. The bottleneck was agent roundtrips: many ReAct/tool-calling steps, repeated validations, browser use, and manual orchestration.

## Deterministic runner pattern

Normal REC requests should go through one deterministic command:

```bash
/root/mgs-agent/scripts/mgs-rec-runner.py \
  --site <site_key> \
  --card "<exact card name>" \
  --status <draft|publish> \
  --source-url "<official URL>"
```

Expected responsibilities of the runner:

- Load site/template config.
- Check local card cache before browser/research.
- Use official URL and provided data when available.
- Generate/assemble article with LazyBlocks.
- Enforce subtitle <=100 chars.
- Validate final visible word count 450-500.
- Apply deterministic padding/trim repair for mechanical failures instead of asking the LLM again.
- Validate article content **before** new WordPress media uploads to avoid orphan media when word-count/SEO validation fails.
- Rebuild/revalidate the exact final HTML after media IDs/URLs are known.
- Reuse cached card media when available; support `--card-image-url` as a manual override to skip image search.
- Return one JSON summary with `timings_sec`, cost estimate, URLs, IDs, validations, and errors.
- Create/update WordPress post and Yoast data when not in dry-run.

## Validation sequence for runner changes

Safe rollout order:

1. Create repo backup before modifying REC scripts/API.
2. `python3 -m py_compile` any changed Python files.
3. Check `mgs-rec-api.service` health:
   ```bash
   systemctl is-active mgs-rec-api.service
   curl -s http://127.0.0.1:8001/health
   ```
4. Run `mgs-rec-runner.py --help`.
5. Run a cache-HIT `--dry-run` smoke test first.
6. Only after dry-run succeeds, run a real `--status draft` test with a new card and official URL.
7. Publish directly only after the draft path is validated end-to-end.

## Mechanical repair lessons

Common article-validation failures should be fixed deterministically inside the runner before falling back to manual orchestration:

- Subtitle too long: rewrite only the first paragraph/subtitle to <=100 chars, preserving `<strong>{card_name}</strong>` when possible.
- Word count below 450 after subtitle shortening: insert a short generic compliance/comparison paragraph before the CTA/LazyBlock, then re-run validation.
- Word count slightly above 500 after API generation: trim prose once from the last normal paragraph before the CTA, never from the subtitle, LazyBlocks, or comparative table, then validate the exact final HTML again. Use a small safety margin (for example, excess + 3 words) because validator tokenization may differ from plain `.split()` counts.

Do not spend another LLM call on these mechanical failures unless deterministic repair fails.

## WordPress term resolution in runner

`resolve-term.sh` can fail with HTTP 400 `term_exists` even when the term is usable and the response body contains `data.term_id`. The deterministic runner should tolerate this by parsing `"term_id": <id>` from stderr/stdout and continuing with that ID instead of aborting publication.

This is especially important for common reusable tags such as `travel credit card`, `no annual fee`, issuer names, and other SEO tags that already exist on eggbev.

## Playwright/browser policy

Use browser/Playwright as fallback, not as the default path.

Preferred order:

1. Card cache HIT.
2. Official URL + curl/static extraction if enough.
3. Provided manual fields (`annual_fee`, `apr`, `benefit`, `competitor`).
4. Local Playwright fallback for image/search when scripts require it.
5. External anti-bot/proxy provider only if approved for strong Cloudflare/geo blocks.

Do not do browser-search loops when the user gave a valid official URL.

## Standard request template for Rodolfo -> Atena

Use this when Rodolfo wants a fast normal REC:

```text
Atena, publique direto um REC no eggbev.

Tipo: REC
Site: eggbev
Vertical/template: gb-cc-en
Status: publish
Cartão: [NOME EXATO DO CARTÃO]
URL oficial: [URL OFICIAL DO BANCO/EMISSOR]

Use o mgs-rec-runner determinístico, não o fluxo manual passo a passo.
Depois me envie o resumo final com:
Post ID, URL pública, edit link, Yoast, word count, subtitle chars, meta chars, imagens, custo e tempo.
```

For first validation of a new runner path, change `Status: publish` to `Status: draft`.

Optional fields to reduce research further:

```text
Annual fee: [...]
APR: [...]
Benefits:
- [...]
- [...]
Competitors:
- [...]
Card image URL: [...]  # optional; maps to --card-image-url and skips Bing/Playwright image search
```

## Current optimized runner behavior (2026-05-16)

The runner now follows this safer/faster order:

1. Load config + cache.
2. Extract/request/cache card facts.
3. Generate article via local API.
4. Assemble and validate content before any new WP media upload.
5. Upload/reuse card image and generate/upload featured image only after content validation passes.
6. Rebuild and revalidate final HTML with real media IDs/URLs.
7. Resolve taxonomy, create post, update Yoast, score, save cache, verify public URL.

A cache-HIT dry-run for `American Express Rewards Credit Card` validated in ~20s with `timings_sec.article_api_sec` around 20s and both pre-upload/final validation around 0.1s each.

## Reporting standard for optimization audits

When asked to review REC speed/cost, report:

- Step-by-step path actually used.
- Whether browser/Playwright was used and why.
- Total duration and post-confirmation duration when available.
- True incremental API/article cost vs any legacy token/session estimate.
- The bottleneck: LLM/tool roundtrips, browser fallback, image handling, Yoast/WP, or API generation.
- Concrete next change, with safe validation status (`dry-run`, `draft`, or `publish`).
