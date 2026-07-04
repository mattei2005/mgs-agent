# SB Messenger Purple Approval Diagnostics — 2026-07-02

## When to use

Use this when Rodolfo asks what a purple approval bar means in Smart Bidding Messenger templates, or asks whether Zeus can identify which page/segurador/app caused a purple alert.

## Confirmed finding

The dashboard UI may only show a purple bar and a tooltip summary, but the authenticated backend payload contains enough detail to diagnose the cause.

Relevant endpoints:

```text
GET /broadcast/Messenger?companies[]=digital-trust&companies[]=digital-trust-2&source=Messenger
GET /campaigns/Messenger?companies[]=<publisherId>&source=Messenger
GET /company
```

For each Broadcast Template row, `MESSAGES` is a JSON message array. Each message can include:

```text
APPROVED
REJECTED
INVALID_FORMAT
ERROR
REJECTED_REASON
```

Operational color/status mapping observed:

```text
ERROR > 0 or INVALID_FORMAT > 0  => purple bar / operational error
REJECTED > 0                     => red/rejected
APPROVED > 0                     => approved/green
all zero/missing                 => gray/no-status
```

## Diagnostic workflow

1. Capture live `/broadcast/Messenger` through headed Playwright/Xvfb using the logged-in SB dashboard session.
2. Parse each template's `MESSAGES` JSON.
3. Flag messages where `ERROR > 0` or `INVALID_FORMAT > 0`.
4. Extract `REJECTED_REASON`; despite the name, SB also stores Meta/API error text there for purple `ERROR` cases.
5. Capture all publisher IDs from `/company[].publishers[].publisherId`.
6. Query `/campaigns/Messenger` for all publisher IDs, full MGS scope should be 56 publishers and ~3,237 page rows when Digital trust + Digital trust 2 are selected.
7. Join `Broadcast Template.NAME` to `campaigns/Messenger[].BROADCAST_TEMPLATE_NAME`.
8. Report `PROFILE_NAME`, `LOGIN`, `PAGE_ID`, `FB_PAGE_ID`, `PAGE_NAME`, `STATUS`, `BROADCAST_TIME`, `LEADS_TOTAL`.

## Example confirmed by Rodolfo screenshot

Template:

```text
Openzed - US-CC-EN/EN - AV - g001-d Icaro
```

Live backend result:

```text
Messages: 20
Rejected/red: 3
Error/purple: 17
Approved: 0
Linked page rows: 12
Profile/segurador: Phong Huynh on 12/12 rows
Login: disparosducapesusccen@gmail.com
Page status: 8 Broadcast, 4 On-hold
```

Purple reason:

```text
Any of the pages_read_engagement, pages_manage_metadata, pages_read_user_content,
pages_manage_ads, pages_show_list or pages_messaging permission(s) must be granted
before impersonating a user's page.
```

Interpretation: the app/profile lost page permissions or was removed from the app. This matched Rodolfo's manual B010 finding and Ciro's explanation that purple means the app, segurador, or page broke.

Visible linked pages from the live join included:

```text
PAGE_ID  FB_PAGE_ID        PAGE_NAME           STATUS
19236    1055980650923052  Paloma Kinsworth   Broadcast
19235    943286485544569   Maelis Davenport   Broadcast
19221    1085850704601046  Selina Whitcroft   Broadcast
19214    1003539719515982  Ulyssa Hartcroft   Broadcast
19208    868713562996598   Alice Turner       On-hold
19197    985407817995962   Brenna Hargrove    On-hold
19193    942206922313466   Blair Kensington   Broadcast
13931    928529200351988   Yvonne Redford     Broadcast
13796    913222261876028   Joanna Richards    On-hold
11076    779750141898906   Savannah Jenkins   On-hold
11037    870102562854311   Violet Rivera      Broadcast
8347     813130558552315   Sophia Miller      Broadcast
```

## Other purple reasons observed in same live scan

```text
Application has been deleted
Any of the pages_read_engagement... pages_messaging permission(s) must be granted...
Invalid parameter
Non-JSON response / PHP Error from backend
```

## Reporting guidance

For Rodolfo, answer result-first:

```text
Sim — dá pra descobrir via API. Roxo não é só visual; o backend entrega ERROR/INVALID_FORMAT + REJECTED_REASON, e dá pra cruzar com Page API para segurador e páginas afetadas.
```

Then give a compact table/list with:

```text
Template — erro roxo/reason — segurador/profile — login — linked pages — page statuses
```

Avoid claiming the Broadcast Template `PAGES` field is the same as live Page-tab row count. Label them separately if both are shown.
