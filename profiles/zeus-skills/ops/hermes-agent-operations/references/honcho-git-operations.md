# Honcho and Git Operations

> Extracted from the former monolithic `SKILL.md` on 2026-07-10. Load this file only when its branch is relevant.

## 8. Agent memory / conclusion layers

When Rodolfo asks to evaluate or configure Honcho for Zeus/Atena/Ares/agente legado, first determine which architecture is meant:

- **Native Hermes memory provider** — `memory.provider: honcho`, profile-local `honcho.json`, provider status, bounded context injection, and Honcho tools.
- **Legacy/manual MGS copilot** — `/root/mgs-agent/scripts/mgs-memory-copilot` and the sanitized briefing workflow.

Read the current official Hermes Memory Providers and Honcho documentation before designing the solution; native provider capabilities can supersede older MGS wrapper assumptions. For the reusable multi-profile implementation and verification procedure, load `references/native-managed-honcho-rollout.md`. For post-rollout USER/MEMORY capacity protection and accurate “what remains?” reconciliation across runtime, checkpoints and parallel Discord threads, load `references/post-rollout-memory-capacity-and-pending-reconciliation.md`. Then use `references/honcho-managed-memory-spike.md`, `references/honcho-manual-briefing-command-2026-06-02.md`, the coverage note `references/discord-response-lint-and-honcho-coverage-2026-06-15.md`, and the repair/reporting note `references/hermes-update-reporting-and-honcho-repair-2026-06-21.md` only for the matching MGS branch. For cost/credit/billing questions, use `references/honcho-usage-and-billing-check-2026-07-01.md`.

Operational rule: Honcho may be the active memory provider and materially reduce dependence on growing file-backed USER/MEMORY, but it remains a user-modeling, session-context, search, and conclusion layer—not the source of truth for MGS operations. Canonical facts remain in JSON/DB/Git/WordPress/audit logs; procedures remain in Hermes skills; global authority and safety remain in SOUL/AGENT or minimal always-active memory. Validate Honcho conclusions against canonical MGS sources before reporting or acting.

Integration audit pitfall: do not infer native activation from an API key, an old `honcho: {}` stanza, successful manual copilot output, or wrapper support. Verify independently: (1) live `memory.provider` resolves to `honcho`; (2) profile-local/global Honcho config exists without exposing credentials; (3) `hermes honcho status` or the current provider status path succeeds; (4) gateway peer mapping is correct; and (5) a real cross-session continuity canary passes. Audit the manual wrapper separately through `AGENT_PROFILES` when that branch is still used.

Before custom semantic compaction for recurring USER/MEMORY pressure, evaluate a one-profile native Honcho pilot. Use a bounded `contextTokens` budget and preserve the 90% monitor as a residual fail-safe until migration, rollback, and continuity are proven. Native Honcho does not itself compact or safely migrate existing USER/MEMORY files.

### MGS cross-agent standard

Rodolfo's approved architecture is native Honcho integration for every current and future MGS agent. Treat this as a rollout objective, not evidence that any profile is already active. Audit Zeus, Atena, Ares, agente legado, and each future profile independently; an empty `memory.provider` or absent `honcho.json` means native integration is not configured even when the manual copilot and API credential exist.

Roll out sequentially with one canary per agent: protected backup → provider/config setup → isolated AI peer and Discord identity mapping → bounded context budget → native profile read → full Hermes-agent canary → rollback/readback. Keep MGS OS/runtime/audit as canonical and keep USER/MEMORY minimal for always-active invariants. Rodolfo explicitly authorized managed Honcho to receive operational conversations on 2026-07-17; `saveMessages=true` is therefore permitted for the MGS profiles under this decision. This data-handling decision does not authorize sending credentials or treating Honcho conclusions as operational truth.

Built-in USER/MEMORY remains always active alongside Honcho. Honcho models the user from persisted conversations; the current native `on_memory_write` hook additionally mirrors only successful `add` writes targeting `user` into a Honcho conclusion. It is not bidirectional byte synchronization: USER `replace`/`remove` and MEMORY writes are not mirrored by that hook. Preserve exact always-active preferences in USER/MEMORY and use Honcho for longitudinal context, semantic retrieval and conclusions.

Deployment pitfalls verified on the MGS build:

