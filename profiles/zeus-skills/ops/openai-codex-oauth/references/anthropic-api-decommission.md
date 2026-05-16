# Anthropic API Decommission — MGS

Use when Rodolfo says Anthropic/Claude API is too expensive or asks to ensure no pay-per-token Claude usage remains.

## Policy

- Default state: **zero Anthropic/Claude API pay-per-token**.
- Any use of `provider: anthropic`, `claude-*`, `ANTHROPIC_API_KEY`, `api.anthropic.com`, or Python `anthropic` in an active service is a cost risk.
- Do not keep Claude/Haiku as a hidden fallback after migrating Zeus/Atena to GPT-5.5/OAuth.
- If a service must keep Anthropic temporarily, report it as an explicit exception with owner, cost risk, and migration path.

## Audit checklist

1. Repo/static scan:
   - `git grep -n -i -E 'ANTHROPIC_API_KEY|api\.anthropic\.com|anthropic\.Anthropic|import anthropic|claude-|provider: anthropic'`
   - Separate active code/config from historical docs, backups, changelog, and deprecated folders.
2. Runtime scan:
   - `systemctl list-units --type=service --state=running`
   - inspect services under MGS that load `.env` or call Python APIs.
   - `ss -ltnp` for local APIs (example: `127.0.0.1:8001` mgs-rec-api).
3. Logs/evidence:
   - Search recent logs for `https://api.anthropic.com/v1/messages` or Anthropic HTTP client traces.
   - Redact keys; never print tokens.
4. Credentials:
   - Find local env entries only by key name / presence / length.
   - Remove from active `.env` only after confirming no required production path depends on it, or after Rodolfo explicitly accepts breakage.

## Known MGS pitfall from 2026-05-16

Renaming cost monitors and migrating agent profiles is not enough. `mgs-rec-api.service` remained active and `api/generate-rec-api.py` still used:

- `import anthropic`
- `ANTHROPIC_API_KEY`
- `MODEL = "claude-sonnet-4-6"`
- `anthropic.Anthropic(...).messages.create(...)`

`mgs-rec-runner.py` also had an Anthropic fallback for reference extraction when cache/manual facts were missing.

Operational implication: stopping/removing Anthropic may break the REC fast runner until the generation API is migrated to GPT/OAuth or another no-pay-per-token path. Report that tradeoff clearly before disabling services.

## Safe response pattern

Use an aligned table:

```text
Uso Anthropic ainda ativo      Impacto
────────────────────────────  ─────────────────────────────────────
mgs-rec-api.service            Gera REC via Claude API real
scripts/mgs-rec-runner.py      Pode acionar Claude como fallback
ANTHROPIC_API_KEY em .env      Permite chamadas se algum script usar
```

Then recommend:

1. Stop/disable active Anthropic services for immediate cost stop.
2. Neutralize fallback code paths.
3. Remove local env exposure; keep credential only in 1Password/archive if needed.
4. Migrate functionality to GPT-5.5/OAuth or deterministic/script-only flow.
