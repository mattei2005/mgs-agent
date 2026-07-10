# Cron model/provider policy after GPT-5.5 OAuth migration

Current MGS policy (2026-05-16): **zero Anthropic/Claude pay-per-token API by default**.

## Defaults

- Interactive Zeus/Atena: `openai-codex` + `gpt-5.5`.
- Deterministic recurring jobs: `script` + `no_agent: true` or plain Linux cron.
- LLM-based recurring jobs: require an explicit provider/model decision before activation.

## Cost-risk patterns

Flag these in active paths:

- `provider: anthropic`
- `claude-*`
- `ANTHROPIC_API_KEY`
- `api.anthropic.com`
- `anthropic.Anthropic`
- services/listeners wrapping Claude calls, e.g. old `mgs-rec-api.service`

Historical docs/backups may keep these strings for audit context. Active service units, scripts, crons, profile configs and runtime env files should not.

## Migration approach

1. Prefer converting the job to script-only/no_agent.
2. If reasoning is required, use GPT-5.5/OAuth or ask Rodolfo before choosing any pay-per-token provider.
3. Before running or resuming a cron, inspect its model/provider and runtime env.
4. Validate by checking logs and grepping active paths for cost-risk patterns.

## Do not preserve old Haiku default

Previous guidance suggested `claude-haiku-4-5-20251001` for cheap cron jobs. That is now outdated for MGS because Rodolfo rejected Anthropic pay-per-token usage entirely unless explicitly approved.
