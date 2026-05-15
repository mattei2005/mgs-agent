# Hermes cron-worker architecture — MGS

Use this reference when auditing or changing scheduled work for Zeus/Atena.

## Target architecture

| Profile | Purpose | Default model |
|---|---|---|
| `zeus` | GM/orchestration, authorization, executive analysis | `gpt-5.5` via `openai-codex` |
| `atena` | Editorial/content operations | `gpt-5.5` via `openai-codex` |
| `cron-worker` | Scheduled jobs, watchdogs, cheap recurring routines | `claude-haiku-4-5-20251001` via `anthropic` |

## Durable rules

- New LLM-based cron jobs should live in `cron-worker`, not Zeus/Atena.
- If the job is deterministic/script-only, prefer `no_agent=True` or plain Linux cron; do not spend LLM tokens.
- Zeus/Atena should not accumulate operational crons except explicit documented exceptions.
- Use provider pinning for Claude models: `provider: anthropic`; do not rely on `provider: auto` when a profile default is `openai-codex`.

## Haiku model ID

`claude-haiku-4-5-20251001` is a valid Anthropic model/snapshot ID. The suffix is a date snapshot: `2025-10-01`.

If this error appears:

```text
The 'claude-haiku-4-5-20251001' model is not supported when using Codex with a ChatGPT account.
```

The likely issue is not the model name; it is provider resolution. Hermes is trying to call a Claude model through Codex/ChatGPT, often because a config uses `provider: auto` under a profile whose default provider is `openai-codex`.

Correct shape:

```yaml
model:
  provider: anthropic
  default: claude-haiku-4-5-20251001
```

For individual cron jobs, pin both provider and model when needed:

```yaml
provider: anthropic
model: claude-haiku-4-5-20251001
```

## Phase 1 audit pattern — read-only

Before creating `cron-worker` or migrating jobs, audit without writes/restarts:

1. Read `/root/.hermes/profiles/{zeus,atena}/config.yaml` and summarize:
   - main `model.default`, `model.provider`, `model.base_url`
   - auxiliary providers/models
   - `cron` section
2. Inspect Hermes cron files:
   - `/root/.hermes/profiles/zeus/cron/jobs.json`
   - `/root/.hermes/profiles/atena/cron/jobs.json`
3. Check whether `/root/.hermes/profiles/cron-worker` exists.
4. Inspect systemd units read-only:
   - `systemctl cat zeus-gateway.service atena-gateway.service --no-pager`
   - check whether `cron-worker-gateway.service` exists before proposing creation.
5. Inspect Linux crontab read-only:
   - `crontab -l`
   - classify entries as `script-only`, `agent-based`, `paused`, `orphan`, or `duplicate`.
6. Redact all secrets from `.env`; report only presence and length for sensitive values.

## Classification guidance

- Scripts that parse logs, call Discord webhooks, run SQL, or rebuild indexes are usually `script-only` even if comments mention `OpenAI`, `Anthropic`, `Hermes`, or model names for pricing/calculation context.
- A job is `agent-based` only if Hermes will invoke an LLM agent for the scheduled prompt, or if the script itself calls an LLM API.
- Do not migrate the Linux crontab wholesale just to centralize. Keep stable script-only monitors in Linux cron unless there is an operational reason to move them.

## Recommended migration pattern

1. Create `cron-worker` profile with Anthropic/Haiku default.
2. Create separate systemd service, e.g. `cron-worker-gateway.service` running `hermes -p cron-worker gateway run`.
3. Migrate only Hermes cron jobs that need LLM reasoning first.
4. Convert deterministic jobs to `no_agent=True` only when moving them into Hermes cron provides clear value.
5. Validate by listing jobs, running one controlled test, and checking logs before declaring complete.
