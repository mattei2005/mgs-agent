# Messenger Page Health Monitoring Blueprint — B001–B010 / Segurador Tokens

Session-derived operational pattern for monitoring whether a Messenger page is still usable, still sending, and still producing ChatPion/SB leads.

## Source layers

```text
Layer                  Source / token                         Best for
---------------------  -------------------------------------  ---------------------------------------------
Meta App B001–B010     app_id|app_secret + app roles          app health, rate limit, app admins/seguradores
Segurador profile      user token for the segurador profile    pages inside profile, page access, conversations
SB Messenger Report    /reports/messenger / internal API       sends, delivered, leads, sessions, revenue by page
ChatPion/DigitalTrChat bot backend                            subscriber/lead object, tags, custom fields, flows
```

Do not treat Meta Lead Forms as the MGS Messenger lead source unless Rodolfo says so. In this operation, “lead” usually means a Messenger/ChatPion subscriber/lead, not a Facebook Lead Form submission.

## Segurador token capabilities validated

With item pattern like `Segurador Dân Kbang (B005) Token`, the token can validate:

```text
/me                                             profile identity
/me/accounts?fields=id,name,category,tasks...  pages in the segurador profile
/{page_id}?fields=...                          page published/basic state
/{page_id}/subscribed_apps                     bot/app subscription on page
/{page_id}/conversations                       Messenger conversations
/{conversation_id}/messages                    messages, participants, templates/CTAs
/{page_id}/insights                            basic Messenger/page metrics
/{page_id}/posts                               page posts
/{page_id}/leadgen_forms                       native Lead Forms only; not ChatPion leads
```

Useful page fields:

```text
id, name, category, fan_count, followers_count, verification_status, is_published, link
```

Useful account fields:

```text
id, name, category, tasks, access_token
```

Never print user access tokens, page access tokens, app secrets, bearer tokens, cookies, or Auth0/session data.

## Permissions

Current broad permission set that worked for page/conversation/lead-form probes:

```text
pages_show_list
business_management
pages_messaging
pages_read_engagement
pages_manage_metadata
pages_read_user_content
pages_manage_posts
pages_manage_engagement
pages_utility_messaging
pages_manage_ads
leads_retrieval
read_insights
public_profile
```

Instagram scopes are useful only for IG-connected checks; they are not central for Messenger page delivery.

`pages_manage_ads` + `leads_retrieval` unlock native Lead Form endpoints, but native lead forms may still return `0 forms`. That does not mean Messenger/ChatPion leads are zero.

## SB Messenger Pages report

Dashboard route:

```text
https://app.smartbiddingdigital.com/reports/messenger
```

Internal authenticated endpoint observed:

```text
POST https://api.jbfdigital.com.br/report/messenger
```

The route may load as SPA with raw HTTP 404 but render correctly. Use headed/Xvfb Smart Bidding access; do not use headless as final path.

Filter by `PAGE_ID` or `PAGE_NAME`. Example validated for Patricia Smith:

```text
PAGE_ID       796622570197092
PAGE_NAME     Patricia Smith
PROFILE_NAME  Dân Kbang
DOMAIN        zytiva
STATUS        Broadcast
LEADS_TOTAL   1396
LEADS         495
SENDS         0
DELIVEREDS    0
BD_SENDS      0
BD_DELIVEREDS 0
DRIP_DELIVEREDS 0
```

Important fields to monitor:

```text
PAGE_ID, PAGE_NAME, PROFILE_NAME, USER_LOGIN, DOMAIN, STATUS, UTM_CAMPAIGN,
LEADS_TOTAL, LEADS, SUBSCRIBED, UNSUBSCRIBERS,
SENDS, DELIVEREDS, BD_SENDS, BD_DELIVEREDS, DRIP_DELIVEREDS,
%DELIVERED, SESSIONS, CTR, REVENUE, BD_REVENUE, DRIP_REVENUE
```

## Alert logic recommendation

Avoid alerting on `0 sends` alone when Rodolfo is intentionally reconfiguring Utility templates/broadcast. Use maintenance flags or expected-active state.

```text
Severity   Condition
---------  --------------------------------------------------------------------------------
CRITICAL   page disappears from /me/accounts or page basic query fails
CRITICAL   is_published false / unpublished
CRITICAL   subscribed_apps missing/empty when page should have bot installed
CRITICAL   SB/ChatPion reports sends > 0 but delivered = 0 or % delivered collapses
CRITICAL   page had active baseline and drops to 0 delivered without maintenance flag
RISK       Meta conversations OK but SB sends/delivery missing for X intervals while active
RISK       app X-App-Usage >=85% and page delivery is degraded
ATTENTION  leads/subscribers stop growing vs baseline on expected-active page
INFO       new page appears or new app user appears
```

Decision matrix:

```text
Meta page OK + SB delivery bad        => ChatPion/SB/template/disparo issue
Meta page bad + SB delivery bad       => page/profile/token/access issue
App rate limit high + delivery bad    => app/rate-limit issue
Everything OK but leads/revenue down  => funnel/traffic/offer issue
```

## Suggested cadences

```text
Monitor                         Frequency
-------------------------------  ----------------
App roles/rate limit             2 min (active)
Meta page health                 5–10 min
SB delivery/leads                15 min or hourly
Baseline/revenue drift           daily/intraday
```

## Report format for page alerts

```text
CRÍTICO — Messenger Page Delivery

App: B005
Segurador: Dân Kbang
Página: Patricia Smith
Page ID: 796622570197092
Perfil admin do app: Wana Hsh

Meta:
Página publicada: Sim
Bot inscrito: Sim
Conversas acessíveis: Sim

SB:
Status: Broadcast
Leads total: 1396
Sends hoje: 1200
Delivered hoje: 0
% Delivered: 0%
Baseline delivered 7d: 98.7%

Diagnóstico provável:
SB/ChatPion tentou disparar, mas a página não está entregando.

Ação:
Verificar Utility template, status no ChatPion/DigitalTrChat e restrição de messaging.
```
