# Auto-push divergent commit reconciliation

## When this applies

Use this when `monitor-auto-push.sh` reports `START sem OK`, `push pendente`, or `main local != origin/main`, especially after two commits with the same subject were created close together and one push was rejected as non-fast-forward.

## Durable lesson

A `START sem OK` in `auto-push.log` is not always an active failure. It can be historical noise after the repo was reconciled by another worktree or after the failed commit was superseded by a later commit that contains the desired change.

The monitor should distinguish:

- active failure: failed commit is still on local `HEAD` and not in `origin/main`;
- resolved by remote: failed commit is already an ancestor of `origin/main`;
- superseded: failed commit is not an ancestor of current `HEAD` anymore.

Only the active case should keep the alert red.

## Safe recovery pattern

1. Fetch and inspect divergence without touching the dirty runtime tree:
   ```bash
   cd /root/mgs-agent
   git fetch origin main --quiet
   git rev-list --left-right --count HEAD...origin/main
   git log --oneline origin/main..HEAD --max-count=10
   git log --oneline HEAD..origin/main --max-count=10
   git diff --stat HEAD..origin/main | head -80
   ```

2. If the worktree is dirty or has unrelated runtime files, do not merge/commit in place. Use a clean detached worktree from `origin/main`:
   ```bash
   git worktree add --detach /tmp/mgs-agent-autopush-reconcile origin/main
   cd /tmp/mgs-agent-autopush-reconcile
   # apply only the minimal desired patch
   git add <files>
   git commit -m '...'
   ```

3. Push with the same non-persistent `GIT_ASKPASS` pattern as the post-commit hook; never print the token:
   ```bash
   ASKER=$(mktemp)
   cat > "$ASKER" <<'SCRIPT'
   #!/bin/bash
   case "$1" in
     *Username*) echo "mattei2005" ;;
     *Password*) op item get "GitHub PAT - mgs-agent" --vault "MGS Conteúdo" --fields github_token --reveal ;;
   esac
   SCRIPT
   chmod +x "$ASKER"
   set -a; . /root/mgs-agent/.env; set +a
   GIT_ASKPASS="$ASKER" GIT_TERMINAL_PROMPT=0 git push origin HEAD:main
   rm -f "$ASKER"
   ```

4. In the live repo, fetch and only move the local branch ref to the pushed remote when safe. This does not overwrite dirty files:
   ```bash
   cd /root/mgs-agent
   git fetch origin main --quiet
   git update-ref refs/heads/main origin/main
   git rev-list --left-right --count HEAD...origin/main
   ```

5. Validate the monitor with dry-run first, then real run if clean:
   ```bash
   bash -n /root/mgs-agent/scripts/monitor-auto-push.sh
   /root/mgs-agent/scripts/monitor-auto-push.sh --dry-run
   /root/mgs-agent/scripts/monitor-auto-push.sh >> /root/mgs-agent/logs/monitor-auto-push.log 2>&1
   jq '{consecutive_failures,last_failure_details}' /root/mgs-agent/data/auto-push-monitor.json
   ```

## Monitor hardening pattern

Inside the `START sem OK` loop, ignore historical failures that are no longer active:

```bash
if ! grep -q "auto-push OK commit=${commit}" "$PUSH_LOG"; then
    if git -C "$BASE_DIR" merge-base --is-ancestor "$commit" origin/main 2>/dev/null; then
        continue
    fi
    if ! git -C "$BASE_DIR" merge-base --is-ancestor "$commit" HEAD 2>/dev/null; then
        continue
    fi
    NEW_FAILURES+=("${ts} commit=${commit} [START sem OK]")
fi
```

## Reporting standard

Report separately:

- GitHub sync: `HEAD`, `origin/main`, ahead/behind.
- Monitor state: `consecutive_failures`, `last_failure_details`.
- Whether a green resolution alert was posted.
- Any unrelated dirty runtime files as non-blocking noise, not as the auto-push failure itself.
