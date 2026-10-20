# Bank card limits → Google Sheets

Use for an authorized reconciliation of card credit/spending limits and available amounts from an issuer's authenticated dashboard into an existing Sheet. This is account reading and spreadsheet maintenance, not permission to make payments, accept credit offers, change limits, enroll products or modify authentication.

## 1. Freeze the requested scope

1. Identify whether the request covers one test card, all cards under a login, or a named subset. Do not silently expand a one-card test to every account; when the user extends scope, reuse the session and reconcile only the added cards.
2. Read Drive metadata and Sheets tab metadata through the canonical Service Account helper. Resolve the supplied numeric `gid` to the current tab title and verify exact edit capability.
3. Read the bounded destination range with `valueRenderOption=FORMULA`. Resolve headers and unique issuer/product/suffix rows; retain the original values and formulas as the rollback baseline before a write.

## 2. Open the authenticated source

1. Use the user's explicitly requested browser/profile. For native Windows Chrome with 1Password, follow `secure-remote-windows-automation` and its interactive-browser-authentication reference: shared lease, exact window capture, inline manager fill and human unlock/2FA handoff.
2. After approval, verify an authenticated account page rather than assuming the acknowledgement proves login. Reuse it without reopening the password manager unless login is actually required.
3. Complete source reads promptly within the live inactivity timeout. If the site logs out, return through normal protected login; a new push is required only if the issuer presents one. Do not weaken timeout/security settings.

## 3. Read each card's explicit fields

1. Select the exact card by product and displayed suffix from the overview or account selector. Recapture and resolve a unique semantic label/role before each click; banner loading can shift indices between captures.
2. Preserve the source suffix verbatim in protected evidence. An issuer can show a longer trailing suffix than the Sheet; reconcile its last four digits together with issuer/product and require uniqueness. Do not alter the Sheet's existing identifier format or request the full number.
3. Open the source's balance/credit details, then bind every captured amount to its displayed label and card identity. Record currency and observation time.
4. In American Express, the overview lists multiple products, including non-card lines of credit. Open only the requested card. A credit-card dashboard can expose **Show Balance & Credit Details** with **Credit Limit** and **Available Credit**; a Business Platinum dashboard can instead expose **View Balance & Limit Details** with **Available to Spend**. Read the live labels rather than treating the two layouts as identical.
5. Distinguish **Total Balance** (amount owed), **Credit Limit**, **Available Credit**, **Available to Spend**, **Spending Limit** and **Pay Over Time limit**. Do not use one as a substitute for another, and do not calculate a missing limit from balance plus availability.
6. If **Spending & Limit Details** is blank, allow loading, then perform one safe dashboard reload and reopen the exact details panel. If still blank, mark the total limit unverified. A visible zero for **Available to Spend** remains a valid source value; a blank limit is not zero and does not prove the card has no preset limit.
7. Dismiss promotional overlays without accepting an offer. Avoid **Make Payment**, **Accept Offer**, card applications and limit-change controls. A definitions panel may explain labels but does not establish a missing account-specific amount.

## 4. Write the minimum verified delta

1. Build a per-field plan containing exact target range, previous value, expected numeric value, source label, card identity and verification status.
2. Preserve the original snapshot separately from the final receipt. Re-read immediately before writing; skip already-equal cells, and stop on unexpected concurrent changes or formulas in a target expected to be a literal.
3. For one changed numeric cell, use `spreadsheets.values.update` with `valueInputOption=RAW`, explicit A1 range, `majorDimension=ROWS` and `values=[[number]]`. Keep inherited currency formatting; do not replace the row or write currency text when the column is numeric.
4. If the total limit is unverified, preserve that existing cell while updating a separately verified available amount. Do not clear, recompute or silently relabel the old total. Explain its unvalidated status in the result; adding a new status/date column requires the corresponding layout scope.
5. Read the full bounded range again with `valueRenderOption=FORMULA`. Require exact equality to the original snapshot except for the authorized cells. Keep a compact receipt with before/after, source labels, safe evidence path, observation/readback time and preserved-field caveats.

## 5. Close and report

- Release the desktop lease and scoped automation client; preserve the user's browser and unrelated tabs.
- Report issuer/product plus last four digits, verified total limit if available, verified available amount using the source's actual meaning, and exact changed row/cell or verified no-op.
- When a total is missing, explicitly distinguish the preserved historical Sheet amount from a current bank-confirmed amount. Partial validation is not complete reconciliation of both columns.
- State the actual manual authentication dependency observed, not a promise that every future run will be unattended. Do not schedule future polling as part of a single test.
