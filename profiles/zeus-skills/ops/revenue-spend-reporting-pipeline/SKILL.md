---
name: revenue-spend-reporting-pipeline
description: Use when processing MGS weekly revenue/spend Excel reports into a Google Sheet or master Long table, including AV/SB/JBF/MonetizeMore revenue, Facebook/Google spend, manager attribution, vertical classification, reconciliation, and site-level profit/margin summaries.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, revenue, spend, adops, google-sheets, excel, reporting, reconciliation]
    related_skills: [productivity-workspace-apis, google-drive-agent-automation]
---

# Revenue × Spend Reporting Pipeline

## Overview

This skill governs the MGS weekly reporting workflow that turns one Excel workbook into a clean `Long` table for the master sheet and optional site consolidations such as Fincgriffin profit/margin views.

The non-negotiable invariant is reconciliation: no revenue or spend may disappear. The sum of output `Long.Receita` must match the raw sum of all revenue tabs, and the sum of output `Long.Gasto` must match the raw sum of all spend tabs. If reconciliation fails, do not upload or present the output as final.

Validated runner:

```bash
/root/mgs-agent/scripts/process-revenue-spend-report.py --input /path/report.xlsx --sheet-id GOOGLE_SHEET_ID
```

Preflight only, before writing a Sheet:

```bash
/root/mgs-agent/scripts/process-revenue-spend-report.py --preflight --input /path/report.xlsx
```

### Google authentication invariant

- The validated runner uses the MGS Service Account by default through `/root/mgs-agent/scripts/mgs_google_workspace_auth.py` and sends its `x-goog-user-project` quota project.
- Require Sheets API HTTP 200, `roles/serviceusage.serviceUsageConsumer`, destination `writer` access, and readback before upload.
- `--auth-mode oauth` is rollback-only. Do not make user OAuth the default again, and do not revoke/delete its refresh token without the separate credential-critical confirmation.

## When to Use

Use when Rodolfo provides or references:

- Weekly `.xlsx` reports with tabs like `report AV`, `report SB-1`, `report SB-2`, `MonetizeMore`, `Gastos FB`, `Gastos Google`.
- A Google Sheet destination for the processed report.
- Requests for `Long`, `Resumo_dia`, or site-level consolidation with `Lucro` and `Margem %`.
- Questions about revenue split by site, vertical, manager, country, day, URI, or traffic source.
- Ad-hoc ActiveView questions such as "quanto o openzed rendeu ontem?" where a domain/date can be answered via the AV external API.

Do not use for editorial content, campaign execution, or generic Google Sheets formatting that does not involve revenue/spend reconciliation.

## Required Operating Sequence

1. **Preflight input before any sheet write.**
   - Open the workbook and list detected tabs, row counts, columns, date ranges, and raw totals.
   - Confirm all required revenue/spend tabs with data are present.
   - If a required tab is empty or a new account/site cannot be mapped, stop and ask Rodolfo for the mapping.
   - Do not write to the destination Google Sheet during this phase.

2. **Classify tabs by content, not fixed names.**
   - AV revenue: has `Site` and `Ad Exchange revenue ($)` or equivalent.
   - SB/JBF revenue: has `Placement` and `Ad Exchange revenue`.
   - MonetizeMore/Wantabrand: block-style domain sections with `Date` and `Gross Revenue`.
   - Facebook spend: `Account name`, `Day`, `Currency`, `Amount spent`.
   - Google spend: `Dia`, `Nome da conta`, `Valor gasto`.

3. **Resolve mapping blockers before processing.**
   - New Google Ads accounts such as `Mattei 1` or `Gamingadx-US-01` must be mapped to site/vertical/gestor before upload.
   - Confirm cycle-specific exceptions such as `fincgriffin _gb` before applying them.
   - If Rodolfo has not confirmed, preserve source classification and flag it rather than silently rewriting.

4. **Build deterministic output.**
   - `Long`: `Data | Site | Vertical | Gestor | Conta_FB | Gasto | Receita`.
   - `Resumo_dia`: daily spend/revenue totals.
   - Optional site consolidations only when asked: daily, daily+gestor, gestor summary, with `Lucro = Receita - Gasto` and `Margem % = Lucro / Gasto`.

