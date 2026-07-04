# SmartBidding API observations — Messenger template inventory (2026-06-29)

## Auth model

The SB dashboard uses an internal API under:

```text
https://api.jbfdigital.com.br
```

This is not a public/open API contract. It requires the authenticated dashboard session/bearer token from the SPA. A Playwright request context using only cookies/storage state returned `401 Unauthorized`; the working path was observing/executing requests from the logged-in dashboard page where the SPA had an Authorization bearer token.

Never print the bearer token.

## Company scope

For Zeus' current SB user, `/company` returned only two companies:

```text
digital-trust    -> Digital trust
digital-trust-2  -> Digital trust 2
```

No visible company matched `jbf`, `jbfdigital`, `smartbidding`, `smart-bidding`, `smartbiddingdigital`, `legacy`, `mgs`, or `sb`.

Testing invalid `companies[]` values against `/broadcast/Messenger` still returned the same 94 scoped rows. Treat `companies[]` on that endpoint as not a reliable discovery mechanism for other companies; the backend may ignore invalid filters or apply the current user's allowed company scope.

## Messenger Broadcast Template endpoint

Observed endpoint:

```text
GET /broadcast/Messenger?companies[]=digital-trust&companies[]=digital-trust-2&source=Messenger
```

Response rows include backend fields not always visible in every UI viewport/session:

```text
ID
NAME
MESSAGES
COMPANY
PUBLISHER_ID
LANGUAGE
UTM_CONTENT_MASK
PAGES
LEADS
```

`MESSAGES`, `LEADS`, and `PAGES` are backend-returned fields, not agent-calculated fields. UI may show only up to `MESSAGES` depending on width/state, but the API can still return `LEADS` and `PAGES`.

## Security pitfall

The `/company` response can contain nested publisher/site operational data and credential-like fields (e.g. VPS/panel/WordPress structures). Do not dump raw `/company` JSON into Discord or logs. Summarize only non-sensitive fields such as company IDs/names/counts.

## Extraction guidance

For table inventory:

1. Use headed/Xvfb SB session.
2. Trigger the UI route so the SPA obtains/uses the bearer token.
3. Prefer capturing table/API responses inside the page session.
4. Redact tokens and avoid printing raw payloads if endpoint may include credentials.
5. Validate row counts with UI/Sheet readback before reporting.
