# Handoff — t_32bc2e19 → t_f4bacf0f (Ares)

## Aceite e limite

Instalação aceita em GET real read-only nas 10 campanhas / 10 conjuntos / 20 anúncios do **mesmo** request `shein-1570314359530459327`, conta `937846586033361`. Esta manutenção não executou campanhas, ativação, QA renderizado restante, writes Meta/Drive nem posts na thread de origem. Ares/t_f4bacf0f continua único dono da entrega.

Estado preservado byte a byte: request.json, state.json (inclui manifests, resolved_request, clock e media_qa8), core checkpoint, primeiro continuation-live-readback.json e job da fila. Os objetos permanecem PAUSED, runner POSTPROCESS_PENDING; media_qa permanece exatamente com os 8 IDs originais. Fonte018 não foi alvo de writes. Nenhum grant/review/reserva histórico foi alterado. A política de observação manual e seu TTL120 continuam intactos; este receipt não substitui dependencies/source-proof fresco.

## Correção central

`shein_elapsed_continuation.py` valida receipt separado + grant de digest exclusivamente para este request/conta. Binding: política canônica de Rodolfo1558142161659105342 anterior aos objetos, autoridade original/live, literal humano, request/resolved, manifests selados, clock original, checkpoint completo, primeiro readback e IDs. Não muda início, clock ou selo. Não infere NOW antigo nem aceita tolerância.

- 160–167: EXACT_ORIGINAL, início `2026-11-12T01:00:00-0500`, intacto.
- 168–169: NATIVE_ELAPSED_COPY, `2026-11-12T01:20:27-0500`, exclusivamente segundo provado na janela `06:20:26.213729Z`–`06:20:31.219732Z` do mesmo bundle5.
- Mesma data America/New_York obrigatória em uso. Outra data/futuro/policy off/autoridade ausente/prova alterada/manual histórico falham fechados.

Consumidores validados: `shein_elapsed_schema.admission` do target inteiro exato (sem vazamento de contexto), QA `verify_readback`, `activation.validate_live` pre/final, guard separado de horário vencido e final readback do runner. O receipt **não certifica QA**, não libera histórico nem cria outro writer.

## Receipts

- `data/ares/meta-ads/audit/maintenance/t_32bc2e19/installation.json`: 9 arquivos instalados e hashes.
- `data/ares/meta-ads/audit/maintenance/t_32bc2e19/acceptance-installed.json`: GET real das 10 árvores, todos validadores, final ACTIVE exercitado somente em cópia em memória; não é ativação real.
- `data/ares/meta-ads/audit/maintenance/t_32bc2e19/installed/live-trees.json`: readback novo separado; primeiro receipt do intake preservado.
- `data/ares/meta-ads/state/shein-campaigns/elapsed-continuations/shein-1570314359530459327.json`: receipt imutável.
- `data/ares/meta-ads/policies/shein-elapsed-continuations.json`: grant exato; digest receipt `cd8d1e6f46d1d2174297cfbb8b96bfc4184aec35af4dd405f7b9c62c886fb1d9`.
- `data/ares/meta-ads/audit/maintenance/t_32bc2e19/preservation-before.json`: hashes protegidos, todos conferidos após instalação.
- Backup/rollback em `.../t_32bc2e19/backup/`. Rollback de código: restaurar somente activation.py/schema.py/shein_single_clone.py/shein_copy_schedule.py dos backups; módulos novos/receipt ficam inertes. Não deletar/alterar histórico ou seals.

## Testes

39 testes novos passaram, incluindo negativas de identidade, segundo extra/fora janela, dia, policy futura/off, manifests resealados, clock, autoridade/provas faltantes, schema scope e fence real Engine/activation para takeover histórico.

Suíte focada staging: 177 passed +63 subtests, sem falhas. Ampla instalada: 301 passed +99 subtests e **9 falhas preexistentes**, mesmas identidades do baseline (0 novas): 8 fixtures antigas sem slots criativos exigidos pela política de background e 1 fixture SimpleNamespace sem operation. Não são falhas introduzidas nem uma suíte ampla verde; detalhes em `tests-summary.json`, baseline/installed-regression.xml/log.

Reexecutar aceite somente leitura:

    cd /root/mgs-agent
    PYTHONPATH=scripts python3 data/ares/meta-ads/audit/maintenance/t_32bc2e19/acceptance.py --installed --live

Esse comando não realiza QA renderizado nem ativação e não altera runner/core/job. Não rodar install.py novamente nem regenerar receipt/clock.

## Retomada — somente Ares

Input literal:
`/root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1570314359530459327/request.json`

1. Ler job/runner/core + installation/acceptance/receipt; exigir IDs preservados, foreground/deliveryares/notificationnull e nenhum executor concorrente. Não criar outro request/card de campanha/cron/worker.
2. `PYTHONPATH=/root/mgs-agent/scripts python3 -m ares_campaign_v3.shein_request_queue --inspect <INPUT>`; exigir dependencies[] com source proof positiva fresca (TTL120). Preservar manutenção anterior t_ee2d9949. Se necessário, takeover canônico `--take-foreground <INPUT>`; nunca executar o writer histórico.
3. Dry-run central do input original; depois o mesmo comando `python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input <INPUT> --confirm-execute`, foreground timeout600 ou maior seguro. Nesta fase core já COMPLETE: somente pós-processamento/QA restante/ativação de IDs existentes. Receipt efetivo é consumido automaticamente; sem editar input/manifest/clock/schedule.
4. Completar QA semântico/renderizado 10/10, 20ads e comparar IDs/creatives. Autoridade live forçada antes da ativação. Guard global de QA e readbacks continua obrigatório.
5. Exigir 10campaigns/10adsets/20ads ACTIVE no readback real, todos budgets8500/COST_CAP95, conjunto de IDs igual ao core, fonte018 fora dos writes. ACTIVE não significa serving.
6. Entrega única na origem1558134703565967394 por Ares com bloco Iris/UTMs literais, USD850/dia delta e validações requeridas pelo card. Zeus não postou na origem.

REPORT-INFRA Zeus1570328163353890831 em alerts-infra1498132022634483894 conferido por GET exato: content vazio, mentions vazias, sem thread. Inventário `ares-shein-explicit-partial-t_32bc2e19`.
