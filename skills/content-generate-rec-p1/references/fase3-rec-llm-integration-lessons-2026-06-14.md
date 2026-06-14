# Fase 3 — REC LLM integration lessons (2026-06-14)

Context: Rodolfo is using Claude to draft Fase 3 packages, but Zeus must review every package against the live VPS state before applying. Several mismatches were caught because Claude worked from stale copies while the VPS had newer auto-committed files.

## Durable process rule

When Rodolfo forwards Claude output for REC/P1 migration:

1. Treat Claude as a design assistant, not source of truth.
2. Verify against live VPS files, git state, logs and service state before approving or applying.
3. If Claude says a string/rule "does not exist", run a live grep yourself and separate real contradictions from historical/reference hits.
4. Review both mechanism and merit: script safety is not enough; check whether the proposed architecture matches the current runner pipeline.

## Fase 3.0.1 fallback correction

A stale Fase 3 note had been written into active skill/reference state saying deterministic fallback was acceptable for draft/test and blocked for publish. Final Rodolfo decision:

- No automatic deterministic fallback in any status.
- Draft and publish use the same logic.
- Default body mode is LLM.
- If LLM fails: one regeneration, then block.
- Deterministic mode exists only behind explicit debug/reversion flags (`--rec-body-mode deterministic`, `--p1-body-mode deterministic`).

## Fase 3.1 Hermes CLI probe results

The isolated probe using `/root/.local/bin/hermes -p atena -z <prompt>` proved:

- GPT-5.5/OpenAI-Codex via Atena profile returns clean stdout with no banner/log noise.
- A real REC prompt with `cc-rec.md` + category map was ~23k chars, below the 90k hard gate.
- One REC body call took ~49s.
- Parser with fixed markers worked and extracted clean HTML.
- Gateway Atena remained stable: active before/after, same PID, no restart, no journal noise.
- Generated body was ~480 words, respected fixture facts, and showed better narrative specificity than deterministic Python.

Prompt lessons from the probe:

- Require H2/H3 to use the card name or a specific card/category angle; avoid generic headings like "Benefits of the Card".
- Require neutral, non-moralizing financial tone; avoid phrases such as "impulsive spender".
- Keep facts deterministic: GPT writes narrative only from confirmed facts.

## Timing / parallelism decision

Do not parallelize REC and P1 in early Fase 3. Two sequential LLM calls at ~49s each leave ~5.3 minutes of a 7-minute budget for gates, images, Yoast and publication. P1 also needs REC context to avoid repetition. Consider parallelism only after real REC+P1 metrics consistently exceed the SLA.

## Fase 3.2 REC runner design pitfalls

`generate_article_local(site, card_slug, card_data)` does two things:

1. Writes deterministic REC article body.
2. Derives structural metadata consumed by LazyBlock/card/button:
   - `card_data["tag10"]`
   - `card_data["tag2"]`
   - `card_data["descriptor"]`
   via `derive_lazyblock_tags(...)`, `card_ui_descriptor(...)`, and a `primary` value derived from confirmed benefits.

For the initial REC LLM integration:

- Do not replace the whole function blindly.
- Let GPT replace only the narrative/body generation.
- Preserve deterministic structural metadata derivation in Python.
- Prefer the smallest safe diff for 3.2: `generate_rec_body_llm(...)` may call `derive_lazyblock_tags`/`card_ui_descriptor` directly and replicate the small metadata block rather than refactoring `generate_article_local` immediately.
- Keep `generate_article_local` intact as explicit deterministic mode.
- `generate_article_local` had only one call site in the live file at the time of review, around the main pipeline call.
- No gate/renderer dependency was found on the exact string `local_deterministic_rec_contract_v2`; LLM mode can use `generator="llm_hermes_cli_rec"` while deterministic mode keeps the old generator string.

## Gate retry caveat

Retrying a failed Hermes call/parser is local to `generate_rec_body_llm`. Retrying when downstream gates fail is different: current validation happens after `api = generate_*` inside `build_and_validate_current`. If 3.2 promises regeneration on gate failure, the patch must explicitly wrap generation + validation so a failed validation triggers one new LLM call and a second validation. If that makes the patch too large, defer gate-failure regeneration to a follow-up package and say so explicitly.
