# GB-CC-EN Utility adaptation + rejected-copy rewrite — 2026-06-30

## Context

Rodolfo asked to continue the Utility Template approval workflow for `GB-CC-EN` after the `US-CC-EN` batch had produced 187 approved messages.

Goal for the next approval probe:

- take the 187 approved messages;
- adapt them for GB by replacing `$` with `£`;
- rewrite the messages that had been rejected / not part of the approved bank;
- prepare a CSV Rodolfo can upload in SB, link to one page, and submit for approval.

## Durable workflow

1. Start from the current approved-bank CSV, not from memory. In this session it was:
   - `/root/mgs-agent/work/meta-utility/us-cc-en-approved-187.csv`
2. Identify rejected/non-approved rows by comparing the canonical 200 tracker against the 187 approved texts using normalized text keys.
   - In this session, 14 tracker rows were not present in the approved 187.
3. For GB adaptation, replace currency symbols only where present:
   - `$15,000` → `£15,000`
   - `$14,200` → `£14,200`
   - Validate `dollar_symbols_remaining == 0`.
4. Rewrite the missing/rejected rows as fresh utility/status-style credit-card messages.
   - Do not mechanically reuse the rejected wording.
   - Keep credit-card-specific framing.
   - Avoid fake guaranteed approval, official release, package/courier dominance, or unsupported claims.
5. Pull the exact target template link sequence from SB for the GB template. Do not reuse US links or invent a neat rotation.
6. Assemble the import CSV with the original SB 9 columns only:
   - `MESSAGE ID,TEXT,DESCRIPTION,IMAGE,CTA 1,LINK 1,CTA 2,LINK 2,TEXT 2`
7. Export import CSV as UTF-8 BOM + CRLF when emojis are present.
8. Validate before reporting ready:
   - row count;
   - required columns;
   - no empty `TEXT`, `CTA 1`, `LINK 1`;
   - no exact duplicate texts;
   - target-template links repeat in the exact extracted order;
   - no `$` remains for GB;
   - zip contains CSV(s) plus `_audit.json`.

## Session artifact shape

The useful output shape was a zip containing:

- adapted approved-bank CSV (`187` rows);
- full approval probe CSV (`187 + rewritten rejects`, here `201` rows);
- `_audit.json` with source file, target template name, extracted link count, row counts, rewritten IDs, encoding, hashes and sizes.

Example artifact path from this session:

- `/root/mgs-agent/work/meta-utility/gb-cc-en-utility-test-201-newsoun-links.zip`

## Pitfalls

- Do not assume `GB-CC-EN` means only currency replacement. Rejected/non-approved messages still need fresh rewrite before the next probe.
- Do not use US `LINK 1` values in GB batches. Use the exact GB template sequence from SB.
- Do not simplify links to `mct-001..N` if the source template has a different order, duplicates, `-2` variants, or query params.
- Do not treat the 187 approved-bank CSV as proof that all 200 original candidate messages passed. Compare against the tracker to find missing/rejected rows.
