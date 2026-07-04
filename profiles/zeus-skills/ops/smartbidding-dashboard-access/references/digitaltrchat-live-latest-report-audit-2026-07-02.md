# DigitalTRChat live latest-report audit — 2026-07-02

## Correction captured

Rodolfo corrected the first phase-1 audit methodology: scanning every historical `Completed` campaign/report is wrong for current page/app/profile health.

Reason: older reports can reflect a past app outage, a temporary page restriction, a permission problem, or a developer/profile migration that has already been fixed. The latest sent message is the current operational signal.

## Mandatory rule

For DigitalTRChat bot/dashboard audits:

```text
Live mode only.
Current status per page = latest sent/Completed campaign report only.
Older Completed reports = history, not current state.
```

Do not use saved screenshots, cached JSON, prior reports, or historical snapshots unless Rodolfo explicitly asks for snapshot-only/historical analysis.

## Live XHR route

For each bot user from 1Password:

1. Login to `https://digitaltrchat.com/home/login` with session cookies.
2. Open live route:

```text
GET /messenger_bot_enhancers/subscriber_broadcast_campaign
```

3. Parse `#csrf_token` and `#search_page_id` options. Each non-empty option is a page in that bot user.
4. For each page, query only the latest completed campaign:

```text
POST /messenger_bot_enhancers/subscriber_broadcast_campaign_data
search_page_id=<page_id>
search_status=2              # Completed
order[0][column]=12          # Scheduled at
order[0][dir]=desc
length=1
csrf_token=<csrf>
```

5. If no row comes back, classify page as `NO_COMPLETED_REPORT` / `sem último Completed/report útil`.
6. Extract the row's `cam-id` from the action HTML and open the live report:

```text
POST /messenger_bot_enhancers/campaign_sent_status
id=<cam_id>
csrf_token=<csrf>

POST /messenger_bot_enhancers/campaign_sent_status_data
campaign_id=<cam_id>
csrf_token=<csrf>
length=<large enough for all rows>
order[0][column]=3
order[0][dir]=desc
```

7. Classify only the returned `Sent response` values from this newest campaign/report.

## Report shape Rodolfo expects

Keep the same executive shape as previous reports, but the counts must be based on latest report only:

```text
Usuários informados
Logins OK
Usuários sem páginas no bot
Páginas sem último Completed/report
Páginas com erro no último report
Páginas com #2022 no último report
#2022 puro
#2022 misturado com outro erro
```

Then list:

```text
Páginas com #2022 no último report
Top usuários com erro por quantidade de páginas afetadas
Usuários sem nenhuma página no bot
Páginas sem último Completed/report útil — count/group by user unless full list requested
```

Do not list OK pages unless Rodolfo explicitly asks for full inventory.

## Error classification notes

Useful buckets observed in live audit:

```text
#2022 temporary restriction
PERMISSION / pages_messaging permission missing
APP_DELETED / application has been deleted
#10 outside allowed messaging window
#551 person unavailable
#100 template/user not found
TOKEN/session invalid
OTHER
```

If a latest report has both `#2022` and another high-volume error such as `#10`, split it as `#2022 misturado` and do not treat it as a clean auto-action candidate without review.

## Pitfalls

- Never answer a live dashboard-state request from the prior session summary or a saved report.
- Never aggregate every historical `Completed` report as if it were current health.
- `Pending` is not a send-result signal.
- A page can exist in the bot but have no useful completed report because it was added and never used; report as inventory/setup, not critical failure.
- Keep secrets out of stdout and final reports: no passwords, cookies, CSRF tokens, bearer headers, or session values.
