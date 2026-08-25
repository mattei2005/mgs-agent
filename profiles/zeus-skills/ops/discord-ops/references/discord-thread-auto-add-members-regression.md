# Discord thread auto-add members regression

## Trigger

Use this when an MGS agent still creates Discord threads but no longer adds the expected people automatically, especially when one profile serves parent channels with different audiences (team vs. private/director).

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

- `/root/.hermes/hermes-agent/plugins/platforms/discord/adapter.py`
- `_auto_create_thread(...)` creates the thread; `_auto_add_parent_channel_members_to_thread(...)` performs deterministic membership sync immediately afterward.
- Inspect `_discord_thread_auto_add_user_ids(...)`, `DISCORD_THREAD_AUTO_ADD_USERS_BY_CHANNEL`, `DISCORD_THREAD_AUTO_ADD_USERS`, `thread.add_user`, and the `Auto-thread member sync` log marker.
- If the runtime has no member-sync call after thread creation, member addition cannot be guaranteed by config alone.

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
- Keep auto-add logic scoped to newly created threads so follow-ups/old threads do not re-run membership logic.
- Treat "respective people in the agent channel" as the agent's operational membership, not all guild members:
  - Atena/content threads: Raquel Oliveira (`1496254952501280974`) + Rodolfo Mattei (`344196393512075265`).
  - Zeus/admin threads: Rodolfo Mattei only, unless a future admin user is explicitly authorized for that channel.
  - Prefer sourcing this mapping from `/root/mgs-agent/data/authorized-users.json` and/or the profile's explicit config; never auto-add every guild/channel-visible member.
- Bootstrap script should do both actions in one `execute_code` call: `PATCH /channels/{THREAD_ID}` for rename, then idempotent `PUT /channels/{THREAD_ID}/thread-members/{USER_ID}` for each required user.
- Use `os.environ.get('DISCORD_BOT_TOKEN')`; never hardcode or print credentials.
- Log only counts/user IDs/names, not headers.
- After changing profile config, update both the live profile (`/root/.hermes/profiles/{agent}/config.yaml`) and the versioned copy (`/root/mgs-agent/profiles/{agent}-config.yaml`), validate YAML, then restart the affected gateway and verify `Connected as ...` + `Gateway running with 1 platform(s)`.
- For the already-broken test thread, manually add the missing user with the same `PUT thread-members` endpoint and verify `GET /channels/{THREAD_ID}/thread-members` shows the expected count.

More robust repair — required when one profile serves channels with different audiences:

- Implement deterministic post-create member addition immediately after `_auto_create_thread(...)`; do not depend on an LLM prompt running later.
- Keep `discord.thread_auto_add_users` only as the legacy profile-wide fallback.
- Add `discord.thread_auto_add_users_by_channel` as an explicit parent-channel mapping. Precedence must be:
  1. exact parent-channel entry;
  2. legacy profile-wide list;
  3. broad guild-member discovery only when neither source was configured.
- An explicit empty list is meaningful and must **fail closed**. Never interpret `[]` or an intentionally empty runtime value as permission to discover/add every visible guild member.
- If the adapter remains env-driven internally, hydrate the YAML mapping as JSON into `DISCORD_THREAD_AUTO_ADD_USERS_BY_CHANNEL`; keep YAML as the public configuration surface.
- For Ares, apply the active institutional policy `ARES-DISCORD-ZEUS-ALL-THREADS-V1` from `context/ares-operational-map.md`: Zeus (`1496296175014252634`) is mandatory in every Ares-created thread, including Diretoria and every future parent channel. Per-channel manager lists are additive and must never replace Zeus.
- Every new Ares parent-channel onboarding must add Zeus to that channel's explicit `thread_auto_add_users_by_channel` entry before activation; an explicit empty list is no longer valid for an Ares channel while this policy is active.
- Explicit configured targets may be bots. Keep filtering bots during broad guild discovery, but honor another MGS agent bot when its ID is explicitly configured; exclude only the current profile's own bot. Preserve this behavior in the Hermes patch guard and a targeted regression test.
- Update live + versioned profile configs, preserve the runtime patch artifact and patch guard, and take a rollback snapshot before restart.
- Regression tests must prove: channel-specific lists win over global fallback; Ares mappings always retain Zeus; manager lists remain additive; explicitly configured peer-agent bots are honored; broad discovery still filters bots.
- Validate config hydration/type, targeted tests, patch guard, detached safe restart, new process env without printing secrets, and a real thread-member API readback when a new operational thread is available.

## Safety notes

- Do not restore broad, long prompt scripts blindly if the original simplification was done to reduce REC latency or bot loops.
- Avoid auto-adding all guild members. Prefer explicit user IDs or role-based eligibility with clear audit output.
- Do not use one global auto-add list when the same profile has both team and private/director channels; that either leaks managers into private threads or silently disables the team channel.
- Diagnose the exact layer separately: authorization, parent visibility, thread membership, config hydration and active process state are different controls.
- Do not mention another bot in shared Rodolfo threads unless explicitly asked; membership and notification are separate concerns.
