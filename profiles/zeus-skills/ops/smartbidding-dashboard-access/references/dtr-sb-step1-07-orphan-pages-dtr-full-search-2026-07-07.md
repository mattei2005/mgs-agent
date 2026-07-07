# DTR↔SB Step 1 — 07 orphan pages after Facebook availability check (2026-07-07)

## Context

During Step 1 PAGE ID reconciliation, Rodolfo reviewed the `07 SB sem Bot DTR` tab manually in a logged-in Facebook browser. After already removing SB `Blocked` rows, Facebook availability split the remaining rows into:

- pages that show `This content isn't available right now` → should be treated as unavailable/deleted and set `STATUS=Blocked` in SmartBidding with backup + live readback;
- pages that still open publicly → must **not** be blocked just because they are absent from DTR.

## Critical corrections

1. A logged-out Facebook redirect/login wall is **inconclusive**, not proof that a page opens.
   - If the browser lands on `/login/?next=...` or body text says `Log in to Facebook` / `Explore the things you love`, discard the result.
   - Use Rodolfo/logged-in browser evidence or a valid logged-in Facebook context for availability.

2. If Rodolfo says a page opens publicly, do **not** mark it `Blocked` in SB.
   - It may be an orphaned SmartBidding row: public Facebook page exists, but DTR/Bot no longer has it linked under any segurador.

3. Before calling a remaining `07` row truly `SB sem Bot/DTR`, search the **entire DTR scope** by IDs:
   - all DigitalTRChat 1Password users;
   - all top-bar seguradores/accounts per user;
   - every page card in each account;
   - match by large `FB_PAGE_ID` first;
   - also search small `PAGE_ID/PG` as a sanity check.

4. If both large `FB_PAGE_ID` and small `PAGE_ID/PG` are absent from the full DTR scan, classify as:
   - `SB orphan — public Facebook page exists, missing from DTR`
   - not `Blocked`, not a DTR match, not a restricted-page error.

## Operational example from the session

After filtering `07` and blocking 79 unavailable pages, 10 rows remained public/open. Full live DTR search scanned:

- 88 DTR logins;
- 88/88 login OK;
- 226 seguradores/accounts;
- all target large `FB_PAGE_ID`s;
- all target small `PAGE_ID/PG`s.

Result: `0/10` found in DTR by `FB_PAGE_ID`; `0/10` found by `PAGE_ID/PG`.

Specific validation: `disparoseggbev@gmail.com` → `Reginaldo Novaes Santiago` had `0` pages in DTR, matching Rodolfo’s manual check, while SB still had public pages under that profile/login.

## Final decision rule

For `07 SB sem Bot DTR`:

- `SB Status = Blocked` → ignore/remove from active comparison.
- Facebook unavailable warning confirmed by logged-in human/session → set SB `STATUS=Blocked` with backup + readback.
- Facebook page opens + full DTR ID search returns no match → keep as `SB orphan / cleanup candidate`, not blocked.
- Never rely on page name alone; use `FB_PAGE_ID` and `PAGE_ID/PG`.
