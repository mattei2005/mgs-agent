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

For `PAGE_ID` / `UTM_CAMPAIGN` registration corrections, do **not** rely on `PUT /campaigns/Messenger/update-many`: it can return HTTP 200 while ignoring those fields. Use `GET /campaigns/Messenger/{ID}` to fetch the exact row payload, modify only `PAGE_ID` and `UTM_CAMPAIGN`, then `POST /campaigns/Messenger`; validate against a fresh full-scope `/campaigns/Messenger` readback. Avoid posting the full-table row shape for this correction class — it can return SB HTTP 500 while the exact-row payload succeeds.

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

