# Clean-page selection by latest DTR Sent — 2026-07-07

Session context: Rodolfo needed one page per Utility Template vertical to use as clean canary approval page, preferring Newsoun where possible. Zeus combined live SB Broadcast Template/Page data with DigitalTRChat latest-message checks.

## Goal

Return one page per vertical that is safe for canary template approval:

- the vertical has a Broadcast Template with `PAGES > 0`;
- the selected SB Page row is operational (`STATUS` normally `Broadcast`/`Campaign` and no active `RESTRICTED_UNTIL`);
- the page's latest useful DTR message/report is `Sent`;
- prefer the same site requested by Rodolfo, e.g. Newsoun.

## Correct evidence standard

Do **not** infer a page is clean from SB alone. SB proves routing/status, but DTR proves the last send result.

Validation must check DigitalTRChat:

1. Log into the bot user from the SB row's `USER_LOGIN`.
2. Iterate all top-bar seguradores/accounts for that DTR user.
3. Find the matching DTR `search_page_id` / PG.
4. Fetch latest Completed campaign/report for that page.
5. Classify the report via sent-status data.
6. Accept only `status == SENT` as clean.

If there is no Completed/latest campaign, report as no clean page for that candidate. Example from session: `disparosfinanceadxar@gmail.com` / `Leticia Anzaldo pg_5439` and `Teresa Camacho pg_19337` both had `NO_COMPLETED`, so neither is proven clean even if the page is more recent.

## Selection heuristic

1. Build linked vertical inventory from live `/broadcast/Messenger`, using Broadcast Template `PAGES > 0`.
2. Join SB Messenger Page rows by `BROADCAST_TEMPLATE_NAME`.
3. Filter page rows to operational status and no active restriction.
4. Prefer candidate templates/pages whose template/site name matches Rodolfo's requested site.
5. For each vertical, test candidates in order until DTR latest status is `SENT`.
6. Return page name, `FB_PAGE_ID`, `PAGE_ID/PG`, source template, DTR campaign id/date when available.

## Reporting shape

Use a compact table:

```text
Vertical     Site usado     Página teste           FB_PAGE_ID          PG     Último envio
US-CC-EN     Newsoun        Iona Brookfield         952051961334613    19225  Sent
...
```

For verticals without a clean DTR-Sent candidate, state that explicitly and why (`no candidate`, `NO_COMPLETED`, `DTR credential missing`, etc.). Do not label `NO_COMPLETED` as clean.

## Pitfalls

- DTR account switcher can show duplicate entries with the same `data-id`; dedupe by `id|name` before treating them as separate seguradores.
- A page being newer/recent is not equivalent to having a latest `Sent` report.
- Prefer Newsoun when requested, but only if the Newsoun candidate passes the DTR `Sent` check.
- Keep SB source and DTR source separate in the final language: SB = template/page routing; DTR = send-result truth.
