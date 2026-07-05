---
name: smartbidding-dashboard-access
description: Use whenever any MGS agent needs to log into, navigate, inspect, export, or troubleshoot the Smart Bidding (SB) dashboard, especially app.smartbiddingdigital.com/accounts, Messenger Page, Broadcast Template, Messenger Daily, Messenger Pages, or Auth0/BotGuard issues.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, smartbidding, sb, dashboard, auth0, playwright, xvfb, botguard, messenger, reports]
    related_skills: [log-monitor-discord-alert, wp-plugin-mass-operation, hermes-update]
---

## Recent operational references

- `references/dtr-step1-step2-segurador-inventory-corrections-2026-07-03.md` — Rodolfo-corrected Step 1/Step 2 rules for DTR/SB audits: sheet-first filtering, `X` precedence, duplicate/no-pages semantics, four active sheet overrides, 1Password username discovery, and context-safety before SB writes.
- `references/sb-restricted-pending-file-bulk-apply-2026-07-04.md` — External restricted-pending text file → live SB bulk update workflow: `pg_` PAGE_ID normalization, full publisher scope, On-hold safety gate, backup, grouped update-many writes, and readback validation.
- `references/dtr-sb-page-health-sync-save-fallbacks-2026-07-05.md` — Save fallback lessons for DTR→SB page-health sync: distinguish DTR login vs SB save failures, omit null fields in modal-style payloads, dedupe unsafe context by SB row ID, and handle Blocked rows where status can be fixed but NOTES append is refused.

# Smart Bidding Dashboard Access — MGS

## Purpose

This is the canonical access route for Smart Bidding (`https://app.smartbiddingdigital.com/`) used by MGS agents.

Load this skill whenever Rodolfo asks an agent to:

- log into SB / Smart Bidding;
- inspect `/accounts`;
- navigate Messenger `Page` or `Broadcast Template`;
- inspect `Reports > Messenger Daily` or `Reports > Messenger Pages`;
- export reports or read delivered/leads/revenue tables;
- debug Auth0 login or `BotGuardError`;
- repeat a previous Zeus route that successfully entered the SB dashboard.

## Critical Lesson

Do **not** default to Playwright headless for SB dashboard navigation.

Headless can authenticate with Auth0 and still fail inside the SB runtime with:

```text
BotGuardError: Automated browser detected
Failed to validate user; attempting cookie fallback
```

This is not a bad-password signal. It means the browser automation mode was detected.

The route that worked for Zeus was **Playwright headed under Xvfb**:

```text
Playwright Chromium
headless=False
xvfb-run -a
--disable-blink-features=AutomationControlled
normal Chrome user-agent
persistent storage_state: /tmp/smartbidding_state_headed.json
```

## Canonical Command Pattern

Use the existing venv when present:

```bash
cd /root/mgs-agent
set -a
source .env 2>/dev/null || true
set +a
xvfb-run -a /tmp/sb-venv/bin/python <script>.py
```

If `/tmp/sb-venv` is missing, create a temporary venv and install Playwright before use:

```bash
python3 -m venv /tmp/sb-venv
/tmp/sb-venv/bin/pip install --quiet playwright
/tmp/sb-venv/bin/python -m playwright install chromium
```

Avoid installing Playwright system-wide. Ubuntu may block system pip via PEP 668.

## Browser Context Pattern

In Python/Playwright:

```python
browser = await p.chromium.launch(
    headless=False,
    args=["--disable-blink-features=AutomationControlled"],
)
ctx = await browser.new_context(
    storage_state="/tmp/smartbidding_state_headed.json",
    viewport={"width": 1600, "height": 1000},
    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
)
```

If there is no valid storage state yet, create the context without `storage_state`, perform login, then save it:

```python
await ctx.storage_state(path="/tmp/smartbidding_state_headed.json")
```

## Credentials

The 1Password item used by Zeus is:

```text
Item: Zeus - Smartbidding Dashboard
Vault: MGS Conteúdo
URL: https://app.smartbiddingdigital.com
```

Never print the password/token/session in chat or logs.

When retrieving a concealed password through `op`, use `--reveal`:

```bash
op item get 'Zeus - Smartbidding Dashboard' \
  --vault 'MGS Conteúdo' \
  --field password \
  --reveal
```

Without `--reveal`, `op` can return a masked/reference-like value. Auth0 may then show `Wrong email or password` even though the human credential is valid.

## Fresh Login Flow

1. Start headed Playwright under Xvfb.
2. Go to the target URL, usually:

```text
https://app.smartbiddingdigital.com/accounts
```

3. If redirected to Auth0, fill:
   - email/username from 1Password;
   - password from 1Password with `--reveal`.
4. Click `Continue`.
5. Wait for SB app to load.
6. Confirm body text contains the dashboard and user `Zeus - Agent`.
7. Save storage state:

```python
await ctx.storage_state(path="/tmp/smartbidding_state_headed.json")
```

## Known Good Verification

A successful access check should look like:

```text
url   https://app.smartbiddingdigital.com/accounts
title Accounts
user  Zeus - Agent
botguard False
```

The `/accounts` page loaded with visible sidebar/menu:

```text
Dashboard
Reports
Inventory
Smart Routing
Ads Pilot
IA Content
Quiz Maker
OKRS
```


## Mandatory fresh-session/full-scope rule

Before any Smart Bidding action/write, start from a fresh authenticated session: logout/login when practical, then select/filter the full MGS Messenger scope: all sites/publishers under `digital-trust` and `digital-trust-2`. Do not act from a stale UI/API context, partial 45-site capture, default company, or cached state. Validate the full Page scope before writes (expected current full table baseline: `/campaigns/Messenger` live rows around 3,237; the UI label may vary, but both companies must be included).

## Messenger Navigation Route

From `/accounts`:

1. Use the top source/context dropdown.
2. Select `Messenger`.
3. Confirm tabs appear:

```text
Account
User
Page
Broadcast Template
```

### Page tab

`Messenger > Page` shows pages and installed template fields. This is also where page-level broadcast schedules live: the schedule is the row's `BROADCAST_TIME`/Broadcast tab data tied to a selected `BROADCAST_TEMPLATE_NAME`, not necessarily a property of the Broadcast Template message body itself.

For temporary Facebook/Messenger send restrictions discovered in DigitalTRChat campaign reports, edit the Page row and use the **Broadcast** tab's `Restricted Until` field. Latest Rodolfo-approved rule after the July 2026 audit: if the latest current DigitalTRChat report shows pure `#2022`, set Page `Status = Broadcast` and `Restricted Until = X + 1 calendar day`; later, when the restriction expires and the page should return to operation, clear `Restricted Until`, save, and restore `Status = Broadcast`. Keeping `Status = Broadcast` with only `Restricted Until` was an earlier approach and should only be used if Rodolfo explicitly asks for that behavior.

