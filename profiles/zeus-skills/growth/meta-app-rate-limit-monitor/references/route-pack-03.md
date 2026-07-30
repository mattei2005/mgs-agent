## Advanced-Access App Without Seguradores as App Admins

Rodolfo clarified for B012 that the app may have Advanced Access permissions in a verified Business Manager and the seguradores will not necessarily be added as app administrators. This is a valid Meta operating model for ChatPion/DigitalTrChat-style integrations: Advanced Access allows non-app-role customers/users to grant the app permissions after App Review, but it does **not** remove page-level access requirements for Graph API reads.

Operational implication:

```text
Goal                                      Required access model
----------------------------------------- ------------------------------------------------
Monitor app health / X-App-Usage          App ID + app_secret, plus optional admin user token.
Read /{app_id}/roles                      App access token; only shows app roles/admins, not connected pages.
List pages via /me/accounts               User/System User must have page/business tasks + pages_show_list.
Read Page metadata / subscribed apps      Page access token + pages_manage_metadata + pages_show_list.
Messenger send/webhook/ChatPion operation Advanced pages_messaging + pages_manage_metadata; Page token from page connection.
Dashboard/lead/subscriber truth           ChatPion/DigitalTrChat source, not app roles.
```

For B012-style apps, do not expect the app-role monitor to list seguradores via `/roles`. B012 follows the DTR/ChatPion page-token route: reconcile every Sheet row with `NO APP = B012`, including rows already marked `X`, and alert when a valid connection disappears or recovers. Production runs hourly at `:24` from 08:24–23:24 ET, staggered 20 minutes after the Meta roles monitor; keep the non-blocking lock because a full 28-target run takes several minutes. A single app token cannot enumerate all customer pages solely because the app has Advanced Access.

Validated DTR verification route for B012-style connected profiles:

```text
1. Use every sheet row where `NO APP = B012` by default; `Migrado` is informational unless Rodolfo explicitly asks for an active-migrated-only audit.
2. Map each bot user to its `Digitaltrchat - ...` 1Password item.
3. Login to `https://digitaltrchat.com/social_accounts/index`.
4. Switch top-bar segurador/account via `.account_switch` / `POST /social_accounts/fb_rx_account_switch`.
5. Extract the active Facebook user token only inside the script from DTR HTML `graph.facebook.com/me/picture?access_token=...`; never print or store the token.
6. First validate account-level linkage with Meta `/debug_token` using the B012 app token; if `debug_token.data.app_id == B012 app_id` and `is_valid=true`, the segurador is linked to B012 even if `/me/accounts` returns zero pages.
7. Then call Meta `/me/accounts?fields=id,name,access_token` with that active connection token only to validate page-level inventory.
8. For each returned page token, call `/{page_id}/subscribed_apps?fields=id,name` and match by B012 `app_id`.
9. Report two statuses separately: `Account link` and `Page inventory`. Do not mark a segurador unlinked just because it has 0 pages.
```

Interpretation rules:

```text
DTR page count > Graph page count       The DTR UI has page rows that the current Meta token does not return; report as discrepancy, not connected.
Graph OAuth #190 subcode 459/460        Facebook checkpoint/session invalidated; reconnection needed in DTR.
`Application has been deleted`          Old app connection/token; reconnect the segurador/page to the current B012 app.
`subscribed_apps` empty for a page       That page is not connected to B012 even if the segurador account itself is connected.
```

Validated B012 route when Rodolfo asks “quais seguradores estão conectados nesse app”:

```text
DigitalTRChat bot login
→ `.account_switch` segurador
→ POST `/social_accounts/fb_rx_account_switch`
→ token ativo da conexão DTR no contexto do segurador
→ Meta `/me/accounts`
→ Page Access Token
→ `/{page_id}/subscribed_apps`
→ match com B012 `app_id`
```

- `references/b011-dtr-connection-verification-2026-07-04.md` and `references/b011-dtr-link-monitor-2026-07-04.md` preserve the historical B011 validation model inherited by B012.
- `references/b012-dtr-cutover-2026-07-30.md` is the active B011→B012 cutover record: credential duplicate-title guard, current item pin, Service Account Sheet route, all-row monitoring, cron/state artifacts and live validation.
- `references/b011-cache-clean-and-alert-routing-2026-07-04.md` remains historical evidence for why DTR/ChatPion apps must never render through the Meta `/roles` path.

Recommended token scopes for generating the B012 app-health token:

```text
public_profile
pages_show_list
pages_read_engagement
pages_manage_metadata
business_management   # only if using BM/System User/asset diagnostics
```

Add `pages_messaging` only if the token will actively test Messenger send/webhook behavior; not needed for pure app health and role/rate-limit monitoring. Do not request `pages_manage_posts` or `ads_management` for this monitor unless a separate workflow needs them.

## Segurador Page Token Monitoring

When Rodolfo provides a token for a specific segurador profile, do not treat it like the B001–B010 app token. Use it to inspect the pages inside that segurador via `/me/accounts` and page access tokens.

Expected capability with the right scopes:

```text
Capability                                Source / endpoint
----------------------------------------- ------------------------------------------------
List pages inside segurador               /me/accounts
Page status/basic metadata                /{page_id}?fields=id,name,is_published,...
Page tasks/permissions                    /me/accounts fields=tasks
Messenger conversations                   /{page_id}/conversations
Messages/replies/participants             /{conversation_id}/messages
Template/button/CTA content               message attachments/generic_template where returned
Subscribed app/bot presence               /{page_id}/subscribed_apps
Basic Messenger insights                  /{page_id}/insights
Native Meta Lead Forms                    /{page_id}/leadgen_forms + leads_retrieval
```

Important distinction from Rodolfo: most MGS “leads” in this flow are **ChatPion/DigitalTrChat leads/subscribers**, not native Meta Lead Forms. Meta Graph can show page conversations, messages, replies, CTAs and page health symptoms; definitive subscriber/lead count, tags, custom fields, sequence/campaign membership and bot delivery status should come from ChatPion/DigitalTrChat.

For native Lead Forms, add/verify:

```text
pages_manage_ads
leads_retrieval
```

A successful `/leadgen_forms` response with `0` forms means the page has no native Lead Forms; it is not proof of no ChatPion leads.

See `references/segurador-page-token-monitoring.md` for the Dân Kbang/Patricia Smith probe pattern and source split.

