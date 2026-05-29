---
name: content-generate-rec
description: Operates MGS credit-card REC, P1 and REC+P1 production through the approved runners/orchestrator, using the active GB-CC-EN contract as the editorial source of truth and no editorial card cache.
---

# content-generate-rec

## Purpose

Use this skill when Rodolfo/Raquel asks Atena to create, update, audit or report credit-card content of type REC, P1 or REC+P1.

This skill is now intentionally short. It is an operational routing guide, not the editorial rulebook.

Active editorial rules live in:

```text
/root/mgs-agent/skills/content-generate-rec/contracts/gb-cc-en.md
```

Historical lessons live in `references/` and `references/archive/`. They are not active production rules unless a rule has been promoted into the contract or runtime validators.

Refactor sequencing reference: `references/rec-p1-refactor-sequencing-no-cache.md` captures the durable process rule for REC/P1 architecture changes: active content map first, one current ordered plan, REC+P1 as one business request/two technical generations, and no editorial card-cache in production.

Benchmark reference: `references/rec-p1-orchestrator-benchmark-nationwide-2026-05-27.md` captures the first post-refactor live REC+P1 orchestrator validation pattern, including invalid manual image handling, no-cache evidence, semantic QA reporting and post-publish metadata repair disclosure.

Production blocker reference: `references/rec-p1-production-blockers-and-cleanup-2026-05-27.md` captures the corrected rule after Rodolfo's review: official URL/card mismatch blocks before publish; failed/uncertain card image blocks instead of falling back silently; bad publish cleanup must remove posts, operation media and bad fingerprints after explicit confirmation.

Orphan media cleanup reference: `references/rec-p1-orphan-media-cleanup-2026-05-27.md` captures the durable cleanup lesson from the Nationwide benchmark: failed attempts can upload WordPress media before post creation, so cleanup must search by card slug/timestamp for orphan attachments, not only delete media IDs from the final published posts.

Visible fallback/boilerplate gates reference: `references/rec-p1-visible-fallback-and-boilerplate-gates-2026-05-27.md` captures Rodolfo's correction that `Not stated...` text, generic LazyBlock tags, and repeated P1 eligibility/application boilerplate are scale blockers; durable rules must live in the contract or runtime validators, not scattered references.

LazyBlock tags/opening gates reference: `references/rec-p1-lazyblock-tags-and-opening-gates-2026-05-27.md` captures Rodolfo's correction that technically valid REC/P1 can still be too generic; tags must be commercial, non-redundant and non-fragmented, and openings must lead with user outcome/problem rather than product inventory.

Manual low-res image scope reference: `references/manual-low-res-card-image-scope-2026-05-27.md` captures Rodolfo's correction that small user-supplied card images can publish after normalization; size below 600px is warning-only when identity/semantics pass.

Manual banner extraction reference: `references/manual-banner-card-extraction-and-rotation-2026-05-28.md` captures Rodolfo's correction from the HSBC Rewards run: if a supplied manual card image is a banner/canvas with a vertical card inside, extract the actual card, remove headline/canvas, rotate the card horizontal, regenerate featured images, and verify public pages no longer reference the bad asset.

Manual card image quality reference: `references/manual-card-image-quality-and-lazyblock-context-2026-05-28.md` captures the follow-up HSBC Rewards correction: extraction/rotation is not enough; the final LazyBlock card must be visually acceptable in context, using a better official/source-safe asset when available, and low-res/upscaled/pixelated/notched outputs must be reported or repaired.

Rule consolidation / flow review reference: `references/rec-p1-rule-consolidation-and-flow-review-2026-05-28.md` captures Rodolfo's anti-bola-de-neve correction: after multiple REC/P1 repairs or new rules, produce a reviewable initial flow for Rodolfo/Raquel and consolidate approved lessons into the active contract/runtime gates rather than letting references become competing production rule sources.

Featured image separation reference: `references/rec-p1-featured-image-separation-2026-05-28.md` captures Rodolfo's correction that REC and P1 must not share the same featured image; they need distinct media IDs, URLs and visual concepts, with REST/public verification before success is reported.

Featured card identity overlay repair reference: `references/featured-card-identity-overlay-repair-2026-05-28.md` captures the durable RBS Reward Black workaround: when generative featured images alter card identity, add a second card, or produce CGI/prohibited artifacts, generate/select a no-card realistic background and overlay the validated real card asset locally, then audit before publish.

