# B011 DTR Connection Verification — 2026-07-04

## Context

B011 is a Meta app with Advanced Access used through DigitalTRChat/ChatPion page connections. Rodolfo does **not** add seguradores as app admins. Therefore `/app_id/roles` is the wrong source for B011 segurador/page membership.

## Key correction

The cron bug was caused by sheet parsing: `NO APP = B011` was normalized as `B001`, so the role reconciler compared B011 rows against B001 `/roles` and marked them with `X` in `Removidos acumulado`.

Correct rule:

```text
B011 must remain B011.
B005-2 must remain B005-2.
Do not normalize alpha suffixes away.
```

For B011, role-based reconciliation must clear/prevent role-derived `X` markers. A separate DTR/page-token checker owns connection health.

## Correct verification route

Use the DTR connection token, not the app-health token and not `/roles`:

```text
DigitalTRChat bot login
→ /social_accounts/index
→ switch top-bar segurador/account via .account_switch
→ POST /social_accounts/fb_rx_account_switch id=<data-id>
→ read active Facebook connection token from DTR HTML only inside script
→ Meta /me/accounts?fields=id,name,access_token
→ for each page token: /{page_id}/subscribed_apps?fields=id,name
→ match B011 app_id
```

Never print or persist DTR/Facebook access tokens. Report only sanitized fields:

```text
bot user, segurador, DTR page count, Graph page count, connected page count,
page_id, page_name, matched app name, error class.
```

## OAuth URL interpretation

A URL like:

```text
https://www.facebook.com/dialog/oauth/business/cancel/?app_id=26641125658889443&...
```

is useful as evidence of the connection flow, app ID, redirect URI, and requested scopes, but it is **not** a data source. It contains no `code` or token after cancellation.

Useful fields observed:

```text
app_id        26641125658889443  # B011
redirect_uri  https://digitaltrchat.com/social_accounts/manual_renew_account
scopes        read_insights, business_management, pages_messaging,
              pages_utility_messaging, pages_manage_engagement,
              pages_read_engagement, pages_manage_metadata,
              pages_read_user_content, pages_show_list
```

## Validated findings from corrected run

Using Rodolfo's actual B011 list, not all stale sheet rows:

```text
Seguradores checked       19
Connected seguradores     16
Connected pages           173
B011 sheet rows X after  0
```

Important examples:

```text
Lorena Santos Cardoso / disparoslyzmogb
- DTR visible pages: 2
- Graph pages: 2
- B011 connected: 2/2
- Pages: Paula González, Maura Thornwick

Caue Pereira / disparoseggbev
- DTR/Graph pages: 10
- B011 connected: 7/10
- Not connected: Elegant rfe1, Lithe fyp1, Glorious cfh8

Kaio Sousa / disparosconecta
- DTR visible pages: 16
- Graph error: OAuth #190 subcode 459 checkpoint
- Action: Facebook login/checkpoint/reconnection needed

William Nogueira / disparosnewsoun
- Graph error: OAuth #190 subcode 460 session invalidated
- Action: reconnect in DTR

Yudi Anggara / disparoscliquet
- Account present but Graph returned 0 pages
```

## Operational rule

B011 uses DTR/page-token validation instead of `/roles`, but it must follow the same operating plan as B001–B010:

```text
Every 2 minutes
→ read sheet rows assigned to B011
→ validate each segurador/account against the current B011 app connection via DTR/Meta
→ disconnected/not linked = write X in Removidos acumulado
→ linked/current = clear X
→ status changed disconnected/connected = alert in #b011-app-rate-limit
```

When Rodolfo asks why B011 has `X` or asks for B011 connected seguradores, do **not** answer from `/roles`. Use DTR/page-token validation. The source is different; the X/alert/state contract is the same as B001–B010.
