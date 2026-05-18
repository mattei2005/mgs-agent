# REC benchmark audit — Zable draft (2026-05-18)

Use this as a concrete audit pattern when Rodolfo asks whether a post-REC benchmark actually proved the fast-path workflow.

## Case summary

Thread `1505988988836778086` produced draft post `62084` for `Zable Credit Card` on `eggbev`.

User-facing result looked successful:

```text
Post ID              62084
Status               draft
Yoast                SEO 88 / Readability 90
Word count           475
Card image           62082
Featured image       62083
Thread elapsed       ~6m36s
```

But operationally it was only a **partial benchmark pass**. It proved Atena can recover and create the draft, but it did **not** prove the ideal high-production path of `one mgs-rec-runner.py command -> JSON -> one final summary`.

## What actually happened

```text
Step                         Evidence / outcome
---------------------------- ------------------------------------------------
Runner attempt 1              Failed with unsupported flags: --vertical / --official-url
Runner attempt 2              Correct flags, but cache MISS hit Anthropic-disabled extraction path
Manual recovery               Atena manually fetched official facts, image, uploads, terms, post
Final delivery                Draft created successfully
Benchmark quality             Weak: no runner duration_sec/timings_sec in final report
```

Durable lesson: a created post is not enough to validate REC speed. For benchmark claims, confirm the actual path from Atena's session/logs.

## Audit checklist for future REC benchmarks

1. Import/read the Discord thread, but do not rely on the final summary alone.
2. Inspect Atena session/logs for the actual execution path:
   - Did it call `mgs-rec-runner.py` with supported flags?
   - Did it complete as one runner run?
   - Did it drift into manual `search-card-image.sh`, `upload-image.sh`, term resolution, `create-post.sh`, or `update-yoast.sh` outside the runner?
3. Require benchmark evidence in the final summary:
   - `duration_sec`
   - `timings_sec`
   - `term_cache.cache_hits/cache_misses`
   - `steps`
   - `warnings`
4. If those fields are missing, classify the benchmark as **post delivery validated, fast-path not validated**.
5. For cache-miss cards, either:
   - provide explicit official facts (`--annual-fee`, `--apr`, repeated `--benefit`, competitors), or
   - make the runner's extraction path use the approved provider instead of Anthropic.

## Draft URL interpretation

For draft posts, public URLs usually return 404. Do not mark this as failure.

```text
Draft post public URL     404 expected
Future permalink          useful for reference, not currently public
CTA/P1 apply URL          404 expected in REC-only if P1 not created yet
Media URLs                should return 200
WP REST/edit context      should confirm status=draft and featured_media
```

User-facing wording should say `URL pública futura` or `permalink futuro`, not imply the draft is currently public.

## Image QA lesson

The Zable card image was acceptable: horizontal 1600x900, Zable legible.

The featured image was technically valid 16:9 but editorially weak: card floating unnaturally, odd shadow/layer over the person, AI-composite look. For draft this is acceptable to send to Raquel for review; for publish/scale it should be flagged.

Add this distinction to reports:

```text
Featured technical gate    16:9 / media present / URL 200
Featured editorial gate    realistic integration, no floating card/suspicious layer
```

Do not call featured quality clean just because it is 16:9.

## Final verdict wording

Recommended verdict shape:

```text
Post delivery: OK.
Fast-path benchmark: partial fail / not proven.
Reason: Atena recovered manually after runner/cache-miss failures, so elapsed time includes manual workflow.
Next: fix cache-miss extraction or provide official facts before the next benchmark.
```