5. **Write only the requested output shape.**
   - Do not create many diagnostic tabs in the user-facing Sheet by default.
   - Keep verbose diagnostics in local CSV/JSON audit files, or create a single concise `Validacao` tab only if useful.
   - The destination Sheet is an operator-facing artifact, not a debug dump.

6. **Validate by read-back.**
   - After upload, read back tab row counts and key totals.
   - Final report must state raw revenue, output revenue, raw spend, output spend, date ranges, and blockers/assumptions.

## Canonical Rules Validated on 16–29 Jun

- `gamezonead.com`: official token `br-game-br`; Google account `Mattei 1`; gestor `g002-d`.
- `gamingadx.com`: official token `us-game-en`; Google account `Gamingadx-US-01`; gestor `g002-d`.
- `de.newsoun.com`: any `Newsoun-DE` spend/revenue belongs here, vertical `de-cc-de`, gestor Kelly `g005-d`, regardless of other fields.
- `creditoparaveiculo.com`: FB account tags such as `-G003`, `-G005`, `-G002` assign spend to those gestores.
- Manager tags in FB names are case/format-insensitive and suffix-insensitive: `g002`, `G002`, `-G002`, ` g002`, `g002-s`, `g002-d` all normalize to `g002-d`. Never split by `-s` vs `-d`.
- In revenue `utm_medium`, `g00X-s` and `g00X-d` also normalize to `g00X-d`. Unknown media (`-`, `q1-s`, email, sms) fall back to site owner.

## Revenue Rules

### AV revenue

- For workbook-based reporting, parse AV exports as described below.
- For API/dashboard-based reporting, use `references/activeview-api-recon.md` before building a client or answering ad-hoc revenue questions. It contains the official external base URL/auth, validated Openzed/OpenzedFinanças mappings, and the AV+Meta workflow for revenue/spend questions.
- For ad-hoc questions like “quanto o openzed rendeu ontem?” prefer the official external endpoint `GET https://external-api.activeview.app/report/:NETWORK_CODE/:DOMAIN?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`, sum `response[].revenue`, and keep the API key sanitized. For `openzed.com` and `finanzas.openzed.com`, validated network code is `23054305319`.
- For OpenzedFinanças revenue+spend, pair AV revenue for `finanzas.openzed.com` with Meta spend from Ares operation `OpenzedFinanzas-CC-ES` / ad account `act_1356770869843984`; report Receita, Gasto, Lucro, ROAS, and Margem, and note if the last day has partial/zero spend.
- Resolve manager from `utm_medium` when it matches `g001`…`g006` with any suffix (`-d`, `-s`, etc.); otherwise use site owner.
- Normalize manager output to `g00X-d`.
- Resolve country/vertical by explicit string checks, never truthiness:

```python
def pick(*vals):
    for v in vals:
        if isinstance(v, str) and v:
            return v
    return None
```

- Classification cascade:
  1. `utm_term` regex `(us|gb|es|de|mx|ca|za|ar|br)-(cc|job|car)-(en|es|de|pt|br)`
  2. `utm_content` regex `(?:drip|bd)_(country)_(cc|job|car)_`
  3. page map `(site, pg) -> country`
  4. site default

- Build page map before final classification by scanning all AV rows across all days. Key by `(site, pg)`, not just `pg`. Exclude `pg = '-'`. Flag pages that reveal more than one country.

### SB/JBF revenue

- `pl_digital-trust_{brand}_{country}` maps to site `{brand}.com` and vertical as country for standard JBF brands.
- `creditoparaveiculo` maps to `creditoparaveiculo.com`, `br-car-br`.
- `gamezonead` maps to `gamezonead.com`, `br-game-br`.
- `gamingadx` maps to `gamingadx.com`, `us-game-en`.
- `fincgriffin` normally maps to `fincgriffin.com`, `us-car-en`, but `_gb` is cycle-specific and must be confirmed.
- Strip currency prefixes such as `CA$` from revenue values but do not convert currency.

### MonetizeMore / Wantabrand

- Parse block-style sheets where a domain appears as a section header and following rows contain `Date | Gross Revenue`.
- `wantabrand.com` -> `us-cc-es`, owner `g001-d`.
- `finance.wantabrand.com` -> `gb-cc-en`, owner `g001-d`.

