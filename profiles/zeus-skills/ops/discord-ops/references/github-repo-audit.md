# GitHub repo credential validation and audit checklist — MGS

Use when Rodolfo asks whether Zeus can scan GitHub or requests a complete repository audit.

## Credential validation without persisting secrets

Preferred pattern: use the GitHub PAT from 1Password on demand, do not store it in `git remote` or global credential helpers.

Validated checks:

```bash
cd /root/mgs-agent

# Local repo facts; redact any embedded credentials in remote URLs
git remote -v | sed -E 's#https://[^/@]*@github.com/#https://***@github.com/#g'
git branch --show-current
git status --short

# 1Password availability
set -a; . ./.env >/dev/null 2>&1; set +a
op whoami
op item list --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --format json

# GitHub PAT item expected in MGS vault
# Item: GitHub PAT - mgs-agent
# Field: github_token
# Never print the token; report only field name and len.
```

API validation pattern:

```bash
TOKEN="$(op item get 'GitHub PAT - mgs-agent' --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --fields github_token --reveal)"

curl -sS -o /tmp/gh_user.json -w '%{http_code}' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Accept: application/vnd.github+json' \
  https://api.github.com/user

curl -sS -o /tmp/gh_repo.json -w '%{http_code}' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Accept: application/vnd.github+json' \
  https://api.github.com/repos/mattei2005/mgs-agent
```

Authenticated git without storing token:

```bash
TMPASK=$(mktemp)
chmod 700 "$TMPASK"
cat > "$TMPASK" <<'SH'
#!/bin/sh
case "$1" in
  *Username*) echo x-access-token ;;
  *Password*) echo "$GITHUB_TOKEN" ;;
  *) echo ;;
esac
SH
chmod 700 "$TMPASK"
GIT_ASKPASS="$TMPASK" GITHUB_TOKEN="$TOKEN" GIT_TERMINAL_PROMPT=0 \
  git ls-remote --heads https://github.com/mattei2005/mgs-agent.git main
rm -f "$TMPASK"
```

## Complete repo audit checklist

1. Scope/state:
   - `git status --short`
   - tracked file count, top directories, large tracked files, extension counts
   - history size: `git rev-list --all --count`, unique historical paths, current tracked paths, historical-only paths
2. Secrets/current tree:
   - check `.gitignore` covers `.env`, logs, DB/state files as intended
   - scan tracked files for token/key/webhook/private-key patterns
   - do not print secret values; mask or report path/line/pattern only
3. Secrets/history:
   - scan `git rev-list --all` with conservative patterns for PATs, Discord webhooks, private key markers, OP tokens
   - use `git grep -I -n -E -e "$PATTERN" $(git rev-list --all)`; the `-e` is mandatory when a pattern branch begins with `-----BEGIN`, otherwise git treats it as an option
   - de-duplicate findings by `(path,line,type,masked text)` and report only commit/path/line/type, never raw values
   - compare historical secret hashes to current `.env`/profile `.env` hashes internally; report only match/no-match and token length/type
   - validate suspected current GitHub PATs via GitHub API without printing the token; `401` means inactive/revoked
4. Compressed archives in history:
   - enumerate `*.tar.gz`, `*.tgz`, `*.zip`, `*.gz` from historical path names
   - extract blob with `git show REV:path` into memory/tempfile and inspect member names + text payloads
   - scan archived `.env`, `config.yaml`, crontab, DB snapshots, and profile backups; archives can contain secrets even when `git grep` on text blobs looks clean
   - report archive path, commit, risky member names/count, secret types found; never print member contents
5. Artifact classification:
   - classify historical-only paths into credential/env backups, backups/snapshots, runtime/log/tmp, tempfiles, deprecated/legacy, and data JSON
   - separate `current tree clean` from `history dirty`; these imply different risk and remediation
6. Syntax/structure:
   - JSON parse all `*.json`
   - YAML parse all `*.yaml`
   - `python -m compileall` for Python scripts
   - `bash -n` all shell scripts when ShellCheck is unavailable
7. Operational logs:
   - stale-log dry-run if available
   - recent log semantic scan for `error|erro|fatal|traceback|exception|failed|syntax error`
8. Cron/systemd:
   - `crontab -l` redacted
   - `systemctl list-units` for MGS services
   - verify cron scripts are executable and have observable logs
9. Dependency hygiene:
   - `npm audit` for Node subprojects if package-lock exists
