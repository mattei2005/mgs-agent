# Cron backup + housekeeping preserve-latest pattern

Validated for MGS cron hardening sessions where Rodolfo asks to improve backup cleanup and then "execute tudo" for cron reliability.

## Durable pattern

Split backup creation from backup cleanup:

- `mgs-safety-backup.sh`: creates operational snapshots on a gated interval (default every 3 days).
- `housekeeping-bak-cleanup.sh`: deletes old backup artifacts, but always preserves the newest artifact per backup family.

Do not combine these responsibilities in one script. Creation and deletion have different risks, schedules, and validation paths.

## Housekeeping rule

For backup cleanup, preserve the latest file per family even when it is older than retention. If only one backup exists for a family, keep it.

Recommended candidate patterns:

```text
*.bak*
*.backup*
*.old
*.orig
*~
```

Group by stable backup family, typically same directory + normalized base filename. Normalize common suffixes like:

```text
SOUL.md.bak-20260602-195530              -> SOUL.md
file.md-pre-ceo-corrections-20260605.bak -> file.md
crontab-root-20260603-151254.bak         -> crontab-root
config.yaml.old                          -> config.yaml
file~                                    -> file
```

Use Python for grouping instead of shell arrays when file names may contain spaces or timestamps. Emit three classes in logs/dry-run: delete candidate, preserve_latest, inside_retention.

## Safety backup rule

A recurring safety backup should exclude secret-bearing files by name, validate the archive, and maintain a manifest that lists paths + hash + size only, never contents.

Default exclusions:

```text
.env, .env.*
*auth.json*
*credentials*, *credential*
*secret*, *token*, *password*, *passwd*, *webhook*
*.sqlite, *.db, *.log
.git, node_modules, __pycache__, backups
```

Validation checklist:

```bash
bash -n scripts/housekeeping-bak-cleanup.sh scripts/mgs-safety-backup.sh
RETENTION_DAYS=15 scripts/housekeeping-bak-cleanup.sh --dry-run
scripts/mgs-safety-backup.sh --dry-run
latest=$(find /root/mgs-agent/backups/safety -maxdepth 1 -type f -name 'mgs-safety-*.tar.gz' -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
tar -tzf "$latest" >/dev/null
tar -tzf "$latest" | grep -Ei '(^|/)(\.env|.*auth\.json.*|.*credential.*|.*secret.*|.*token.*|.*password.*|.*passwd.*|.*webhook.*)(/|$)' || true
```

The final grep should return no matches.

## Cron hardening additions found useful

When doing a broad cron hardening pass, also check:

- `monitor-auto-push.sh`: add `--dry-run`; lazy-load webhook only when sending alerts; do not count a dirty working tree as a push failure because auto-commit may be in debounce/guardrail.
- `sync-codex-oauth.sh`: before overwriting `auth.json`, create a chmod `0600` backup and validate candidate JSON/OpenAI-Codex state before atomic replace. Never log token values.
- `cleanup-zombie-sessions.sh`: use last real message activity (`max(sessions.started_at, messages.timestamp)`) rather than only session `started_at`; include all active profiles; use a conservative grace window (e.g. 180min) and validate with `--dry-run` before applying.
- `infra-discovery.sh`: write to temp file, validate with `jq -e`, then `mv` atomically.
- `monitor-service-restarts.sh`: keep service list current as new agents are added (Zeus/Atena/Ares/agente legado/autocommit).
- `monitor-gpt55-oauth-cost.sh`: label output as `uso hipotético`/simulated usage, not real cost; OAuth cost is `$0.00`; include all agent profiles.
- `monitor-yoast-health-eggbev.sh`: support `--dry-run` that may query live data but must not save snapshots or post Discord.
- `cron-smoke-test.sh`: aim for zero fixed skips by running risky/posting/deleting jobs in dry-run.
- `monitor-cron-stale-logs.sh`: detect semantic errors in fresh logs, not just stale mtime; scan only the latest execution block when possible.

## Validation response shape

Report concise executive evidence:

```text
bash -n / py_compile         OK
cron-smoke-test              runs=N skips=0 fails=0
monitor-cron-stale dry-run   problems=0
critical state               consecutive_failures=0 / zombies=0 / archive_valid=1
```

Avoid saying "resolved" unless backed by live script output or state file evidence.