REC top-of-page ad keywords reference: `references/rec-top-of-page-ad-keywords-and-commercial-context-2026-05-27.md` captures Rodolfo's correction that REC is the commercial/monetisation heart of REC+P1: the title/summary and first 1-2 paragraphs appear before the mobile ad and must carry high-value intent keywords plus user pain/outcome before the card/P1 button.

Raquel editorial benchmark reference: `references/rec-p1-raquel-editorial-benchmark-2026-05-27.md` captures the durable REC/P1 lesson that technical correctness is insufficient; openings, LazyBlock tags and first benefit blocks must sell the user outcome, especially debt relief/interest pressure for balance-transfer cards.

Editorial production lessons reference: `references/rec-p1-editorial-production-lessons-2026-05-28.md` captures follow-up REC/P1 lessons from the NatWest Travel Reward run: REC is the pre-ad monetisation bridge, missing card images should be searched independently, travel/rewards framing outranks generic low-rate framing, and final QA must inspect intent alignment, not only machine pass/fail.

Perceived-benefit tone reference: `references/rec-p1-perceived-benefit-tone-and-table-scope-2026-05-28.md` captures Rodolfo's correction that technical benefits must become perceived user benefits, `gb-cc-en` REC comparison tables should stand alone without generic aftertext, and P1 intros should use compact 30–35 word mobile paragraphs. Table requirements are vertical-scoped, not global.

Vertical table-scope reference: `references/vertical-table-scope-gb-cc-en-only-2026-05-28.md` captures the explicit correction that article comparison-table requirements apply only to `gb-cc-en` unless another vertical contract independently requires them.

Experience-led category map reference: `references/rec-p1-experience-led-category-map-2026-05-28.md` captures Rodolfo/Raquel's scale correction that REC/P1 must adapt tone by card category and hybrid combinations, writing from real user routine/emotion/experience rather than banking features, without copying examples or inventing benefits.

Experience-led runner gates reference: `references/rec-p1-experience-led-runner-gates-hsbc-2026-05-28.md` captures the durable HSBC Rewards benchmark: generic `N/A` visible facts must be replaced only with verified official/request facts, rewards benefit copy must vary by benefit type, padding helpers must not reintroduce impersonal language, and P1 can be rerun standalone after a clean REC if only P1 failed.

Cross-corpus boilerplate audit reference: `references/rec-p1-cross-corpus-boilerplate-audit-2026-05-28.md` captures Rodolfo's correction from the RBS Reward Black run: P1 can pass REC↔P1 semantic QA while still repeating full sentences from older P1s; fixed filler and deterministic category buckets must be treated as scale blockers unless guarded by cross-corpus duplicate QA.

## Authority model

```text
1. Current user request
2. contracts/gb-cc-en.md
3. runner/orchestrator hard gates and validators
4. data/sites.json
5. historical references only when explicitly needed for audit/migration
```

Do not choose between many old reference files during normal production. If a rule matters, it belongs in the contract or in runtime validation.

## Architecture triage / explaining the file surface

When Rodolfo sends GitHub/file-search screenshots or asks what a REC/P1 file list means, answer as architecture triage, not as production execution. Separate the surfaces clearly:

```text
Editorial active     -> contracts/gb-cc-en.md; templates only if explicitly still used/derived
Runtime              -> mgs-rec-runner.py, mgs-p1-runner.py, mgs-rec-p1-orchestrator.py, validators
Publishing/infra     -> content-publish-wordpress/SKILL.md + WordPress scripts
Historical/reference -> references/*.md and references/archive/*
Technical cache      -> sites.json, wp-term-cache.json, rec-fingerprints.db
Editorial cache      -> data/card-cache.db; not allowed as production content source
```

If asked whether `references/*.md` are a cache for redoing articles, say no: they are lesson logs / incident references / historical rule evidence. The reusable production source should be the active contract and runtime gates, not a flat pile of dated references. The actual dangerous editorial cache is `data/card-cache.db`, because it can preserve facts/positioning and influence future articles if used.

When counting “route files” for a refactor or Lovable-style architecture map, do not inflate the core route with every helper. Count central route files first; add auxiliary files only if imported/called in the real flow or if they carry operational authority. `content-publish-wordpress/SKILL.md` exists and should be counted as publishing/infra authority, not REC/P1 editorial authority.

## Rule consolidation / anti-bola-de-neve

When a REC/P1 session produces several corrections, repairs or new rule candidates, do not let the library turn into a long flat list of active one-off instructions. Use references as incident evidence only, then promote approved durable behavior into the active contract and/or runtime validators.