### Page tab

`Messenger > Page` shows pages and installed template fields. Observed columns include:

```text
COMPANY
DOMAIN
URL
USER NAME
LOGIN
PROFILE NAME
PAGE ID
FB PAGE ID
PAGE NAME
UTM CAMPAIGN
LEADS TOTAL
LEADS ACTIVE
LEADS ACTIVE%
SOURCE
VERTICAL
COUNTRY
NOTES
TEMPLATE NAME
LANGUAGE
BROADCAST_TIME
CURRENT MESSAGE ID
MESSAGE ID
LAST SCHEDULE
STATUS
RESTRICTED_UNTIL
```

Column/API mapping for message pointers:

```text
UI column             API field
CURRENT MESSAGE ID    BROADCAST_CURRENT_MESSAGE_ID
MESSAGE ID            BROADCAST_MESSAGE_ID
```

When Rodolfo asks about the `MESSAGE ID` column, operate on `BROADCAST_MESSAGE_ID`, not `BROADCAST_CURRENT_MESSAGE_ID`. For a full reset to `-1`, read the full `Digital trust + Digital trust 2` Messenger Page table, backup rows where `BROADCAST_MESSAGE_ID != -1`, update `/campaigns/Messenger/update-many`, then re-fetch and validate final count. Restricted rows may return HTTP 500 if only `BROADCAST_MESSAGE_ID` is sent; preserve companion fields such as `STATUS` and `RESTRICTED_UNTIL` in grouped payloads. See `references/sb-messenger-page-message-id-reset-2026-07-02.md`.

### Page restriction workflow for purple/template-error cleanup

When DigitalTRChat shows a current temporary Messenger send restriction (`#2022 ... temporarily restricted ... until DATE`) for a page, suppress the page in Smart Bidding instead of changing template copy:

```text
Accounts > Messenger > Page > edit target row > Broadcast tab > Restricted Until
```

Latest operational rule from Rodolfo: for **pure/current #2022** rows, set `Status = Broadcast` and `Restricted Until` to the **same calendar date** shown in DigitalTRChat. Ciro/SB clears/handles the restriction automatically; do not schedule a manual clear.

Example:

```text
DigitalTRChat: restricted until July 22 at 7:55 AM
Smart Bidding: STATUS = Broadcast
Smart Bidding: RESTRICTED_UNTIL = 2026-07-22
```

Reactivation after expiry: edit the page, open the `Restricted Until` calendar, click `Clear`, save, and restore `Status = Broadcast` when the page is ready to return to operation. Do not apply this automatically to mixed `#2022 + other error` rows unless Rodolfo explicitly includes them.

The authenticated SPA API can apply this safely after capturing `/campaigns/Messenger` headers from the headed browser:

```text
PUT https://api.jbfdigital.com.br/campaigns/Messenger/update-many
Payload: {"RESTRICTED_UNTIL":"YYYY-MM-DD", "ids":["<SB row ID>"]}
```

Always validate by re-reading `/campaigns/Messenger` and checking the exact page row: `PAGE_NAME`, `PAGE_ID`, `FB_PAGE_ID`, `USER_LOGIN`, `STATUS == Broadcast`, and `RESTRICTED_UNTIL == target date`.

See `references/digitaltrchat-page-restriction-workflow-2026-07-02.md` for the DigitalTRChat XHR endpoints and the validated Zytiva test.

Operational use:

- inspect all pages;
- see installed template per page;
- see broadcast timing/current message state;
- verify status and page/template mapping;
- map or bulk-update Messenger Page broadcast schedules (`BROADCAST_TIME`).

For MGS schedule work, the correct full scope is `Digital trust` + `Digital trust 2`: confirm `56 sites`, click the blue refresh/update button, and validate `3,237` rows before analysis or edits. Capturing before `Digital trust 2` is selected/updated returns an incomplete `45 sites` / `2,443` rows dataset.

`BROADCAST_TIME` is stored/displayed in `America/Sao_Paulo` (Brasil). Convert from Brasil to the target country timezone for operational interpretation. For bulk edits by template/page, backup rows first, use `/campaigns/Messenger/update-many`, and validate via per-ID readback plus a fresh full-table recapture. See `references/sb-page-broadcast-times-bulk-update-2026-07-01.md`.


Critical schedule-edit caveat: changing the site multiselect is not enough. For MGS scope, select all 45 `Digital trust` child sites plus all 11 `Digital trust 2` child sites, then click the blue refresh/update button before trusting counts or API responses. Correct runtime baseline observed: `56 sites`, `3,237` pages, `53` templates. A stale 45-site capture returned `2,443` pages and was wrong.

For bulk schedule changes, the SPA route `PUT /campaigns/Messenger/update-many` can update only intended Page row IDs with `BROADCAST_TIME`; always backup rows first and re-read the full 56-site table afterward. See `references/messenger-page-schedule-update-2026-07-01.md`.
- audit or plan schedule reductions by grouping `BROADCAST_TIME` per `BROADCAST_TEMPLATE_NAME`.

Broadcast schedule caveat: the send-hour list is edited from `Messenger > Page` → row pencil or `Edit selecteds` → `Broadcast` tab → `Scheduled Times`. Even though the modal references `Message Template`, the schedule list is stored on Page/campaign rows and is exposed by the SPA `GET /campaigns/Messenger?...` payload as `BROADCAST_TIME`. Do not assume changing a Broadcast Template message bank changes page schedules. For schedule changes, backup the affected page rows, canary one exact template/subset first, then re-read `/campaigns/Messenger` to validate target rows changed and unrelated rows did not.

Timezone caveat: Rodolfo treats SB schedule values as Brazil-time operational inputs. Do not auto-convert to local country time or infer target hours; ask/confirm the exact SB hour list per country/template before writing.

Canonical country timezone map for converting desired local send hours into SB/Dash Brazil-time `BROADCAST_TIME` values:

```text
US -> America/New_York
CA -> America/Toronto
MX -> America/Mexico_City
AR -> America/Sao_Paulo + America/Santiago
DE -> Europe/Berlin
ES -> Europe/Paris + Europe/Rome
GB -> Europe/London
ZA -> Africa/Johannesburg
FR -> Europe/Paris
```

For countries with two operational zones, calculate both converted schedules and apply according to the page/template country routing that Rodolfo names; if the routing is not explicit, stop and confirm before writing.

Routing correction from the Utility pending-template session: when updating Messenger Page `BROADCAST_TIME`, a Page row's `COUNTRY` can be misleading or stale relative to the installed template. If Rodolfo names templates by vertical/country code, derive the schedule timezone from the **template name/code** (`DE-CC-DE`, `MX-CC-ES`, `US-JOB-ES`, etc.), not from the Page row `COUNTRY`, unless he explicitly says to route by Page country.

