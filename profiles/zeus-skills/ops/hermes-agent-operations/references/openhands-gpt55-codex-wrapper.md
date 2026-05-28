# OpenHands + GPT-5.5/OpenAI-Codex OAuth — MGS pattern

## Trigger

Use this reference when Atena/Zeus/OpenHands must run coding-agent work under the MGS provider policy: GPT-5.5/OpenAI-Codex OAuth by default; no Anthropic/Claude/Haiku/OpenRouter/other provider unless Rodolfo explicitly approves an exception.

## Durable lesson

OpenHands can appear "fixed" while actually running through an unauthorized provider. In the observed case, a wrapper used `anthropic/claude-sonnet-*` with a 1Password API key after the Atena Codex OAuth profile was broken. That solved the immediate task but violated MGS cost/governance policy.

Correct response:

1. Restore/validate the target Hermes profile's `openai-codex` OAuth auth.
2. Do **not** switch to Anthropic/Claude/other providers as a workaround.
3. Make the OpenHands wrapper force GPT-5.5/OpenAI-Codex.
4. Verify the actual runtime model from OpenHands output/trajectory, not just exit code.
5. Register the decision in audit log without secrets.

## Wrapper shape

The wrapper should:

- read `/root/.hermes/profiles/<profile>/auth.json` for provider `openai-codex`;
- export the OAuth `access_token` only into process env; never print it;
- set `LLM_MODEL=openai/gpt-5.5`;
- set `LLM_BASE_URL=https://chatgpt.com/backend-api/codex`;
- block/ignore caller attempts to steer to `anthropic`, `claude`, `haiku`, OpenRouter, or any other provider unless there is explicit Rodolfo approval;
- use an isolated OpenHands persistence dir if needed so stale agent settings do not preserve an old provider.

## OpenHands/Codex compatibility quirks

OpenHands/LiteLLM may require compatibility handling for the ChatGPT Codex backend:

- Codex backend requires streaming.
- Some OpenHands headless paths may call streaming without an `on_token` callback.
- Codex rejects unsupported params such as `max_output_tokens`, `temperature`, reasoning/include params in subscription mode.
- Env override paths may not preserve OpenHands private subscription flags.

If a local compatibility patch is needed, capture it as an idempotent script (for example `scripts/patch-openhands-gpt55-codex.sh`) and run it after OpenHands reinstalls/upgrades. The patch should make the Codex backend behave as subscription mode and add no-op token callbacks where headless mode lacks them.

## Verification gate

Do not claim OpenHands is ready unless validation proves all three:

- output contains `Agent initialized with model: openai/gpt-5.5` (strip ANSI before matching);
- output contains an agent `MessageEvent` or final agent message with the expected sentinel (for smoke: `OPENHANDS_OK`);
- output contains no `ConversationErrorEvent`.

Exit code alone is insufficient: OpenHands can return `0` after rendering a conversation summary even when the LLM call failed earlier.

## Reporting to Rodolfo

Use a short executive block:

```text
Atena / OpenHands
-----------------
Modelo obrigatório     openai/gpt-5.5
Auth                   OpenAI-Codex OAuth da Atena
Anthropic/Claude       bloqueado
OpenRouter/outros      bloqueado salvo autorização explícita
Smoke test             OK/FAIL — evidence
Commit/local patch     <short id or file>
```

Always include `Próximo passo pendente:` when a validation/push/monitoring step remains.
