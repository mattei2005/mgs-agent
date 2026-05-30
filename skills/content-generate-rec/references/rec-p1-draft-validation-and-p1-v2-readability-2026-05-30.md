# REC+P1 draft validation + P1-v2 readability lessons — 2026-05-30

Session context: REC+P1 draft test for Eggbev / gb-cc-en / Barclaycard Rewards Credit Card after universal-contract and site.language refactor.

## What worked

- REC+P1 command used no `--lang`; production language correctly came from `site.language=en`.
- REC loaded `contracts/cc-rec.md`.
- P1 loaded `contracts/cc-p1.md` with `contract_mode=deterministic_python_from_versioned_spec` and `llm_runtime=disabled`.
- REC draft succeeded once verified request facts were supplied for missing facts/competitors.
- REC→P1 handoff worked via `https://<domain>/?p=<rec_post_id>` for a draft REC.

## Durable runner fixes discovered

### 1. Footer error phrases must not false-block valid issuer pages

Barclaycard’s valid product page contained footer/support copy similar to `we're truly sorry about this` about contact centre delays. A naive error-marker gate treated `sorry about this` as a full-page error.

Durable rule:

- Keep hard blockers for clear error-page markers (`page not found`, `try our search tool`, access denied, Cloudflare, etc.).
- Treat `sorry about this` as an error marker only when the page lacks product-specific hits and requested card/issuer terms.
- Apply the same logic in REC and P1 official-source gates so the runners do not disagree on the same URL.

### 2. Draft posts are not public-verifiable like published posts

A draft REC was created successfully but public verification hit `404` because draft URLs are not publicly visible. That is expected, not a content failure.

Durable rule:

- For `status=publish`, keep full public verification as a hard gate.
- For `status=draft`, skip public HTTP verification and return a structured marker such as:
  `{"ok": true, "skipped": "draft_not_public", "url": ...}`.
- P1 must do the same for draft mode.

### 3. P1-v2 deterministic filler must not create QA/readability failures

Initial P1-v2 deterministic expansion repeated fixed filler sentences until word count reached 900+. Semantic QA blocked repeated sentences. After de-duplicating filler, Yoast readability still blocked at `readability=60` even with SEO green.

Durable rule:

- Never loop over a tiny fixed filler set to reach word count.
- Track existing sentences before adding filler.
- Add enough unique, context-relevant sentences or expand core sections, not a tail of generic paragraphs.
- Avoid cutting subtitles at a fixed character boundary that can truncate words; truncate on word boundary and end with punctuation.
- Treat Yoast readability <70 as a P1-v2 generator quality blocker, not an operational success.

### 4. Partial P1 drafts can exist after post creation but before final validation

A P1 draft was created before Yoast readability failed. The runner cleaned failed featured media, but the partial draft post remained and slug conflict showed:

```text
apply-now-gb-cc-barclaycard-rewards-credit-card -> draft post ID 62408
```

Durable rule:

- After P1 failure post-creation, check for partial draft slug conflicts before rerunning.
- Either update the partial draft via `--update-post-id` or clean it explicitly after Rodolfo approves deletion.
- Do not blindly rerun and create duplicate/variant drafts.

## Known validation sequence for future REC+P1 draft tests

1. Run orchestrator in draft with exact official URL and no `--lang`.
2. If extraction misses required visible facts, supply verified request facts via `--annual-fee`, `--apr`, `--benefit`, and two real `--competitor` JSON values for gb-cc-en.
3. If REC succeeds but P1 fails:
   - preserve REC draft ID/URL;
   - inspect P1 blocker;
   - check for partial P1 draft slug conflicts;
   - rerun P1 standalone against `?p=<rec_id>` only after fixing the generator/blocker or with `--update-post-id` when appropriate.
4. Do not call a draft REC+P1 test clean unless both REC and P1 pass their validation gates.
