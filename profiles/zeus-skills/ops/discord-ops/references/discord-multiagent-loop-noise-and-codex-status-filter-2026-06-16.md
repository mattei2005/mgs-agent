# Discord multi-agent loop noise + Codex status filter — 2026-06-16

## Incident class

Shared Discord thread with multiple MGS bots (Ares/Hera) looped after the actual task was complete. The original cross-agent handoff was legitimate, but subsequent bot-originated acknowledgements and provider/runtime notices kept waking the other bot because `DISCORD_ALLOW_BOTS=mentions` allowed bot messages when the receiving bot was mentioned.

Observed thread: `1516587465735934093`.

Noise that must not wake another agent:

- `Sem ação pendente`
- `Sem ação`
- `Silêncio operacional`
- `Recebido`, `Confirmado`, `Encerrado`, `Fechado`
- Emoji-only acknowledgements such as `👍`, `✅`, `👌`
- `⚠️ Empty response from model — retrying`
- `❌ Model returned no content after all retries. No fallback providers configured.`
- `Codex response remained incomplete after 3 continuation attempts`
- `⚠️ Processing stopped: Codex response remained incomplete ...`

## Correct fix pattern

Do not disable bot-to-bot handoff globally; Ares/Hera still need explicit mentions for legitimate cross-agent routing.

Patch the Discord adapter to add a narrow pre-`DISCORD_ALLOW_BOTS` filter for bot-originated low-information messages:

- only applies to `message.author.bot == True`;
- preserves messages with attachments or embeds;
- strips Discord mentions/channels before normalization;
- blocks exact low-information markers and known provider/status prefixes;
- lets substantive handoffs through when explicitly mentioned.

Runtime patch points:

- `/root/.hermes/hermes-agent/plugins/platforms/discord/adapter.py`
  - helper: `_is_discord_bot_loop_noise(...)`
  - call inside `on_message(...)`, before evaluating `DISCORD_ALLOW_BOTS`.
- `/root/.hermes/hermes-agent/gateway/run.py`
  - extend `_MOBILE_CHAT_NOISY_STATUS_RE` for Discord-visible provider/status noise.
  - pass `platform=source.platform` into `_normalize_empty_agent_response(...)`.
  - suppress Discord final response for `agent_result.partial` when error contains `Codex response remained incomplete`.

Canonical local patch recorded at:

`/root/mgs-agent/patches/hermes/discord-multiagent-loop-noise-and-codex-status-filter.patch`

## Validation commands

Run from `/root/.hermes/hermes-agent`:

```bash
venv/bin/python -m py_compile \
  plugins/platforms/discord/adapter.py \
  gateway/run.py \
  tests/gateway/test_discord_bot_filter.py \
  tests/gateway/test_telegram_noise_filter.py

venv/bin/python -m pytest \
  tests/gateway/test_discord_bot_filter.py \
  tests/gateway/test_telegram_noise_filter.py \
  -q
```

Expected validated result for this incident: `19 passed, 6 subtests passed`.

After patching Ares/Hera runtime, restart only affected gateways via the safe detached restart helper:

```bash
/root/mgs-agent/scripts/mgs-gateway-restart-safe.sh \
  --agents "ares hera" \
  --reason "urgent-discord-multiagent-loop-noise-filter" \
  --delay 2 \
  --execute
```

Verify:

- `systemctl show ares-gateway.service hera-gateway.service -p ActiveState -p SubState -p MainPID -p ExecMainStartTimestamp`
- agent logs contain fresh `Connected as ...`, `✓ discord connected`, `Gateway running with 1 platform(s)`.

## Reporting guidance

Report to Rodolfo in executive terms:

- Distinguish the legitimate handoff from the post-completion loop.
- Explain Codex incomplete/no-content notices as runtime/provider diagnostics, not actionable Discord messages.
- State whether the fix preserves real cross-agent mentions.
- State test result and gateway status.

Do not paste token values, raw stack traces, or long journal output into Discord.