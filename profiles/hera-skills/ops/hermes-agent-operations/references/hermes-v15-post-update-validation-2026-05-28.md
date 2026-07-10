# Hermes v15 post-update validation — MGS notes from 2026-05-28

## Context

Rodolfo had already completed the Hermes v15 backup and update. The operational task was not to decide whether to update, but to validate the live post-update state and identify next hardening actions.

## Durable workflow correction

When the user says the update is already done, do not keep recommending an update window. Switch immediately to post-update verification.

## Read-only post-update checklist used

```text
1. hermes --version
2. git HEAD vs origin/main in /root/.hermes/hermes-agent
3. systemctl state for zeus-gateway, atena-gateway, ares-gateway
4. git status/diff stat for local MGS patches
5. py_compile critical gateway/Discord files
6. scan for MGS Discord patch capability in new plugin path
7. profile config/auth audit for openai-codex / gpt-5.5 without printing tokens
8. log tail for active gateway errors after restart
9. pytest for changed gateway tests when present
```

## Expected evidence shape

```text
Hermes                       v0.15.0 / up to date
Repo Hermes                  HEAD = origin/main / behind 0
Zeus/Atena/Ares              active
Provider profiles            openai-codex / gpt-5.5
OAuth Codex profiles         present, report only token length/presence
Patches MGS Discord          present in plugin/platform adapter path
Py compile critical          OK
Gateway tests                pass
```

## Pitfall

Do not treat `gateway/platforms/discord.py` missing as patch loss without checking the v15 path migration. In v15 the Discord adapter may live under:

```text
/root/.hermes/hermes-agent/plugins/platforms/discord/adapter.py
```

Validate capability by scanning for MGS patch markers/helpers and compiling the actual file.

## Communication note

If Rodolfo says a checklist item is already being handled elsewhere, skip it and execute the remaining read-only checks. In this session, the REC+P1 dry-run was skipped because the content process was already active.
