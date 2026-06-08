# REC/P1 visible fallback and boilerplate gates — 2026-05-27

## Why this exists

Rodolfo reviewed a failed Nationwide Balance Transfer REC+P1 benchmark and identified two scale blockers:

1. Extraction failure text leaked into visible content, e.g. `Not stated on the official product page` and truncated LazyBlock tags like `Not stated on the officia`.
2. P1 sections reused boilerplate across cards, especially eligibility/application paragraphs that appeared nearly identical between Santander and Nationwide.

At 25–30 sites and multiple countries/verticals, this becomes duplicate/plagiaristic content and cannot be handled by article-by-article human correction.

## Durable rules

- If a phrase could fit any card unchanged, it is not publishable P1 copy.
- `Not stated`, `N/A`, `unknown`, `check issuer terms`, and similar extraction failures may exist internally as raw flags, but must never appear in visible article text, LazyBlock tags, tables, subtitles, meta descriptions, or descriptors.
- LazyBlock labels must be product-specific. Generic labels like `Card benefits`, `Credit card`, or truncated extraction text must block.
- P1 must not pad missing benefits with generic filler. If fewer than enough specific facts are available, block and ask for better official/request facts.
- Eligibility/application sections must be rewritten around the specific card/use case, not reused as fixed boilerplate.
- Balance-transfer cards need their own angle: transfer window, transfer fee, repayment plan, post-promotional APR, and timing rules — not generic rewards/lifestyle copy.

## Correct implementation locations

```text
Rule/learning                         | Active location
--------------------------------------|-------------------------------------------
Visible fallback hard block            | qa-content-validator.py + REC/P1 runners
LazyBlock generic tag block            | REC/P1 runners
P1 boilerplate phrase block            | qa-content-validator.py
P1 product-specific copy generation    | mgs-p1-runner.py
Balance-transfer positioning           | REC/P1 runners
Editorial contract wording             | contracts/gb-cc-en.md
Incident-specific detail               | this reference
```

Do not solve this by adding another long reference as active instruction. Promote only durable rules into the contract or runtime validators.

## Known bad phrases to block

```text
Not stated on the official product page
The official source states Not stated...
Applications, eligibility checks and final lending decisions are handled by the issuer...
Therefore, the button sends you to the official card page.
Use this page as a decision-support step...
The issuer does not guarantee acceptance. It may assess credit history, income, affordability...
An eligibility check can help users understand whether acceptance is likely...
Only apply if the monthly cost, possible interest charges and repayment obligations fit your situation...
```

## Verification pattern

After changes, run at minimum:

```bash
python3 -m py_compile \
  /root/mgs-agent/scripts/qa-content-validator.py \
  /root/mgs-agent/scripts/mgs-rec-runner.py \
  /root/mgs-agent/scripts/mgs-p1-runner.py \
  /root/mgs-agent/scripts/mgs-rec-p1-orchestrator.py

# QA fixture with Not stated + known boilerplate must return BLOCK.
python3 /root/mgs-agent/scripts/qa-content-validator.py \
  --type p1 \
  --file /tmp/qa-bad-p1.html \
  --card 'Nationwide Balance Transfer Credit Card'

# REC fixture with annual_fee='Not stated on the official product page' must block.
# P1 balance-transfer fixture with good facts must generate without known boilerplate and tag10='Balance transfer'.
```

## Reporting rule

When reporting cleanup or validation after a failed publish attempt, include evidence for:

- visible fallback blocked;
- boilerplate blocked or absent;
- LazyBlock tag specificity;
- P1-vs-REC similarity;
- orphan media cleanup if any upload happened before failure.
