# MGS controlled Hermes update rule

This is the permanent MGS rule for Hermes Agent updates approved by Rodolfo: no Hermes update is considered complete until the pre-update state is backed up, compared against the post-update state, and MGS-critical invariants are validated.

## Rule

Never update Hermes "over the top" without this sequence:

1. Backup profiles and operational state.
2. Save pre-update Git state: HEAD, origin/main, behind/ahead, status, local diff and untracked list.
3. Save sanitized profile config/auth presence for Zeus, Atena, Ares and agente legado; never print tokens.
4. Check canonical MGS patches against upstream in a temporary worktree before mutating the live checkout.
5. Update Hermes.
6. Compare post-update Git/config/runtime state against the pre-update artifacts.
7. Run `/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh` and fail closed if a critical invariant is missing.
8. Compile critical files touched by Discord/gateway/tools patches.
9. Validate gateway/systemd state and logs.
10. Write `final-report.md` before any gateway restart, because restarting Zeus can terminate the current turn before a Discord reply is delivered.
11. Send the final/failure report directly to the update-review Discord thread from the script using the bot token; do not rely only on the interrupted Zeus turn.
12. Restart gateways only when the update path explicitly includes restart approval; otherwise report that new code is staged but not active in running gateways.
13. On recovery after a restart checkpoint, do not re-run update/restart; read the latest update artifact and deliver the final report in the thread.
14. Produce an artifact directory with report/evidence files.

## Critical MGS surface

```text
Area                         Preserve/validate
---------------------------- ----------------------------------------
Profiles                     config.yaml, SOUL.md, auth presence sanitized
Gateways                     Zeus, Atena, Ares, agente legado systemd units
Discord                      thread titles, bot loop guard, auto-add, REPORT-INFRA inline
Restart                      planned restart resume, anti-reexecution checkpoints
Providers                    GPT-5.5/OpenAI-Codex default, zero Claude unless approved
Tools                        web tooling, file tools cwd, terminal behavior
Crons                        root crontab + Hermes cron inventory
Patches locais               /root/mgs-agent/patches/hermes/
Scripts MGS                  ensure-hermes-mgs-patches.sh and update reports
Telegram                     não crítico na MGS; sem backup/teste dedicado salvo impacto compartilhado
```

Detalhe operacional da decisão Telegram + port canônico 2026-07-04: `references/hermes-update-telegram-noncritical-and-20260704-port.md`.

## Standard command

Precheck/dry-run evidence without mutating live checkout:

```bash
PRECHECK_ONLY=1 /root/mgs-agent/scripts/run-hermes-update-controlled.sh
```

Controlled update without gateway restart:

```bash
RESTART_GATEWAYS=0 /root/mgs-agent/scripts/run-hermes-update-controlled.sh
```

Controlled update with gateway restart after validation:

```bash
RESTART_GATEWAYS=1 /root/mgs-agent/scripts/run-hermes-update-controlled.sh
```

If the upstream patch dry-run reports drift, the script fails closed before mutation. Only set this after manual review/porting confirms the drift is acceptable:

```bash
ALLOW_PATCH_DRIFT=1 RESTART_GATEWAYS=0 /root/mgs-agent/scripts/run-hermes-update-controlled.sh
```

Artifacts are written to:

```text
/root/mgs-agent/reports/hermes-updates/<timestamp>/
```

Minimum evidence expected:

```text
pre-revisions.txt
pre-git-status.txt
pre-local-diff.patch
pre-upstream-patch-check.txt
pre-profiles-sanitized.txt
post-revisions.txt
post-git-status.txt
post-local-diff-stat.txt
patch-guard.log
py-compile.log
post-systemd-active.txt
final-report.md
```

## Failure policy

Fail closed when:

- backup is missing or empty;
- patch guard fails;
- critical files do not compile;
- post-update HEAD/behind state is inconsistent;
- a critical MGS invariant disappears;
- gateway restart was requested but services do not return active.

If a patch does not apply cleanly to upstream but invariants are already present, treat as controlled/manual drift: report it explicitly and validate by invariant checks + py_compile before any restart.

## Reporting shape

Use Discord-safe aligned `text` blocks, not raw Markdown tables. The final update report must include:

```text
Item                    Estado
----------------------  --------------------------------
Backup                  path + size
Repo                    pre HEAD -> post HEAD, behind
Patch MGS               OK/fail + log path
Config/Auth             GPT-5.5/OpenAI-Codex presence, sanitized
Gateways                active states, restart yes/no
Pendências              explicit next action or none
```
