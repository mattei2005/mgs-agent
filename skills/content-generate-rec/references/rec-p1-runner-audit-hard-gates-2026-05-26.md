# REC/P1 runner audit hard gates — 2026-05-26

Context: Rodolfo asked Atena to use OpenHands/audit reasoning to find repeated mistakes in P1 and REC production. OpenHands was not configured for headless execution in that session, so the useful durable finding came from direct inspection of the deterministic REC/P1 runner contracts.

## Durable findings

### 1. `Review` must be a hard publish blocker

REC title generation still had a fallback shape equivalent to `Card Review`, and REC/P1 fallback copy also used the word `Review` in generic guidance. This conflicts with Rodolfo's permanent REC title/content rule: do not use the word `Review`.

Hard gate to encode in runners/validators:

- Block `Review` case-insensitively in `post_title`.
- Block `Review` case-insensitively in meta description and subtitle/excerpt unless Rodolfo explicitly approves a non-title exception.
- Prefer replacing fallback phrases with `Check`, `Read`, `Compare`, `See`, or `Review the issuer page` alternatives that do not include the forbidden word.

Recommended validation wording:

```text
Forbidden term gate failed: field=<title|subtitle|meta|body> term=Review
```

### 2. REC competitor fallback must not be hardcoded

A REC cache-miss extraction path used generic hardcoded competitors (`Barclaycard Platinum`, `Tesco Bank Credit Card`) when no competitors were extracted. That can publish irrelevant comparisons for non-comparable cards.

Hard gate:

- Competitors must come from one of: official/source extraction, cache, explicit runner arguments, or a vetted same-segment candidate analysis.
- If competitors are unavailable, use neutral comparison language or omit competitor names; do not inject a fixed UK pair.

### 3. Public verification must prove content, not only HTTP 200

REC public verification was too shallow if it only confirmed `http_status` and bytes. A successful publish report should verify key rendered facts:

- public URL returns expected 2xx/3xx for published posts;
- official/source URL appears in CTA or expected redirect context when applicable;
- LazyBlock card image URL appears in rendered content when a card image was expected;
- featured image URL is set and public;
- REC-only future P1 CTA 404 is reported as `P1 futura ainda não criada`, not as a hidden failure.

P1 verification already checks more of this; REC should be brought closer to P1's `contains_apply_now`, `contains_redirected`, `contains_official_url`, `contains_featured`, and `contains_card` style.

### 4. Yoast score should be treated as a gate when Rodolfo asks for publication-quality output

The runners scored Yoast after publish, but a bad score did not necessarily block the success report. For publication-quality tasks, the final summary must not call a post clean/fully validated if Yoast scoring failed or returned poor scores.

Recommended policy:

- If scorer errors: report as `Yoast não validado`, not clean success.
- If score is below the agreed threshold for the article type/site: stop or repair before final success, unless Rodolfo explicitly accepts the exception.
- Always distinguish `Yoast meta saved` from `Yoast score green`.

### 5. Deterministic speed must not hide weak editorial fallback

The REC runner is correctly optimized for speed, but cache-miss/local-generation fallback can produce technically valid yet editorially generic copy. When auditing repeated failures, check for this class separately:

- valid word count does not prove source specificity;
- generic benefits/fallback facts must be clearly labelled or blocked;
- official facts should be passed explicitly when source extraction is weak.

## Future audit checklist

When Rodolfo asks for an REC/P1 failure audit:

1. Inspect runner contracts/gates first; do not start a broad manual publishing workflow.
2. Check forbidden terms (`Review`), title/meta/subtitle limits, tags (`lang_*`, `atena_agent`), image gates, official-source gates, public verification, Yoast gate, and final-summary renderer usage.
3. Patch the runner/validator/template where the rule belongs; do not rely on Atena remembering the correction in chat.
4. Report only actionable failures and proposed fixes; avoid long environment/setup explanations unless they block the requested tool.
