---
name: mgs-finance-dashboard
description: Use when auditing or building the MGS finance dashboard.
version: 0.1.11
author: Rodolfo Mattei, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [mgs, finance, dashboard, google-sheets, audit]
    related_skills: [monthly-finance-sheet-fill, google-drive-agent-automation]
---

# MGS Finance Dashboard

Audit, correct, normalize, and build the MGS executive finance dashboard without treating visually valid formulas as financially correct. This skill governs the dashboard initiative; detailed monthly fill mechanics remain in `monthly-finance-sheet-fill`.

## When to Use

- Auditing the principal MGS finance workbook before a dashboard or month rollover.
- Continuing the August 2026 dashboard initiative from another session.
- Reconciling the principal monthly tab, `CAIXA SINTETICO`, and manager workbooks.
- Building or validating the normalized dashboard base and executive views.

Do not use this skill to change source formulas without an explicit, cell-bounded correction authorized by Rodolfo.

## Canonical sources

- Principal workbook: `16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak`.
- Production identity: `mgsagent@mgs-core-prod.iam.gserviceaccount.com` through `/root/mgs-agent/scripts/mgs_google_workspace_auth.py`.
- Current initiative checkpoint: `ZEUS-FINANCE-DASH-AUGUST-20260904` in `/root/mgs-agent/data/agent-checkpoints.json`.
- Current detailed ledger: `references/august-2026-audit-ledger.md`.
- Formula-audit artifacts: `/root/mgs-agent/work/finance-dashboard-august-20260904/`.

The dashboard business inputs are only the approved monthly tab and `CAIXA SINTETICO`. Manager workbooks are upstream dependencies used to validate imported calculations, not independent dashboard facts.

## Non-negotiable rules

1. Work one confirmed problem at a time when Rodolfo requests the stepwise flow.
2. After Rodolfo edits a cell/range, read back `FORMULA`, `UNFORMATTED_VALUE`, and `FORMATTED_VALUE`; then send the next confirmed problem automatically.
3. Keep `CAIXA SINTETICO` deferred until the monthly tab is fully audited when Rodolfo sets that order.
4. Never use `ROI GERAL AGOSTO` as a source: its hard-coded coordinates drifted after the monthly layout expanded.
5. Snapshot and hash before any agent-side write. The current manual-correction flow is performed by Rodolfo unless he delegates the write.
6. Resolve every `IMPORTRANGE` recursively and require exact spill parity before treating manager outputs as valid.
7. A zero `#REF!` count does not prove semantic correctness; validate metric headers, components, totals, currencies, and row continuity.
8. Preserve the MGS exchange lifecycle:
   - `F1` follows the matching `CAIXA SINTETICO` month cell and is the same provisional-to-actual lifecycle as the other exchange cells; the active formula lives in the summary cell, not necessarily in `F1` itself.
   - `H1` is provisional USD/CAD for Rede1 until payment proof, normally days 21–25 of the following month, then Rodolfo replaces it with the actual rate including spread.
   - `I1` remains fixed for the retired YMonetize relationship; do not restore a live GBP formula while its blocks are zero/inactive.
9. Dashboard views must label the month `PROVISÓRIO` until every still-active partner payout rate has been replaced by the actual settlement rate.
10. Never include credentials or the `USUARIOS BOT` tab in the dashboard.

## Current business state

- **Current audit status: REOPENED / semantic FAIL (2026-09-05).** Rodolfo requested a complete read-only re-audit in message `1545832349957234688`. The historical PASS below is superseded, not erased. Seven full source tabs were recaptured; first correction pending is `CAIXA SINTETICO!J70` (Yolokfx J37 omitted). Follow `references/august-2026-reaudit-20260905.md` and the ordered findings queue; never assume the existing dashboard's source totals are currently reconciled.
- August 2026 formula repairs 1–14 are historically complete and read back successfully; see the ledger for exact ranges. Those bounded repairs did not prove every other formula semantically correct.
- `AmazingXJobs` and `WavesBee`, the YMonetize blocks reviewed in this initiative, contain zero nonzero numeric values in rows 5–36.
- YMonetize is no longer an active MGS partner for these blocks.
- Planned disposition: migrate the affected sites to Rede1.
- August remains financially provisional until Rede1 and other active payout rates are replaced from payment proof.
- `CAIXA SINTETICO!J2:J75` is complete for August: `J2` and six correct summary formulas were preserved, 49 previously blank source-link/data cells were populated across the two authorized phases, four spacer rows remained blank, and formula/value/scope readback passed with zero displayed errors. Downstream `J77`, `J79:J81` recalculated and passed independent arithmetic checks.
- `BASE_DASH` and `DASH EXECUTIVO` are live in the principal workbook for August 2026. The normalized base has separate `SITE`, `PAÍS`, `GERAL`, and `GERAL_MÊS` levels so executive totals do not double-count country rows. Executive KPIs bind to `CAIXA SINTETICO`; site/country analytics bind to the audited August blocks. August remains `PROVISÓRIO`.

## Procedure

