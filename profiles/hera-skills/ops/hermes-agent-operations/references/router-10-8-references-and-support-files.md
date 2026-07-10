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
