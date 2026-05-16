# Repo hardening audit patterns — MGS agent repo

Use this as a compact checklist for future `/root/mgs-agent` or GitHub repo hardening sessions.

## Safe scan order

1. Read the repo agent instructions (`AGENT.md`, `CLAUDE.md`) before writes.
2. Verify Git/GitHub access without persisting tokens in remotes:
   - prefer 1Password/PAT loaded only for the command;
   - use temporary `GIT_ASKPASS` or env-scoped credentials;
   - never print token values, only item name and length/status.
3. Scan current tree and tracked history for obvious secrets before functional fixes.
4. Validate syntax before and after patches:
   - JSON/YAML parsers;
   - `python3 -m py_compile`;
   - `bash -n` for touched scripts;
   - package audit only in the affected package directory.
5. Confirm crons/systemd references before deleting/deprecating scripts.

## Durable pitfalls found

### `grep -c ... || echo 0` can create `0\n0`

`grep -c` prints `0` and exits `1` when there are no matches. Under command substitution with `|| echo 0`, the variable becomes two lines (`0\n0`) and numeric tests fail.

Bad:

```bash
COUNT=$(printf "%s" "$DATA" | grep -c "pattern" || echo 0)
[[ "$COUNT" -eq 0 ]]
```

Good:

```bash
COUNT=$(printf "%s" "$DATA" | grep -c "pattern" || true)
COUNT="${COUNT:-0}"
```

### Auto-commit watchers need preflight secret guards

Avoid raw `git add .` in systemd/cron auto-commit scripts. Pattern:

- inspect `git status --porcelain` first;
- abort the cycle if paths match sensitive names (`.env`, `*.pem`, `*.key`, `id_rsa`, `*token*`, `*secret*`, `*password*`, `*webhook*`, etc.);
- stage with safer explicit rules after the guard;
- validate pathspec changes because ignored files can make Git abort in surprising ways.

### Cron monitors need semantic error detection

A fresh log does not mean a healthy cron. For monitors like `monitor-cron-stale-logs.sh`, check both:

- stale/missing log age;
- recent execution block/tail for semantic errors (`syntax error`, `Traceback`, `Exception`, `fatal`, `critical`, `failed`, `erro`, etc.).

Scan only the most recent execution window where possible to avoid alerting forever on fixed historical errors.

### SSH hardening for scripts using jump hosts

For cron/monitor scripts using `ssh/scp -J` and password/expect, do not jump straight to permanent SSH keys without Rodolfo's explicit approval. First harden operationally:

```text
StrictHostKeyChecking=accept-new
UserKnownHostsFile=/root/.ssh/known_hosts_mgs
mktemp -d + chmod 700
trap cleanup EXIT
remote script names with PID/random suffix
remote cleanup after execution
```

Validate with a controlled real run only if it will not post noisy Discord alerts or mutate production.

### Deprecated scripts

Do not harden dead code blindly. First check cron/systemd/hooks/pipelines/docs references. If unused, replace with an explicit stub that exits non-zero and points to the active replacement, leaving old implementation recoverable through Git history.

### Runtime state and backups

Runtime state/log snapshots should usually be ignored, not versioned:

- `data/cron-stale-logs-state.json`
- `data/chat-logs/`
- backup directories/files under `data/backup-*` or `.bak*`

Preserve local copies when removing from Git unless Rodolfo explicitly asks for deletion.

### Dependency/tooling pass without surprise upgrades

After script hardening, run a final dependency/tooling pass. Keep it read-mostly and non-destructive:

- enumerate package manifests first; do not assume a repo-wide package manager;
- run `npm audit`, `npm outdated`, and `npm test` inside each actual package directory;
- if `npm test` is the default placeholder, replace it with a deterministic syntax check rather than inventing a broad test suite;
- do not run `npm audit fix` or major upgrades without explicit approval;
- for legacy services that use disallowed pay-per-token providers and are already `masked`/`inactive`, replace runnable code with a fail-closed stub instead of leaving dormant credential-reading code.

Detailed recipe: `references/mgs-deps-tooling-audit.md`.

## Reporting pattern

For multi-step infra hardening reports to Rodolfo, end each partial report with:

```text
Próximo passo pendente: <ação operacional concreta>
```

Keep the report short, use aligned status blocks, and do not expose secrets or credential-derived values.
