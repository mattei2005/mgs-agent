# Detailed Reference Catalog

> Extracted from the former monolithic `SKILL.md` on 2026-07-10. Load this file only when its branch is relevant.

## 10. References and support files

Para manutenção de VPS/update com backup, recuperação manual de npm quando self-update quebra, e política de retenção/limpeza de backups, ver `references/vps-update-npm-backup-retention-2026-05-24.md`. Para manutenção OS/Node quando Hermes já foi tratado em outro escopo, incluindo `cloud-init`/`fwupd` retidos, conffile prompt e hardline de reboot/restart, ver `references/vps-os-package-maintenance-after-hermes-update-2026-07-05.md`.

Esta umbrella absorveu as antigas skills especializadas abaixo. Conteúdo detalhado e histórico foi preservado nos arquivos de suporte:

- `references/hermes-update-2026-07-05-autorestart-and-staged-patch-port.md` — sessão de update controlado em que `RESTART_GATEWAYS=0` não impediu o `hermes update` oficial de drenar/reiniciar Ares/Atena/agente legado, gerando órfãos `gateway run --replace`; inclui recuperação segura e pitfall de `git apply --3way` deixar mudanças staged, exigindo `git diff --binary HEAD` para gerar patch canônico não-vazio.
- `references/hermes-update-2026-07-07-canonical-patch-port.md` — sessão de update com 210 commits novos em que o patch canônico e o live diff driftaram; documenta port em worktree upstream, promoção do novo patch no guard antes da validação, resolução de duplicatas no fluxo Discord thread-title, repetição da colisão `--replace`, e pitfall de `infra-discovery.sh`/auto-commit commitar temp `data/infra-inventory.json.tmp.*`.
- `references/hermes-bundled-skill-sync-merge-2026-07-05.md` — playbook para resolver `user-modified bundled skills` após update: inventário por profile, diff, backup, classificação restore/rebaseline/merge manual, manifest baseline e validação final.
- `references/hermes-update-original-skill.md`
- `references/hermes-update-post-update-validation.md`
- `references/hermes-controlled-update-rule-mgs.md` — regra permanente MGS aprovada por Rodolfo: backup + diff/snapshot pré-update + comparação pós-update + guard de patches/invariantes + validação runtime real antes de considerar update concluído.
- `references/mgs-discord-tool-progress-and-backup-retention-2026-06-30.md` — sessão em que Rodolfo corrigiu a expectativa de Discord sem breadcrumbs de tool/code e pediu reparo da retenção de backups: per-platform `tool_progress` override para Discord, cleanup_progress, política de retenção para `hermes-profiles-backup-*.tar.gz`, e tratamento seguro de `tar: file changed as we read it` no safety backup.
- `references/hermes-controlled-update-git-hygiene-2026-06-15.md` — incidente/recuperação de Git hygiene quando reports/backups de update entraram no auto-commit: pausar autocommit, ignorar artifacts antes de gerar, force-push com lease após aprovação e `git gc` para recuperar espaço.
- `references/hermes-update-discord-report-and-followup-2026-06-17.md` — lessons from update where a stale hardcoded Discord thread received a report, detached restart finalizer did not proactively follow up, and Hermes news cron confused update scope; includes opt-in Discord delivery and backup cleanup guidance.
- `references/hermes-update-local-patch-surface-fail-closed-2026-06-17.md` — post-update local patch loss case: why file-level diff comparison missed missing functions, how to restore `pre-local-diff*`, promote author suffix/anti-loop/auto-attach/delete-message invariants to the guard, clean patch archives, and fail closed before mutation when live local diff does not apply to `origin/main`.
- `references/hermes-v017-controlled-update-mgs-customizations-2026-06-20.md` — validated v0.16→v0.17 MGS update pattern: precheck-only, port patches in worktree, consolidated runtime customization patch, clean-worktree guard validation, external ordered restart, full report including backups/crons/auth/tests/Git hygiene.
- `references/hermes-controlled-update-canonical-port-2026-06-26.md` — canonical patch port workflow for large upstream deltas: create a fresh port patch in detached worktree, validate apply/py_compile/targeted pytest before live update, use `RESTORE_LOCAL_DIFFS=0` when the stale live diff is known-drifted, and treat harmless upstream config schema/default additions as WARN when MGS critical invariants survive.
- `references/hermes-update-port-canonical-patch-2026-06-26.md` — safe workflow for large upstream drift where the old live local diff no longer applies: port consolidated MGS runtime customizations in an `origin/main` worktree, validate invariants/py_compile/target pytest, create a new canonical patch, and use `RESTORE_LOCAL_DIFFS=0` only after validation.
- `references/hermes-controlled-update-report-and-backup-compare-2026-06-15.md` — incidente/lesson de update Hermes em que backup/snapshot existiam mas a comparação backup↔estado vivo e o relatório pós-restart não foram entregues corretamente; define evidências obrigatórias `post-backup-live-profile-compare.txt`, `post-profiles-sanitized.txt` e `post-readonly-invariants.txt`.
- `references/hermes-local-patch-surface-guard-2026-06-17.md` — incidente/lesson em que update preservou arquivos modificados mas perdeu funções locais não-canônicas; exige restaurar `pre-local-diff*` pós-update e comparar markers/funções/strings do diff pré-update, não só nomes de arquivos.
- `references/hermes-manual-no-restart-update-patch-drift.md` — atualização manual sem restart automático: backup/diff, pull ff-only, reaplicar patches MGS, lidar com patch context drift, limpar `.update_check`, validar testes e pedir restart separado.
- `references/hermes-update-enospc-partial-update-recovery.md` — recuperar update parcial após `ENOSPC`: liberar espaço, distinguir repo atualizado vs. dependências falhas, reparar npm/uv, compilar e só então reiniciar gateways.
- `references/post-update-gateway-restart-validation.md` — validar update/restart Zeus+Atena+Ares quando Zeus reinicia a si mesmo; finalizer via systemd-run, distinção entre falha histórica de restart e erro ativo pós-start.
- `references/hermes-restart-loop-and-cron-drift-2026-06-11.md` — incidente de loop profundo ao reiniciar Zeus/Atena/Ares/agente legado a partir da própria conversa do Zeus; ensina finalizer único/idempotente, Zeus por último, inspeção de log antes de novas tentativas, e checagem de drift em root crontab vs. `docs/CRONS.md`.
- `references/hermes-update-enospc-controlled-recovery.md` — recuperar update parcial após `No space left on device`: inventário/limpeza de backups, reparo de Python/npm sem restart, validação e restart separado.
- `references/mgs-full-vps-migration-hostinger-2026-06-18.md` — full MGS/Hermes VPS migration playbook from Hetzner to Hostinger: full mirror + controlled cutover, `hermes backup/import` limitations, finalizer pattern, target validation, old-VPS standby audit, and mgs-autocommit watcher pitfall.
- `references/hermes-update-pre-update-review.md`
- `references/hermes-update-2026-05-16-mgs-relevance.md`
- `references/hermes-update-2026-06-04-all-agents-test-env.md` — all-agent restart validation for Zeus/Atena/Ares plus pytest cwd/env isolation pitfalls after Hermes updates
- `references/mgs-full-maintenance-validation-and-npm-manual-update.md` — full post-maintenance validation checklist + safe manual npm replacement/rollback pattern
- `references/hermes-web-tooling-original-skill.md`
- `references/hermes-web-tooling-2026-05-17.md`
- `references/hermes-web-brave-search-mgs-2026-05-17.md`
- `scripts/test-brave-search-mgs.sh`
- `references/hermes-profile-config-migration-mgs.md` — migração controlada de `config.yaml` por profile após update Hermes: backup pequeno, `hermes -p <profile> config migrate`, validação provider/model/auth/gateway/patch guard, sync dos mirrors MGS, restart gracioso e audit log.
- `references/discord-table-format-and-standards-drift.md` — padrão MGS para tabelas em Discord: blocos simples/alinhados sem tabela Markdown crua para respostas operacionais; inclui workflow para corrigir drift de SOUL/estilo.
- `references/discord-output-and-attachment-guard-2026-06-15.md` — correção de saída Discord quebrada por language-tagged fences/linha solta `text` e regra forte contra anexos não solicitados; inclui uso de `/root/mgs-agent/scripts/discord-response-lint.py`.
- `references/openai-codex-oauth-original-skill.md`
- `references/openai-codex-cron-model-pinning.md`
- `references/openai-codex-anthropic-api-decommission.md`
- `references/openai-codex-cost-monitoring-gpt-oauth.md`
- `references/hermes-image-gen-openai-codex-mgs.md` — configurar image generation via `openai-codex`/ChatGPT OAuth para perfis MGS como agente legado; separa modelo de chat (`gpt-5.5`) de backend de imagem, evita fallback FAL sem `FAL_KEY`, e inclui smoke test real com `hermes -p <profile> -t image_gen -z ...`.
- `references/grok-xai-oauth-creative-media-rollout-2026-06-16.md` — rollout MGS de Grok/xAI via OAuth SuperGrok para Creative Ops: OAuth manual-paste, cópia segura de `providers.xai-oauth` entre profiles, configuração agente legado GPT+Grok lado a lado, wrapper `/root/mgs-agent/scripts/mgs-grok-generate.py`, smoke tests reais de imagem/vídeo e pitfall de ignorar `data/generated/` no Git.
- `references/legacy-agent-creative-calibration-and-xai-auth-2026-06-17.md` — correção de agente legado quando Creative Ops parece genérica/perdida: hard gates para referência externa e GPT+Grok, cópia segura de xAI OAuth válido preservando `active_provider=openai-codex`, smoke tests reais e padrão de diretora de arte/produtora.
- `references/atena-openhands-provider-diagnostic.md` — diagnosticar OpenHands da Atena: funcionalidade vs. provider/modelo/custo, wrapper e trajectories sem vazar credenciais
- `references/openhands-gpt55-codex-wrapper.md` — padrão MGS para OpenHands com GPT-5.5/OpenAI-Codex OAuth, bloqueio de fallback provider e validação real do runtime model
- `references/honcho-managed-memory-spike.md` — avaliação/configuração de Honcho como camada managed de conclusões sobre histórico sanitizado; inclui política de fonte de verdade, 1Password/API key, smoke test sintético e ingestão manual de logs sanitizados.
- `references/honcho-targeted-rounds-2026-06-02.md` — primeira rodada MGS com datasets por domínio; registra limite de 100 mensagens por batch, vantagem de agregados determinísticos sobre logs brutos, pitfall de secret-scan com placeholders e scoping de `.chat()` por sessão.
- `references/honcho-manual-briefing-command-2026-06-02.md` — comando manual `/root/mgs-agent/scripts/run-honcho-briefing`, renderer Markdown/Discord, política de on-demand only, e lessons de Zeus deterministic layer sobre Honcho hypotheses.
- `references/hermes-update-reporting-and-honcho-repair-2026-06-21.md` — checklist de relatório completo para updates/repairs Hermes-MGS, sem “acabou operacionalmente” vago; inclui diagnóstico/correção de Honcho cold storage, cobertura agente legado e workaround de REPORT-INFRA via Zeus Bot quando webhook 403.
- `scripts/honcho_sanitized_secret_scan.py` — scanner local para barrar padrões óbvios de secrets antes de enviar dataset sanitizado ao Honcho
