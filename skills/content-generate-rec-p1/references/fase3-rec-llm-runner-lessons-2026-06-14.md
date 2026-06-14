# Fase 3 REC LLM runner lessons — 2026-06-14

Context: Pacote 3.2A attempted to move REC body generation from deterministic Python to GPT-5.5 via Hermes CLI inside `scripts/mgs-rec-runner.py`.

## Durable lessons

1. **Telemetry must be propagated from `api` into the runner result JSON.**
   - Returning `body_generation` from `generate_rec_body_llm()` is not enough if `main()` only uses `cost_usd` and `card_data`.
   - The success result should include at least `generator`, `body_generation`, `article_body_chars`, and a preview/path for dry-run inspection.
   - Failure result should also include `body_generation` when the LLM blocks after retries.

2. **Avoid nested failure telemetry.**
   - If a helper receives a mutable `telemetry_sink`, do not write `telemetry_sink["body_generation"] = body_generation` when the final JSON uses `"body_generation": rec_body_telemetry`.
   - Prefer:
     ```python
     telemetry_sink.clear()
     telemetry_sink.update(body_generation)
     ```
   - This keeps failure JSON flat: `body_generation.mode`, `body_generation.attempts`, `body_generation.blocked_reason`.

3. **Validate against the real article gates, not just parser success.**
   - A real dry-run proved Hermes CLI + parser worked (`rc=0`, markers parsed), but `validate-article.sh` failed.
   - Current REC validation gates include:
     - visible word count 450–500;
     - first visible `<p>` is subtitle/excerpt and must be <=100 chars;
     - average paragraph words <=30;
     - max paragraph words <=30;
     - max paragraphs under one H2 <=4;
     - long sentence ratio (sentences >20 words) <=20%.
   - Prompt must explicitly instruct these gates with margin: first `<p>` <=95 chars, paragraphs <=28 words, sentences preferably <=20 words, target 460–490 visible words.

4. **Do not leave a default-path change applied after a failed smoke.**
   - If `--rec-body-mode` default becomes `llm` and dry-run fails, revert to the previous SHA before reporting.
   - Keep the generated JSON/body artifacts in `/tmp` for diagnosis, but do not leave production runner changed.

5. **3.2A and 3.2B should remain separate.**
   - 3.2A: GPT writes REC body; LazyBlock microcopy still Python.
   - 3.2B: GPT writes LazyBlock microcopy with strict negative guardrails.
   - Do not test “microcopy variation” as a 3.2A success criterion.

## Useful smoke pattern

- Apply package with SHA lock and backup.
- Run one dry-run LLM with explicit verified facts.
- Run deterministic mode to confirm old path still works.
- If either smoke fails after a default-path change, restore backup and verify SHA.
- Report parser telemetry separately from validation outcome.
