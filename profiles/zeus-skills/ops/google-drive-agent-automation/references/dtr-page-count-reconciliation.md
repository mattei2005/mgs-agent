# DigitalTRChat page counts → Sheets

For MGS requests to refresh a Sheet's per-segurador page-count column from DigitalTRChat:

- Process every Sheet occurrence independently; do not deduplicate repeated names/logins.
- Match exact `User` plus normalized `Segurador`, switch with `fb_rx_account_switch`, reload `/social_accounts/index`, and use the active account's `N Pages` value. Do not substitute Graph, subscribed-app or Smart Bidding totals.
- If duplicate normalized account names exist, inspect every matching account ID. Auto-resolve only if all counts are zero or exactly one candidate is nonzero; otherwise preserve the Sheet cell as inconclusive.
- Back up the complete target column before the first write and never overwrite that backup after a canary retry.
- Pause only concurrent monitors that can write the same Sheet, then resume them after closure.
- Apply one-cell canary → readback → remaining batch; write only changed cells in the authorized column.
- Sheets RAW numeric values read back as strings. Compare normalized numeric text (`"38"` and `38`), not Python container types.
- Afterward, read the full operational range and require all resolved rows to match; preserve unresolved and non-operational rows.
- Report verified, changed, unchanged and inconclusive counts, increases/decreases, backup hash and readback mismatches.
