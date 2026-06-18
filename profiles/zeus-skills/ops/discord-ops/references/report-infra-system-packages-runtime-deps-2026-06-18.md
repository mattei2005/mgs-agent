# REPORT-INFRA — system packages and runtime dependencies

Use when another MGS agent reports runtime prep via apt/Playwright/system packages rather than a repo script/cron/skill.

## Pattern

Some infra reports have no shared code/config change, but still alter durable VPS runtime state. Examples:
- Playwright `install-deps` / apt browser dependencies for Chromium automation.
- `libimage-exiftool-perl` or other sanitizer/metadata tools installed system-wide.
- Runtime validation projects under `/tmp` used only as test artifacts.

## Zeus processing checklist

1. Validate the installed package state without dumping huge apt logs:
   - `dpkg-query -W -f='${Status} ${Version}\n' <package>` for explicit packages.
   - Validate required binaries with `command -v <binary>` or direct executable path checks.
   - For Node Playwright projects, run a compact probe from the project dir:
     - `node -e "const {chromium}=require('playwright'); console.log(require('playwright/package.json').version); console.log(chromium.executablePath())"`
     - then check the executable exists.
2. Treat `/tmp/...` artifacts as validation evidence, not inventory targets, unless the agent explicitly promotes them into a durable script/config path.
3. Update `/root/mgs-agent/data/infra-inventory.json` with a durable `system_packages[]` entry containing:
   - `id`, `agent`, `manager`, `source_report`, package list/count or explicit package/version, runtime validation, purpose, and any known pending risk.
4. Patch `/root/mgs-agent/scripts/infra-discovery.sh` if needed so manual inventory sections like `system_packages` are preserved on regeneration, the same way `discord_permissions` and `oauth_auth_states` are preserved.
5. Record `report_infra_processed` in `events-audit.jsonl` with validations and `inventory_updated=true`.
6. Commit only relevant repo files (`infra-inventory.json`, and `infra-discovery.sh` if preservation logic changed). Do not version `/tmp` validation artifacts.

## Pitfall

Do not ignore a REPORT-INFRA just because it says “sem alteração em código/config compartilhado.” System package installs are durable runtime infra and belong in the inventory. If the report includes an unresolved operational caveat, record it as a pending/risk note instead of treating the report as fully clean.