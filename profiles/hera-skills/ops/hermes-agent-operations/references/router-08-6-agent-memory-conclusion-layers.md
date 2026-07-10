## 6. Agent memory / conclusion layers

When Rodolfo asks to evaluate or configure external memory infrastructure such as Honcho for Zeus/Atena/Ares, use `references/honcho-managed-memory-spike.md`. For the validated manual briefing command and renderer, use `references/honcho-manual-briefing-command-2026-06-02.md`.

Operational rule: treat Honcho-like systems as a conclusion/insight layer over sanitized history, not as source of truth. Canonical facts remain in JSON/DB/Git/WordPress/audit logs; procedures remain in Hermes skills; stable preferences remain in Hermes memory. Zeus may use Honcho to generate hypotheses, but must validate them against canonical MGS sources before reporting or acting.

Managed Honcho default for first spike: use only synthetic or sanitized data; store `HONCHO_API_KEY` in 1Password (`MGS Conteúdo` → `Honcho API - MGS` → `api key`); never paste or print the key. Self-hosting requires a separate infra decision because it introduces Docker/Postgres+pgvector/Redis/services.

Manual briefing command now exists for on-demand use only:

```bash
/root/mgs-agent/scripts/run-honcho-briefing
```

This command regenerates sanitized datasets, runs targeted Honcho rounds, builds a Zeus deterministic assessment, and renders Discord-safe Markdown. Do not schedule it as cron until each domain summarizer is deterministic enough and the final report preserves source counts/evidence. The final briefing should label Honcho outputs as hypotheses and use Zeus/canonical counters for operational conclusions.
