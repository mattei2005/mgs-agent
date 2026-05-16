# Cron semantic error + auto-commit guardrails — 2026-05-16

## Context

During a repository-wide MGS ops audit, a cron was updating its log regularly but still failing semantically. The stale-log monitor reported OK because it only checked mtime.

Validated case:

```bash
PUB_COUNT=$(printf "%s" "$PUBLICATIONS" | grep -c "create-post OK" || echo 0)
[[ "$PUB_COUNT" -eq 0 ]]
```

When there were zero matches, `grep -c` printed `0` and exited 1, then `|| echo 0` printed another `0`. The variable became `0\n0`, breaking Bash arithmetic with:

```text
syntax error in expression (error token is "0")
```

## Fix pattern

Use one numeric source, not `grep -c ... || echo 0`:

```bash
COUNT=$(printf "%s" "$TEXT" | grep -c "PATTERN" || true)
COUNT="${COUNT:-0}"
```

or:

```bash
COUNT=$(grep -c "PATTERN" <<< "$TEXT" || true)
COUNT="${COUNT:-0}"
```

## Semantic log monitor pattern

Stale-log monitors must detect recent errors, not only recent writes.

Implementation pattern:

1. Read only the last N log lines.
2. If the log has a clear execution-start marker (`start`, `iniciando`, `===`), scan only the latest execution block.
3. Match specific failure patterns such as:
   - `syntax error`
   - `traceback`
   - `exception`
   - `fatal:`
   - `critical`
   - `erro crítico`
   - `error token`
   - `command not found`
   - `permission denied`
   - `no such file or directory`
4. Avoid broad `error|erro|failed` unless the script’s normal success language is known, because phrases like `zero falhas` and comments can false-positive.
5. Dry-run should show `ERROR` rows but not send Discord.
6. After fixing the underlying script, force one clean run into the cron log and re-run dry-run; the monitor should return `problems=0`.

## Auto-commit watcher guardrail

`git add .` in an auto-commit watcher is a future secret-leak risk. Add a pre-commit guardrail before staging:

```bash
SENSITIVE_PATH_REGEX='(^|/)(\.env|.*\.pem|.*\.key|id_rsa|id_ed25519|.*credential.*|.*secret.*|.*token.*|.*password.*|hosts\.yml|\.npmrc|\.pypirc)$'

SENSITIVE_CHANGES=$(git status --porcelain | awk '{print $2}' | grep -Ei "$SENSITIVE_PATH_REGEX" || true)
if [ -n "$SENSITIVE_CHANGES" ]; then
  log "BLOQUEADO: arquivo sensível detectado; commit automático abortado"
  printf '%s\n' "$SENSITIVE_CHANGES" | while IFS= read -r f; do log "  sensitive: $f"; done
  continue
fi

git add -A -- .
```

Important pitfall: do not combine `git add -A -- .` with pathspec excludes for ignored sensitive files like `.env` unless tested. In this environment, an exclusion pathspec including `.env` caused Git to fail with:

```text
The following paths are ignored by one of your .gitignore files:
.env
```

The safer pattern is: keep `.gitignore` for ignored files, add the sensitive-name preflight for non-ignored files, then stage normally.

## Validation checklist

```bash
bash -n scripts/track-article-cost.sh scripts/auto-commit-watcher.sh scripts/monitor-cron-stale-logs.sh
scripts/track-article-cost.sh >> logs/track-article-cost-cron.log 2>&1
scripts/monitor-cron-stale-logs.sh --dry-run
systemctl restart mgs-autocommit.service
systemctl status mgs-autocommit.service --no-pager --lines=10
git status -sb
```

Expected final state:

```text
track-article-cost.sh            | OK
monitor-cron-stale-logs.sh       | SKIP watchdog self-skip
problems=0 resolved=0 dry_run=1
mgs-autocommit.service           | active/running
```
