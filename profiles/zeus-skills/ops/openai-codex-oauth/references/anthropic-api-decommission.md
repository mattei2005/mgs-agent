# Anthropic API Decommission — MGS

Use when Rodolfo decides to stop Anthropic/Claude pay-per-token usage, or when a scan finds `ANTHROPIC_API_KEY`, `api.anthropic.com`, `anthropic.Anthropic`, `provider: anthropic`, or `claude-*` in active operational paths.

## Policy

- Default state: zero Anthropic/Claude pay-per-token API calls.
- Any exception requires explicit Rodolfo approval.
- GPT-5.5/OAuth is preferred for agent work; deterministic/script-only paths are preferred for recurring monitors.

## Immediate cutoff checklist

1. Identify active services and listeners that can call Anthropic.
   - Example: `mgs-rec-api.service` on `127.0.0.1:8001`.
2. Stop, disable, and mask the service if it exists only to call Claude.
   - Backup unit outside repo first.
   - `systemctl stop <service>`
   - `systemctl disable <service>`
   - If masking fails because the unit file exists, back up and remove the unit file, `systemctl daemon-reload`, then `systemctl mask <service>`.
3. Remove `ANTHROPIC_API_KEY=` lines from local runtime `.env` files without printing values.
   - Back up files outside repo with mode 600.
   - Never display the key in chat or logs.
4. Patch active code paths to fail closed before any network call.
   - Replace Anthropic fallback/extraction with a clear error such as: `Anthropic/Claude API disabled by policy`.
   - Do not merely rely on a missing key; code should not read credentials or instantiate an Anthropic client.
5. Validate.
   - `systemctl show <service> -p LoadState -p UnitFileState -p ActiveState`
   - `ss -ltnp | grep ':8001' || true`
   - grep active repo paths for `ANTHROPIC_API_KEY|api.anthropic.com|anthropic.Anthropic|model="claude|MODEL = "claude`.
   - Run a smoke test that previously would have called Anthropic; expected result is fast fail-closed, not a paid call.
6. Record in audit log with actions taken and backup location.

## Repo scan classification

Treat these as active risk:
- `api/`, `scripts/`, active `profiles/*config*`, active service units, cron entries, current `.env` files.

Treat these as historical context unless referenced by active code:
- `docs/changelog/`, `docs/PENDENCIAS-HISTORICO.md`, crontab backups, deprecated backups, old audit notes.

## MGS case study — 2026-05-16

Findings:
- `mgs-rec-api.service` was active and calling `https://api.anthropic.com/v1/messages`.
- `api/generate-rec-api.py` used `anthropic` + `claude-sonnet-4-6`.
- `scripts/mgs-rec-runner.py` had a cache-miss fallback to Anthropic.
- Zeus/Atena `.env` contained `ANTHROPIC_API_KEY`.

Actions:
- Stopped/disabled/masked `mgs-rec-api.service`.
- Removed `ANTHROPIC_API_KEY` from Zeus/Atena local `.env` files without exposing values.
- Patched `mgs-rec-runner.py` fallback to fail closed.
- Validated port 8001 closed and no active Anthropic key line in local envs.
- Dry-run failed in ~0.05s with connection refused/fail-closed and no Anthropic call.
