# Discord thread auto-add members regression (Atena/Zeus)

## Trigger

Use this when Rodolfo reports that Atena/Zeus still creates Discord threads but no longer adds people to those threads automatically.

## Durable lesson

The Hermes Discord gateway auto-thread path creates threads, but does not add arbitrary guild members to them by default. In the MGS setup, automatic member-addition previously came from an agent `channel_prompts` bootstrap script that the agent executed via `execute_code`, not from the core gateway.

If people stop being added, diagnose prompt/config history before blaming Discord permissions.

## What to inspect

Current profile config:

```bash
python3 - <<'PY'
import yaml
for p in ['/root/.hermes/profiles/atena/config.yaml','/root/.hermes/profiles/zeus/config.yaml']:
    data=yaml.safe_load(open(p))
    d=data.get('discord',{})
    print('\n##', p)
    print('allowed_channels:', d.get('allowed_channels'))
    print('auto_thread:', d.get('auto_thread'))
    print('thread_require_mention:', d.get('thread_require_mention'))
    print('channel_prompts keys:', list((d.get('channel_prompts') or {}).keys()))
    for cid, prompt in (d.get('channel_prompts') or {}).items():
        print('---', cid)
        print(prompt[:2000])
PY
```

Gateway thread creation code:

- `/root/.hermes/hermes-agent/gateway/platforms/discord.py`
- `_auto_create_thread(...)` normally calls `message.create_thread(...)` or a fallback seed message then `seed_msg.create_thread(...)`.
- The gateway path should be inspected for `thread.add_user`, `thread-members`, or equivalent `PUT /channels/{THREAD_ID}/thread-members/{uid}`. If absent, member-addition is not happening in core.

Historical prompt/config evidence:

```bash
git -C /root/mgs-agent show <commit> -- profiles/atena-config.yaml | grep -n -E 'auto-discover|thread-members|renomear thread|members|channel_prompts' -C 3
```

Known MGS regression point from 2026-05-17:

- Commit `a2a70e1...` replaced the old Atena `channel_prompts` bootstrap with an enxuto prompt.
- The removed prompt said: `renomear thread + adicionar membros automaticamente via execute_code`.
- The removed script discovered roles/members and called:

```text
PUT /channels/{THREAD_ID}/thread-members/{uid}
```

The current prompt after that change only renames the thread via:

```text
PATCH /channels/{THREAD_ID}
```

## Runtime verification via Discord API

Without exposing tokens, query the thread and members using `DISCORD_BOT_TOKEN` from environment. Report only IDs/counts, never token/header values.

Expected failure symptom:

```text
member_count: 2
members: [Rodolfo, bot owner]
```

That confirms the user and bot are in the thread, but no extra eligible members were added.

## Diagnosis phrasing

Use this conclusion shape:

```text
Parou por mudança de configuração/prompt, não por bug do Discord.
Antes a própria Atena executava um script de auto-discover + PUT thread-members.
Agora o prompt só renomeia a thread. O gateway Hermes cria a thread, mas não adiciona membros extras.
```

## Repair options

Fast restoration:

- Reintroduce a bounded `channel_prompts` bootstrap for **new threads only**.
- Keep the `rename-on-create, then freeze` rule so follow-ups/old threads do not re-run membership logic.
- Use `os.environ.get('DISCORD_BOT_TOKEN')`; never hardcode or print credentials.
- Log only counts/user IDs/names, not headers.

More robust repair:

- Implement deterministic post-create member-addition in the Discord gateway/runtime after `_auto_create_thread(...)`.
- Configure explicit allowed users/roles per profile/channel, e.g. `thread_auto_add_users` and later `thread_auto_add_roles`.
- Validate with a real new test thread and `GET /channels/{THREAD_ID}/thread-members`.

## Safety notes

- Do not restore broad, long prompt scripts blindly if the original simplification was done to reduce REC latency or bot loops.
- Avoid auto-adding all guild members. Prefer explicit user IDs or role-based eligibility with clear audit output.
- Do not mention another bot in shared Rodolfo threads unless explicitly asked; membership and notification are separate concerns.
