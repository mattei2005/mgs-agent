# MGS Agent auto-commit / auto-push repair

Use this reference when `/root/mgs-agent` stops updating GitHub automatically or GitHub `main` looks stale while the VPS has newer local work.

## Durable failure pattern

The MGS repo has two layers:

1. `mgs-autocommit.service` runs `scripts/auto-commit-watcher.sh` and commits file changes detected by `inotifywait`.
2. `.git/hooks/post-commit` pushes commits to GitHub.

A stale GitHub page can happen even when the service is `active` if:

- the repo is checked out on a side branch instead of `main`;
- the post-commit hook pushes hardcoded `origin main`, so side-branch commits do not update GitHub/main;
- the watcher blocks on a false-positive sensitive filename, leaving a dirty tree forever;
- the monitor only reads `logs/auto-push.log` and does not compare live Git state (`HEAD`, `origin/main`, branch, dirty tree).

## Controlled repair workflow

```bash
cd /root/mgs-agent
systemctl stop mgs-autocommit.service

TS=$(date +%Y%m%d-%H%M%S)
BK=/root/mgs-agent-rescue/git-rescue-$TS
mkdir -p "$BK"
git status --porcelain=v1 > "$BK/status.txt"
git diff > "$BK/working-tree.diff"
git diff --cached > "$BK/index.diff"
git log --oneline main..HEAD > "$BK/commits-ahead-main.txt"
```

Before staging, run a secret scan over changed files. Do not print credentials. If the scan is clean:

```bash
git add -A -- .
git commit -m "auto: consolidate local ops updates before main restore"
git checkout main
git merge --ff-only <side-branch>
```

Then repair the auto-push layer and commit it on `main`.

## Hardening rules

- `auto-commit-watcher.sh` should only commit when `git rev-parse --abbrev-ref HEAD` is `main`. On any other branch, log and skip.
- Sensitive filename guardrails need allowlists for deterministic security tooling names such as `honcho_sanitized_secret_scan.py`; do not make `secret` in a filename an unconditional blocker.
- `.git/hooks/post-commit` should push `origin HEAD:main` only when current branch is `main`; if branch is not `main`, log an explicit failure instead of silently pushing the wrong ref.
- `monitor-auto-push.sh` must validate repo health, not just push-log lines: current branch, `HEAD` vs `origin/main`, dirty tree count, and fetchability of `origin/main`.
- Ignore transient state/rescue files such as `data/git-rescue-*/` and `data/hermes-news-explainer-state.json.*` so runtime state does not enter commits.
- Under `set -euo pipefail`, avoid `git status --porcelain | head -N | ...`: with many dirty files the producer can receive SIGPIPE and the watcher exits `141`, causing a systemd restart loop. Capture status once (`STATUS_OUTPUT=$(git status --porcelain -- <filtered pathspecs>)`) and derive commit messages/guardrails from that variable.
- If adding ignores for a directory that already has tracked files (example: heavy generated Ares video frame samples), do not use broad `git add -A -- .` from the watcher. Stage only the paths returned by the filtered `git status`, otherwise Git may error with “paths are ignored” and restart the service.

## Validation

After patching:

```bash
bash -n scripts/auto-commit-watcher.sh scripts/monitor-auto-push.sh .git/hooks/post-commit
systemctl start mgs-autocommit.service
bash scripts/monitor-auto-push.sh
```

Run a real smoke test by creating a safe temporary file under `data/`, wait for the watcher, confirm auto-commit and push, then delete the file and confirm the cleanup commit also pushes.

Expected final checks:

```bash
systemctl is-active mgs-autocommit.service
git fetch --quiet origin main
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
git rev-parse --short origin/main
git ls-remote origin refs/heads/main | cut -f1 | cut -c1-7
git status --porcelain=v1 | wc -l
```

Healthy state: service `active`, branch `main`, `HEAD == origin/main == ls-remote`, dirty count `0`, monitor consecutive failures `0`.