Schedule conversion pitfall: when updating Page `BROADCAST_TIME` for templates, derive the country from `BROADCAST_TEMPLATE_NAME` / vertical first (`DE-CC-DE`, `MX-CC-ES`, etc.), not from the Page row `COUNTRY`. Some rows can have `COUNTRY=US` while attached to a DE/MX template, and using the Page country writes the wrong converted hours. See `references/pending-template-local-time-rollout-2026-07-02.md`.

### Broadcast Template tab

REGRA CRÍTICA — filtro obrigatório: sempre que operar ou auditar `Messenger > Broadcast Template`, filtrar a coluna `COMPANY` por `digital-trust`. Esse filtro é o jeito correto de trazer juntos os templates de `digital-trust` e `digital-trust-2`. Nunca analisar Broadcast Template sem esse filtro quando o escopo for MGS.

`Messenger > Broadcast Template` shows installed templates and message counts. Observed columns include:

```text
COMPANY
DOMAIN
LANGUAGE
NAME
MESSAGES
LEADS
PAGES
APPROVAL
```

Operational use:

- find installed templates;
- identify template names by domain/language;
- inspect message counts before opening/editing templates;
- read backend `LEADS` and `PAGES` when visible or when the API response includes them;
- pull the full `MESSAGES` JSON for approval status and link extraction.

Critical `PAGES` distinction:

- When Rodolfo asks for the template list with pages/message count from this tab, use **Broadcast Template `PAGES`** from `/broadcast/Messenger[].PAGES` / the visible Broadcast Template column.
- Do **not** substitute a Page-tab row count grouped by `BROADCAST_TEMPLATE_NAME` unless explicitly labeled as `Page rows live`.
- Page-tab row counts are for `BROADCAST_TIME`, schedule work, and page-row ETA. Broadcast Template `PAGES` is what Rodolfo expects when pointing at `Accounts → Messenger → Broadcast Template`.

Backend caveat: `/broadcast/Messenger` returns `MESSAGES` as a JSON-encoded message array with `APPROVED`, `INVALID_FORMAT`, `REJECTED`, `LINK_1`, etc.; the UI may render it as a count. See `references/messenger-backend-fields-and-company-scope-2026-06-29.md` and `references/sb-utility-rollout-broadcast-pages-correction-2026-07-02.md`.

Bulk-update pattern: when editing many Messenger Broadcast Templates, the authenticated SPA API can be safer than repeated UI modal imports. Capture a real `/broadcast/Messenger` request/response from the headed browser, backup each full row, alter only `MESSAGES`, then `POST /broadcast/Messenger` with the complete template payload and captured auth headers. Re-read `/broadcast/Messenger` before claiming success. See `references/sb-broadcast-template-api-update-pattern-2026-06-30.md`.

- identify template names by domain/language;
- inspect message counts before opening/editing templates.

## Reports Navigation

Known SB report routes from prior MGS work:

```text
Reports > Messenger Daily
https://app.smartbiddingdigital.com/reports/messenger_daily

Reports > Messenger Pages
https://app.smartbiddingdigital.com/reports/messenger
```

Use `Messenger Daily` for revenue by segurador/date/site grouping.
Use `Messenger Pages` for page-level send/delivered/leads metrics.

Rodolfo correction 2026-07-03: the fast prefilter for low-delivery page health belongs in **Reports > Messenger Pages** (`https://app.smartbiddingdigital.com/reports/messenger`), not `Accounts > Messenger > Page`. Before trusting any SB report/filter, select the full MGS scope: all sites from `digital-trust` and all sites from `digital-trust-2`, then refresh/apply the selector. Rodolfo correction 2026-07-03: for the page-health execution, do **not** use low delivery as the operational criterion. The target is pages that sent broadcast and delivered **zero** messages. In the UI this may be inspected through the Messenger Pages filter, but the collector/logic must resolve it as:

```text
bd_sends > 0
bd_delivereds == 0
# equivalent delivered-rate check: bd_delivered_rate == 0
```

Do not treat `bd_delivered_rate<0.5` as actionable for this plan; that was an over-broad interpretation. Use zero-delivery rows as the suspect list for SB↔DTR confirmation: SB identifies pages that sent and delivered nothing; DTR/Bot confirms the latest actual error code/status before any write.

Important exception: bot users/seguradores/pages whose user/site/domain contains `cliquet`, `openzed`, or `zuout` may not appear in this low-delivery report. They only appear through the page-registration/reporting path (`Reports > Messenger Pages` / accounts route context) and must be swept directly in the Bot/DTR without depending on the SB low-delivery filter.

When possible, prefer export/CSV for large analysis. Dashboard navigation is for locating filters and confirming runtime behavior.

## Internal API Notes

The dashboard uses authenticated internal API calls. For Broadcast Template inventory, Zeus observed:

```text
GET https://api.jbfdigital.com.br/broadcast/Messenger?companies[]=digital-trust&companies[]=digital-trust-2&source=Messenger
```

This returned 94+ rows under Zeus' current company scope and included backend fields such as `LEADS`, `PAGES`, and `MESSAGES`. The API is not public/open: direct calls without the SPA authorization context return `401 Unauthorized`. Never print bearer tokens/cookies; summarize only status/count/keys/safe sample fields.

If `ctx.request.get()` returns `401` while the headed UI is logged in and working, trigger the real frontend route and capture the `/broadcast/Messenger` response via `page.on('response', ...)` instead of declaring the API inaccessible. This preserves the app's own auth/runtime headers and is the safest way to extract exact `MESSAGES` JSON/link sequences. See `references/sb-broadcast-response-capture-2026-06-30.md`.

`GET /company` under Zeus scope returned only `digital-trust` and `digital-trust-2`. If invalid company names are passed to `/broadcast/Messenger`, the endpoint may still return the authorized default scope, so do not treat a non-empty response as proof that the requested company exists.

## Runtime Caveats

