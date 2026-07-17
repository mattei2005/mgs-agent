# MGS Discord tool-progress noise + backup retention fix — 2026-06-30

## Context

During a controlled Hermes update/restart session, Discord displayed the full tool breadcrumb stream (`terminal`, `read_file`, `search_files`, code snippets) instead of only leaving the final report. Rodolfo expected progress/code breadcrumbs to disappear when the final report landed.

Separately, a post-update backup audit showed that the existing housekeeping automation was running, but did not clean large Hermes update profile tarballs.

## Durable lessons

### 1. Discord tool progress has per-platform override precedence

Do not trust `display.tool_progress: off` alone. Hermes resolves per-platform settings first:

1. `display.platforms.discord.tool_progress`
2. `display.tool_progress`
3. built-in Discord default

In the MGS profiles, `display.platforms.discord.tool_progress: all` overrode the global `off`, so Discord kept showing every tool call.

MGS desired Discord settings for Zeus/Atena/Ares/agente legado:

```yaml
display:
  tool_progress: off
  tool_preview_length: 0
  tool_progress_command: false
  platforms:
    discord:
      tool_progress: off
      tool_preview_length: 0
      cleanup_progress: true
      interim_assistant_messages: false
      busy_ack_detail: false
```

Apply this to both live profiles and versioned mirrors:

- `/root/.hermes/profiles/{zeus,atena,ares,legacy-agent}/config.yaml`
- `/root/mgs-agent/profiles/{zeus,atena,ares,legacy-agent}-config.yaml`

Validation pattern:

```bash
hermes -p zeus config check
hermes -p atena config check
hermes -p ares config check
hermes -p legacy-agent config check
python3 - <<'PY'
import yaml
for p in ['zeus','atena','ares','legacy-agent']:
    d=yaml.safe_load(open(f'/root/.hermes/profiles/{p}/config.yaml')) or {}
    disp=d.get('display') or {}
    disc=(disp.get('platforms') or {}).get('discord') or {}
    print(p, disp.get('tool_progress'), disc.get('tool_progress'), disc.get('tool_preview_length'), disc.get('cleanup_progress'))
PY
```

For code-level validation, `gateway.display_config.resolve_display_setting(config, 'discord', 'tool_progress')` must return `off`.

### 2. Tool progress changes usually do not need restart

Gateway reads display config for new turns. If only `display.*` settings changed, validate config and start a new turn; avoid restarting gateways unless a code path requires it.

### 3. Existing housekeeping did not cover Hermes update tarballs

`housekeeping-bak-cleanup.sh` originally cleaned only explicit backup markers:

- `.bak`
- `.backup`
- `.old`
- `.orig`
- `~`

It did **not** cover large update artifacts like:

```text
/root/mgs-agent/reports/hermes-updates/**/hermes-profiles-backup-*.tar.gz
```

This allowed multiple 1.5–1.6GB profile backups to accumulate.

MGS retention policy added on 2026-06-30:

- Keep the 2 newest `hermes-profiles-backup*.tar.gz` globally.
- Delete older Hermes update tarballs above `HERMES_UPDATE_BACKUP_RETENTION_DAYS=2`.
- Continue the old small-backup retention for `.bak/.backup/.old/.orig/~` with `RETENTION_DAYS=15` and preserve-latest-by-family.

Validation:

```bash
bash -n /root/mgs-agent/scripts/housekeeping-bak-cleanup.sh
RETENTION_DAYS=15 HERMES_UPDATE_BACKUP_RETENTION_DAYS=2 HERMES_UPDATE_BACKUP_KEEP_LATEST=2 \
  /root/mgs-agent/scripts/housekeeping-bak-cleanup.sh --dry-run
```

### 4. Safety backup tar can return rc=1 for live data drift

`mgs-safety-backup.sh` can hit:

```text
tar: root/mgs-agent/data: file changed as we read it
```

That is acceptable for an operational snapshot if and only if:

- tar exit code is `1`,
- the archive exists and is non-empty,
- stderr contains `file changed as we read it`, and
- `tar -tzf "$ARCHIVE"` validates afterward.

Treat it as WARN and continue to manifest/validation/retention. Any other tar error still fails closed.

Validation:

```bash
bash -n /root/mgs-agent/scripts/mgs-safety-backup.sh
/root/mgs-agent/scripts/mgs-safety-backup.sh --dry-run
```

### 5. Conservative cleanup of Hermes archives and Git worktrees

Before deleting a redundant `hermes-profiles-backup*.tar.gz`, validate both the current canonical archive and the one prior archive that will remain with `tar -tzf`. Preserve the surrounding report/evidence directory and remove only the redundant large archive unless the user explicitly authorizes deleting the whole report.

Inventory worktrees separately with `git worktree list --porcelain`. Registered temporary worktrees must be removed through:

```bash
git -C /root/.hermes/hermes-agent worktree remove --force /exact/worktree/path
git -C /root/.hermes/hermes-agent worktree prune
```

Do not `rm -rf` a registered worktree first; that leaves stale Git metadata. Unregistered temporary directories may be removed only when they were included explicitly in the confirmed deletion scope.

An explicit backup policy wins over generic count-based advice. For example, safety snapshots governed by `RETENTION_DAYS=30` remain protected during a conservative Hermes cleanup even if several copies exist; changing that policy is a separate script/config decision and confirmation. Recalculate actual bytes immediately before deletion and report actual reclaimed space afterward, because temporary directories may disappear between inventory and execution.

### 6. Infra reporting checklist after changing backup automation

Because these are scripts/config/data, the task is not complete until:

1. `bash -n` passes for changed scripts.
2. dry-runs pass.
3. `docs/CRONS.md` reflects the actual behavior.
4. `infra-discovery.sh` regenerates `/root/mgs-agent/data/infra-inventory.json`.
5. Audit log gets an entry.
6. `[REPORT-INFRA]` is posted to `#alerts-infra` and returns HTTP 204.

## Pitfall

Do not announce “the cleanup automation works” from cron presence alone. Check scope: what filename patterns it scans, which directories it traverses, retention thresholds, and whether the log shows successful closure (`END OK`/`END`).
