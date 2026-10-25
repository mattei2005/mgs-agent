# Recuperação financeira de 24/10 — rollover preservado

Autoridade: Rodolfo1563920408531435650, thread1545426987756298340. Checkpoint ZEUS-FINANCE-RECOVERY-1563920408531435650.

## Resultado validado
- Gastos Meta/Google e receita GAM completos até2026-10-24. Spend last_status=ok, last_until=2026-10-24, zero falhas de fonte/descoberta/consulta, exceções ou valores não atribuídos. Trava de cinco falhas e contador zerados pelo sucesso real do runner, não por edição manual de state.
- GAM:2581linhas→73grupos; CAD62949.21171892676757311015 e USD6799.23883785002822431107. Apply/verify PASS, revisão971→972, audit5142, cutoff24/10. Replay already_applied/verify PASS.
- SMS24/10 preservado integralmente:21667envios,173336centavos BRL, audit5139/revisão970. Nenhum relançamento de SMS.
- Growpowerhub: países DE+US, titular MGS, INATIVO/não participa e G004/Joe preservados. Gasto23/10 USD8.85 mantido;24/10 USD11.83 aplicado uma vez e conferido na API, ledger de importação e custo do gestor.
- Relatório Diário autenticado em1440px e390px mostra24dias completos; sem erro JS, sem overflow e zero POST financeiro do navegador. Login/MFA/health/logout validados. Módulos produtivos:15/15combinações competência×gestor reconciliadas.
- Replay seco de gastos:zero campos alterados. Plano final de rollover:zero mudanças, blockers, alteração de workspace/registry/receipt. Confirmação conjunta1563926648326193208 entregue e relida na thread de origem.

## Problema, causa e solução
A verificação mensal anterior aos gastos tentava regredir Growpowerhub de DE+US para DE, herdando novamente setembro. A aprovação de24/10 foi respeitada na primeira passagem, mas o site preservado foi omitido do recibo de herança. Na execução seguinte, a ausência de recibo foi interpretada incorretamente como permissão de copiar a configuração antiga. O validador financeiro bloqueou a proposta antes da gravação: o workspace persistido permanecia correto, e seu cálculo isolado passou.

A correção conserva sites já existentes que não estão no recibo anterior; sites realmente ausentes continuam podendo ser criados e configurações ainda herdadas continuam atualizáveis. Nenhuma trava de vínculo, data, país, moeda, revisão ou total foi enfraquecida. Nenhum gasto foi reatribuído por inferência. A reconciliação usa o audit produtivo5119 e a decisão1563528749830377524; não é mudança concorrente sem origem.

## Publicação e prevenção
- Alteração produtiva somente no script local scripts/finance-month-rollover-core.mjs; ampliada tests/finance-month-rollover.test.mjs. Aplicação remota, credenciais, serviços, cron e horários não foram alterados/reiniciados.
- Candidato isolado; dois novos casos falharam antes da correção e passaram depois.9testes Node de rollover +3calendário Python. Gates completos da aplicação inalterada:279Node+242Python, sem skips. Total533testes.
- Ensaio remoto somente leitura:quatro gerações consecutivas de recibo mantêm DE+US/G004/custo, zero mutações e fingerprints financeiros/históricos/ledger preservados.
- Publicação local por bootstrap exato, com admissão exclusiva, locks legados, manifesto de hashes, backup reversível, journal e testes/readback do ativo. Controlador regular não admite scripts/; nenhum alargamento de allowlist ou contorno de guard. Não houve necessidade de reiniciar serviço.
- SHA256 do core publicado:3be5b934ace9b616c2eb648cc041d527e6d424a1791a1a948e53b74e9519bfb5; anterior69e1a727989de7fecba7bb1642e15080f5ed10bdbdff3e72625820a26602d38b.
- Nova coleta real01–24/10 feita read-only, importada pelo runner manual canônico com --since/--until/--collection-file após correção. GAM retomado pelo par original preservado, com backups/hash/readback. Nenhum sucesso foi escrito manualmente, fonte inventada ou notificação reimportada.
- Procedimento persistido em mgs-finance-dashboard/references/api-first-site-daily-spend.md, seção Monthly-configuration preflight and repeated receipts. Cobertura é específica desta regressão; novas fontes indisponíveis/classificações desconhecidas ainda podem exigir recuperação.

## Evidências
- apps/finance-system/private/daily-recovery-1563920408531435650/:diagnosis.json,manifest.json,stage-proof.json,publish-journal.json,before/,candidate/,gates/,regression-before.log,regression-after.log,fresh-collection.json,spend-recovery.log,gam-recovery.log,spend-replay.json,gam-replay.log,rollover-final-plan.json,browser-production.json,manager-health.json.
- Gastos:private/media-spend-runs/20261025T104418-0400/result.json.
- GAM apply:private/gam-email-runs/20261025T104458-0400/result.json; replay:20261025T104708-0400/result.json.
- Backups de código e financeiros preservados. Artefatos de testes foram gerados pelos gates em private/; nenhuma limpeza destrutiva foi executada.
