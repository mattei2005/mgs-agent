# GPT-5.6 Sol automatic reasoning routing — MGS

Use when Rodolfo wants Zeus/Atena/Ares/agente legado to choose reasoning depth automatically while keeping `gpt-5.6-sol` as the principal model.

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
- Apply the decision in both the principal gateway turn and background-task path. On cached-agent reuse, assign the routed value to `agent.reasoning_config` again for that turn.
- Keep `reasoning_config` out of `_agent_config_signature`: it does not change the system prompt or tool schemas. For Codex Responses, `medium`/`high`/`xhigh` must keep the same content-addressed `prompt_cache_key`; only `reasoning.effort` changes.
- This is a conservative current-message heuristic, not full semantic classification: it does not inspect conversation history or re-evaluate after tools. Subagents inherit the parent turn effort unless `delegation.reasoning_effort` overrides it.
- `codex_app_server` currently does not forward effort in `turn/start`; scope initial MGS validation to `codex_responses`.

## Guardrails and UX semantics

- Parse numeric thresholds with safe defaults and clamps. Invalid strings or YAML `null` must never raise `ValueError`/`TypeError` in the message path.
- Disabled or malformed auto-routing must fail closed to the profile default.
- Explicit session `/reasoning <level>` wins; `/reasoning reset` resumes automatic routing.
- Define `/reasoning <level> --global` honestly: with auto-routing enabled, either disable auto-routing or state that the global value changed only the fallback. Do not claim all turns are pinned.
- `/reasoning` status must expose that Auto is active; reporting only `high/global` is misleading when the next turn may route to `medium` or `xhigh`.
- A session `/model` override can select a backend that rejects `xhigh`. Clamp by the active model/provider capability or fall back to its configured effort.
- The base `gpt-5.6-sol` may itself advertise `low`, `medium`, `high`, `xhigh`, `max`, and `ultra`; in that case Extra High is `xhigh` and does not require a `*-pro` slug. Treat missing Pro variants as a separate Codex catalog/picker issue.

## Read-only audit with concurrent working-tree changes

- Record `git status` at the beginning and end.
- If new files/diffs appear during the audit, treat them as concurrent work: inspect and test read-only, but do not overwrite or claim authorship.
- Report which files pre-existed, which appeared during the audit, and whether the auditor changed any source/config.

Canonical patch and guard:

- `/root/mgs-agent/patches/hermes/mgs-auto-reasoning-routing.patch`
- `/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh`
- `/root/mgs-agent/scripts/run-hermes-update-controlled.sh`

Required validation:

1. `git apply --reverse --check mgs-auto-reasoning-routing.patch` against the live checkout.
2. `git apply --check` against an `origin/main` worktree before Hermes updates.
3. `py_compile gateway/run.py gateway/reasoning_router.py`.
4. `pytest tests/gateway/test_auto_reasoning_routing.py tests/gateway/test_reasoning_command.py`.
5. Add behavior tests for malformed/`null` thresholds, session-override precedence, reset-to-auto, provider/model capability clamp, and both principal/background integration paths.
6. Assert cache invariants explicitly: same cached `AIAgent`, frozen system prompt, and same `prompt_cache_key` across `medium`, `high`, and `xhigh`.
7. Read back live + mirror configs for all four profiles.
8. Restart gateways safely with Zeus last, then run real smoke calls. Separate unrelated pre-existing suite failures from routing regressions.
9. If Zeus restarts, use an external finalizer that validates new PIDs/services and posts a clean callback to the originating thread. A file-only log or `systemctl active` without delivery is not completion; auto-resume may fail even when restart succeeds.

## OAuth prerequisite

A profile pointing to `openai-codex` is not operational merely because systemd is active. Validate each profile with a real `hermes -p <agent> -z ...` call.

Do not treat copying an `openai-codex` provider block between profiles as a durable fix. Codex refresh tokens rotate and are single-use; cloned profiles can later race and produce `refresh_token_reused`. Copying may be used only as a time-boxed emergency recovery after Rodolfo's critical confirmation, followed by independent OAuth sessions per profile or a genuinely shared auth store with cross-process locking and refresh write-through. Never print token values or commit `auth.json`.

## Finalizer and restart pitfalls

- Detached `systemd-run` units do not inherit the interactive PATH. Use `/root/.local/bin/hermes` for smoke tests.
- A Zeus self-restart remains `deactivating` until the active Discord turn exits. A finalizer polling during that turn can falsely report `service zeus not ready`; respond before scheduling and let the active turn finish.
- Validate all four services and all four real inference smokes. Service state alone is insufficient.

## Explicit override semantics

`/reasoning <effort>` is a session override and wins over automatic routing. `/reasoning <effort> --global` changes the profile fallback/default; while `reasoning_auto_routing.enabled: true`, automatic per-turn selection still applies to sessions without an explicit override.

## Sol Pro limitation

Do not infer availability from a synthesized model-picker entry. On the current ChatGPT OAuth account, a real `gpt-5.6-sol-pro` call returned HTTP 400: the model is not supported for Codex with a ChatGPT account. Use `gpt-5.6-sol` with `xhigh` for critical work until a real Pro smoke succeeds.