- Site count is runtime/filter dependent. Always verify the current selected-site count and paginator count before reporting. For full MGS Messenger Page schedule inventory, validate `Digital trust` + `Digital trust 2`, selector `56 sites`, and paginator `Showing 1 to 50 of 3237` when that is the expected full scope. A prior 45-site capture returned only 2,443 rows and was incomplete.
- In the Messenger Page site multiselect, checking a company/group row such as `Digital trust 2` may not select all child publishers. If full scope matters, filter/search the selector and confirm the child publishers are selected, then click the blue square refresh/update button beside the site selector. See `references/sb-messenger-page-site-selection-and-schedule-inventory-2026-06-30.md`.
- `/reports/...` routes may return SPA shell with HTTP 404 while still rendering correctly in browser. Do not rely on raw HTTP status alone.
- If the body is blank after login, inspect console. If it contains `BotGuardError`, switch to headed/Xvfb route.
- If Auth0 says wrong password, first verify that `op --reveal` was used before assuming credentials are wrong.
- For any Rodolfo request about SB/DigitalTRChat/dashboard state, final answers must come from live dashboard/API, not historical snapshots, backups, cached exports, or persisted state. Snapshots/backups are only support evidence or rollback material unless Rodolfo explicitly authorizes snapshot-only analysis. If Rodolfo says “atualizado”, “na dashboard”, “na Dash”, “lista”, “relatório”, “páginas”, “msgs”, “bot”, “campanha”, or asks a correction to a prior report, re-query live first. If a snapshot/state disagrees with live SB/DTR, live wins.
- For DigitalTRChat page/app/profile health, **current status = only the latest sent/Completed campaign report per page**. Do not scan all historical `Completed` reports and aggregate them as current state: older reports can reflect past app outages, temporary restrictions, permission failures, or profile migrations that later recovered. Per page: filter/query `Completed`, order by schedule/send time descending, open only the newest report with `Campaign report`, classify its `Sent response`, and label pages with no newest report as `sem último Completed/report útil`.
- DigitalTRChat bot-user audits must iterate **all top-bar seguradores/accounts**, not just the first account loaded after login. The top switcher uses `.account_switch` entries and `POST /social_accounts/fb_rx_account_switch` with `id=<data-id>`. For each bot user: enumerate account switcher entries, switch segurador, reload Subscriber broadcast, parse that segurador's `search_page_id` pages, then apply the latest-Completed-report rule per page. Always state accounts/seguradores visited and page contexts audited in the report.
- **Bot dashboard provenance rule:** when Rodolfo asks whether a DTR/Bot classification was trustworthy, keep sources explicit. `Dashboard da SB` = `app.smartbiddingdigital.com` / `api.jbfdigital.com.br/campaigns/Messenger` and only proves operational state such as `STATUS`/`RESTRICTED_UNTIL`. `Dashboard do Bot` = `digitaltrchat.com` and is the source for sent-message code classification (`Sent`, `#2022`, `#10`, `#100`, `#551`). Do not answer a Bot-source question with SB-only evidence. For Bot audits, never trust `search_page_id=''` or account labels alone: validate the account context changed, enumerate real `search_page_id` options, then query newest Completed per page. If repeated campaign IDs/signatures appear across seguradores, invalidate the scan and redo page-by-page. See `references/dtr-bot-dashboard-page-by-page-validation-2026-07-03.md`.
- For DigitalTRChat error reports, cross-check live SB Messenger Page status before reporting/action. Exclude pages already `On-hold` or permanently `Blocked` from current operational errors: their latest DTR `Completed` report can be historical noise because they no longer enter scheduling. Report counts before/after this SB filter (`ignored On-hold`, `ignored Blocked`, `missing SB match`). See `references/digitaltrchat-sb-onhold-filter-and-2022-apply-2026-07-02.md`.
- Current #2022 rule from Rodolfo/Ciro: for pure/current temporary Messenger restriction, keep/set `STATUS=Broadcast` and set `RESTRICTED_UNTIL` to the same calendar date shown in DigitalTRChat. Do not add one day, do not use `Blocked` by default, and do not plan manual clear/reactivation; SB handles expiry. Operational counts must come from `Accounts > Messenger > Page` filtered to `Broadcast`, not Broadcast Template `PAGES`. See `references/digitaltrchat-2022-broadcast-sameday-rule-2026-07-02.md`.
- Broadcast Template `PAGES` can disagree with live Page rows.
- For `#2022` bulk remediation after the SB status filter, apply `STATUS=Broadcast` + `RESTRICTED_UNTIL=DATE` to any current operational row whose latest DTR report contains `#2022`, including mixed `#2022 + other codes`. Mixed-code rows must also be saved to local state/database for post-expiry investigation, because the companion error may explain why the page entered restriction. Always group updates by target date, backup the exact SB rows first, and validate by re-reading `/campaigns/Messenger` for every row (`STATUS`, `RESTRICTED_UNTIL`, `PAGE_ID`, `USER_LOGIN`, `PROFILE_NAME`, companion DTR codes if mixed).
- Broadcast Template `PAGES` can disagree with live Page rows. When Rodolfo points to or asks about `Accounts > Messenger > Broadcast Template`, use the Broadcast Template `PAGES` column from live `/broadcast/Messenger[].PAGES`. Only use `Messenger > Page` row counts when he explicitly asks for Page-tab rows/schedule/page mapping, and label them clearly.
- Rodolfo clarified the `PAGES` count semantics for Messenger templates: `PAGES = Status Broadcast + Status Campaign`. `Campaign` is operationally active and can send broadcast. `Blocked` and `On-hold` are excluded from the template page count. For actual send/approval availability, also exclude pages with active `RESTRICTED_UNTIL` even if the row still says `Broadcast`.
- For DTR→SB page-health apply jobs, the validated activation gate is strict: canary → batch/apply with readback → consolidate JSON/XLSX → resolve every readback failure and DTR context warning → REPORT-INFRA/inventory → only then enable the recurring cron. If Rodolfo asks whether the plan is “executing correctly,” compare the live script/cron against the validated thread rules before saying yes. If an apply run is active and the audit finds a rule violation, stop it first, patch, dry-run small, and only re-enable after a clean reconciliation.

For DigitalTRChat `#2022 temporarily restricted until DATE` page errors, the agreed SB control is: set Messenger Page `STATUS=Broadcast` and `RESTRICTED_UNTIL=DATE` (same date shown by DigitalTRChat) **only for operational rows where the status gate allows it**. `On-hold` rows must not be reactivated or restricted automatically; record/report instead. `Blocked` rows must not be set to Broadcast unless `https://facebook.com/{FB_PAGE_ID}` opens normally; unavailable/ambiguous Facebook checks keep the row Blocked. Ciro/SB handles expiry automatically; no manual clear workflow is needed by default. Do not auto-block other error classes without Rodolfo’s approval.

