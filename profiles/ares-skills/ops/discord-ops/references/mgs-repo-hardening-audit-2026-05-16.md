# MGS repo hardening audit — 2026-05-16

Use this reference when Rodolfo asks Zeus to scan or harden the private `mgs-agent` repository after a GitHub/repo audit. It captures reusable patterns from the May 2026 repo cleanup, not a one-off task log.

## Scope pattern

Run the audit in phases and validate after each write:

1. Read `/root/mgs-agent/AGENT.md` before changing repo behavior.
2. Confirm Git/GitHub access without persisting credentials in the remote:
   - prefer 1Password PAT fetched at runtime;
   - use temporary auth / `GIT_ASKPASS` style where needed;
   - never print token values, only source item and `len=N` if necessary.
3. Scan current tree and history for obvious secrets, but do not expose matches in chat.
4. Validate syntax/formats before and after changes:
   - JSON/YAML parse;
   - `python3 -m py_compile` for Python touched;
   - `bash -n` for shell touched;
   - targeted dry-runs when scripts support them.
5. Let the auto-commit watcher run if production uses it, but always verify final `git status`, recent commits, and service status before reporting success.

## Durable fixes/pitfalls found

### `grep -c` with `set -e` / arithmetic checks

Pitfall:

```bash
COUNT=$(printf "%s" "$DATA" | grep -c "pattern" || echo 0)
```

When there are no matches, `grep -c` prints `0` and exits `1`; `|| echo 0` appends another zero. Later `[[ "$COUNT" -eq 0 ]]` can see `0\n0` and fail.

Safer pattern:

```bash
COUNT=$(printf "%s" "$DATA" | grep -c "pattern" || true)
COUNT="${COUNT:-0}"
```

Apply this to cron monitors, housekeeping scripts, counters, and any script that feeds `grep -c` into numeric comparisons.

### Auto-commit watcher guardrails

Avoid `git add .` in automation. Pattern:

- inspect `git status --porcelain` first;
- abort the cycle if changed/untracked paths look sensitive (`.env`, `*.pem`, `*.key`, `id_rsa`, `*token*`, `*secret*`, `*password*`, `webhook`, `private`, `.npmrc`, `.pypirc`, etc.);
- stage tracked changes with `git add -u` and untracked non-sensitive files explicitly;
- validate that ignored files such as `.env` do not make pathspec exclusions abort the service.

### Cron freshness is not health

A cron can keep writing a log while failing internally. Cron monitors should check both:

- stale/missing log based on mtime;
- semantic failures in the latest execution block or recent tail (`syntax error`, `Traceback`, `Exception`, `fatal`, `critical`, `failed`, `falha`, `erro`, `error`).

To avoid false positives after a fix, scan only the most recent execution block or a small recent tail, not the entire historical log.

### SSH/SCP hardening via RunCloud jump hosts

For existing password/expect flows, do not jump straight to permanent SSH keys without Rodolfo's approval. First harden the existing flow:

```bash
-o StrictHostKeyChecking=accept-new \
-o UserKnownHostsFile=/root/.ssh/known_hosts_mgs
```

Also use:

- `mkdir -p /root/.ssh && chmod 700 /root/.ssh`;
- `mktemp -d` + `chmod 700` for local temporary workspace;
- `trap cleanup EXIT`;
- unique remote script paths using PID or random suffix;
- remote cleanup after execution;
- real validation in silent/no-Discord mode when possible.

### Deprecated scripts

For deprecated operational scripts that still contain insecure SSH/tempfile patterns:

1. Check crontab, systemd, hooks, pipelines, and references first.
2. If unused, replace with a safe stub that exits non-zero and points to the active replacement.
3. Keep the old body recoverable via Git history instead of leaving executable insecure code in the working tree.

### Backup/runtime hygiene

- Do not keep `data/backup-*`, chat logs, cron state, or other high-churn runtime files versioned unless they are explicit fixtures.
- Preserve local files if useful, but `git rm --cached` and add precise `.gitignore` rules.
- Old backups are covered by snapshots/Git history; versioned backups frequently reintroduce insecure examples.

### Discord approval button runtime

If Discord shows `This interaction failed` for Hermes approval buttons:

- patch the Discord interaction handler to ACK/defer immediately (`interaction.response.defer(...)`) before queue resolution / message edit;
- then resolve the approval and edit/delete the original message;
- validate with Python compile and a controlled gateway restart.

For repeated low/medium false positives in known MGS operations, prefer `approvals.mode: smart` + a longer gateway timeout, not global approval disablement.

## Reporting shape for Rodolfo

For multi-step hardening runs, every partial report should end with:

```text
Próximo passo pendente: <next concrete operational step>
```

Use aligned `text` blocks for findings, actions, validations, and commit hashes. Avoid dumping raw logs or secrets; summarize and redact.