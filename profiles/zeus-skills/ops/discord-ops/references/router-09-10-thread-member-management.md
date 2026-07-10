### Adding a user to a private Discord thread

When Rodolfo asks to add Raquel/Kelly/Geizian/Ially/gestor or another approved person to a Zeus/Atena/Ares/Hera thread, **execute it**; do not answer “não consigo” unless API validation proves a real blocker. Use Discord API `PUT /channels/{thread_id}/thread-members/{user_id}`. Do this even when no dedicated `discord_admin` tool is loaded: load the bot token from the active profile `.env` or runtime service environment inside a terminal/shell command, call Discord API directly, and never print the token.

Canonical helper for the normal path:

```bash
/root/mgs-agent/scripts/discord-add-thread-member.sh --profile <agent> --thread <thread_id> --user <user_id>
```

If it returns `403 Missing Access`, diagnose before refusing:
- `GET /channels/{thread_id}` with the posting bot token to confirm thread access.
- Search/confirm the user ID in the guild if only a human name was provided.
- If the user is in the guild but lacks access to the private parent channel, Zeus/admin can set a **minimal parent-channel user overwrite** (`VIEW_CHANNEL + SEND_MESSAGES + READ_MESSAGE_HISTORY + SEND_MESSAGES_IN_THREADS`) and retry the thread-member PUT. Validate `PUT .../thread-members/{user_id}` = `204` and `GET .../thread-members/{user_id}` = `200` before claiming success.

For Zeus, keep this command pattern in `command_allowlist`/Always Allow so routine thread adds do not create approval friction:

```text
/root/mgs-agent/scripts/discord-add-thread-member.sh --profile zeus --thread * --user *
```

Do not claim the thread add succeeded until the API returns `204`; verify with `GET /channels/{thread_id}/thread-members/{user_id}` returning `200` when possible.

Zeus-specific correction validated: if the helper returns `403 Missing Access` because the user is not in the parent private channel, apply a narrow parent-channel overwrite for the user first (`VIEW_CHANNEL`, `SEND_MESSAGES`, `READ_MESSAGE_HISTORY`, `SEND_MESSAGES_IN_THREADS`), then retry the helper/API add. Confirm success only after parent overwrite `204` when needed, thread-member PUT `204`, and member GET `200`. Rodolfo expects Zeus to resolve this path, not answer that it cannot add people. For exact reproduction and allowlist details, see `references/discord-thread-member-parent-access-and-allowlist-2026-06-29.md`.

For Zeus, this helper should be in `command_allowlist` as:

```text
/root/mgs-agent/scripts/discord-add-thread-member.sh --profile zeus --thread * --user *
```

Operational correction validated on Hera and Ares: if the agent replied “não consigo adicionar pessoas na thread”, fix the profile so future requests are executable, not just manually handled once:

```yaml
command_allowlist:
- /root/mgs-agent/scripts/discord-add-thread-member.sh --profile zeus --thread * --user *
```

Validate via ad-hoc `/tmp/hermes-verify-*` script: YAML parses, entry appears exactly once in active + versioned Zeus config, and a representative command matches the glob. This is not suite green.

Operational correction validated on Hera and Ares: if the agent replied “não consigo adicionar pessoas na thread”, fix the profile so future requests are executable, not just manually handled once:
- Add the explicit user IDs to `discord.thread_auto_add_users` in `config.yaml` for automatic inclusion in new threads.
- If `.env` already defines `DISCORD_THREAD_AUTO_ADD_USERS`, update `.env` too; runtime env takes precedence over config hydration (`config.yaml` only sets env when the env var is absent).
- Add a short channel prompt/SOUL rule: on Rodolfo’s natural-language “adiciona X na thread”, call `/root/mgs-agent/scripts/discord-add-thread-member.sh --profile <agent> --thread <thread_id> --user <user_id>` or the equivalent Discord API directly, and confirm only after HTTP 204/GET 200; on 403, report Missing Access/parent-channel access needed.
- Restart the affected gateway and verify `systemctl is-active`, `Connected as ...`, `✓ discord connected`, and that `/proc/<pid>/environ` has the updated auto-add env value length/count without printing secrets.
- Record the authorization/profile change in `events-audit.jsonl` and check live config equals versioned config before reporting completion.

Pitfall: avoid rewriting full `config.yaml` with PyYAML for small profile edits unless necessary; it can reformat unrelated fields and generate noisy auto-commits. Prefer targeted patches, or restore from backup and reapply minimal textual edits before final validation. Auto-push/auto-commit may capture intermediate config states, so inspect recent commits/status if the edit was iterative.

Session reference: `references/discord-thread-member-autonomy-ares-hera-2026-06-16.md`.


#### Conferência pós-update/restart não é só “online”

Quando Rodolfo pedir para “conferir tudo de novo” após update, limpeza ou restart Hermes, não responder apenas que gateways estão `active/running`. Se a preocupação declarada for perda de configuração/patch local, validar e reportar explicitamente a recuperação da superfície local:
- comparar todos os markers/funções do `pre-local-diff.patch` e `pre-local-diff-cached.patch` contra o runtime vivo;
- rodar `ensure-hermes-mgs-patches.sh`, `py_compile` e testes alvo;
- separar `runtime íntegro` de `higiene de patch artifact`;
- dizer claramente quantos markers foram conferidos e quantos faltam, ex.: `35/35 OK, missing=0`.

Pitfall validado: responder “Zeus/Atena/Ares/Hera online” quando Rodolfo perguntou se “recuperou tudo que estava fora” é incompleto e irrita, porque ele já sabe que os serviços estão online; a pergunta é sobre integridade dos patches/configs locais.