When Rodolfo provides an external restricted-pending file/list for SB updates, treat it as an SB bulk-write job with the same safety gate: parse dates to ISO, match file `pg_<id>` against SB numeric `PAGE_ID` plus exact `FB_PAGE_ID`/`UTM_CAMPAIGN`, backup matched rows, update only operational `Broadcast`/`Campaign` rows, skip `On-hold`/`Blocked` on the first pass, then re-fetch `/campaigns/Messenger` and validate every row by `ID`. If Rodolfo explicitly approves preserving `On-hold`, run a second pass over only On-hold rows: set `RESTRICTED_UNTIL` while keeping `STATUS=On-hold`; if update-many returns HTTP 500 with only `RESTRICTED_UNTIL`, retry with explicit `STATUS=On-hold` and validate status did not change. Do not apply this to `Blocked` rows without separate approval and Facebook/page validation. For this route, build full scope from **all** `Digital trust` + `Digital trust 2` child publisher IDs returned by `/company`; active-only publishers can miss rows. See `references/sb-restricted-pending-file-bulk-apply-2026-07-04.md`.
- Utility approval workflow: templates with Broadcast Template `PAGES > 0` can be approved; templates with `PAGES = 0` should stay at 10 messages and must not be Run-Approved because approval has no linked page to execute against. Cron should monitor `PAGES=0` templates and, when one gains pages, start the normal rule.
- Script-only cron reports can run successfully but fail to appear in Discord/thread. When a scheduled SB review report is missing, inspect Hermes cron output under `~/.hermes/profiles/zeus/cron/output/` and the rollout log under `/root/mgs-agent/logs/` before concluding the cron did not run.

## Do / Don't

Do:

- use headed Playwright via `xvfb-run`;
- use persistent storage state;
- retrieve password with `--reveal`;
- validate real page body/title after login;
- keep secrets out of stdout/final responses;
- use screenshots/exports/API if UI navigation becomes unstable.

Don't:

- use Playwright headless as final path;
- report BotGuard as bad credentials;
- print cookies, Auth0 codes, access tokens, refresh tokens, or passwords;
- assume site count from memory;
- claim dashboard data without verifying current runtime/export.

## Broadcast Template Import/Replacement Pattern

Use this when Rodolfo asks to replace messages inside existing SB Messenger Broadcast Templates.

Controlled sequence for full-bank replacement only:

```text
Filter/open exact template
→ backup raw JSON + import-format CSV from `/broadcast/Messenger`
→ if reducing/ranking messages, select text/CTA first and assign numbered links separately in the target template's original numeric order
→ click blue `N Messages`
→ Import tab
→ Erase all ONLY when intentionally replacing every message
→ Upload prepared CSV
→ verify uploaded/total count in the Import tab
→ Update in the Messenger Messages modal
→ Save in the parent Edit Messenger Broadcast modal
→ re-query `/broadcast/Messenger` and validate count + first/last text/link
```

Current Utility live-repair rule from Rodolfo 2026-07-03: do **not** use `Erase All` for normal production repair. Edit/replace only problem message slots. Editing one individual message should only reset that message to gray; if the whole template turns gray, treat it as an SB/Ciro bug. Global rollout replaces red/REJECTED only; gray is alert-after-2-days; purple is diagnosis-only unless running an explicitly approved single-template test.

Pitfalls:

- `Update` inside the message modal is not the final persistence step. The parent `Edit Messenger Broadcast` modal also needs `Save`.
- Do not treat a backup as a good rollback if the live template already has an unexpected count/content; stop and report.
- MANDATORY LINK INVARIANT: message replacement/reduction/rollout must treat `LINK_1` as a slot column, not as part of the selected message. After choosing/reordering TEXT/CTA, reassign `LINK_1` by target `MESSAGE_ID` from the template’s canonical pre-change source bank: row 1 gets source link slot 1, row 2 gets source link slot 2, etc. Never let a rollout start at `mct-003-2` or skip earlier link slots because the selected text originally came from a later row.
- Preserve each target template’s exact `LINK_1` slot sequence from its own source bank when preparing replacement CSVs/API payloads. Do not infer a neat `1..15` rotation; keep repeated links, `-2` variants, and query params exactly as the source template uses them.
- When ranking/selecting only the best subset of messages, do not carry the selected row's old link if that breaks numbered `mct` order. For numbered templates, reassign links as `mct-001`, `mct-001-2`, `mct-002`, etc. while preserving exact URL strings from the source bank. For single-link/non-numbered templates, use the source bank’s repeated link slots exactly.
- Validation gate before Save/POST success: compare current `LINK_1` list by `MESSAGE_ID` against `source_bank[:N].LINK_1`. If any mismatch exists, stop and fix before Run Approvals or final report.
- After any message update/import/API write, expect statuses to reset to gray/no-status until approval is run. Do not interpret all-gray as final Meta result. Run Approval only for templates with live Broadcast Template `PAGES > 0`; leave `PAGES = 0` templates at 10 messages and skip approval.
- Utility rollout cron status rule: replace only true red `REJECTED` messages caused by copy/category/policy issues. Do **not** replace purple/error messages (`ERROR` / `INVALID_FORMAT`) because they usually mean app/page/segurador permission, execution failure, or a restricted page contaminating approval. Purple is a diagnosis queue, not a copy-change trigger: first inspect DigitalTRChat Subscriber broadcast campaign reports for `Sent response` errors such as `#2022 temporarily restricted until X`, then set the affected SB Page `Restricted Until` to `X` (same date shown) while keeping `Status=Broadcast`. Only after restricted pages are excluded should approval be rerun/awaited. Do not freeze the whole template just because some page/segurador rows are purple; a template can be installed on many pages/profiles and only a subset may be broken.
- When leveling an active Utility rollout after Rodolfo asks to simplify: `PAGES > 0` templates should be normalized to 20 messages; `PAGES = 0` templates should be normalized to 10 messages. Preserve link slots during leveling, then produce a live report split by linked vs unlinked templates if requested.
- When Rodolfo gives exact test template names and asks for results in a Sheet, read those templates from SB/Dash and output raw rows per template with source/status columns. Do not consolidate or dedupe across templates unless explicitly requested.
- When a production rollout is expanded with “also do these templates,” reuse the exact previously selected bank for the same vertical/language, not a newly regenerated or different-language bank. Still backup each additional target and validate each by API.
- Before applying a bank to templates, guard against wrong vertical/language by checking both the bank source path/name and obvious content markers (for example reject Spanish `tarjeta/solicitud/aprobado` markers when applying `GB-CC-EN`).
- When Rodolfo points to a template with zero-width characters (for example `ES-ZW` naming), inspect the live `MESSAGES` payload and count Unicode zero-width characters (`U+200B`, `U+200C`, `U+200D`, `U+FEFF`, `U+2060`) separately from message content. Treat this as analysis only unless he explicitly asks to modify/import the template.

See `references/broadcast-template-import-replacement-2026-06-29.md` for the detailed session pattern.
See `meta-utility-template-approval/references/gb-us-cc-template-reduction-link-order-and-raw-results-2026-06-30.md` for the 70-message reduction, numbered link order correction, and raw per-template approval-result sheet pattern.
See `references/broadcast-template-import-replacement-2026-06-29.md` for the detailed session pattern.