- Install `honcho-ai` in the active Hermes venv before calling the native provider.
- Keep the API key only in protected profile `.env` files; profile-local `honcho.json` should remain non-secret and mode `0600`.
- Common `contextCadence` and `dialecticCadence` must also exist at JSON root because startup reads them from `cfg.raw`, even when identities live in a host block.
- `hermes honcho status` prints an API-key suffix. Do not run or relay its raw output in Discord; use `hermes memory status` plus an internal resolver that reports only `key_present=true` and non-secret settings.
- Hybrid mode creates daemon workers for session init, dialectic/context prefetch and async writes. Preserve and test the MGS shutdown-drain patch; flushing without stopping the manager or draining context workers can make a successful short-lived CLI canary exit with `SIGABRT`.

Billing/usage rule: local MGS logs can prove call volume but not exact dollar spend. As of the 2026-07-01 check, Honcho's public OpenAPI exposed workspace/peer/session/conclusion routes but no billing/usage/credits endpoint; obvious `/v3/usage`, `/v3/billing`, `/v3/credits` probes returned 404. For daily spend questions, report confirmed operational volume first (e.g. health monitor runs × agents checked), then label any dollar figure as an estimate based on observed credit balance changes. If Honcho is only “segunda opinião”, avoid aggressive health polling such as 15-min × 4 agents unless Rodolfo explicitly wants it; hourly or 2–4/day preserves credits better during benchmarking.

Managed Honcho data handling: before an explicit corporate decision, use only synthetic or sanitized data. For MGS profiles, Rodolfo's 2026-07-17 decision authorizes persisted operational conversations, but never credentials. Store `HONCHO_API_KEY` in 1Password (`MGS Conteúdo` → `Honcho API - MGS` → `api key`) and protected profile environments; never paste or print the key. Self-hosting remains a separate infrastructure decision because it introduces Docker/Postgres+pgvector/Redis/services.

Manual briefing command now exists for on-demand use only:

```bash
/root/mgs-agent/scripts/run-honcho-briefing
```

This command regenerates sanitized datasets, runs targeted Honcho rounds, builds a Zeus deterministic assessment, and renders Discord-safe Markdown. Do not schedule it as cron until each domain summarizer is deterministic enough and the final report preserves source counts/evidence. The final briefing should label Honcho outputs as hypotheses and use Zeus/canonical counters for operational conclusions.

## 9. Git / auto-commit / auto-push do `/root/mgs-agent`

Quando o GitHub `main` parecer velho apesar de haver commits/mudanças recentes no VPS, não assumir falha do GitHub. Validar a cadeia completa: branch atual, `HEAD` vs `origin/main`, dirty tree, `mgs-autocommit.service`, `scripts/auto-commit-watcher.sh`, `.git/hooks/post-commit` e `scripts/monitor-auto-push.sh`. Playbook: `references/mgs-agent-auto-commit-auto-push-repair.md`.

Pitfalls duráveis:

- Watcher `active` não significa GitHub atualizado; ele pode estar abortando por guardrail ou rodando em branch lateral.
- Um watcher baseado em `inotify` iniciado **depois** que a árvore já ficou dirty não recebe retroativamente esses eventos. Só iniciar/reiniciar `mgs-autocommit.service` pode deixar mudanças antigas indefinidamente sem commit. Para catch-up automático, confirme o monitor pronto, gere um evento real `modify` em um arquivo autorizado já dirty (reescrever conteúdo idêntico é suficiente), aguarde o flush e valide `status` limpo + `HEAD == origin/main`. `utime`/mudança apenas de atributo não serve quando o watcher escuta somente `modify,create,delete,move`. Se reduzir temporariamente `MGS_AUTOCOMMIT_BATCH_MAX_WAIT_SECONDS`, restaure o ambiente e o serviço normal após o commit.
- Hook hardcoded `git push origin main` pode registrar `Everything up-to-date` mesmo com commits novos em outra branch; em `main`, preferir `git push origin HEAD:main`, e fora de `main` logar falha explícita.
- Guardrail de nome sensível deve bloquear credenciais reais sem travar ferramentas defensivas com nomes como `*_secret_scan.py`.
- Monitor deve checar estado Git vivo, não só linhas de `auto-push.log`.
