# Discord cross-agent thread reply scope — agente legado/Ares case (2026-06-20)

## Trigger

Use this when Rodolfo reports that every message in a specific thread wakes two agents, especially when the thread belongs to one agent's channel but another agent has been allowed to participate for handoffs.

Validated case: thread `1517911362280493089` belonged to agente legado's channel, but both agente legado and Ares responded to Rodolfo's normal messages even when he did not mention either bot.

## Root cause pattern

A cross-agent `allowed_channels` grant is safe only if thread mention gating remains enabled for the visiting agent.

Bad effective state observed on Ares:

```text
allowed_channels         own Ares channel + agente legado channel + logs-aquisicao
free_response_channels   own Ares channel + logs-aquisicao
thread_require_mention   false
```

Because Ares had agente legado's channel in `allowed_channels` and `thread_require_mention=false`, any human message inside the agente legado thread was treated as actionable by Ares. agente legado also answered because it owned the thread/channel. This created a dual-response pattern and later a bot-to-bot status loop after handoff messages.

## Correct state

For a visiting agent that may receive explicit handoffs in another agent's channel/thread:

```text
allowed_channels         include the external channel only if needed for handoff
free_response_channels   only the visiting agent's own free-response channels
require_mention          true
thread_require_mention   true
DISCORD_THREAD_REQUIRE_MENTION=true in the active .env if env overrides config
```

Expected behavior after fix:

- Human message in agente legado thread without mentioning Ares → agente legado only.
- Human message directly mentioning Ares → Ares may answer.
- agente legado handoff directly mentioning Ares → Ares may answer.
- Ares must not wake just because the thread is under an allowed agente legado channel.

## Diagnostic checklist

1. Inspect both config and active env for the visiting agent. Runtime `.env` can override the YAML and is often the real cause:

```bash
python3 - <<'PY'
import yaml
for agent in ['legacy-agent','ares']:
    p=f'/root/.hermes/profiles/{agent}/config.yaml'
    c=yaml.safe_load(open(p)) or {}
    d=c.get('discord') or {}
    print(agent, {
        'allowed_channels': d.get('allowed_channels'),
        'free_response_channels': d.get('free_response_channels'),
        'require_mention': d.get('require_mention'),
        'thread_require_mention': d.get('thread_require_mention'),
    })
PY

grep -E '^(DISCORD_ALLOWED_CHANNELS|DISCORD_FREE_RESPONSE_CHANNELS|DISCORD_REQUIRE_MENTION|DISCORD_THREAD_REQUIRE_MENTION)=' \
  /root/.hermes/profiles/ares/.env
```

2. Confirm logs show both agents receiving the same thread ID and responding. Look for `inbound message`, `response ready`, and `Sending response` around the thread ID.

3. After patch + restart, validate the live process env, not just files:

```bash
PID=$(systemctl show -p MainPID --value ares-gateway.service)
tr '\0' '\n' < "/proc/$PID/environ" | grep '^DISCORD_THREAD_REQUIRE_MENTION='
```

Expected: `DISCORD_THREAD_REQUIRE_MENTION=true`.

4. Validate reconnection markers:

```bash
grep -E 'Connected as|discord connected|Gateway running' /root/.hermes/profiles/ares/logs/agent.log | tail -8
```

## Patch pattern

Patch all effective copies when applicable:

- `/root/.hermes/profiles/ares/config.yaml`
- `/root/mgs-agent/profiles/ares-config.yaml`
- `/root/.hermes/profiles/ares/.env` if it defines `DISCORD_THREAD_REQUIRE_MENTION`

Then restart only the affected visiting agent via the safe detached restart helper. Do not restart Zeus/agente legado unless their configs changed.

## Reporting note

Tell Rodolfo the behavior in terms of who should answer next:

```text
Mensagem sua na thread da agente legado sem mencionar ninguém → só agente legado.
Mensagem sua mencionando Ares diretamente → Ares pode responder.
agente legado mencionando Ares em handoff → Ares pode responder.
```

This avoids over-explaining implementation when the operational question is whether the loop will continue.
