# SmartBidding Messenger Backend Findings — 2026-06-29

Session-specific backend observations useful for future SB dashboard automation. Do not treat these as a public API contract; validate runtime every time.

## Auth behavior

Direct HTTP without the SPA's bearer token returns 401, even if cookies/storage state exist in Playwright request context:

```text
{"message":"Unauthorized","statusCode":401}
```

The bearer token is attached by the browser SPA to API requests. For investigation, capture authenticated browser requests/responses in headed Playwright rather than printing tokens. Never expose the Authorization header.

## Scoped companies

`GET https://api.jbfdigital.com.br/company` under Zeus's SB account returned only:

```text
digital-trust    / Digital trust
digital-trust-2  / Digital trust 2
```

No visible company named `jbf`, `jbfdigital`, `smartbidding`, `smartbiddingdigital`, `legacy`, or `mgs` in this account scope.

Testing `/broadcast/Messenger?companies[]=<candidate>&source=Messenger` with invalid company names returned the same visible scoped data rather than proving those companies exist. Do not infer company existence from that endpoint alone.

## Broadcast Messenger endpoint

Observed endpoint:

```text
https://api.jbfdigital.com.br/broadcast/Messenger?companies[]=digital-trust&companies[]=digital-trust-2&source=Messenger
```

Useful top-level fields per template:

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

`MESSAGES` is a JSON-encoded array, not just a count. Each message can include:

```text
MESSAGE_ID
TEXT
DESCRIPTION
IMAGE
CTA_1
LINK_1
CTA_2
LINK_2
TEXT_2
APPROVAL
APPROVED
INVALID_FORMAT
REJECTED
```

Approval classification:

```text
REJECTED > 0        → rejected / red bar
INVALID_FORMAT > 0  → invalid format
APPROVED > 0        → approved / green bar
```

The dashboard may show `MESSAGES` as a count, but the backend field contains the full message list.

## UI/API mismatch

Some users/screens may not visibly show `LEADS` or `PAGES` columns, but the backend response can include them. When asked where those values came from, answer that they were read from the authenticated SB backend response and/or rendered DOM, not calculated locally.

## Safety

The `/company` response can contain sensitive site/server/panel fields. If inspecting it, summarize only company IDs/names and operational non-secret counts. Never paste raw company JSON into chat or logs.
