---
name: soul-md-persist-rules
description: >
  Persist operational rules to Atena's SOUL.md permanently — survives model resets and upgrades.
  Covers edit, sync to mgs-agent repo, commit, and push with 1Password token.
triggers:
  - "adicionar regra ao SOUL.md"
  - "persistir no SOUL.md"
  - "regra permanente identidade"
  - "memory.jsonl vs SOUL.md"
---

# Persist Rules to SOUL.md

## When to use
When a rule must survive model resets and upgrades. `memory.jsonl` is volatile — SOUL.md is the permanent identity file.

## File locations

| Role | Path |
|---|---|
| Live SOUL.md (Atena) | `/root/.hermes/profiles/atena/SOUL.md` |
| Repo mirror (Atena) | `/root/mgs-agent/profiles/atena-soul.md` |
| Sync script | `/root/mgs-agent/scripts/sync-souls.sh` |

## Steps

### 1. Capture MD5 before editing
```bash
md5sum /root/.hermes/profiles/atena/SOUL.md
```

### 2. Find the right insertion point
```bash
# Check last N lines for context
read_file("/root/.hermes/profiles/atena/SOUL.md", offset=270, limit=15)
```

### 3. Edit via patch (append to end of file)
Use `mcp_patch` with `path=/root/.hermes/profiles/atena/SOUL.md`.
- Find the last meaningful line (e.g. `"Leia AGENT.md agora..."`)
- Append new section after it

### 4. Validate with grep
```bash
grep -c -iE "keyword1" /root/.hermes/profiles/atena/SOUL.md
grep -n -iE "keyword1" /root/.hermes/profiles/atena/SOUL.md
```
All 3+ terms must return ≥1 match.

### 5. Sync to repo
```bash
bash /root/mgs-agent/scripts/sync-souls.sh
```
The script copies SOUL.md → `profiles/atena-soul.md` only if source is newer. Verify MD5s match:
```bash
md5sum /root/.hermes/profiles/atena/SOUL.md
md5sum /root/mgs-agent/profiles/atena-soul.md
```

### 6. Commit
```bash
cd /root/mgs-agent
git add profiles/atena-soul.md
git commit -m "docs(soul/atena): <description of rules added>"
```

### 7. Push with 1Password token
```bash
set -a && . /root/mgs-agent/.env && set +a
TOKEN=$(op item get 'GitHub PAT - mgs-agent' --vault 'MGS Conteúdo' --fields github_token --reveal 2>/dev/null)
git push "https://$TOKEN@github.com/mattei2005/mgs-agent.git" main
```
Field name in 1Password: `github_token` (not `credential` or `token`).

## Pitfalls

- **`profiles/atena-soul.md` in repo ≠ `~/.hermes/profiles/atena/SOUL.md`** — always sync via script before committing, or the repo will have stale content.
- **`~/.hermes/` is NOT a git repo** — commits must go to `/root/mgs-agent/`.
- **`sync-souls.sh` only copies if source is newer** — if you manually copied and timestamps are wrong, it may skip. Force with `cp` directly if needed.
- **1Password field is `github_token`**, not `credential` or `password` — wrong field name returns empty token silently.
- **`git push` may say "Everything up-to-date"** if a previous auto-process already pushed — this is not an error, verify with `git log --oneline -3`.

## Reporting format
After completion, report:
- MD5 before / after
- Grep match counts per term
- Commit hash
- Push status
