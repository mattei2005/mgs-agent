# REPORT-INFRA — Meta cron + controlled-write validation pattern — 2026-06-19

## Context

Ares reported multiple infrastructure changes around Meta Ads automation for OpenzedFinanzas/Elena:

- repo Python scripts for probes and cron runners;
- profile-local Hermes cron wrappers under `/root/.hermes/profiles/ares/scripts/`;
- Hermes cron jobs in the Ares profile;
- operation/policy JSON files;
- audit JSON files under `data/ares/meta-ads/audit/`;
- one approved one-shot controlled-write job scheduled for Meta account midnight.

This reference captures the reusable processing pattern for Zeus when handling similar `[REPORT-INFRA]` messages.

## Validation checklist

For repo Python scripts:

```bash
python3 -m py_compile /root/mgs-agent/scripts/<script>.py
sha256sum /root/mgs-agent/scripts/<script>.py
```

For profile-local cron wrappers:

```bash
bash -n /root/.hermes/profiles/<agent>/scripts/<wrapper>.sh
sha256sum /root/.hermes/profiles/<agent>/scripts/<wrapper>.sh
```

Profile-local wrappers are runtime artifacts outside the repo. Inventory them with `path`, `size_bytes`, `modified_at`, `sha256`, `profile`, `agent`, and `git_tracked=false`; do not try to `git add` them.

For JSON operation/policy/audit files:

```bash
python3 -m json.tool /root/mgs-agent/data/.../<file>.json >/dev/null
sha256sum /root/mgs-agent/data/.../<file>.json
```

Run a literal secret scan on new/modified scripts and audit/data artifacts before committing. Permit `token_len` metadata, but never commit or print tokens/access_token/Bearer strings.

## Hermes cron job validation

Inspect `/root/.hermes/profiles/<agent>/cron/jobs.json` directly and confirm the reported IDs:

- `id`
- `name`
- `schedule`
- `enabled=true`
- `state=scheduled`
- `script`
- `no_agent`
- `deliver`
- `next_run_at`
- `repeat`

For timezone-sensitive Meta jobs, record both stored server/user time and intended account time in `infra-inventory.json`, e.g. `2026-06-19 18:00 America/New_York / 2026-06-20 00:00 Europe/Madrid`.

## Dry-run / controlled-write evidence

When a reported job is a future controlled-write, validate the dry-run audit before ACK:

- audit JSON parses;
- `mode` is `dry_run`;
- final block says `ok=true`, `dry_run=true`, expected campaign/rule counts, `error_count=0`;
- audit contains only safe metadata (`token_len`, item/field names), not credentials;
- wrapper points to the repo script with the expected `--execute` only when the scheduled job is explicitly approved.

For read-only/dry-run cron runners, local wrapper execution can be validated safely by redirecting stdout to `/tmp` and deleting it afterward. This checks execution without posting raw Discord output:

```bash
timeout 90 bash /root/.hermes/profiles/<agent>/scripts/<wrapper>.sh >/tmp/<wrapper>.out 2>&1
```

Do not use `notify_on_complete` or let raw cron output auto-deliver in `#alerts-infra`.

## Inventory update pattern

Update these sections surgically:

- `scripts[]` — repo scripts and profile-local wrappers.
- `data_files[]` — operation/policy/audit JSON files.
- `crons[]` — Hermes cron jobs with profile/id/schedule/state/deliver/repeat/next run.

Preserve existing inventory structure. Do not regenerate unrelated sections or include dirty files from other agents/threads.

## Commit scope

Commit only relevant repo-tracked artifacts:

- `data/infra-inventory.json`
- changed repo scripts
- changed operation/policy/audit JSON files

Do not commit profile-local wrappers directly; inventory them only.

Final ACK remains the canonical short form:

```text
✅ Registrado. Inventário atualizado (commit XXXX).
```
