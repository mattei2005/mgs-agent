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

Quick live-count question: when Rodolfo asks whether “templates de broad/broadcast” are at 20 messages, interpret this as the Broadcast Template inventory with `PAGES > 0`, not a literal `NAME` substring search. Validate both company scopes, decode `MESSAGES`, and report exact exceptions. Follow `references/broadcast-template-live-message-count-verification.md`.

Critical `PAGES` distinction:

- When Rodolfo asks for the template list with pages/message count from this tab, use **Broadcast Template `PAGES`** from `/broadcast/Messenger[].PAGES` / the visible Broadcast Template column.
- Do **not** substitute a Page-tab row count grouped by `BROADCAST_TEMPLATE_NAME` unless explicitly labeled as `Page rows live`.
- Page-tab row counts are for `BROADCAST_TIME`, schedule work, and page-row ETA. Broadcast Template `PAGES` is what Rodolfo expects when pointing at `Accounts → Messenger → Broadcast Template`.
- When reconciling template `PAGES` to `/campaigns/Messenger` rows, group by immutable `BROADCAST_TEMPLATE_ID`, not name alone. In the validated purple-audit case, `Broadcast` + `Campaign` rows reconciled to `PAGES`; attached `Ready`, `On-hold`, and `Blocked` rows did not. Assert the reconciliation per template instead of assuming a fixed status rule.
- When Rodolfo asks for “templates atuais com páginas linkadas” or “verticais que temos nos templates com páginas linkadas”, include only `/broadcast/Messenger` rows where `PAGES > 0`, derive the vertical from the template `NAME` code (`COUNTRY-VERTICAL-LANGUAGE`, e.g. `US-CC-EN`), and summarize by vertical before listing template detail. See `references/template-vertical-inventory-linked-pages-2026-07-07.md`.

Purple-count pitfall:

- `MESSAGES[].ERROR` / `INVALID_FORMAT` and `REJECTED_REASON` totals count **messages**, not pages.
- Purple belongs to the message/template aggregate. The SB Broadcast API does not identify the Page ID that caused a purple result.
- Distinguish a reason-specific subset from the full purple universe. If a page total seems unexpectedly low, aggregate every purple reason family before answering.
- “Active pages linked to templates with purple” can be produced by joining `BROADCAST_TEMPLATE_ID`; “pages that caused purple” requires per-page DTR/Meta corroboration and may remain unprovable from SB alone.
- Operational XLSX exports must include a prominent `Nome do template` column, preferably directly after `Página`, plus segurador, page link, bot user, Facebook Page ID, internal PG/Page ID, status, purple category/reason, and a methodology caveat.

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