Rodolfo/Raquel review format should start from the clean initial flow, not from the incident history:

```text
request -> source/card identity validation -> LazyBlock image validation -> REC -> P1 -> distinct featured images -> public/link/Yoast verification -> final evidence report
```

Treat the card image as a pre-publication dependency because a bad LazyBlock asset contaminates REC, P1, featured images, public QA and cleanup.

## Product model

```text
REC     = short recommendation article; routes reader to P1.
P1      = longer complementary article; routes reader to official issuer/bank.
REC+P1  = one operational request that creates two separate articles.
SEO     = separate future product; out of scope for this skill.
```

REC+P1 is not a third article template. It is one business operation composed of a REC generation and a P1 generation.

## No editorial cache policy

Production content must not use editorial card cache.

Do not use `data/card-cache.db` or `card-cache-*` scripts as source of truth for:

- benefits;
- rewards;
- APR;
- annual fee;
- eligibility;
- descriptor/tag/headline;
- body copy;
- table copy;
- opening angle;
- official URL, unless Rodolfo explicitly approves a temporary manual fallback;
- card image, unless validated in the current run.

Allowed technical caches/data:

- `data/sites.json` for site config;
- `data/wp-term-cache.json` for WordPress taxonomy IDs;
- `data/rec-fingerprints.db` or successor QA DB for similarity history;
- logs/audit files.

Transition rule: until the runners are fully refactored, always pass the current official URL explicitly. If runner output shows content came from `card-cache`, `cache_hit`, or missing official URL fallback from cache, report it as a migration blocker instead of claiming clean production success.

## Normal REC operation

Use the REC runner. Do not manually reproduce the whole workflow unless the runner fails with a clear error and Rodolfo approves the fallback.

The legacy `mgs-rec-api` path is intentionally disabled. Do not restart or depend on it during production. REC generation should use the current deterministic local path from official/request facts and then pass validators/QA.

Command shape:

```bash
/root/mgs-agent/scripts/mgs-rec-runner.py \
  --site <site_key> \
  --card "<exact card name>" \
  --status <draft|publish> \
  --source-url "<official issuer URL>" \
  [--card-image-url "<direct card image URL when supplied>"]
```

Requirements:

- Load/follow `contracts/gb-cc-en.md` for editorial rules.
- Use current official source.
- Do not rely on editorial cache.
- Treat REC top-of-page as a monetisation surface: the title/summary and first 1-2 paragraphs appear before the mobile ad and before the card, so they must carry the strongest commercial intent keywords and user pain/outcome before any generic explanation.
- Convert technical benefits into perceived user benefits throughout the REC: make the reader imagine the card in practical use, not merely read extracted facts.
- Use a professional, accessible, confident and human tone; persuasive without exaggeration, never cold product inventory.
- For `gb-cc-en` REC only: when the contract includes a comparison table, let it stand alone. Do not add generic post-table explanation paragraphs (`Compared with...`, `The table is a quick orientation tool`, `Rates and terms can change`). Use the space for a useful next section. Do not carry this table requirement into other verticals unless that vertical contract explicitly requires it.
- For balance-transfer REC, lead with `0% interest`/`interest-free`, duration, debt/repayment pressure, interest savings and transfer-fee trade-off when supported by facts.
- If Rodolfo/Raquel do not supply a card image URL, search independently before blocking. Prefer the official issuer page/static assets first, then source-safe web image candidates. Do not publish until the selected image passes identity/semantics/normalization validation.
- Treat REC top-of-page as a monetisation surface: title/summary and first 1-2 paragraphs appear before the mobile ad/card, so they must carry high-value commercial intent keywords plus user pain/outcome before any generic explanation.
- After runner completion, inspect JSON for validation status, warnings, timing and any cache-related steps.
- Do not report success if public verification, image validation, Yoast/readability gate, or required links fail.

- Do not report success if public verification, image validation, Yoast/readability gate, or required links fail.

## Normal P1 operation

Use the P1 runner for standalone P1 or for a P1 linked to an existing REC.

Command shape:

```bash
/root/mgs-agent/scripts/mgs-p1-runner.py \
  --site <site_key> \
  --rec-url "<published REC URL>" \
  --official-url "<official issuer URL>" \
  --status <draft|publish>
```

Requirements:

