# Honcho manual briefing command — MGS (2026-06-02)

## Context

Rodolfo evaluated Honcho as a managed memory/conclusion layer for MGS agents. The validated pattern is **not** to let Honcho define truth. Honcho generates hypotheses from sanitized operational history; Zeus validates against deterministic/canonical sources before reporting.

This session produced a manual internal command for experimental briefings:

```bash
/root/mgs-agent/scripts/run-honcho-briefing
```

The command is intentionally manual. Do **not** schedule it as cron until the summarizer is more deterministic per operational domain.

## Flow implemented

1. Fetch `HONCHO_API_KEY` from 1Password only:
   - vault: `MGS Conteúdo`
   - item: `Honcho API - MGS`
   - field: `api key`
2. Regenerate sanitized domain datasets.
3. Run targeted Honcho rounds for:
   - authorization;
   - REC/P1/content operations;
   - Hermes/gateway events by agent.
4. Build `manual_briefing_report.json` with two layers:
   - Honcho raw briefing/hypotheses;
   - Zeus deterministic assessment using counters from sanitized aggregate files.
5. Render Discord-safe Markdown/table output via `render_discord_briefing.py`.
6. Run secret scan before sending data to Honcho and before presenting rendered output.

## Files created in repo

```text
/root/mgs-agent/scripts/run-honcho-briefing
/root/mgs-agent/experiments/honcho-spike/run-honcho-briefing
/root/mgs-agent/experiments/honcho-spike/run_manual_briefing_with_1password.sh
/root/mgs-agent/experiments/honcho-spike/manual_briefing.py
/root/mgs-agent/experiments/honcho-spike/render_discord_briefing.py
/root/mgs-agent/experiments/honcho-spike/run_targeted_rounds.py
/root/mgs-agent/experiments/honcho-spike/run_targeted_rounds_with_1password.sh
```

Runtime outputs are ignored by the spike `.gitignore`:

```text
sanitized_*.json
manual_briefing_report.json
manual_briefing_discord.md
targeted_rounds_report.json
*_output*.txt
*_output*.md
*_error.log
```

## Validated output shape

Use Discord-friendly aligned blocks, not raw JSON:

```text
Sinais de conteúdo

Categoria                  Ocorrências
-------------------------  -----------
image_quality_or_lookup    67
runner_failures            54
wordpress_publish_or_rest  53
provider_ttfb              30
```

```text
Gateway por agente

Agente  Tool errors  Provider TTFB  Credential blocks
------  -----------  -------------  -----------------
ares    43           4              17
atena   206          38             19
zeus    365          42             48
```

## Lessons / pitfalls

- Honcho is useful for REC/P1/content bottleneck hypotheses when the input contains deterministic aggregates.
- Honcho is weaker over raw gateway logs and should not be trusted to rank agent risk by itself.
- Authorization briefings must stay deterministic; Honcho tended to mix credential-safety/configuration warnings with actual authorization incidents.
- Honcho API accepts at most 100 messages per `session.add_messages(...)` request. Keep each round under that or batch explicitly.
- Scope `.chat()` to the session when asking about newly ingested data; otherwise the SDK may search broader memory and return weak/irrelevant answers.
- Secret scan can false-positive on already-masked placeholders like `TOKEN=***`; redaction should replace the whole field with `[REDACTED_CREDENTIAL_FIELD]`, not leave `TOKEN=***` text that matches scanners.
- Do not hardcode or paste the Honcho key. If a key is pasted in chat/screenshot, treat it as compromised: revoke, recreate, update 1Password, rerun validation.

## Current recommendation

Keep this as an on-demand experimental command. Do not cron it yet. Before productionizing:

1. make each domain summarizer deterministic;
2. preserve source counts/evidence in the final report;
3. keep Honcho output clearly labeled as hypotheses;
4. require Zeus validation against canonical logs/JSON/DB before any alert or operational action.
