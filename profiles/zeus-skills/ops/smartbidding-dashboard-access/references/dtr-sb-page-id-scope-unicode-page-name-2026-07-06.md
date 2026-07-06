# DTR/Bot ↔ SmartBidding PAGE ID audit — scope and Unicode PAGE_NAME correction — 2026-07-06

## Trigger

Use this note when auditing or correcting the cadastral relationship between DigitalTRChat/Bot page cards and SmartBidding `Accounts > Messenger > Page`, especially when Rodolfo asks for an updated Excel/report of divergences.

## What went wrong

A PAGE ID audit initially reported a large `NO_SB_MATCH` count after fetching SmartBidding with only `publisher.active == true` child publishers. That produced an incomplete SB scope:

- Incorrect/incomplete: `46` publishers / `3,218` Messenger Page rows.
- Correct full MGS PAGE audit scope: `digital-trust` + `digital-trust-2` **all child publisher IDs**, regardless of `active`, yielding `56` publishers / about `3,237` rows at the time.

Rodolfo challenged the result because `Existe no Bot/DTR e não na SB: 414` did not make operational sense. The corrected fetch using all child publishers reduced the false scope problem.

## Hard rule for future PAGE ID registration audits

For this specific registration audit only, fetch SB Messenger Page rows with:

1. `GET /company`.
2. Normalize company names, e.g. `Digital trust` → `digital-trust`, `Digital trust 2` → `digital-trust-2`.
3. Include **all** `publisherId` children under both companies, not just `active == true`.
4. Query `/campaigns/Messenger?companies[]=<publisherId>...&source=Messenger`.
5. Hard-stop before reporting if the full-scope guard fails. As of this session, expected guardrails were:
   - `publishers_total_all >= 56`;
   - `sb_rows_total >= ~3230`.

Never report a PAGE ID registration audit from an active-only SB publisher scope.

## Unicode PAGE_NAME pitfall

Several `PAGE_NAME` divergences in Excel looked identical to Rodolfo. They were false positives caused by Unicode normalization differences:

- DTR string used precomposed accents (`é`, `ó`, `í`).
- SB string sometimes used decomposed accents (`e` + combining acute, `o` + combining acute).
- Excel rendered both visually the same, but byte/string comparison marked them different.

Fix for comparator:

```python
import unicodedata

def name_norm(v):
    s = unicodedata.normalize('NFC', clean(v)).lower()
    s = re.sub(r'\s+', ' ', s)
    return s
```

Only report `PAGE_NAME` as divergent after Unicode NFC normalization.

## Excel row-number caution

When Rodolfo references Excel rows, remember row 1 is the header. Map the requested worksheet row number directly to `ws[row]`; do not subtract one in the user-facing interpretation.

In this session, Rodolfo said:

- Rows 2 and 3: manual verification.
- Rows 16, 24, 25: correct SB `PAGE_NAME` to the DTR value.
- Rows 4–23 and 27–29: appeared identical in Excel and were Unicode false positives.

After applying the three requested SB `PAGE_NAME` corrections and NFC normalization, real divergences dropped to 3:

- Two `PAGE_ID + SEGURADOR` rows left for manual decision.
- One real `PAGE_NAME` divergence not yet requested for correction.

## Safe correction pattern for PAGE_NAME-only fixes

When Rodolfo explicitly asks to correct SB page names from this audit:

1. Re-open the exact Excel/JSON used for the report and identify the worksheet rows.
2. Verify the row is `DIVERGENTE` with `PAGE_NAME` only, or that Rodolfo explicitly approved the named row.
3. Use live SB full scope (`56` publisher guard) and fetch the exact row by `SB ID`.
4. Back up the raw SB row.
5. Save via `POST /campaigns/Messenger` using the whitelist payload pattern from the PAGE ID registration skill, changing only `PAGE_NAME`.
6. Re-fetch `/campaigns/Messenger` and validate exact readback of `PAGE_NAME`.
7. Re-run comparison with Unicode NFC normalization before producing a new divergence Excel.

Do not auto-correct `PAGE_ID + SEGURADOR` rows. Those require manual decision because they may represent same FB page under different segurador/profile contexts.
