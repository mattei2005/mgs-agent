# B011 cache clean + alert routing correction — 2026-07-04

## Trigger

Rodolfo found a B011 validation alert posted in the B007 channel (`1520510823426949313`) and corrected the operating model:

- B011's correct channel is `1522830283240505385`.
- B011 must be part of the same 11-channel operating contract as B001–B010.
- The **route for discovering users is different**: DTR/ChatPion + Meta `debug_token`, not Meta `/app/roles`.
- Historical/temporary labels such as `B001A` must be removed from active scripts, state files, docs, and alert titles; current canonical label is only `B011`.

## Durable rule

B011 is not a Meta `/roles` app for manager-facing user reports. It is a DTR/ChatPion connection app.

```text
B001-B010/B005-2 users  -> Meta /{app_id}/roles + sheet reconciliation
B011 users              -> DTR/ChatPion account switch + Meta /debug_token + sheet reconciliation
```

The operating contract is the same:

```text
read runtime source -> compare/reconcile sheet -> write/clear X -> alert channel on change/problem
```

Only the runtime source differs.

## Hard pitfall

Never send a B011 validation alert through `meta-app-roles-watch.sh` / `MGS_META_APP_ROLES_FORCE_LIVE_ALERT`. That path renders the app owner/admin from `/roles` (example: `Thiago Oliveira`) as if it were the B011 segurador list, which is wrong.

For B011 manual validation, always use:

```bash
MGS_B011_DTR_FORCE_LIVE_ALERT=1 /root/.hermes/profiles/zeus/scripts/b011-dtr-link-watch.sh
```

Expected channel:

```text
B011 -> 1522830283240505385
B007 -> 1520510823426949313
```

## Required script behavior

`meta-app-roles-watch.sh`:

- Must exclude `BOT B011 Token` from app-role item discovery, even if present in 1Password.
- Must not keep or render `B011`/`B001A` state keys.
- Must not mark B011 rows by `/roles` absence.

`b011-dtr-link-watch.sh`:

- Reads `BOT B011 Token` config.
- Reads sheet rows where `NO APP = B011` and active source filter applies.
- Logs into DTR/ChatPion using existing 1Password items.
- Switches to each segurador.
- Validates account link by `debug_token.data.app_id == app_id` and `is_valid == true`.
- Uses page inventory only as secondary evidence; `0 pages` is not disconnected.
- Syncs X in the sheet and alerts `1522830283240505385` on changes/problems or explicit force-live validation.

## Safe cache clean procedure

When B011 cache/state is suspected polluted:

1. Pause both Hermes cron jobs:
   - `meta-app-roles-watch` (`0cc7ed1e587e`)
   - `b011-dtr-link-watch` (`498fb0d95e10`)
2. Backup and delete/rebuild `/root/mgs-agent/data/b011-dtr-link-monitor-state.json`.
3. Backup `/root/mgs-agent/data/meta-app-role-monitor-state.json` and remove B011/B001A keys only.
4. Run `meta-app-roles-watch.sh` once and verify discovered items exclude `BOT B011 Token`.
5. Run B011 force-live validation with `MGS_B011_DTR_FORCE_LIVE_ALERT=1`.
6. Verify alert channel is `1522830283240505385` and content is DTR/ChatPion, not `Meta APP - B011` `/roles` owner/admin content.
7. Resume both cron jobs.
8. Update infra inventory/audit/report if scripts, docs, skills, cron, or data state were modified.

## Validation values from the correction run

```text
meta-app-roles items: B001-B010/B005-2 only
meta errors:          0
B011 channel:         1522830283240505385
B011 targets:         19
B011 linked:          18
B011 pending:         1
B011 alerts_sent:     1
```

The one pending user at validation time was `Kaio Sousa` / `disparosconecta@gmail.com` because `debug_token` did not validate against B011.
