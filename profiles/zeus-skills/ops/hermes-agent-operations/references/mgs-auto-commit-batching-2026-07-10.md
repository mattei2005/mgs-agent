# MGS Auto-Commit Batching — 2026-07-10

## Canonical behavior

Rodolfo approved replacing the old 10-second commit debounce with bounded batching to reduce Git commit churn, GitHub pushes, and shared 1Password PAT lookups.

Runtime script: `/root/mgs-agent/scripts/auto-commit-watcher.sh`
Service: `mgs-autocommit.service`

Flush a commit when either condition occurs first:

1. Ten distinct change bursts/lots were observed.
2. Ten minutes elapsed since the first observed lot.

Defaults:

```text
MGS_AUTOCOMMIT_BATCH_TARGET=10
MGS_AUTOCOMMIT_BATCH_QUIET_SECONDS=10
MGS_AUTOCOMMIT_BATCH_MAX_WAIT_SECONDS=600
```

The time ceiling is mandatory. A pure count-only policy could leave fewer than ten changes uncommitted indefinitely. The watcher keeps one persistent `inotifywait -m` stream for its entire lifetime so changes are not missed during quiet windows, staging, or commit. A non-blocking `flock` on `.git/auto-commit-watcher.lock` prevents duplicate watcher instances from sharing the Git index. The batch accumulator resets before the Git snapshot; events arriving during status/add/commit remain queued for the next batch.

The watcher still commits only on `main`, preserves sensitive-path blocking and path exclusions, and relies on the existing `post-commit` hook for background GitHub push. Manual commits still trigger the hook immediately.

## Verification

Before service restart:

1. `bash -n /root/mgs-agent/scripts/auto-commit-watcher.sh`.
2. Run the actual script against a temporary Git repository using `MGS_AUTOCOMMIT_REPO_DIR` and `MGS_AUTOCOMMIT_LOG_FILE` overrides.
3. Validate the persistent-monitor branches:
   - target reached → log contains `reason=batch_target`;
   - timeout reached → log contains `reason=max_wait` and a commit exists;
   - duplicate watcher → second process exits cleanly with `outra instância` in its log;
   - temporary worktree remains clean.
4. Restart only `mgs-autocommit.service`, then verify `active`, `NRestarts`, process command line, and startup log with the canonical defaults.

Do not count raw file-system events as human actions in reports. The implementation counts separated change bursts after a quiet window; one operational action may touch multiple files.
