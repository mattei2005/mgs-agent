# GPT-5.6 Sol automatic reasoning routing — MGS

Use when Rodolfo wants Zeus/Atena/Ares/Hera to choose reasoning depth automatically while keeping `gpt-5.6-sol` as the principal model.

## Runtime contract

- Principal model: `openai-codex/gpt-5.6-sol`.
- Simple conversational requests: `medium`.
- Normal operational requests: `high`.
- Critical/long/code-heavy requests: `xhigh` (ChatGPT UI equivalent of Extra High).
- Explicit `/reasoning <level>` session overrides always win over automatic routing.
- `gpt-5.6-sol-pro` is not assumed available. Validate the live Codex model list before offering Pro.

Profile config:

```yaml
agent:
  reasoning_effort: high
  reasoning_auto_routing:
    enabled: true
    simple_effort: medium
    default_effort: high
    critical_effort: xhigh
    simple_char_threshold: 180
    critical_char_threshold: 1200
```

Implementation:

- `/root/.hermes/hermes-agent/gateway/reasoning_router.py` contains the deterministic, side-effect-free router.
- `GatewayRunner._resolve_turn_reasoning_config()` applies it per message.
- The router runs after session override resolution and before `agent.reasoning_config` is assigned.
- It does not make an extra LLM call or alter the prompt, preserving latency and prompt-cache stability.
- Safety order: critical markers / long payload / code-heavy payload are evaluated before the short-message fast path, so terse production commands are never downgraded.

Canonical patch and guard:

- `/root/mgs-agent/patches/hermes/mgs-auto-reasoning-routing.patch`
- `/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh`
- `/root/mgs-agent/scripts/run-hermes-update-controlled.sh`

Required validation:

1. `git apply --reverse --check mgs-auto-reasoning-routing.patch` against the live checkout.
2. `git apply --check` against an `origin/main` worktree before Hermes updates.
3. `py_compile gateway/run.py gateway/reasoning_router.py`.
4. `pytest tests/gateway/test_auto_reasoning_routing.py tests/gateway/test_reasoning_command.py`.
5. Read back live + mirror configs for all four profiles.
6. Restart gateways safely with Zeus last, then run real smoke calls.

## OAuth prerequisite

A profile pointing to `openai-codex` is not operational merely because systemd is active. Validate each profile with a real `hermes -p <agent> -z ...` call. If OAuth is missing/invalid, back up `auth.json` outside Git, copy only a known-working `openai-codex` provider block after critical confirmation, preserve the intended `active_provider`, and repeat the smoke test.
