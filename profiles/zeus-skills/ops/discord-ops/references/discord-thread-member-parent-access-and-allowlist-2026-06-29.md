# Discord Thread Member Add — Parent Access + Always Allow — 2026-06-29

## Trigger

Rodolfo asked Zeus to add Ially and Geizian to an active Zeus Discord thread. Zeus initially replied incorrectly that it lacked the tool/API path. Rodolfo corrected this strongly.

## Correct operating model

For MGS Discord thread membership requests, Zeus should act, not deflect.

Canonical helper:

```bash
/root/mgs-agent/scripts/discord-add-thread-member.sh --profile zeus --thread <thread_id> --user <user_id>
```

If this returns:

```text
403 Missing Access
```

Do not stop there. The likely issue is that the target user does not yet have access to the parent private channel. Apply a narrow parent-channel permission overwrite first, then retry the thread add.

## Validated sequence

1. Resolve current thread ID from context or Discord API.
2. Search guild members by name if IDs are not already known.
3. For each target user, apply minimal parent-channel overwrite:
   - `VIEW_CHANNEL`
   - `SEND_MESSAGES`
   - `READ_MESSAGE_HISTORY`
   - `SEND_MESSAGES_IN_THREADS`
4. Retry `PUT /channels/{thread_id}/thread-members/{user_id}`.
5. Verify with `GET /channels/{thread_id}/thread-members/{user_id}`.
6. Only report success after:
   - parent overwrite returns `204` when needed;
   - thread member PUT returns `204`;
   - thread member GET returns `200`.
7. Register audit log.

Validated example from session:

```text
Ially    1415413060197290084
Geizian  321263240782807040
Thread   1520998070693924925
Parent   1496267442899521627

parent_permission_put 204
thread_add_put        204
thread_member_get     200
```

## Approval/Always Allow lesson

Rodolfo asked to make the helper command `Always Allow` after approval prompts interrupted the workflow.

Allowlist pattern added for Zeus:

```text
/root/mgs-agent/scripts/discord-add-thread-member.sh --profile zeus --thread * --user *
```

If approval prompts reappear for this exact helper, verify `command_allowlist` in both:

```text
/root/.hermes/profiles/zeus/config.yaml
/root/mgs-agent/profiles/zeus-config.yaml
```

Ad-hoc verification pattern:
- YAML parses.
- Entry appears exactly once.
- Sample command matches via `fnmatch`.

## Pitfall

Do not answer “I cannot add users to the thread” until after attempting the Discord API/helper path. For CCO/ops behavior, the correct response is to resolve access, apply minimal channel/thread permissions, validate, and report concise status.
