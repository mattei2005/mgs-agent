## Alert Format

Rodolfo approved the compact monospaced code-block format. Do **not** use embeds, Markdown tables, page hyperlinks, Facebook URLs, legend text, or footer timestamps for the normal report: Discord embeds/Markdown tables rendered cramped/ugly and Facebook links generated unwanted preview cards.

Approved first-pass channel format:

````text
<@344196393512075265> ALERTA — Relatório Segurador/Página

Domain: zytiva
User: disparoszytiva@gmail.com
Segurador: Dân Kbang
Recorte: 1 página neste teste

```
Página             PG ID            Ativa  Leads  Enviando
-----------------  ---------------  -----  -----  --------
Patricia Smith     796622570197092  sim    495    não
```
````

Format rules:

```text
- Include Domain, User, Segurador and Recorte above the table.
- Do not include Company.
- Do not include legend/footer in production alerts.
- Do not include page links; page names stay plain text.
- Use exactly one monospaced code block for the table.
- Use `flags: SUPPRESS_EMBEDS` when posting through Discord API as a safety guard.
```

Column semantics for Rodolfo’s requested table:

```text
pagina      = nome da página, plain text by default
pg id       = Facebook Page ID
ativa       = sim/não based on Meta access + publication status
leads       = quantity of leads in the period from SB/ChatPion
enviando    = sim/não based on SB/ChatPion message activity, not app rate-limit
```

Guardrail: do not alert on healthy pages. If `Ativa = sim`, `Enviando = sim`, leads are within expected baseline, and segurador/page access checks are OK, stay silent in Discord and only persist state/logs. Alert only when a page/segurador breaks one of the anomaly rules below.

## Patricia Smith Probe — Known Example

With `Segurador Dân Kbang (B005) Token`, page `Patricia Smith` / `796622570197092` returned:

```text
Meta:
page_basic OK
is_published true
category Business Consultant
followers/fan_count 423
conversations OK
messages OK
subscribed_apps OK
leadgen_forms OK but 0 forms

SB Messenger report:
PAGE_ID 796622570197092
PROFILE_NAME Dân Kbang
PAGE_NAME Patricia Smith
STATUS Broadcast
LEADS_TOTAL 1396
LEADS 495
SENDS 0
DELIVEREDS 0
BD_SENDS 0
BD_DELIVEREDS 0
DRIP_DELIVEREDS 0
```

Rodolfo clarified that 0 sends/delivered in this moment was expected because Utility templates were being reconfigured after Meta blocked legacy broadcast. Treat planned reconfiguration as maintenance/exclusion, not anomaly.

## Implementation Priorities

First production monitor should start with **Step 1 inventory reconciliation** before any page-health/error classification:

```text
0. Read migration/control sheet first: active rows only (`NO APP` present, no `X`).
1. Detect duplicate segurador/accounts in DigitalTRChat before reading pages; report duplicates and skip automatic choice.
2. Treat sheet `X` as confirmed/out-of-scope before opening dashboard details.
3. Treat active segurador appearing exactly once with zero pages as `NO_PAGES`: report and ignore, not an operational error.
4. Treat pages with no sends/leads as non-error unless a baseline/expected sending pattern proves a collapse.
```

Then the first production monitor should cover only:

```text
1. Segurador token still valid.
2. Known pages still visible in /me/accounts.
3. Known pages still published and accessible.
4. Expected bot/app still subscribed.
5. SB report still sees the page.
6. Leads/DELIVEREDS do not collapse against baseline unless maintenance is active.
```

Avoid overbuilding the first version. The valuable alert is: **which page/segurador stopped working and whether Meta or SB/ChatPion is the likely side of the problem.**

## References

- `references/restricted-pages-discord-domino-flow-2026-07-09.md` — Correct gestores-facing restricted-pages channel flow: DTR sweep applies `Restricted Until`, posts only new Broadcast #2022 deltas with `Sites`, suppresses already-known pages, and ignores On-hold pages.
- `references/digitaltrchat-live-audit-all-seguradores-latest-report-2026-07-02.md` — Rodolfo's methodology corrections for bot audits: iterate every top-selector segurador/account per user, classify only from the latest completed/sent report per page, filter out SB `On-hold`/`Blocked`, and handle #10/#551/#100/permission/app-deleted categories.
- `references/digitaltrchat-purple-template-diagnosis-2026-07-02.md` — Rodolfo's July 2026 correction for purple template bars: diagnose row-level DigitalTRChat `Sent response`, use Smart Bidding `Restricted Until` for temporary #2022 page restrictions, use `Status = Blocked` for broken/permanent cases, and do not use roxo alone to decide copy/template changes.
- `references/discord-format-and-sb-api-session-2026-06-30.md` — Rodolfo-approved Discord format for segurador/page reports, healthy-page guardrails, and SB Messenger API session/auth/date validation notes.

## Segurador Token Collection via AdsPower + Meta Tools

Use this workflow when collecting user tokens for seguradores opened through AdsPower profiles/proxies.

URLs:

```text
Graph API Explorer: https://developers.facebook.com/tools/explorer/
Access Token Debugger: https://developers.facebook.com/tools/debug/accesstoken/
```

After opening the segurador's AdsPower instance/profile:

```text
1. Open https://developers.facebook.com/tools/explorer/
2. In Meta App, select the correct Bxxx app for that segurador.
3. Keep User or Page = User Token.
4. Add exactly these 18 permissions:
   - email
   - read_insights
   - pages_show_list
   - business_management
   - pages_messaging
   - instagram_basic
   - instagram_manage_comments
   - instagram_manage_insights
   - instagram_content_publish
   - leads_retrieval
   - instagram_manage_messages
   - pages_read_engagement
   - pages_manage_metadata
   - pages_read_user_content
   - pages_manage_ads
   - pages_manage_posts
   - pages_manage_engagement
   - pages_utility_messaging
5. Click Generate Access Token.
6. Copy the generated token locally only; never paste it into Discord/chat/logs.
7. Open a new tab: https://developers.facebook.com/tools/debug/accesstoken/
8. Paste the token into "Enter an access token to debug" and click Debug.
9. Scroll to the bottom and click the debug/extend action.
10. Copy the new/extended token.
11. Validate the extended token with:
    - /me
    - /debug_token
    - /me/accounts
12. Save only the extended token to 1Password using the segurador item pattern.
```

Operational guardrails:

```text
- Never print access_token, page token, app secret, Auth0 token, cookie, or bearer token.
- Confirm the selected Meta App matches the segurador's NO APP/Bxxx before generating.
- If Meta asks checkpoint/2FA/captcha, stop automation and request human intervention.
- User Token is the intended mode; do not switch to Page Token for this collector.
- Token is considered usable only after /me, /debug_token, and /me/accounts pass.
```

## Common Pitfalls

1. Do not confuse Meta Lead Forms with ChatPion/SB Messenger leads.
2. Do not involve B001–B010 app rate-limit in this monitor.
3. Do not alert on 0 sends/delivered when Rodolfo marked Utility/template maintenance.
4. Do not print page access tokens or user tokens.
5. Do not treat a single day of low leads as page restriction without checking Meta health and recent baseline.
6. Do not use raw page name only; always key by `page_id`.
7. Do not post placeholder/example Domain/User values; pull real values from SB rows.
8. Do not post an operational report from a zero-row SB response without validating date/auth first.
