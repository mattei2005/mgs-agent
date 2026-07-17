# REPORT-INFRA — system packages and runtime dependencies

Use when another MGS agent reports runtime prep via apt/Playwright/system packages rather than a repo script/cron/skill.

## Pattern

Some infra reports have no shared code/config change, but still alter durable VPS runtime state. Examples:
- Playwright `install-deps` / apt browser dependencies for Chromium automation.
- `libimage-exiftool-perl`, `mat2`, `ffmpeg`, `python3-pil` or other sanitizer/media tooling installed system-wide.
- Runtime validation projects under `/tmp` used only as test artifacts.

## Zeus processing checklist

1. Validate the installed package state without dumping huge apt logs:
   - `dpkg-query -W -f='${binary:Package}\t${Status}\t${Version}\n' <package>` for explicit packages.
   - Validate required binaries with `command -v <binary>` or direct executable path checks.
   - For media/video deps, compact probes are enough: `ffmpeg -version | head -1`, `ffprobe -version | head -1`, and a tiny Python/PIL import + in-memory image smoke test.
   - For Node Playwright projects, run a compact probe from the project dir:
     - `node -e "const {chromium}=require('playwright'); console.log(require('playwright/package.json').version); console.log(chromium.executablePath())"`
     - then check the executable exists.
2. Treat `/tmp/...` artifacts as validation evidence, not inventory targets, unless the agent explicitly promotes them into a durable script/config path.
3. Update `/root/mgs-agent/data/infra-inventory.json` with a durable `system_packages[]` entry containing:
   - `id`, `agent`, `manager`, `source_report`, package list/count or explicit package/version, runtime validation, purpose, and any known pending risk.
4. Preserve existing manual inventory sections. `infra-discovery.sh` must preserve not only `system_packages`, `discord_permissions`, and `oauth_auth_states`, but also `runtime_artifacts` when present. Otherwise a later regeneration silently drops previously registered manual artifacts.
5. If `infra-inventory.json` already has unrelated diffs from cron/another agent, avoid committing their drift. Restore just the inventory file from HEAD if necessary, reapply the new entry, and verify existing manual sections still exist before staging.
6. Patch `/root/mgs-agent/scripts/infra-discovery.sh` if needed so manual inventory sections are preserved on regeneration.
7. Record `report_infra_processed` in `events-audit.jsonl` with validations and `inventory_updated=true`.
8. Commit only relevant repo files (`infra-inventory.json`, and `infra-discovery.sh` if preservation logic changed). Do not version `/tmp` validation artifacts.

## Validation gates before ACK

- `python3 -m json.tool /root/mgs-agent/data/infra-inventory.json >/dev/null`
- `bash -n /root/mgs-agent/scripts/infra-discovery.sh` if touched.
- A semantic check that the new `system_packages[]` entry exists by `id`.
- A preservation check for manual sections already present, especially `runtime_artifacts`.
- `git show --stat --oneline -1` after commit; ACK with that commit only if it contains the intended files.

## Pitfalls

- Do not ignore a REPORT-INFRA just because it says “sem alteração em código/config compartilhado.” System package installs are durable runtime infra and belong in the inventory.
- Do not let `infra-discovery.sh` drop manual sections while adding a new one. Preserving `system_packages` but losing `runtime_artifacts` is still an inventory regression.
- Do not commit unrelated Ares/agente legado audit JSONs or sync-souls drift while processing a package report. Staging must be surgical.
- If the report includes an unresolved operational caveat, record it as a pending/risk note instead of treating the report as fully clean.
