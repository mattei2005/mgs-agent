# Discord provider retry noise filter — Codex TTFB / retry chatter

## Trigger

Use this reference when Rodolfo reports that Zeus/Atena posts technical provider status messages into Discord threads, especially messages like:

- `⏳ Retrying in Xs (attempt 1/3)...`
- `⚠️ No first byte from provider in 45s (codex stream, model: gpt-5.5). Reconnecting.`
- `⏱️ Rate limited. Waiting ...`
- auxiliary/compression failure chatter that is useful in logs but noisy in chat

## Operational distinction

These messages are usually **transient provider/gateway status callbacks**, not the final answer and not necessarily a task failure. The retry should remain active internally, but routine retry/status chatter should not be sent to Discord threads because it creates noise and makes every user message look broken.

## Durable fix pattern

Patch the gateway status-filter path, not the model config:

- File: `/root/.hermes/hermes-agent/gateway/run.py`
- Function: `_prepare_gateway_status_message(platform, event_type, message)`
- Existing pattern: Telegram already suppresses noisy status via a regex.
- MGS desired behavior: apply the same suppression to Discord for transient noise while preserving normal final responses and local diagnostics.

Recommended code shape:

```python
platform_value = _gateway_platform_value(platform)
if platform_value not in {"telegram", "discord"}:
    return text

text = _redact_gateway_user_facing_secrets(text)
if _MOBILE_CHAT_NOISY_STATUS_RE.search(text):
    return None
if platform_value == "telegram" and _looks_like_gateway_provider_error(text):
    return _gateway_provider_error_reply(text)
return text
```

Add `no first byte from provider in \d` to the noisy-status regex alongside `retrying in \d`, `rate limited. waiting`, and auxiliary/compression failure patterns.

## Tests to update/run

- File: `/root/.hermes/hermes-agent/tests/gateway/test_telegram_noise_filter.py`
- Broaden the noisy-status suppression test to assert both `Platform.TELEGRAM` and `Platform.DISCORD` return `None` for retry/TTFB chatter.
- Keep local/non-chat status unchanged.

Validation:

```bash
cd /root/.hermes/hermes-agent
venv/bin/python -m py_compile gateway/run.py tests/gateway/test_telegram_noise_filter.py
venv/bin/python -m pytest tests/gateway/test_telegram_noise_filter.py -q
```

## Restart/validation

After patching, restart affected gateways and validate `Connected as ...`, `✓ discord connected`, and `Gateway running with 1 platform(s)` in each profile log.

Be careful with Zeus: restarting `zeus-gateway.service` during an active turn can enter `deactivating/stop-sigterm` while it drains the current response. Do not declare failure immediately; check `systemctl show -p ActiveState -p SubState -p MainPID` and wait for reconnect logs.

## Reporting to Rodolfo

Report the distinction clearly:

- The provider retry still happens internally.
- The noisy intermediate retry messages no longer appear in Discord.
- The model/provider was not changed.
- Include validation evidence and any restart still draining.
