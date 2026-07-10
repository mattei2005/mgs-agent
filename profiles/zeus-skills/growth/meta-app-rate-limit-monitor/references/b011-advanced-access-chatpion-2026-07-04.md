# B011 — Advanced Access + ChatPion connection model (2026-07-04)

## Trigger

Use this reference when configuring or troubleshooting B011-style Meta apps where:

- the app is in a verified Business Manager;
- the app has Advanced Access permissions approved;
- seguradores/pages are connected through ChatPion/DigitalTrChat;
- seguradores are **not** added as app administrators/roles.

## Key lesson

Advanced Access lets non-app-role customers/users grant the app approved permissions, but it does **not** make `/app/roles` a valid inventory of connected seguradores/pages.

For B011, `/app/roles` is expected to show only the app owner/admin side. That is not an outage and must not be used to mark connected seguradores as removed.

## Token scopes for B011 app-health token

Recommended token permissions when generating/saving `BOT B011 Token`:

```text
public_profile
pages_show_list
pages_read_engagement
pages_manage_metadata
pages_messaging
business_management
```

Operational split:

```text
Need                                      Source / permission model
----------------------------------------- ------------------------------------------------
App health, debug_token, X-App-Usage      app_id + app_secret + saved user access token
App roles/admin drift                     /{app_id}/roles, but only for app owners/admins
Connected pages / ChatPion delivery       ChatPion/DigitalTrChat or Page Tokens from connection
Segurador removal from app                Not determined by /roles for B011
Sheet reconciliation for B011            Preserve existing Removidos acumulado; do not auto-X from /roles
```

## Cron implementation note

The Meta app roles watch script must exclude B011 from role-based sheet removal reconciliation:

```python
ROLE_RECONCILIATION_EXCLUDED_APPS = {'B011'}
```

When processing rows with `NO APP = B011`, preserve the existing `Removidos acumulado` value instead of comparing the sheet row against `/app/roles`. Otherwise the cron will falsely mark all B011 seguradores as removed because they are connected through ChatPion, not app roles.

## Sheet GID correction

For this rollout Rodolfo moved/updated the active `Migracao 22/06` tab to:

```text
gid=542936436
```

Validate the live sheet before changing this again. Do not assume the older gid is still current.

## Validation pattern

Safe validation after adding a new app token:

1. Confirm 1Password item exists by field names and value lengths only; never print secrets.
2. Run the monitor constrained to the app first if needed: `MGS_META_APP_ROLE_ITEMS='BOT B011 Token'`.
3. Confirm:
   - app metadata status 200;
   - `/debug_token` valid;
   - X-App-Usage parsed and below threshold;
   - no raw token/app_secret/page token printed.
4. Run the full cron once and verify summary includes all 11 apps and `errors_count=0`.

## Pitfall

Do not “fix” B011 by adding seguradores as app admins just to satisfy the older `/roles` monitor. That changes the operating model and increases account-role surface area. For B011, connected-page monitoring belongs in the ChatPion/DTR or Page Token layer.