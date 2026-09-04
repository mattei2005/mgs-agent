---
name: mgs-finance-dashboard
description: Use when auditing or building the MGS finance dashboard.
version: 0.1.1
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

- August 2026 formula repairs 1–14 are complete and read back successfully; see the ledger for exact ranges.
- `AmazingXJobs` and `WavesBee`, the YMonetize blocks reviewed in this initiative, contain zero nonzero numeric values in rows 5–36.
- YMonetize is no longer an active MGS partner for these blocks.
- Planned disposition: migrate the affected sites to Rede1.
- August remains financially provisional until Rede1 and other active payout rates are replaced from payment proof.
- `CAIXA SINTETICO` has not yet been corrected in this initiative and remains last in the approved order.

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
- `GOOGLEFINANCE` movement before partner payment is intentional provisional behavior, not formula drift.
- A fixed `I1` is intentional while YMonetize is retired and its blocks are zero.
- Copying July formulas by replacing only the month name is unsafe because August block coordinates changed.
- Inactive blocks still need complete formula structure if August will seed September.

## Verification

- Every listed manual correction has an API readback marked PASS.
- Full monthly tab has zero displayed formula errors after corrections.
- Every external spreadsheet ID and `gid` resolves to the expected August tab.
- Current manager spill parity is exact.
- `CAIXA SINTETICO` remains untouched until its approved phase.
- Dashboard is not declared complete until backup, build, formula parity, KPI recomputation, and chart readback pass.
