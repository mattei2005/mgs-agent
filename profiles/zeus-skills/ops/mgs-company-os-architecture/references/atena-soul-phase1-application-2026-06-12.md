# Atena SOUL Phase 1 application — 2026-06-12

## Context

Rodolfo reviewed a shortened Atena SOUL intended to replace the old long rule-heavy prompt. The goal was a SOUL-only alignment: identity, scope, governance, MGS OS precedence, REC+P1 default, authorization, source fidelity, image principles, Discord behavior, Zeus escalation, and layer separation.

No SKILL, contracts, runners, templates, validators, or `AGENT.md` changes were part of this phase.

## Durable lessons

### 1. Validate the final SOUL against the latest human correction before applying

A generated `SOUL-atena-FINAL-2026-06-12.txt` passed syntactic checks and matched the script's expected SHA, but it had drifted back to an older authorization section (`one-time`, `limited`, `full`, `permissions-matrix`). Rodolfo's latest decision was simpler:

- Rodolfo and Raquel can request articles directly.
- Anyone else requesting an article triggers an authorization question to Rodolfo.
- Rodolfo chooses one of three options:
  1. `Uma vez só` — only that request.
  2. `Somente nesta sessão` — requests in the current session/thread.
  3. `Sempre autorizada` — permanent content requester authorization.
- When supported by the interface, present these as three buttons.

Before applying a SOUL package, do content-level checks for the latest correction, not just `bash -n`, SHA, line count, and secret scan.

### 2. Apply SOUL-only changes in live + versioned paths

For Atena the runtime file is:

```text
/root/.hermes/profiles/atena/SOUL.md
```

The versioned mirror is:

```text
/root/mgs-agent/profiles/atena-soul.md
```

`/root/mgs-agent/scripts/sync-souls.sh` syncs runtime → repo only when runtime is newer. Do not rely on it to push repo edits back into runtime. For approved SOUL application, write both paths and validate `cmp` + SHA equality.

### 3. Avoid staging temporary application files under auto-commit paths

A temporary file named `profiles/atena-soul.NOVO.md` was created under `/root/mgs-agent/profiles/`. The auto-commit/auto-push watcher committed it before cleanup, then committed the deletion. This resolved cleanly but created extra Git noise.

Future pattern:

- Keep temporary SOUL inputs in `/tmp/` or another non-repo staging path.
- Only write the final versioned file into `/root/mgs-agent/profiles/` after validation.
- If a temp file does enter the repo, remove it and verify auto-push returns `HEAD == origin/main` and repo clean.

### 4. Validation pattern that worked

Minimum checks before/after applying:

```bash
cmp -s /root/.hermes/profiles/atena/SOUL.md /root/mgs-agent/profiles/atena-soul.md
sha256sum /root/.hermes/profiles/atena/SOUL.md /root/mgs-agent/profiles/atena-soul.md
wc -l /root/.hermes/profiles/atena/SOUL.md
grep -c 'REGRA [0-9]' /root/.hermes/profiles/atena/SOUL.md
grep -n -A16 '^## Quem pode pedir artigo' /root/.hermes/profiles/atena/SOUL.md
systemctl is-active atena-gateway.service
journalctl -u atena-gateway.service --since '2 minutes ago' --no-pager | grep -Ei 'Traceback|ERROR|CRITICAL|Exception|PrivilegedIntentsRequired'
git -C /root/mgs-agent diff --check -- profiles/atena-soul.md
git -C /root/mgs-agent status --short
git -C /root/mgs-agent fetch --quiet origin main
git -C /root/mgs-agent rev-list --count HEAD..origin/main
git -C /root/mgs-agent rev-list --count origin/main..HEAD
```

Record an audit event in `/root/mgs-agent/logs/events-audit.jsonl` with scope explicitly marked `SOUL-only`.

### 5. Fase 2 is a separate gate

Do not bundle deeper production changes with SOUL Phase 1. Archiving templates, removing runner fallbacks, rewriting `AGENT.md`, changing SKILL pointers, contracts, or validators is a separate operational/technical phase requiring its own diff, tests, and Rodolfo approval.