- Load/follow `contracts/gb-cc-en.md` for P1 rules.
- P1 must use current official source facts.
- P1 must not copy REC body/opening/benefit prose.
- P1 must not reuse full sentences, deterministic filler, or application/eligibility boilerplate from older same-vertical P1s. Cross-corpus repetition is a production blocker even when REC↔P1 similarity passes.
- P1 must not depend on card-cache facts.
- P1 must derive its own LazyBlock tags/descriptor from current official/request facts; do not preserve REC `tag10`, `tag2`, or descriptor by default.
- P1 opening must lead with why the card matters to the user before fees/application mechanics.
- P1 introduction paragraphs should be compact for mobile, normally around 30–35 words each; split dense intros instead of packing multiple ideas into one paragraph.
- P1 framing must match the actual card intent. Travel/rewards signals in the card name or benefits outrank generic low-rate framing even when the card also mentions no foreign transaction fees/no annual fee.
- P1 benefit sections should translate facts into perceived value and real usage: how the benefit feels in trips, purchases, repayments, budgeting, or partner spending.
- P1 structure and tone should flex with the card identity and audience (technical, premium, relaxed, sales-oriented, institutional, young, sophisticated), rather than forcing every card into the same rigid section voice.
- After publishing or updating, manually inspect the first visible paragraphs and major headings for intent alignment; machine QA can pass while the editorial frame is still wrong.
- P1 CTA must route to the official issuer/bank URL.

## Normal REC+P1 operation

Business behavior: Rodolfo/Raquel asks once and receives both articles.

Technical behavior: REC and P1 are generated/validated separately by the orchestrator. Use the orchestrator as the normal entrypoint; do not run manual REC then P1 unless debugging a failed orchestrator run.

For `status=publish`, the orchestrator must stop before creating posts if either of these are true:

- the requested card name and official URL appear inconsistent;
- no card image can be found/validated after searching official/source-safe candidates when Rodolfo/Raquel did not supply one;
- the supplied or found image fails identity/semantics/normalization validation.

If Rodolfo/Raquel do not specify a card image URL, search independently before blocking. Prefer the official issuer page/static assets first, then source-safe web image candidates. Do not publish until the selected image passes identity/semantics/normalization validation.

Manual image quality/size scope: if Rodolfo/Raquel supplied the image and card identity plus normalization pass, useful crop width below 600px is warning-only when the final LazyBlock rendering is visually acceptable. The image quality rule still applies: prefer a better official/source-safe asset when available; report low source resolution, visible pixelation or forced upscaling as `LOW_QUALITY_SOURCE` unless replaced; block if final rendering is visibly poor, fake-looking, broken, clipped, notched, canvas-contaminated or identity-damaged.

- Manual banner/canvas scope: if Rodolfo/Raquel supplied a card image URL that is actually a banner, thumbnail or article graphic with the card inside it, do not upload the whole image into LazyBlock. Extract the internal card object, remove headline/canvas/decorative background, rotate the card to horizontal if the card itself is vertical, then build a LazyBlock-safe presentation asset: centered, padded, and previewed against the actual card-container background so CSS does not expose clipped edges/notches from fragile transparency. Use that corrected card asset for both LazyBlock and featured-image generation. Verify public REC/P1 no longer reference the bad banner/intermediate assets.
- REC/P1 featured-image separation: REC and P1 must never end the operation with the same WordPress featured image. Use different media IDs, URLs and visual concepts. REC should be the short commercial hook image; P1 should be a clearly different application/deep-dive support image. Before reporting success, verify REST/public pages show distinct `featured_media` IDs and distinct featured URLs; if they match, repair first. If Rodolfo says `aplique a regra` after correcting an image issue, promote the lesson into the contract/SKILL/runtime gate where possible, not only into the current post repair.
- Featured card identity repair: if generated featured images alter visible card text/branding, add a second/different card, or produce CGI/prohibited card renders, stop retrying full-card generation. Use a realistic no-card background and overlay the validated real card asset locally, then audit with `scripts/audit-featured-image.py` before upload/publish. Report the blocked generated attempts and clean any temporary bad media.

Do not silently use automatic card-image fallback for published REC+P1 after a manual image fails identity/semantics/normalization. Ask Raquel/Rodolfo for a corrected image URL and resume only after it is supplied.

```bash
/root/mgs-agent/scripts/mgs-rec-p1-orchestrator.py \
  --site <site_key> \
  --card "<exact card name>" \
  --status <draft|publish> \
  --official-url "<official issuer URL>" \
  [--card-image-url "<direct card image URL when supplied>"]
```