10. Report:
   - severity, path/line, evidence, operational impact, proposed fix
   - distinguish `sem vazamento ativo`, `risco futuro`, `bug real rodando`, and `higiene`
   - do not recommend destructive history rewrite as the first move; first confirm repo visibility/forks/secret scanning and revocation status, then plan `git filter-repo` only if needed and explicitly approved

## MGS-specific lessons

- GitHub access may fail via plain HTTPS remote while still being valid via 1Password PAT. Report this as secure on-demand access, not as lack of access.
- The auto-commit watcher using `git add .` is a future secret-leak risk even when the current scan is clean. Prefer guardrails that abort on suspicious filenames (`.env`, key/pem, credential/secret/token/password/webhook/private) and stage with `git add -A -- .` only after those checks. Do not rely on Git pathspec excludes for ignored `.env` files; Git can reject that pattern and break the watcher.
- Runtime state/chat-log files committed frequently pollute history; if they are not canonical state, preserve them locally, `git rm --cached`, add to `.gitignore`, then regenerate infra docs/inventory.
- For shell counters under `set -e`, avoid `VAR=$(grep -c PATTERN || echo 0)`: `grep -c` prints `0` and exits `1` when no match, yielding `0\n0`. Use `VAR=$(... | grep -c PATTERN || true); VAR=${VAR:-0}`.
- Cron log health should check semantic failures, not only freshness. A cron can update its log every run while failing internally; scan a recent tail for specific patterns (`syntax error`, `Traceback`, `Exception`, `fatal`, `critical`, `failed`, `falha`, `erro`, `error`) and keep the window short enough to avoid stale false positives after a fix.
- For Yoast/RunCloud SSH scripts, prefer `mktemp -d`, `trap cleanup EXIT`, `StrictHostKeyChecking=accept-new`, and a dedicated `/root/.ssh/known_hosts_mgs`. Deprecated scripts with risky SSH/expect should become safe stubs if no cron/systemd/pipeline references remain; keep historical code recoverable via Git rather than executable in the working tree.

## Historical Git secret audit pattern

Use this when the current tree is clean but the session needs to assess whether old commits contain secrets or sensitive artifacts.

1. Keep the audit read-only unless Rodolfo explicitly approves destructive history rewriting.
2. Scan both plain historical blobs and compressed archives stored in history. A clean `git grep` is not enough if old `.tar.gz` backups contain `.env` files.
3. Never print secret values. Report only type, path/member name, commit, status, length/hash comparison result, and API status.
4. Compare historical secrets against current secrets internally by hash, then report only booleans such as `current_matches_historical=false`.
5. Validate external exposure before recommending `git filter-repo`:
   - unauthenticated GitHub API / `git ls-remote` visibility;
   - authenticated repo visibility/private flag;
   - fork count;
   - secret-scanning alerts if a temporary PAT has `security_events`/admin permissions.
6. Decision heuristic used for MGS: if repo is private, unauthenticated access is blocked, forks=0, and historical secrets do not match active credentials, prefer no history rewrite. Document the finding and only propose `filter-repo + force-push` as a separate destructive step.
7. After finding historical credential artifacts, tighten forward guardrails. For MGS auto-commit, the sensitive filename guard should include at least `.env`, key/pem, credential, secret, token, password, webhook, and private.

Useful reporting categories:

| Category | Meaning |
|---|---|
| Current tree | Whether any active tracked file contains high-signal secrets |
| Historical Git | Whether old commits contain recoverable sensitive blobs |
| External exposure | GitHub privacy, public access, forks, secret-scanning visibility |
| Credential status | Whether historical values match current active values or API auth succeeds |
| Rewrite recommendation | Operational tradeoff: compliance hygiene vs. destructive force-push risk |

- Cron log health should check semantic failures, not only freshness. A cron can update its log every run while failing internally; scan a recent tail for specific patterns (`syntax error`, `Traceback`, `Exception`, `fatal`, `critical`, `failed`, `falha`, `erro`, `error`) and keep the window short enough to avoid stale false positives after a fix.
- For Yoast/RunCloud SSH scripts, prefer `mktemp -d`, `trap cleanup EXIT`, `StrictHostKeyChecking=accept-new`, and a dedicated `/root/.ssh/known_hosts_mgs`. Deprecated scripts with risky SSH/expect should become safe stubs if no cron/systemd/pipeline references remain; keep historical code recoverable via Git rather than executable in the working tree.
