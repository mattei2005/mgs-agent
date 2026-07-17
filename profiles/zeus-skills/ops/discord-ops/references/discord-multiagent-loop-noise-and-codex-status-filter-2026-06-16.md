# Discord multi-agent loop noise + Codex status filter — 2026-06-16

## Incident

Thread `1516587465735934093` looped between Ares and agente legado after the real handoff was already complete. The pattern repeated an older Zeus↔Atena class of incident: bot-to-bot mentions are necessary for cross-agent routing, but low-information acknowledgements/status messages can wake the peer bot and create a ping-pong.

Observed messages included:
- `Sem ação pendente`
- `Silêncio operacional`
- emoji-only acknowledgements such as `👍`
- `Empty response from model — retrying`
- `Model returned no content after all retries`
- `No fallback providers configured`
- `Codex response remained incomplete after 3 continuation attempts`

## Root cause

`DISCORD_ALLOW_BOTS=mentions` correctly allows bot messages when the destination agent is mentioned. That is needed for explicit handoffs (ex: Ares asking agente legado to move/validate a Drive asset). However, mention-gating alone is not enough: once the task is complete, acknowledgement/status messages can still include or trigger bot-visible context, causing the other gateway to process them as new input.

## Fix applied

Runtime files:
- `/root/.hermes/hermes-agent/plugins/platforms/discord/adapter.py`
- `/root/.hermes/hermes-agent/gateway/run.py`

Patch record:
- `/root/mgs-agent/patches/hermes/discord-multiagent-loop-noise-and-codex-status-filter.patch`

Behavior:
1. Discord adapter runs `_is_discord_bot_loop_noise(...)` before `DISCORD_ALLOW_BOTS` routing.
2. It suppresses only bot-originated, low-information text with no attachments/embeds.
3. It preserves substantive handoffs with real instructions or payloads.
4. Gateway status filtering suppresses Codex retry/incomplete/no-content notices on Discord while keeping them in logs.
5. Partial final response `Codex response remained incomplete...` returns empty on Discord instead of posting a loop-triggering warning.

## Validation

Commands:

```
cd /root/.hermes/hermes-agent
venv/bin/python -m py_compile plugins/platforms/discord/adapter.py gateway/run.py tests/gateway/test_discord_bot_filter.py tests/gateway/test_telegram_noise_filter.py
venv/bin/python -m pytest tests/gateway/test_discord_bot_filter.py tests/gateway/test_telegram_noise_filter.py -q
```

Expected result from incident fix:
- `19 passed, 6 subtests passed`

Operational restart:

```
/root/mgs-agent/scripts/mgs-gateway-restart-safe.sh --agents "ares legacy-agent" --reason "urgent-discord-loop-fix-no-content-notice-extension" --delay 2 --execute
```

Post-restart evidence:
- Ares active/running, connected as Ares
- agente legado active/running, connected as agente legado

## Rule going forward

For any MGS multi-agent thread:
- user mention is for explicit handoff only;
- no-action confirmations, emoji-only replies, lifecycle notices, model retry/status notices and empty-response diagnostics must not wake another bot;
- after a final state is accepted, the correct bot behavior is silence until Rodolfo gives a new request or a real operational alert exists.