1. Load this skill and the current ledger.
2. Read the initiative checkpoint and confirm the active step.
3. Re-read the exact target cell/range from Sheets API; never rely only on the prior snapshot when volatile exchange cells remain.
4. For a correction, state the smallest exact edit and its expected semantic result.
5. After the manual edit, validate every row in the range and the smallest downstream total/KPI.
6. Append the validated correction to the audit trail and update the ledger/checkpoint at material transitions.
7. After all monthly-tab issues are closed, rerun the full formula/error/semantic audit.
8. Only then audit and repair `CAIXA SINTETICO` using live August coordinates, not copied July coordinates.
9. Create the normalized base and executive dashboard only after both source tabs pass and a full backup exists.
10. Validate dashboard totals against direct source recomputation, not against the retired ROI summary.

## Pitfalls

- Lowercase A1 ranges in `IMPORTRANGE` must be normalized before numeric column conversion.
- August 2026 has a legacy USD gross alias: `EO2=GROSS_BR` (Wantabrand BR), with monthly gross in `EO36`. A `GROSS_USD_*` header filter alone omits this revenue. Include EO explicitly, plus all USD gross headers from rows 2 and 102 (daily lower blocks use row+100), and reconcile the resulting monthly sum against independently audited site gross before proposing global ROI formulas. Do not rename headers or blindly carry this coordinate into a redesigned month.
- `GOOGLEFINANCE` movement before partner payment is intentional provisional behavior, not formula drift.
- A fixed `I1` is intentional while YMonetize is retired and its blocks are zero.
- Copying July formulas by replacing only the month name is unsafe because August block coordinates changed.
- Inactive blocks still need complete formula structure if August will seed September.
- Openzed row-38 consolidation must include every Gross country component from both the primary block and the special lower block. For the August layout this means `RS36`, `SB36`, `SK36`, `RS136`, `SB136`, and `SK136`, even when a component is currently zero; never infer the lower-block scope only from the cells present in a stale formula.
- In the Google Sheets API, a `BAR` basic-chart series must target `BOTTOM_AXIS`; `LEFT_AXIS` causes `INVALID_ARGUMENT` for the whole `batchUpdate`. Keep rollback limited to the newly created dashboard sheet IDs, verify they are absent, correct the spec, and rerun only after the source formula hashes still match.
- Multi-manager sites must not be duplicated as separate financial rows because that inflates totals. Store one site row with `Gestor=COMPARTILHADO` and the validated manager list in a separate dimension; leave unmapped ownership explicit rather than guessing.
- A normalized finance base that mixes site, country, daily-global, and monthly-closure facts must carry a `Nível` discriminator. Executive sums use `SITE` or `GERAL_MÊS`; country analyses use `PAÍS`; daily charts use `GERAL`.

## Exhaustive re-audit gates

- Read complete named tabs through Sheets API without a sampled final row/column; include formulas yielding empty strings and imported spill cells. Persist a per-cell inventory and exact formula/effective/formatted evidence.
- Separate formula execution correctness from metric semantics. Re-evaluating the same wrong SUM only validates arithmetic, not its component set.
- Reconcile all independent paths: daily/site totals, row-38 gross summaries, row-83 or special row-184 payout summaries, invalid-traffic groups, rev-share groups, company expenses, personnel, and final 50% results. Require a quantified difference bridge, not a direct link between mismatched totals.
- Require country/component coverage even for currently zero components. A new revenue row such as Yolokfx can sit outside an old rev-share interval; special lower blocks can be included in revenue but absent from invalids or payout estimates.
- Verify ROI with same-currency operands and monthly sums, never unweighted means of daily ratios. Do not reconstruct gross from net via a single share rate when rates differ or invalid traffic was already deducted. Different ROI denominator conventions require an explicit metric definition, not a silent rewrite.
- Manager projections must remain automatic and reusable when the monthly tab is duplicated. Rodolfo clarified on 2026-09-05 (message 1545859094332702771) that the intended estimate is accumulated result / elapsed completed days through yesterday × actual month length. Do not replace C14:F14 with copies of row12 as the repair: that breaks rollover. Supersede the earlier August-only copy-total proposal. A calendar-based divisor must derive month start from a verified date in the tab, cap elapsed days at month length, return empty before/on day1, and assume all portfolio data through yesterday is loaded; otherwise require an explicit last-complete-data date. The first site's last nonblank revenue is not a reliable portfolio cutoff. In Isliago August, A23 is day1 and A23:A53 are the actual days; A21/A22 are month/year headers. Preserve automatic month length and revalidate date anchors during rollover.
- Two manual currency amounts need payment evidence before choosing which one is authoritative; a difference from the provisional exchange rate alone is not a confirmed accounting error.
- Preserve strict one-problem cadence: one proposed edit, Rodolfo's manual completion or explicit delegated write, exact live readback, then the next queued issue automatically.

## Verification

- Every listed manual correction has an API readback marked PASS.
- Full monthly tab has zero displayed formula errors after corrections.
- Every external spreadsheet ID and `gid` resolves to the expected August tab.
- Current manager spill parity is exact.
- `CAIXA SINTETICO` remains untouched until its approved phase.
- Dashboard is not declared complete until backup, build, formula parity, KPI recomputation, and chart readback pass.
