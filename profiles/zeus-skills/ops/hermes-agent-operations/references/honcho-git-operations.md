# Honcho and Git Operations

> Extracted from the former monolithic `SKILL.md` on 2026-07-10. Load this file only when its branch is relevant.

## 8. Agent memory / conclusion layers

When Rodolfo asks to evaluate or configure external memory infrastructure such as Honcho for Zeus/Atena/Ares/Hera, use `references/honcho-managed-memory-spike.md`, `references/honcho-manual-briefing-command-2026-06-02.md`, the coverage note `references/discord-response-lint-and-honcho-coverage-2026-06-15.md`, and the repair/reporting note `references/hermes-update-reporting-and-honcho-repair-2026-06-21.md`. For cost/credit/billing questions, use `references/honcho-usage-and-billing-check-2026-07-01.md`.

Operational rule: treat Honcho-like systems as a conclusion/insight layer over sanitized history, not as source of truth. Canonical facts remain in JSON/DB/Git/WordPress/audit logs; procedures remain in Hermes skills; stable preferences remain in Hermes memory. Zeus may use Honcho to generate hypotheses, but must validate them against canonical MGS sources before reporting or acting.

Billing/usage rule: local MGS logs can prove call volume but not exact dollar spend. As of the 2026-07-01 check, Honcho's public OpenAPI exposed workspace/peer/session/conclusion routes but no billing/usage/credits endpoint; obvious `/v3/usage`, `/v3/billing`, `/v3/credits` probes returned 404. For daily spend questions, report confirmed operational volume first (e.g. health monitor runs × agents checked), then label any dollar figure as an estimate based on observed credit balance changes. If Honcho is only “segunda opinião”, avoid aggressive health polling such as 15-min × 4 agents unless Rodolfo explicitly wants it; hourly or 2–4/day preserves credits better during benchmarking.

Coverage audit pitfall: do not equate `honcho: {}` in a profile config with full operational integration. Check all three layers before answering whether an agent is configured: (1) profile config contains Honcho stanza, (2) agent SOUL contains the Honcho role/rules, and (3) `/root/mgs-agent/scripts/mgs-memory-copilot` / `experiments/honcho-spike/mgs_memory_copilot.py` supports that agent in `AGENT_PROFILES`. As of the 2026-06-21 repair, Zeus/Atena/Ares/Hera are supported by the wrapper; if Honcho returns cold storage, the wrapper classifies it as `cold_storage` and requires manual resume at app.honcho.dev before retrying.

Managed Honcho default for first spike: use only synthetic or sanitized data; store `HONCHO_API_KEY` in 1Password (`MGS Conteúdo` → `Honcho API - MGS` → `api key`); never paste or print the key. Self-hosting requires a separate infra decision because it introduces Docker/Postgres+pgvector/Redis/services.

Manual briefing command now exists for on-demand use only:

```bash
/root/mgs-agent/scripts/run-honcho-briefing
```

This command regenerates sanitized datasets, runs targeted Honcho rounds, builds a Zeus deterministic assessment, and renders Discord-safe Markdown. Do not schedule it as cron until each domain summarizer is deterministic enough and the final report preserves source counts/evidence. The final briefing should label Honcho outputs as hypotheses and use Zeus/canonical counters for operational conclusions.

## 9. Git / auto-commit / auto-push do `/root/mgs-agent`

Quando o GitHub `main` parecer velho apesar de haver commits/mudanças recentes no VPS, não assumir falha do GitHub. Validar a cadeia completa: branch atual, `HEAD` vs `origin/main`, dirty tree, `mgs-autocommit.service`, `scripts/auto-commit-watcher.sh`, `.git/hooks/post-commit` e `scripts/monitor-auto-push.sh`. Playbook: `references/mgs-agent-auto-commit-auto-push-repair.md`.

Pitfalls duráveis:

- Watcher `active` não significa GitHub atualizado; ele pode estar abortando por guardrail ou rodando em branch lateral.
- Hook hardcoded `git push origin main` pode registrar `Everything up-to-date` mesmo com commits novos em outra branch; em `main`, preferir `git push origin HEAD:main`, e fora de `main` logar falha explícita.
- Guardrail de nome sensível deve bloquear credenciais reais sem travar ferramentas defensivas com nomes como `*_secret_scan.py`.
- Monitor deve checar estado Git vivo, não só linhas de `auto-push.log`.