## Table Filtering + Extraction Pattern

SB PrimeVue tables can be filtered and exported through the same headed/Xvfb browser route. Use this when Rodolfo asks to “mapear”, “planilhar”, “filtrar”, or inventory dashboard rows.

Canonical UI sequence:

```text
/accounts
→ select top source/context, e.g. Messenger
→ choose tab, e.g. Broadcast Template or Page
→ click the column filter button for the desired column
→ type the filter value, e.g. digital-tr
→ Apply
→ extract headers + tbody rows across all paginator pages
→ write CSV with UTF-8 BOM when user-facing text may include accents/emoji
→ update/read back the Google Sheet tab if a sheet is the operational tracker
```

Implementation notes:

- Do not rely on raw body text to decide whether the Messenger context is already selected; notification text can contain the word “Messenger”. Select the top dropdown explicitly when the target table depends on it.
- PrimeVue filter buttons are usually `button.p-column-filter-menu-button`; wait for them after switching tabs.
- PrimeVue paginator next button is usually `button.p-paginator-next`; stop when it has `p-disabled` or `disabled`.
- Known `Messenger > Broadcast Template` UI/DOM columns observed in Zeus session: `COMPANY`, `DOMAIN`, `LANGUAGE`, `NAME`, `MESSAGES`, `LEADS`, `PAGES`, `APPROVAL`.
- `LEADS`, `PAGES`, and `MESSAGES` are backend/API-derived values from `/broadcast/Messenger`; they may not be visible in Rodolfo's cropped UI/table layout, but if present in the API they can be planilhados with a clear note that they came from backend data, not manual calculation.
- For inventory work, validate with three checks before reporting: CSV row count, Sheet readback row count, and a sentinel row/domain that should exist.

Support files:

- `scripts/sb_table_export.py` — reusable starter for exporting an SB table through the headed/Xvfb route, applying a company filter, paginating rows, writing a BOM CSV, and optionally updating a Sheet.
- `references/broadcast-template-import-replacement-2026-06-29.md` — controlled replacement workflow for Messenger Broadcast Templates: backup, Import tab, Erase all, Upload, Update, required parent-modal Save, API validation, exact `LINK_1` sequence preservation, and approval status fields.
- `references/broadcast-template-api-and-utility-approval-2026-06-29.md` — session notes on the authenticated `/broadcast/Messenger` API, backend `LEADS/PAGES/MESSAGES` fields, visible company scope, and Rodolfo's Utility canary→production replacement workflow.
- `references/sb-internal-api-template-inventory-2026-06-29.md` — focused API notes: internal auth/bearer behavior, scoped companies, backend `LEADS/PAGES/MESSAGES` fields, invalid-company filter caveat, and raw `/company` payload redaction warning.
- `references/messenger-report-page-health-api.md` — notes on `/reports/messenger` / `POST /report/messenger` for page-level health monitoring, including PAGE_ID filtering, Patricia Smith validation, delivery/lead fields, and false-positive caveats during Utility-template migration.
- `references/digitaltrchat-page-restriction-workflow-2026-07-02.md` — logged-in DigitalTRChat XHR endpoints for Subscriber broadcast campaign reports, `#2022` temporary messaging restriction interpretation, and the Smart Bidding `RESTRICTED_UNTIL = same error date` workflow validated on Zytiva.
- `references/sb-purple-approval-diagnostics-2026-07-02.md` — diagnostic pattern for purple Messenger approval bars: parse `/broadcast/Messenger[].MESSAGES` `ERROR`/`INVALID_FORMAT` + `REJECTED_REASON`, then join `/campaigns/Messenger` by template to identify affected `PROFILE_NAME`, `LOGIN`, pages, and app/page-permission failures.
- `references/sb-digitaltrchat-restricted-page-workflow-2026-07-02.md` — confirmed DigitalTRChat internal XHR endpoints for Subscriber broadcast campaign reports and the Rodolfo-approved cleanup: for `#2022 temporarily restricted until X`, keep SB Page `Status=Broadcast` and set `Restricted Until=X+1 day` so restricted pages are excluded from routing/approval without permanently blocking the page.
- `references/messenger-page-broadcast-schedule-audit-2026-06-30.md` — session note for auditing Messenger Page `BROADCAST_TIME` schedules via `/campaigns/Messenger`, grouping by template/country, and safely planning bulk schedule edits.
- `references/sb-utility-live-inventory-template-rollout-2026-07-02.md` — Rodolfo correction and operating pattern for live SB template inventory, Page-count joins, Utility 10-message conversion, link preservation, Run Approvals, and ETA calculation.
- `references/sb-utility-rollout-broadcast-pages-correction-2026-07-02.md` — correction that Broadcast Template reports must use `/broadcast/Messenger[].PAGES`, not Page-tab row counts; includes cron/report visibility lesson.
- `references/sb-utility-global-rollout-and-cron-review-2026-07-02.md` — global rollout inclusion rule for all non-test/non-NAO-USAR templates, live Page-count validation, and cron review-only delivery/output diagnostics.
- `references/sb-utility-live-rollout-pages-links-2026-07-02.md` — Rodolfo corrections for SB Utility rollout: live-only reports, Broadcast Template `PAGES` vs Page rows, link-slot invariant, 20/10 leveling by pages, Run Approval eligibility, ETA calculation, and cron monitoring for templates that gain pages.
- `meta-utility-template-approval/references/sb-utility-template-status-rules-2026-07-03.md` — companion Utility status rules: do not use Erase All for normal repair, red-only global replacement, gray alert-after-2-days, purple diagnosis-only, individual-message update bug expectations, and controlled single-template test workflow.
- `references/sb-messenger-page-message-id-reset-2026-07-02.md` — `Messenger > Page` `MESSAGE ID` reset workflow: `MESSAGE ID` maps to `BROADCAST_MESSAGE_ID`, not `BROADCAST_CURRENT_MESSAGE_ID`; backup non-`-1` rows, update `/campaigns/Messenger/update-many`, preserve `STATUS`/`RESTRICTED_UNTIL` for restricted rows to avoid backend 500, and validate final live count.
- `references/digitaltrchat-bot-error-audit-and-sb-restrictions-2026-07-02.md` — DigitalTRChat internal campaign/report endpoints, phase-1 exception-only audit shape, `#2022` → SB `Broadcast + Restricted Until same DATE` workflow, and Broadcast Template `PAGES = Broadcast + Campaign` semantics.
- `references/digitaltrchat-live-latest-report-audit-2026-07-02.md` — Rodolfo correction for bot audits: live mode only; current page/app/profile status must use only the newest `Completed` campaign report per page, not all historical `Completed` reports.
- `references/digitaltrchat-all-seguradores-live-audit-2026-07-02.md` — Rodolfo correction that a bot login only opens one segurador/account; full audits must iterate the top-bar `.account_switch` seguradores via `/social_accounts/fb_rx_account_switch`, then audit each segurador's pages using latest Completed report only; includes exact error strings and last-5 checks for `#10`/`#551`.
- `references/digitaltrchat-full-segurador-audit-methodology-2026-07-02.md` — complete live audit methodology after Rodolfo correction: iterate every top-bar segurador/account per bot user, use only newest Completed report per page, filter live SB `On-hold`/`Blocked`, split pure vs mixed `#2022`, inspect last five reports for `#10`/`#551`, and reconcile permission/app-deleted errors with the migration sheet.
- `references/dtr-step1-inventory-reconciliation-2026-07-03.md` — Step 1 inventory gate for DTR/SB page-health: sheet first, `X` before dashboard, duplicate segurador/account detection before page reads, `NO_PAGES` as report-and-ignore, stable classification labels, and the validated read-only execution counts.
- `references/digitaltrchat-sb-onhold-filtered-audit-2026-07-02.md` — Rodolfo correction that DTR latest-report errors must be cross-checked against live SB Messenger Page status before reporting/actioning: ignore `On-hold`/`Blocked`, keep `Broadcast`/`Campaign`, split pure vs mixed `#2022`, validate SB bulk updates by readback, and cross-check migration sheet `X`/`Perfil antigo` markers.

