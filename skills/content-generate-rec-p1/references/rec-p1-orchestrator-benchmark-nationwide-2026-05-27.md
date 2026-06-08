# REC+P1 Orchestrator Benchmark — Nationwide Balance Transfer (2026-05-27)

## Why this reference exists

Captures the first controlled live publish after the REC/P1 architecture refactor:
- `mgs-rec-p1-orchestrator.py` created and used as the single REC+P1 entrypoint.
- editorial `card-cache` removed from REC/P1 runners.
- `qa-content-validator.py` added and integrated into REC/P1 runners.
- `content-generate-rec/SKILL.md` reduced to routing/authority only.

Use this as the durable benchmark pattern for future post-refactor REC+P1 validation runs, not as a one-off article narrative.

## Command pattern that succeeded

Use the orchestrator, not manual REC then P1, once available:

```bash
/root/mgs-agent/scripts/mgs-rec-p1-orchestrator.py \
  --site <site_key> \
  --card "<exact card name>" \
  --official-url "<official issuer URL>" \
  --status <draft|publish> \
  --benefit "<verified benefit>" \
  --competitor '{"name":"<same-segment competitor>","annual_fee":"<fee>","benefit":"<real benefit>","positioning":"<real positioning>"}' \
  --competitor '{"name":"<same-segment competitor>","annual_fee":"<fee>","benefit":"<real benefit>","positioning":"<real positioning>"}' \
  --timeout 2400
```

Pass `--official-url` explicitly. If the official page does not expose enough structured facts for the local generator, provide verified request facts (`--benefit`, `--annual-fee`, `--apr`, `--competitor`) from current official/comparable sources. Do not use editorial cache as fallback.

## Operational lessons

1. **User-supplied card images are not automatically authoritative.**
   - In the benchmark, the supplied image failed useful crop/quality checks.
   - The higher-quality original failed identity audit because it was a Nationwide FlexAccount Visa Debit, not the requested balance-transfer credit card.
   - Correct behavior: let the runner block the manual image, then use automatic current-run image discovery/fallback if allowed by the command path and validated by the semantic image audit.

2. **REC+P1 should remain one business request but use the orchestrator technically.**
   - User should not be bounced between Zeus/Atena during validation.
   - During migration/benchmark, Zeus can run the controlled publish directly.
   - After validation, Atena should route REC+P1 requests through the orchestrator.

3. **If REC fails, P1 must not start.**
   - The orchestrator correctly stopped when REC blocked on missing real competitors or invalid card image.
   - This is the desired failure mode: fix facts/image first, then proceed.

4. **QA evidence to report after publish.**
   Include:
   - REC/P1 URLs and post IDs;
   - official URL;
   - no-editorial-cache status;
   - `semantic_qa` status for REC and P1;
   - P1-vs-REC similarity value;
   - Yoast SEO/readability scores;
   - public verification status;
   - warnings/blockers, especially local-generator fallback or image fallback.

5. **Post-publish metadata repair can be valid but must be disclosed.**
   - In the benchmark, P1 meta description grammar was manually repaired after publish, then Yoast verification and score were rerun.
   - Do not hide repairs; report them as part of final validation.

## Known acceptable warning in benchmark context

`article_api_unavailable_local_generator_used` means the local generator path was used because `mgs-rec-api` was unavailable. This is not a content-cache fallback. It is acceptable for a controlled run if all validations pass, but it should be tracked before scaling.

## Successful validation thresholds observed

- REC semantic QA: `OK`.
- P1 semantic QA: `OK`.
- P1 vs REC 5-gram Jaccard: `0.0147` (well below warn threshold `0.14`).
- Yoast: REC 88/90, P1 90/90.
- Public verify: OK for both articles.

## Pitfall fixed in agent workflow

Do not tell the user “next step: Checkpoint A” and then switch to a different prerequisite. For REC/P1 architecture work, maintain one visible ordered sequence and correct it explicitly if the order changes:

1. active content map;
2. authority/read order;
3. contract;
4. skill reduction;
5. runner cache removal;
6. orchestrator;
7. QA validator;
8. benchmark.
