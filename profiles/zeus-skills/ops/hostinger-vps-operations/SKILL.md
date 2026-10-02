---
name: hostinger-vps-operations
description: "Use when querying MGS Hostinger VPS API or MCP."
version: 1.0.0
author: Zeus - MGS Digital Corp
license: MIT
metadata:
  hermes:
    tags: [hostinger, vps, mcp, metrics, backups, security]
    related_skills: [hermes-agent-operations, vps-maintenance-and-backup-governance]
---

# Hostinger VPS — Zeus

## When to Use

Use for provider-side VPS metrics, state, backup/snapshot inventory, action history and secret-safe Hostinger MCP maintenance. Use Linux/SSH for internal application and OS administration.

## Sources and scope

- Authorized integration: thread `1555572634228490283`, requests `1555597320769372342` and credential bootstrap `1555598627550924800`.
- Target: `srv1767265.hstgr.cloud`, Hostinger VM ID `1767265`.
- Canonical non-secret policy and exact vault references: `/root/mgs-agent/data/hostinger-vps-zeus.json`.
- 1Password: item `Hostinger API - Zeus VPS`, vault `MGS Conteúdo`, field `token`. Never emit its value or duplicate it into .env/config/Git/logs.
- Provider/API observations complement Linux checks. Crons, services, OS/Hermes updates, directory-level disk diagnosis and internal repairs still use Linux/SSH. Backup-list presence does not prove recoverability.

## Entry points

- Zeus-local pinned package: `/root/.hermes/profiles/zeus/mcp/hostinger-vps`, official `hostinger-api-mcp@2.7.0`.
- Hermes key: `mcp_servers.hostinger-vps` in Zeus only.
- Launcher: `/root/mgs-agent/scripts/hostinger-vps-mcp-launch.py`.
- Fixed-VM GET catalog: `/root/mgs-agent/scripts/hostinger-vps-mcp-readonly.mjs`.
- Diagnostics and cron callers:

```
python3 /root/mgs-agent/scripts/mgs-hostinger-vps-probe.py
python3 /root/mgs-agent/scripts/mgs-hostinger-vps-probe.py --verify-guards --output /root/mgs-agent/work/<operation>/hostinger-smoke.json
```

The probe resolves the active Hermes Python via `/root/.local/bin/hermes` when the shell Python lacks the MCP SDK. Do not pin a future cron to a retired worktree Python.

## MCP guard

The official 2.7.0 MCP lists `search`, `execute`, `multi-execute`; API operation names are not independent MCP tools. A Hermes tool-name filter cannot distinguish reboot from metrics: both use `execute`. Keep the local catalog limited to these five GET operations:

- `vps_virtual-machines_get`
- `vps_virtual-machines_metrics`
- `vps_backups_list`
- `vps_snapshots_get`
- `vps_actions_list`

The adapter concretizes the API URL to VM `1767265`, not a schema hint. Do not supply `virtualMachineId`. Unknown operations fail before an API call. Read-only annotations belong to this filtered adapter only, not the unrestricted upstream server. Keep `trust: untrusted`, no unrelated product catalogs, no alternate API base URL or HTTP listener.

Metric execution:

```
{"operation":"vps_virtual-machines_metrics","params":{"date_from":"<UTC ISO timestamp>","date_to":"<UTC ISO timestamp>"}}
```

Generate timestamps with a tool. Provider metrics can lag `df`; report timestamps and units separately. Backups/actions paginate: inspect meta and fetch pages before asserting totals.

## Validation and maintenance

1. Resolve exact item/field IDs through `/root/mgs-agent/scripts/mgs-op-with-service-account.sh`. Inject only into process memory; strip unrelated keys and the service-account bootstrap token before Node starts.
2. Verify official npm repository, Node compatibility and pinned package/lockfile integrity. Install with `--ignore-scripts` into Zeus only.
3. Exercise real stdio handshake, target identity and all five GET calls. Prove reboot/stop/restore/firewall/billing and forbidden batch are denied without side effects. Prove another VM selector cannot redirect the concrete URL.
4. Use the deployed Python SDK's actual Pydantic attributes (`is_error`, `read_only_hint`) or inspect `model_fields`; camelCase wire aliases are not guaranteed Python attributes.
5. Write config objects with native `atomic_config_write`, private backup and semantic readback showing all unrelated keys unchanged. Preserve AdsPower. Sync versioned Zeus config/skill mirror.
6. Never mutate frozen config during a concurrent authorized restart/update. Reconcile audit origin and wait for that flow to finish. Native gateway housekeeping discovers newly configured MCP servers without restart; confirm live log/process/tool registration, do not merely assume adoption.
7. Record audit, inventory, registry/checkpoint and canonical REPORT-INFRA embed with exact-message readback, no second plaintext copy.

## Safety and rollback

Connecting this integration does not authorize schedule changes, broadening monitors, VPS/gateway restart, restore, deletion, firewall/billing/credential changes. Follow current AGENT.md for each exact Critical Subset operation. Never bypass the guard with unrestricted MCP.

Non-destructive rollback: set only `mcp_servers.hostinger-vps.enabled: false` with the native writer; preserve AdsPower and the 1Password item. Package/file deletion and token revocation require their own confirmation. Do not restart the active gateway tool chain.