If the official page extraction cannot produce enough structured facts, pass current verified request facts such as `--benefit`, `--annual-fee`, `--apr` and two real `--competitor` JSON values. Do not use editorial cache.

If extraction returns a generic visible fact like `N/A`, do not publish that value and do not infer a better one. Fetch the official fact or pass a verified request fact. For rewards cards, make benefit copy vary by benefit type (welcome bonus, Pay with Rewards/offset, Mastercard acceptance, recurring payments, partner rewards, general points) so the P1 does not repeat one generic reward-value sentence.

If REC fails, P1 must not start. Treat this as the desired safety behavior, not a partial success.

REC→P1 handoff must be minimal:

```text
Allowed: card_name, card_slug, rec_post_id, rec_url, official_url, validated card_image_id/url.
Forbidden: REC paragraphs, REC opening, REC benefit prose, REC descriptor/tag by default, card-cache data.
```

## Final report requirements

For REC, P1 and REC+P1, the final response must include:

- article type;
- site;
- card name;
- REC URL when applicable;
- P1 URL when applicable;
- official issuer URL;
- validation status;
- image status; if no card image was supplied, report the image source you found and validation result; if supplied/found image is low-res but semantically correct and normalized, report it as a warning, not a blocker; if a manual image was a banner/canvas and required extraction/rotation, report that repair explicitly with the final media ID/URL and note page-context LazyBlock verification/padding; never silently use automatic fallback after identity/semantics failure;
- table status for REC only when the active vertical contract requires an article comparison table; currently this table requirement is scoped to `gb-cc-en`, not global across all future verticals;
- duplicate/similarity status when available, including REC↔P1 similarity and cross-corpus repetition against recent same-vertical posts when the runner/QA exposes it;
- semantic QA status for REC/P1 and P1-vs-REC similarity for REC+P1;
- public verification status;
- REC/P1 featured image separation status for REC+P1: distinct media IDs, distinct URLs and distinct visual concept;
- Yoast SEO/readability scores;
- total user-perceived operation time;
- warnings or blockers;
- any post-publish repair/revalidation performed;
- cleanup evidence for failed or bad operations, including orphan media search by card slug/timestamp when any attempt may have uploaded media before failing.

Do not report only runner duration if retries, repairs, QA or orchestration consumed additional time. Do not hide blocked attempts; summarize them as evidence that gates worked. Do not claim cleanup complete after deleting only final post/media IDs; verify failed-attempt orphan media as well.

Use the deterministic summary renderer when available:

```bash
python3 /root/mgs-agent/scripts/render-article-summary.py --type rec <rec-json>
python3 /root/mgs-agent/scripts/render-article-summary.py --type p1 <p1-json>
python3 /root/mgs-agent/scripts/render-article-summary.py --type rec-p1 <rec-json> <p1-json>
```

## When to inspect historical references

Inspect references only for audit, migration or debugging, not routine production.

Use references when:

- Rodolfo/Zeus asks for an audit;
- a runner fails and the error matches a known incident;
- migrating rules into the contract;
- validating whether an old rule is still relevant.

Do not use references to override the contract during normal article generation.

## Refactor state

Current approved state:

```text
1. Active content map — done
2. GB-CC-EN contract draft — done
3. SKILL.md reduction — done
4. Editorial cache removed from REC/P1 runners — done
5. REC+P1 orchestrator — done
6. Semantic QA validator integrated — done
7. First live REC+P1 benchmark — done
8. Additional benchmark/cleanup before broad scale — next
```

Use `mgs-rec-p1-orchestrator.py` for REC+P1. Use `qa-content-validator.py` evidence in final reports. Keep editorial `card-cache` out of production content.

Additional post-benchmark rule: a mechanically successful publish can still be operationally wrong if the source URL or card image identity is wrong. Treat source identity and card image identity as pre-publication hard gates, not warnings.

Additional editorial benchmark rule: a mechanically valid article can still be scale-blocking if it reads like a product inventory. For REC/P1 comparisons, promote Raquel-style patterns when they improve conversion: lead with the strongest user outcome, explain the pain being solved, use scannable benefit blocks, and treat fees as trade-offs instead of dry facts. For balance-transfer content, the default context is debt, interest pressure, repayment simplification, time to pay and financial control.

The pre-refactor long version of this skill was archived at:

```text
/root/mgs-agent/skills/content-generate-rec/references/archive/SKILL-pre-refactor-2026-05-27.md
```
