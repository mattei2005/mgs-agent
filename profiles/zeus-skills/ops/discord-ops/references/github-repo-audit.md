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
2. Secrets/current tree:
   - check `.gitignore` covers `.env`, logs, DB/state files as intended
   - scan tracked files for token/key/webhook/private-key patterns
   - do not print secret values; mask or report path/line/pattern only
3. Secrets/history:
   - scan `git rev-list --all` with conservative patterns for PATs, Discord webhooks, private key markers, OP tokens
4. Syntax/structure:
   - JSON parse all `*.json`
   - YAML parse all `*.yaml`
   - `python -m compileall` for Python scripts
   - `bash -n` all shell scripts when ShellCheck is unavailable
5. Operational logs:
   - stale-log dry-run if available
   - recent log semantic scan for `error|erro|fatal|traceback|exception|failed|syntax error`
6. Cron/systemd:
   - `crontab -l` redacted
   - `systemctl list-units` for MGS services
   - verify cron scripts are executable and have observable logs
7. Dependency hygiene:
   - `npm audit` for Node subprojects if package-lock exists
8. Report:
   - severity, path/line, evidence, operational impact, proposed fix
   - distinguish `sem vazamento ativo`, `risco futuro`, `bug real rodando`, and `higiene`

## MGS-specific lessons

- GitHub access may fail via plain HTTPS remote while still being valid via 1Password PAT. Report this as secure on-demand access, not as lack of access.
- The auto-commit watcher using `git add .` is a future secret-leak risk even when the current scan is clean. Prefer allowlist or explicit excludes for generated/runtime/sensitive paths.
- Runtime state/chat-log files committed frequently pollute history; call out when they dominate recent commits.