## References

- `references/sb-dtr-page-health-zero-delivery-and-reporting-2026-07-03.md` — Rodolfo corrections from the Passo 1 execution: use zero delivery, not low delivery; include SB active restrictions and direct cliquet/openzed/zuout sweeps; report results only after execution with problem explanations and recommended actions; list exact DTR context-warning users/seguradores instead of vague “contexto inseguro”.
- `references/dtr-sb-full-scope-restricted-sync-2026-07-03.md` — full corrected DTR→SB restricted-page workflow: sheet `gid=562940072` as scope, active bot users only, every top-bar segurador/account, latest Completed per page, SB live filtering, `#2022` pure/mixed write rule, mixed-code state persistence, report labels, alert channels, and validated small-canary rollout sequence.
- `references/dtr-sb-restricted-sync-scope-correction-2026-07-03.md` — Rodolfo correction for DTR→SB automation scope: active bot users must come from live `Migração 22/06` sheet, not all 1Password DTR items; iterate every top-bar segurador/account and every page, inspect latest Completed only, then cross-check SB and skip `On-hold`/`Blocked`/active `RESTRICTED_UNTIL` before any `#2022` write.
- `references/dtr-sb-full-scope-page-by-page-2026-07-03.md` — follow-up correction after a faulty test: DTR `.account_switch` can return HTTP 200 while campaign data remains global/identical; prove account scoping before using segurador labels, otherwise scan page-by-page via `search_page_id`, report unique pages separately from occurrences, and persist mixed `#2022 + other codes` for post-expiry review.
- `references/dtr-sb-page-health-sync-final-2026-07-03.md` — final Rodolfo-validated production workflow: active sheet users only, Bot page-by-page latest Completed, NOTES annotation for every non-Sent result across all SB statuses, `#2022` restricted sync, reconference of already restricted SB pages, On-hold/Blocked safety rules, canary/readback requirement, and canonical script/cron paths.
- `references/dtr-sb-page-health-sync-apply-lessons-2026-07-04.md` — apply-run lessons for the DTR→SB sync: use the Google Sheets `gviz` CSV endpoint when `/export` returns 400, discover DigitalTRChat 1Password items by ID after matching username, treat SB HTTP 500/readback failures as partial apply, skip `account_context_signatures_not_unique` users, and do not enable cron until failed rows/context issues are reconciled.
- `references/dtr-sb-page-health-sync-execution-audit-2026-07-03.md` — execution-audit lessons after Rodolfo asked whether the validated plan was actually running correctly: do not enable recurring apply cron before final reconciliation, hard-gate On-hold/Blocked for `#2022`, skip writes on non-unique DTR context, clear `RESTRICTED_UNTIL` via modal POST, avoid duplicate cron logging, and use the REPORT-INFRA webhook route.
- `references/dtr-sb-page-by-page-notes-and-reactivation-2026-07-03.md` — Rodolfo-approved production rules for DTR page-by-page audit: Dashboard da SB vs Dashboard do Bot naming, `NOTES` append-only code updates for non-`Sent` outcomes, reconfirming already-restricted SB pages, `On-hold` non-reactivation, and Facebook URL validation before unblocking `Blocked` pages.pt/cron paths.
- `references/dtr-sb-page-health-sync-execution-audit-2026-07-03.md` — execution-audit lessons after Rodolfo asked whether the validated plan was actually running correctly: do not enable recurring apply cron before final reconciliation, hard-gate On-hold/Blocked for `#2022`, skip writes on non-unique DTR context, clear `RESTRICTED_UNTIL` via modal POST, avoid duplicate cron logging, and use the REPORT-INFRA webhook route.
- `references/dtr-sb-page-by-page-notes-and-reactivation-2026-07-03.md` — Rodolfo-approved production rules for DTR page-by-page audit: Dashboard da SB vs Dashboard do Bot naming, `NOTES` append-only code updates for non-`Sent` outcomes, reconfirming already-restricted SB pages, `On-hold` non-reactivation, and Facebook URL validation before unblocking `Blocked` pages.
- `references/messenger-backend-fields-and-company-scope-2026-06-29.md` — authenticated SB API observations for `/company` and `/broadcast/Messenger`, scoped companies, backend message fields, approval counters, and safety notes.
- `references/messenger-backend-fields-and-company-scope-2026-06-29.md` — authenticated SB API observations for `/company` and `/broadcast/Messenger`, scoped companies, backend message fields, approval counters, and safety notes.

## Escalation

If headed/Xvfb route fails:

1. Capture console errors with secrets redacted.
2. Try a fresh Auth0 login with `--reveal`.
3. Recreate `/tmp/smartbidding_state_headed.json`.
4. If BotGuard still blocks, ask for manual screenshot/export or ask Ciro/SB for API/token support.


## Update 2026-07-03 — DTR→SB full workflow scope correction

