# Meta App Roles — replacement app canonicalization

Use this when a monitored Meta app is deleted/replaced but the operational lane/channel continues under a replacement suffix such as `B005-2`.

## Durable pattern

When Rodolfo confirms the original app was deleted, treat the replacement code as the canonical app key everywhere. Do not keep the deleted app as an alias unless explicitly requested.

For the Meta app roles monitor (`/root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh`):

1. Remove the deleted app key from routing/owner maps.
   - Example: remove `B005` from `APP_ALERT_CHANNELS` and `APP_OWNER_PROFILES`.
   - Keep only `B005-2` mapped to the existing operational channel.
2. Add a deprecated-item filter for auto-discovery if the old 1Password item may still exist during cleanup.
   - Example: `DEPRECATED_APP_ITEMS = {'BOT B005 Token'}`.
   - If `BOT B005-2 Token` is present, exclude `BOT B005 Token` from discovered items.
3. Update comments to say the active state/alerts/channel routing use the 1Password item code and the replacement key is canonical.
4. Add a one-time state migration guard:
   - if both old and replacement keys exist in `state['apps']`, drop the old deleted key.
5. Validate without leaking secrets:
   - `bash -n` on the script.
   - Dry-run of the monitor.
   - Normal run if safe/idempotent.
   - Confirm `_last_discovered_items` includes the replacement item and excludes the deleted item.
   - Confirm state has replacement key and no deleted key.
6. Update infra inventory/audit if script/state/inventory changed, and post/report according to REPORT-INFRA rules.

## Example validated outcome

After standardizing deleted `B005` to active `B005-2`:

- discovered items: `B001, B002, B003, B004, B005-2, B006, B007, B008, B009, B010`
- state apps: `B005=false`, `B005-2=true`
- `errors_count=0`

## Pitfall

Do not answer future operational summaries as if `B005` still exists just because the physical Discord channel is the same. The business/app identity is `B005-2`; the channel is only the route used for the replacement lane.
