# B011 / B011 canonicalization + all-channel live alert — 2026-07-04

## Trigger

Rodolfo asked for a real alert in all 11 app-rate-limit channels after cache cleanup and sheet reconciliation fixes. The live run sent 11 alerts, but auto-discovery surfaced the B011 credential as `BOT B011 Token`, creating risk that the alert/state would be labeled or routed as `B011` instead of operational app `B011`.

## Durable rule

Operational app/channel scope is 11 channels:

```text
B001
B011
B002
B003
B004
B005-2
B006
B007
B008
B009
B010
```

If 1Password discovery returns `BOT B011 Token`, treat it as the legacy credential name for B011, not as a twelfth operational app:

```python
def canonical_app_key(item_code):
    key = str(item_code or '').strip()
    if key == 'B011':
        return 'B011'
    return key
```

Apply this before:

- state reads/writes;
- channel routing;
- alert title/rendering;
- Google Sheet reconciliation;
- final report counts.

## Cleanup rule

If a previous run created `state.apps.B011`, do not leave it in runtime state. Backup the state file, remove only the stale `B011` app key, and rerun B011 live validation. Do not wipe role baselines for B001–B010/B005-2/B011.

Expected validation shape:

```text
bash -n meta-app-roles-watch.sh                       OK
MGS_META_APP_ROLES_FORCE_LIVE_ALERT=1 \
MGS_META_APP_ROLE_ITEMS='BOT B011 Token' \
bash meta-app-roles-watch.sh                          OK

_last_run_summary.alerts_sent                         1
_last_run_summary.errors_count                        0
_last_run_summary.force_snapshot_effective            false
state.apps has B011                                   false
state.apps.B011.current_count                        present
state.apps.B011.cumulative_removed                   0 unless real active removal
all operational cumulative_removed counts              coherent
```

## User-facing reporting

When reporting back to Rodolfo after “manda alerta real em todos os 11 canais”, use operational names only. Say `B011`, not `B011`, except if explaining the internal credential-name correction.

Do not say the job is done until:

1. alerts were posted via `MGS_META_APP_ROLES_FORCE_LIVE_ALERT=1` (not snapshot);
2. `errors_count=0`;
3. B011 is routed to `#b011-app-rate-limit`;
4. stale `B011` state is gone;
5. cumulative removed counts are not polluted by stale cache;
6. REPORT-INFRA was posted if script/skill/state/inventory changed.

## Pitfall

Auto-discovery count can look correct (`alerts_sent=11`) while one operational label is wrong. Always verify the app keys in state and the routing map, not only the alert count.