Rodolfo corrected the DTR→SB restricted-page automation scope: **do not use all 1Password `Digitaltrchat - Disparos*` items as the source of truth**. The source of active bot users is the live Google Sheet tab `Migração 22/06`; exclude rows/users marked `Removidos acumulado = X`. For each active bot user, log into DigitalTRChat, iterate every top-bar segurador/account, list every page in that segurador, and inspect only the latest `Completed` campaign/report per page. **Validation required after every account switch:** the campaign/page dataset must visibly change or carry an account-specific marker; if identical campaign IDs repeat across multiple seguradores, the switch did not take effect or the endpoint is global, and the run is invalid/non-actionable. Before reporting or writing, cross-check live SmartBidding `Accounts > Messenger > Page` under `digital-trust + digital-trust-2`; ignore `On-hold`, `Blocked`, and pages with active `RESTRICTED_UNTIL` until their release date. Any current `#2022` from the latest report may be auto-applied, including mixed `#2022 + other codes`: keep/set `STATUS=Broadcast`, set `RESTRICTED_UNTIL` to the same date shown by DTR, save via SB, and validate live readback. Mixed `#2022 + other codes` must also be persisted to local state/database for post-expiry investigation (`needs_post_expiry_review=true`) because the companion code may explain why the page entered restriction. Do not auto-write `PERMISSION`, `APP_DELETED`, `#10_WINDOW`, `#551_UNAVAILABLE`, `#100_TEMPLATE`, `TOKEN`, `OTHER` when they occur without `#2022`, or pages with no latest Completed/report; report/diagnose them instead. Target schedule: 07:30 and 15:30 ET, live from scratch, sequential with `flock`, quiet on no-op, and alert if sheet read, DTR login, SB access, write, or readback fails. The old partial cron that used all 1P DTR items was disabled and must not be re-enabled.

## Update 2026-07-02 — #2022 rule correction

Rodolfo/Ciro corrected the temporary restriction workflow: for current/pure `#2022`, keep/set `STATUS=Broadcast` and set `RESTRICTED_UNTIL` to the same date shown in the DigitalTRChat warning, not D+1. Ciro/SB handles expiry automatically. For operational counts, do not trust Broadcast Template `PAGES`; use `Accounts > Messenger > Page` filtered to `STATUS=Broadcast`, and consider active `RESTRICTED_UNTIL` when judging send availability.

## Update 2026-07-02 — restricted pages daily monitor

Zeus criou monitor dedicado para páginas Messenger restritas: `/root/mgs-agent/scripts/monitor-sb-restricted-pages.sh` → Python `/root/mgs-agent/scripts/monitor-sb-restricted-pages.py`, state `/root/mgs-agent/data/sb-restricted-pages-monitor.json`, log `/root/mgs-agent/logs/monitor-sb-restricted-pages.log`, cron `0 8,16 * * *` com `flock`, canal Discord `1522442220903337984`. O monitor lê live `Accounts > Messenger > Page` via `/campaigns/Messenger`, escopo publishers ativos `digital-trust + digital-trust-2`, filtra `STATUS=Broadcast` + `RESTRICTED_UNTIL >= hoje`, e só alerta quando há novas restrições ou resoluções/expirações. Modelo de alerta Discord aprovado por Rodolfo: 2 mensagens em code block sem linguagem — bloco principal com resumo/por data/novas e bloco separado para legenda de erros; sem link da Sheet no alerta. Na seção `POR DATA DE SAÍDA`, ordenar por data crescente (menor → maior), nunca por volume/quantidade de páginas; Rodolfo quer leitura cronológica do que sai primeiro. Regra de segurança de layout: enquanto o cron `monitor-sb-restricted-pages.sh` for SB-only, o alerta não pode exibir `hora DTR`, `Código erro` ou `DTR pendente` como se fossem dados lidos; deve rotular a origem como `SB-only; DTR não lido` ou ocultar colunas DTR até o checker do Bot/DigitalTRChat estar acoplado e validado. DTR enrichment/update implementation status: detector `/root/mgs-agent/scripts/dtr-detect-restricted-pages.py` can log into DigitalTRChat and extract `#2022` + release date/time from recent Completed reports; SB updater `/root/mgs-agent/scripts/sb-set-restricted-until.py` remains a manual single-page dry-run/apply utility. **Do not enable production DTR→SB cron from all 1Password `Digitaltrchat - Disparos*` items.** Rodolfo corrected the scope: active bot users must come from the live `Migração 22/06` sheet, then the detector must log into each active bot user, iterate every top-bar segurador/account, enumerate all pages, inspect only the latest Completed report per page, cross-check live SB, skip `On-hold`/`Blocked`/active `RESTRICTED_UNTIL`, and only then apply current `#2022` (pure or mixed). Mixed `#2022 + other codes` must be saved for post-expiry review. Production cron is not ready until that full dry-run is validated. See `references/dtr-sb-restricted-sync-scope-correction-2026-07-03.md`. Execução inicial 2026-07-02 validou `3.237` rows, `48` publishers ativos e `209` páginas restritas ativas. Para layout, labels, colunas e legenda do report Sheet, seguir `references/sb-restricted-pages-sheet.md`.

Rodolfo corrigiu o desenho final: para horário real de saída, o monitor deve virar `SB filter + DigitalTRChat checker + Sheet writer`. SB só dá data; DTR é a fonte real do erro e hora. Páginas já restritas na SB devem ser puladas no DTR até expirarem. O relatório Discord não deve ter rodapé e deve ter seções `Resumo`, `Por data/hora de saída`, `Novas restrições detectadas`, `Ignoradas nesta rodada`, separando `On-hold` e `Blocked`. O report completo deve ir para a Sheet, com título `Páginas Restritas — MGS`, categoria `Restrita`, bot user sem `@gmail.com`, e a coluna `Página` como hyperlink `https://facebook.com/{FB_PAGE_ID}`. Detalhes em `references/sb-restricted-pages-monitor-and-report-layout-2026-07-02.md`.

Correção de desenho aprovada por Rodolfo: o monitor final deve ser **SB filter + DTR checker**. SB filtra o pool operacional (`Accounts > Messenger > Page`, `STATUS=Broadcast`, `digital-trust + digital-trust-2`) e pula páginas já com `RESTRICTED_UNTIL` ativo; DigitalTRChat é a fonte real para detectar novas restrições e extrair a data/hora exata de saída abrindo a última mensagem/report de cada página checável em todos os usuários/seguradores. Páginas restritas só voltam ao DTR check depois que expiram/limpam. Layout Discord aprovado: seções `Resumo`, `Por data/hora de saída`, `Novas restrições detectadas`, `Ignoradas nesta rodada`; sem rodapé; remover `@gmail.com` do usuário bot; separar `On-hold` e `Blocked`; usar `Sem report DTR válido` em vez de “sem último report útil”. Sempre preferir resumo curto no Discord + Excel completo quando houver mudança/erro. Ver `references/sb-restricted-pages-monitor-layout-and-dtr-enrichment-2026-07-02.md`.