## Spend Rules

### Facebook

- Keep one output row per spend account/day.
- Parse site/vertical from account names like `{Brand}{Finanzas?}-{COUNTRY}-{SEP}-{LANG}-{NN}`.
- Ignore parenthetical suffixes such as `(FAX-US-02)` for mapping.
- Use explicit manager suffix in the account name when present (`g001`…`g006`); otherwise use site owner.
- Standard examples:
  - `CliquetFinanzas-US-CC-ES-03` -> `finanzas.cliquet.com`, `us-cc-es`.
  - `Eggbev-US-CC-EN-03 (FAX-US-02)` -> `eggbev.com`, `us-cc-en`.
  - `Fincgriffin-US-CAR-EN-01 g006` -> `fincgriffin.com`, `us-car-en`, `g006-d`.
  - `Newsoun-DE-CC-DE-01` -> `de.newsoun.com`, `de-cc-de`, `g005-d`.

### Google Ads

- Values may use comma decimal format and must not be auto-converted across currencies.
- Do not assume unknown account names are `gamezonead`. Ask for mapping before upload.
- Mark non-USD or special-currency lines clearly in `Conta_FB`, e.g. `site/account (Google Ads - BRL)` when confirmed.

## Merge Rule for `Long`

Group revenue by `(Data, Site, Vertical, Gestor)`.

For each matching spend group:

1. Generate one row per spend account/day.
2. Put the group revenue only on the first spend row.
3. Put `Receita = 0` on additional spend rows for the same group.
4. Revenue groups with no spend become standalone rows with empty `Conta_FB` and `Gasto = 0`.

This prevents duplicated revenue while preserving spend account granularity.

## Common Pitfalls

1. **Uploading before preflight.** The biggest failure mode is writing a Sheet before detecting empty tabs or unknown mappings. Always inspect first; write second.

2. **Creating debug-tab sprawl.** Rodolfo expects the output he asked for, not a pile of internal diagnostic tabs. Keep diagnostics local unless explicitly requested.

3. **Treating an empty spend workbook as valid.** If `Gastos FB`/`Gastos Google` are expected but empty, stop. Do not generate a misleading all-zero spend report unless Rodolfo explicitly wants revenue-only output.

4. **The pandas `nan` truthiness bug.** Never chain `utm_term or utm_content or page_map`. `nan` is truthy and will block lower layers.

5. **Rounding before reconciliation.** Do not round line-level `Long` amounts before summing for validation. Round only for display; reconcile using full precision.

6. **Assuming Google Ads account mappings.** New account labels must be mapped by Rodolfo or a canonical source. Wrong site/vertical/gestor is worse than a temporary blocker.

7. **Hard-coding sheet names.** Names vary. Detect by columns/content and include the detected tab list in the preflight report.

8. **Splitting manager by suffix.** `-s` and `-d` are traffic-type controls, not separate gestores. Normalize every recognized manager tag to `g00X-d`.

## Master Google Sheet Diagnostics

When Rodolfo provides the master finance Sheet (`MGS - Receita dos Sites 2026`) and asks for a diagnosis before filling a monthly tab:

1. **Compare uploaded workbook against the previously generated `Long` by aggregates first.** Exact row equality can differ only because the merge rule places a group's revenue on the first spend row chosen for that `(Data, Site, Vertical, Gestor)` group. Treat row-level placement differences as non-material when `site × vertical × gestor`, daily totals, revenue total, and spend total all match.
2. **Inspect the target monthly tab and its duplicated backup tab before writing.** Use Google Sheets API read-only calls to list sheet titles, dimensions, formulas, formatted values, and formula errors.
3. **Validate the backup copy is identical before using it as a sandbox.** Compare normalized `FORMULA` render matrices for the original tab and `Copy of ...`; report if formulas/values differ.
4. **Diagnose formulas without changing structure.** Check for `#REF!`, `#N/A`, `#VALUE!`, `#DIV/0!`, etc.; list external dependencies such as `GOOGLEFINANCE` and `IMPORTRANGE` but do not replace them unless Rodolfo explicitly asks.
5. **Understand the sheet layout by blocks.** Monthly tabs are wide site/country blocks with columns like `GROSS`, `NET`, `Imposto`, `Gastos`, `Lucro`, `ROI`, and `TOTAL`. Days are rows; only fill the date range covered by the approved report. Do not touch previous days or structural formulas.
6. **Report the operational conclusion first.** Example: “Cláudio x Zeus bate nos agregados; only non-material row-placement difference is X.” Then state whether the monthly tab has formula errors and which date range is still blank.

