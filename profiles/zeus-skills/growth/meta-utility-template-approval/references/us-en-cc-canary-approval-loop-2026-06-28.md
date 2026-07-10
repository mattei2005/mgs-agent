# US EN CC Canary Approval Loop — 2026-06-28/29

Session-specific reference for the first MGS Meta Utility Template approval operation after the post-24h broadcast tag restriction.

## Context

Rodolfo provided SB group screenshots and Felipe's approved CSV for `US EN CC` credit-card utility-style Messenger messages. Meta/Facebook had blocked the old broadcast path after 24h, and Ciro's dashboard now supports template/message approval with `Run Approvals`.

Operational constants captured:

- MGS sends **12 messages per day per page**.
- Same message can often approve across multiple pages, but this must be validated in scale.
- Target bank: about **200 approved messages per page/cluster**.
- Current safe format: **TEXT + CTA 1 + LINK 1** only; no image, CTA2, text2, dynamic values, or second message until delivery is stable.
- Editing approved copy changes hash and resets approval.

## Important correction from Rodolfo

Rodolfo explicitly corrected the generation method: he wants **GPT/Zeus-written copy ideas**, using Felipe's approved examples as base. Do **not** use purely mechanical/permutation scripts as the creative source.

Correct split:

```text
GPT/Zeus/current model → write the actual copy ideas and angles.
Scripts/Python         → CSV formatting, numbering, dedupe, validation, Sheets/Drive upload.
```

A mechanical 150-copy batch was created first and submitted anyway. Treat its result as robot-learning/audit only, not as the canonical creative bank.

Canonical batch created afterward:

```text
GPT Real 200 = 50 Felipe seed messages + 150 GPT/Zeus-written new independent copies.
```

Sheet tabs created:

```text
README
Approved Seed 56
Canary New 150                 # deprecated/mechanical test
Combined 206                   # deprecated/mechanical test
Approval Tracker               # deprecated/mechanical tracker
GPT Real New 150               # canonical GPT-written new copies
GPT Real 200                   # canonical 200 total
GPT Real Tracker               # canonical approval tracker
```

## Workflow to repeat

1. Start from a real approved seed bank in the same language/vertical.
2. Ask GPT/Zeus to create new utility-style copies as standalone ideas, not permutations.
3. Keep claims neutral/status-oriented; avoid guaranteed approval, exact fake limits, fake courier/package/bank claims unless actually true.
4. Use script only to produce/import CSV with columns:

```csv
MESSAGE ID,TEXT,DESCRIPTION,IMAGE,CTA 1,LINK 1,CTA 2,LINK 2,TEXT 2
```

5. Validate:
   - row count;
   - no exact duplicate `TEXT`;
   - required fields `TEXT`, `CTA 1`, `LINK 1` filled;
   - image/CTA2/link2/text2 empty unless tech confirms support.
6. Upload to Sheet tabs through Sheets API when available.
7. Run approval in dashboard, F5, and fill tracker with approved/rejected/invalid.
8. Next batch should use only **real approved winners** from the latest run.

## Drive/Sheets handling

Initial Drive upload used CSV files plus a Sheet. After Sheets API was enabled and tabs were created, the CSV files in Drive were redundant and were moved to trash. Keep local VPS CSVs under `/root/mgs-agent/work/meta-utility/` for temporary audit/backup, but the Drive source of truth is the Sheet.

## Validation pattern used

Because scripts were created under `work/`, verification was ad-hoc, not full repo suite:

- create temporary verifier under `/tmp` with prefix `hermes-verify-`;
- `py_compile` the changed script;
- execute the real script;
- read generated CSVs and assert counts/required fields/no exact dupes;
- read back Sheets API tab counts;
- remove verifier;
- report explicitly as **ad-hoc focused verification, not suite green**.
