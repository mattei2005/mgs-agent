# Atena REC+P1 rewrite_from_article architecture — 2026-06-28

## Trigger

Rodolfo corrected the Atena REC+P1 architecture: creating content from scratch from the official card source is not viable for the desired output. The normal mode must be rewriting from an article-base URL, using Raquel's REC/P1 markdown/contracts as the target model.

## Durable decision

Normal Atena REC+P1 production should use:

```text
article-base URL -> extract facts/structure/angle -> reconstruct in MGS REC/P1 model -> validate anti-plagiarism -> publish/draft
```

The official/product URL remains required for:

- P1 external CTA / apply link;
- sensitive-claim validation where available;
- blocking product/URL mismatch.

But it is no longer the primary editorial source for normal article generation.

## Architecture implications

Patch/update these layers together when implementing or auditing this class of change:

- `skills/content-generate-rec-p1/SKILL.md` — mode, input contract, operational flow, anti-plagiarism gate.
- `skills/content-generate-rec-p1/contracts/cc-rec.md` — REC article-base rewrite contract.
- `skills/content-generate-rec-p1/contracts/cc-p1.md` — P1 article-base rewrite contract.
- `scripts/mgs-rec-p1-orchestrator.py` — require and pass `--article-url`.
- `scripts/mgs-rec-runner.py` — consume article-base, feed REC LLM prompt, block old official-only mode except explicit debug/reversal flag.
- `scripts/mgs-p1-runner.py` — consume article-base facts; next phase should move body generation to LLM rewrite mode too.

## Anti-plagiarism pattern

Do not treat rewrite as synonym swapping. Require editorial reconstruction:

- different opening;
- different phrasing;
- changed ordering when useful;
- new examples/transitions;
- facts preserved, surface text not preserved;
- block long contiguous copied spans from the article-base.

A first-pass deterministic gate can check `longest_common_word_run` and block if a long run is copied (session used threshold `>= 18`). This is a guardrail, not a complete semantic plagiarism detector.

## Verification pattern

If canonical tests do not exist for SKILL/contracts/reference changes, create an ad-hoc verification script under `/tmp` using a `hermes-verify-` prefix, execute it, then remove it.

For this class, useful checks are:

- changed markdown files exist/read;
- SKILL declares `rewrite_from_article`;
- SKILL requires article-base URL in normal flow;
- orchestrator example includes `--article-url`;
- official URL role remains documented for CTA/claims;
- REC/P1 contracts mention article-base and forbid sentence-by-sentence paraphrase;
- reference mentions affected runners and anti-plagiarism gate;
- no Git conflict markers.

Report this as **ad-hoc verification**, not as full suite green.

## Pitfall

The externally owned `content-generate-rec-p1` skill may be read-only to autonomous skill curation. If direct skill patching is refused, update this Company OS architecture umbrella with the architectural lesson and point future operators to the externally owned operational skill/reference.
