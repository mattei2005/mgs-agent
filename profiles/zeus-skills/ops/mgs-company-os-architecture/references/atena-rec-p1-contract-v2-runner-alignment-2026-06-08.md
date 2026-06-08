# Atena REC/P1 contract v2 + runner alignment — 2026-06-08

## Trigger

Rodolfo sent revised REC and P1 editorial contracts after Raquel optimized them, then approved specific decisions and asked Zeus to execute the runner alignment.

## Durable decisions

- P1 keyword count follows the new contract: **5–8 total uses**.
- REC meta description follows Rodolfo's correction: **130–140 visible characters**.
- REC structure follows the new contract, not the older runner/table-heavy structure. Reason: older examples of benefits were being interpreted too literally by Atena and created conflict.
- P1 structure follows the new contract, with a specific emphasis: P1 must explain more of what the card actually offers and deepen real benefits, instead of replicating REC phrases or generic blocks.
- P1 LazyBlock repetition is correct only for the **card image**: the same isolated card image is reused in REC and P1 LazyBlocks. REC and P1 featured/lifestyle images must remain different.
- Slug rules should be written in the clearest form for Atena/runners:
  - REC: `rec-{sigla-do-pais}-cc-{nome-do-cartao}`
  - P1: `apply-now-{sigla-do-pais}-cc-{nome-do-cartao}`
- The long featured-image composition spec should live as a supporting reference, with concise hard gates in the active contracts.

## Applied architecture pattern

1. Update contracts first:
   - `skills/content-generate-rec-p1/contracts/cc-rec.md`
   - `skills/content-generate-rec-p1/contracts/cc-p1.md`
   - `skills/content-generate-rec-p1/references/featured-image-visual-contract.md`
2. Then patch deterministic runners/validators to match the contracts before allowing production use:
   - `scripts/mgs-rec-runner.py`
   - `scripts/mgs-p1-runner.py`
3. Do **not** publish a real WordPress test during the contract/runner patch unless Rodolfo explicitly asks. Use dry-run/unit generation first.

## Runner alignment details

### REC runner

- Replace table/competitor-primary article structure with contract v2 structure:
  - intro
  - H2 benefits containing H3 benefit sections
  - points to consider
  - recommended profile
  - pros/cons
  - final soft transition to P1
- Enforce REC meta description 130–140 chars in both generator and validation gate.
- Keep word count 450–500 and aim near 470+ when possible.
- Keep QA style gates: paragraph max, sentence length, semantic anti-boilerplate.
- Avoid repeated phrases such as “for the reader” across every benefit; semantic QA blocks impersonal/repeated copy.

### P1 runner

- Generate four WordPress Details blocks:
  - Benefícios
  - Quem deveria usar
  - APR, taxas e custos
  - Requisitos para solicitar
- Keep image flow: excerpt → featured/main image → introduction → LazyBlock → rest.
- Reuse card image from REC LazyBlock; do not treat this as a duplicated featured image.
- Validate P1 keyword count as visible editorial text only, excluding LazyBlock JSON and image alt text to avoid false over-counting.
- Generate title/meta using the full card name when length allows, so keyword count can land in 5–8 without stuffing body copy.
- Validate P1 meta 130–150 chars.

## Validation pattern used

Minimum validation before reporting success:

```bash
python3 -m py_compile /root/mgs-agent/scripts/mgs-rec-runner.py \
  /root/mgs-agent/scripts/mgs-p1-runner.py \
  /root/mgs-agent/scripts/mgs-rec-p1-orchestrator.py

git -C /root/mgs-agent diff --check -- \
  scripts/mgs-rec-runner.py scripts/mgs-p1-runner.py
```

Then run:

- REC dry-run with explicit safe facts and competitors; confirm `success=true`, word count, semantic QA, meta chars 130–140, slug.
- P1 unit generation (function-level if full P1 requires an existing REC); confirm 4 Details blocks, 2 LazyBlocks, word count 900–1000, visible keyword total 5–8, semantic QA OK.
- Confirm `HEAD == origin/main` because auto-push may commit in several small watcher commits.
- Append an event to `logs/events-audit.jsonl` with paths, validations and commit.

## Pitfalls

- Do not stop after contract update. If contract promises structure the runner cannot produce, Atena will report compliance while output violates the new editorial standard.
- Do not count keyword occurrences inside LazyBlock JSON or image alt text for P1 keyword range; count visible editorial text fields.
- Do not copy long visual composition specs into every contract. Keep concise contract gates and one reference file for the full visual brief.
- Do not reintroduce older example-benefit lists as if they were mandatory benefit choices; they caused Atena to use examples as the actual benefits.
