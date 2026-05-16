# Cron model pinning after OpenAI Codex migration

## Durable lesson

When a Hermes profile is migrated to `openai-codex` + `gpt-5.5`, agent-based cron jobs that do not specify their own `model`/`provider` inherit the profile default. That means a newly created or existing unpinned cron can start running on GPT/Codex instead of the intended cheap auxiliary model.

## MGS default policy

- Keep interactive Zeus/Atena profiles on `openai-codex` + `gpt-5.5`.
- Do **not** default scheduled work to Anthropic/Claude/Haiku. Rodolfo's current policy is zero pay-per-token Anthropic unless explicitly approved.
- For deterministic/watchdog cron jobs that do not need reasoning, prefer `script` + `no_agent: true` so no LLM is called.

## Audit checklist

When reviewing cron jobs after a provider migration:

1. List jobs per profile, especially Zeus and Atena.
2. Flag jobs with `model: null` or `provider: null`.
3. If the job is agent-based and should be low-cost, update it with explicit Haiku model override before resuming/running it.
4. If the job is purely script output, convert or recreate as `no_agent: true` where appropriate.

## Example policy statement

"Cron novo = Haiku por padrão, salvo exceção explícita. Script-only = `no_agent: true`."
