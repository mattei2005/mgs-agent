## 4. Reporting templates

### Resposta executiva para tooling web

```text
Pergunta                                      Resposta
──────────────────────────────────────────── ─────────────────────────────
1. Tem web_search nativo?                    Sim/Não + tool name
2. Tem web_fetch nativo?                     Sim/Não + web_extract mapping
3. MCP de busca configurado?                 Sim/Não + profile results
4. Versão trouxe capability nova?            Versão + delta conciso
5. Toolsets ativos Zeus/Atena                tabela abaixo
```

Depois: tabela de toolsets, tabela de backends, recomendação direta e `Próximo passo pendente:`.

### Resposta executiva para update

```text
Resumo: atualizar agora / deferir / janela controlada.
Evidências: commits atrás, highlights, risco local, backup/checks.
Impacto: gateways offline ~1-2 min; Zeus pode interromper sessão ativa.
Próximo passo: comando exato ou validação pendente.
```
## 5. New MGS agent bootstrap

When Rodolfo asks to start a new MGS agent/profile (Ares or future agents), use `references/mgs-new-agent-bootstrap.md`. Core rule: clone profile/config as needed, but immediately blank any inherited Discord bot token; do not create/enable the systemd gateway until the agent has its own dedicated bot token and Rodolfo confirms the Critical Subset system-file write.
## 6. Agent memory / conclusion layers

When Rodolfo asks to evaluate or configure external memory infrastructure such as Honcho for Zeus/Atena/Ares, use `references/honcho-managed-memory-spike.md`. For the validated manual briefing command and renderer, use `references/honcho-manual-briefing-command-2026-06-02.md`.

Operational rule: treat Honcho-like systems as a conclusion/insight layer over sanitized history, not as source of truth. Canonical facts remain in JSON/DB/Git/WordPress/audit logs; procedures remain in Hermes skills; stable preferences remain in Hermes memory. Zeus may use Honcho to generate hypotheses, but must validate them against canonical MGS sources before reporting or acting.

Managed Honcho default for first spike: use only synthetic or sanitized data; store `HONCHO_API_KEY` in 1Password (`MGS Conteúdo` → `Honcho API - MGS` → `api key`); never paste or print the key. Self-hosting requires a separate infra decision because it introduces Docker/Postgres+pgvector/Redis/services.

Manual briefing command now exists for on-demand use only:

```bash
/root/mgs-agent/scripts/run-honcho-briefing
```

This command regenerates sanitized datasets, runs targeted Honcho rounds, builds a Zeus deterministic assessment, and renders Discord-safe Markdown. Do not schedule it as cron until each domain summarizer is deterministic enough and the final report preserves source counts/evidence. The final briefing should label Honcho outputs as hypotheses and use Zeus/canonical counters for operational conclusions.
## 7. Git / auto-commit / auto-push do `/root/mgs-agent`

Quando o GitHub `main` parecer velho apesar de haver commits/mudanças recentes no VPS, não assumir falha do GitHub. Validar a cadeia completa: branch atual, `HEAD` vs `origin/main`, dirty tree, `mgs-autocommit.service`, `scripts/auto-commit-watcher.sh`, `.git/hooks/post-commit` e `scripts/monitor-auto-push.sh`. Playbook: `references/mgs-agent-auto-commit-auto-push-repair.md`.

Pitfalls duráveis:

- Watcher `active` não significa GitHub atualizado; ele pode estar abortando por guardrail ou rodando em branch lateral.
- Hook hardcoded `git push origin main` pode registrar `Everything up-to-date` mesmo com commits novos em outra branch; em `main`, preferir `git push origin HEAD:main`, e fora de `main` logar falha explícita.
- Guardrail de nome sensível deve bloquear credenciais reais sem travar ferramentas defensivas com nomes como `*_secret_scan.py`.
- Monitor deve checar estado Git vivo, não só linhas de `auto-push.log`.
## 8. References and support files

Para manutenção de VPS/update com backup, recuperação manual de npm quando self-update quebra, e política de retenção/limpeza de backups, ver `references/vps-update-npm-backup-retention-2026-05-24.md`.

Esta umbrella absorveu as antigas skills especializadas abaixo. Conteúdo detalhado e histórico foi preservado nos arquivos de suporte:

- `references/hermes-update-original-skill.md`
- `references/hermes-update-post-update-validation.md`
- `references/hermes-manual-no-restart-update-patch-drift.md` — atualização manual sem restart automático: backup/diff, pull ff-only, reaplicar patches MGS, lidar com patch context drift, limpar `.update_check`, validar testes e pedir restart separado.
- `references/hermes-update-enospc-partial-update-recovery.md` — recuperar update parcial após `ENOSPC`: liberar espaço, distinguir repo atualizado vs. dependências falhas, reparar npm/uv, compilar e só então reiniciar gateways.
- `references/post-update-gateway-restart-validation.md` — validar update/restart Zeus+Atena+Ares quando Zeus reinicia a si mesmo; finalizer via systemd-run, distinção entre falha histórica de restart e erro ativo pós-start.
- `references/hermes-update-enospc-controlled-recovery.md` — recuperar update parcial após `No space left on device`: inventário/limpeza de backups, reparo de Python/npm sem restart, validação e restart separado.
- `references/hermes-update-pre-update-review.md`
- `references/hermes-update-2026-05-16-mgs-relevance.md`
- `references/hermes-update-2026-06-04-all-agents-test-env.md` — all-agent restart validation for Zeus/Atena/Ares plus pytest cwd/env isolation pitfalls after Hermes updates
- `references/mgs-full-maintenance-validation-and-npm-manual-update.md` — full post-maintenance validation checklist + safe manual npm replacement/rollback pattern
- `references/hermes-web-tooling-original-skill.md`
- `references/hermes-web-tooling-2026-05-17.md`
- `references/hermes-web-brave-search-mgs-2026-05-17.md`
- `scripts/test-brave-search-mgs.sh`
- `references/openai-codex-oauth-original-skill.md`
- `references/openai-codex-cron-model-pinning.md`
- `references/openai-codex-anthropic-api-decommission.md`
- `references/openai-codex-cost-monitoring-gpt-oauth.md`
- `references/atena-openhands-provider-diagnostic.md` — diagnosticar OpenHands da Atena: funcionalidade vs. provider/modelo/custo, wrapper e trajectories sem vazar credenciais
- `references/openhands-gpt55-codex-wrapper.md` — padrão MGS para OpenHands com GPT-5.5/OpenAI-Codex OAuth, bloqueio de fallback provider e validação real do runtime model
- `references/honcho-managed-memory-spike.md` — avaliação/configuração de Honcho como camada managed de conclusões sobre histórico sanitizado; inclui política de fonte de verdade, 1Password/API key, smoke test sintético e ingestão manual de logs sanitizados.
- `references/honcho-targeted-rounds-2026-06-02.md` — primeira rodada MGS com datasets por domínio; registra limite de 100 mensagens por batch, vantagem de agregados determinísticos sobre logs brutos, pitfall de secret-scan com placeholders e scoping de `.chat()` por sessão.
- `references/honcho-manual-briefing-command-2026-06-02.md` — comando manual `/root/mgs-agent/scripts/run-honcho-briefing`, renderer Markdown/Discord, política de on-demand only, e lessons de Zeus deterministic layer sobre Honcho hypotheses.
- `scripts/honcho_sanitized_secret_scan.py` — scanner local para barrar padrões óbvios de secrets antes de enviar dataset sanitizado ao Honcho
