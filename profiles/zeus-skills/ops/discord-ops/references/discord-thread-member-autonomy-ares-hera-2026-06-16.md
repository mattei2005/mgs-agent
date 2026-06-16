# Discord thread member autonomy — Ares/Hera rollout (2026-06-16)

## Trigger
Rodolfo showed Ares replying “não consigo adicionar pessoas à thread” after being explicitly authorized to add Kelly. The correct behavior for MGS agents is to execute the Discord API add-member action, not deflect to manual steps, when Rodolfo asks to add an approved person to the current thread.

## Durable pattern
- Use Discord API: `PUT /channels/{thread_id}/thread-members/{user_id}`.
- Confirm success only after `204` on PUT and, when possible, `200` on `GET /channels/{thread_id}/thread-members/{user_id}`.
- Keep the bot token internal. Report only status codes, profile name, thread ID, and user ID/name; never print credentials.
- If Discord returns `403 Missing Access`, report that the bot lacks access to the thread or the user is not in the parent channel; do not say “impossible”.

## Helper added
Canonical helper script:

```
/root/mgs-agent/scripts/discord-add-thread-member.sh --profile <agent> --thread <thread_id> --user <user_id>
```

It sources `/root/.hermes/profiles/<agent>/.env`, calls the Discord API, and verifies the member when possible.

## Profile changes applied
Ares and Hera were configured with:
- `discord.thread_auto_add_users` containing the approved MGS thread participants.
- matching `DISCORD_THREAD_AUTO_ADD_USERS` in `.env`, because runtime env can override config hydration.
- channel prompt instruction to execute the helper on Rodolfo’s natural-language add-member requests.

Approved IDs used in this rollout:
- Rodolfo — `344196393512075265`
- Kelly — `1291113428982693940`
- Geizian — `321263240782807040`
- Icaro — `409878085807112207`
- Isliago — `432898782188011543`
- Joe — `1214246869484576890`
- Nicolas — `1055570806945620030`

## Validation performed
- Current Ares thread `1508906079642456084`, Kelly add: PUT `204`, GET verify `200`.
- Restarted `ares-gateway.service` and `hera-gateway.service`; both active.
- Verified `/proc/<pid>/environ` had `DISCORD_THREAD_AUTO_ADD_USERS` length/count loaded for both profiles.
- Appended audit log event `discord_thread_member_autonomy_granted`.

## Pitfall discovered
Using PyYAML to load/dump full profile configs can create noisy diffs by reformatting unrelated YAML fields. Prefer surgical text patches or restore from backup and reapply a minimal targeted edit before final validation. Auto-commit may capture intermediate diffs, so check recent git history and final live/versioned config equality before reporting completion.
