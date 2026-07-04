# DigitalTRChat Bot dashboard — page-by-page validation after false global scan (2026-07-03)

## Trigger

Use this when auditing DigitalTRChat/Bot dashboard page status codes (`#2022`, `#10`, `#100`, `#551`, Sent/OK) across bot users, seguradores/accounts, and pages before syncing or reconciling with SmartBidding.

## Naming convention from Rodolfo

- **Dashboard da SB** = `https://app.smartbiddingdigital.com` and `https://api.jbfdigital.com.br/campaigns/Messenger`.
- **Dashboard do Bot** = `https://digitaltrchat.com/` and its derived endpoints.

Do not blur these sources in reports. SB can show operational page state (`STATUS`, `RESTRICTED_UNTIL`); Bot/DTR is the source for the last sent-message report and error code classification.

## Correction learned

Rodolfo challenged whether the original DTR scan was trustworthy. The prior global/segurador scan produced fake scale because it trusted `.account_switch` and campaign datasets without proving the dataset changed. It reported thousands of page-context rows for one bot user, but corrected page-filter testing showed the real shape is much smaller.

The reliable route is:

1. Read active bot users from the migration Sheet (`gid=562940072`), not all 1Password items.
2. Log into the Bot dashboard for one active user.
3. Enumerate top-bar seguradores/accounts.
4. Switch to each segurador/account.
5. **Validate context changed** before trusting the account label: page options or campaign signatures must differ from other accounts; if identical campaign IDs repeat, mark the scan invalid/non-actionable.
6. Enumerate real page options from `select#search_page_id` / `select[name=search_page_id]`.
7. For each page option, query Subscriber Broadcast campaign data with `search_page_id=<page option value>` and `search_status=2` (`Completed`), ordered newest first.
8. Open only the newest Completed campaign report (`campaign_sent_status_data`).
9. Classify the raw sent status:
   - `Sent`/success => OK/no restriction in Bot.
   - `#2022` => temporary restriction; capture release date/time if present.
   - `#2022 + other codes` => restricted + mixed error; persist for post-expiry review.
   - `#10`, `#100`, `#551`, permission/app/token without `#2022` => non-restriction error class.
   - no latest Completed/report => `sem report DTR válido`.
10. Count **unique pages**, not campaign occurrences or repeated segurador contexts.
11. Only after Bot classification, cross-check SB live by `FB_PAGE_ID`/`PAGE_ID`/`USER_LOGIN` for operational status and `RESTRICTED_UNTIL`.

## Validated one-user probe

User tested: `disparosxyvlovusccen@gmail.com`.

Result of corrected page-by-page Bot route:

```text
Active in Sheet: yes
1Password match: yes
Login: OK
Seguradores/accounts: 2
Context signatures unique: 2

Segurador       Page options  Latest Completed  Sent/OK  Errors  No Completed
Pendang Novi    20            19                2        17      1
Lestari         11            9                 3        6       2
Total           31            28                5        23      3

Code totals from newest Completed reports:
#10   22
#100   6
#2022  1
```

This proved the corrected route returns **31 real page options**, not thousands of fake occurrences, and that account context can be validated by differing campaign signatures.

## Reporting discipline

When Rodolfo asks whether pages are restricted or asks for confidence in DTR classification:

- answer source-specific: `SB says restricted` vs `Bot latest report shows #2022`;
- do not say a page is code-confirmed by Bot if only SB `RESTRICTED_UNTIL` was read;
- do not defend a bad scan by switching terminology mid-answer;
- if Rodolfo asks a narrow source/provenance question, answer that exact provenance first, then add correction only if needed.

## Pitfalls

- HTTP 200 from `fb_rx_account_switch` is not enough; prove the page/campaign dataset changed.
- `search_page_id=''` with completed campaigns can return a global/default view; never use it as page-level truth.
- Repeated campaign IDs under multiple segurador labels mean fake duplication; invalidate the run.
- Bot status classification and SB operational state are related but not the same source. Keep both labels explicit.