## Verification Checklist

- [ ] Input tabs detected by content and row counts reported.
- [ ] Date ranges for each input tab reported; defasagem flagged.
- [ ] Raw revenue totals per source computed.
- [ ] Raw spend totals per source computed.
- [ ] Unknown sites/accounts/mappings resolved or explicitly blocked.
- [ ] AV page-country map built before classification.
- [ ] Ambiguous pages listed.
- [ ] `Long.Receita` equals raw revenue total within floating tolerance.
- [ ] `Long.Gasto` equals raw spend total within floating tolerance.
- [ ] Destination Sheet contains only requested operator-facing tabs.
- [ ] Upload verified by Sheets read-back.

## Master Month Sheet Fill Workflow

When filling Rodolfo's master monthly Google Sheet (e.g. `MGS - Receita dos Sites 2026`, tab `Junho 2026`), do not assume the `Long` table can be pasted directly. First derive an explicit map: `(Site, Vertical/Country, Currency, Account) -> sheet cell/column`.

Operational rules validated on the June 2026 sheet:

1. **Separate source report validation from sheet fill.** Compare the provided workbook against the approved Long/report first: row counts, total revenue, total spend, and site × vertical × gestor aggregates. Only then map into the month tab.
2. **Revenue currency matters.** Some sites are filled into `GROSS_USD_*`; some JBF-style sites are filled into `GROSS_CAD_*` and the adjacent USD columns are calculated by the sheet. Never fill the calculated USD column when the manual source column is CAD.
3. **Spend currency matters.** Most sites use `BM - $` / USD spend columns. `gamezonead.com` and `gamingadx.com` Google Ads spend use `Google Ads -R$` BRL columns.
4. **Account headers are routing keys.** Match spend to the exact ad-account headers when available. If the source account is more granular than the sheet, stop and apply Rodolfo-confirmed aggregation rules rather than guessing.
5. **Special sub-tables can carry real operational splits.** `fincgriffin.com` has a lower gestor table (`Data / Gestor / Gasto / Receita / Lucro / Margem`) that should be extended before summing to the top block. `openzed.com` has a lower `ICARO - G001-D` block starting at `NF100`; do not collapse it into the principal Openzed block.
6. **Write with backup + read-back.** Before a test/final fill, backup formulas/values for the affected sheet/bands. Use broad `batchGet` calls, not one read per cell. Apply via `values:batchUpdate`, then verify representative cells and formula errors in touched bands.

See `references/2026-06-master-sheet-fill-notes.md` for the June 2026 confirmed currency/account mapping, Openzed/Fincgriffin handling, and the tested partial-fill readback.

## Reference Files

- `references/2026-06-first-zeus-handoff.md` — first Zeus handoff notes, including the mistake to avoid: uploading a debug-heavy, revenue-only Sheet before validating complete input and mappings.
- `references/activeview-api-recon.md` — ActiveView official external API + dashboard recon notes: public base URL/auth, documented endpoints, internal dashboard API caveats, encrypted query params, and validation workflow for API-based AV reporting.

## Related Operational Fill Skill

For writing approved `Long` output into Rodolfo's live monthly finance Google Sheets (`Junho 2026`, `Julho 2026`, etc.), use `monthly-finance-sheet-fill` instead of extending this pipeline ad hoc. That skill covers sheet block mapping, `GROSS_USD` vs `GROSS_CAD`, `BM - $` vs `Google Ads - R$`, special blocks like Fincgriffin/Openzed Ícaro/Creditoparaveiculo, backups, and cell-level audits.
- `references/2026-06-master-sheet-fill-notes.md` — Rodolfo-confirmed June 2026 master-sheet fill mapping: USD vs CAD revenue columns, USD vs BRL spend columns, account aggregation exceptions, Openzed Ícaro lower block, Fincgriffin gestor table, and Sheets API backup/readback pitfall.
