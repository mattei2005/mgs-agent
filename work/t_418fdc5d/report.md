# Reconciliação de três regressões legadas — t_418fdc5d

## Entrega

Somente dois arquivos de teste foram ajustados. Nenhum módulo runtime, contrato produtivo, token, grant, budget, gateway, instalação de pacote ou writer Meta/Drive foi modificado por este trabalho. O request operacional de campanha continua exclusivamente em t_8f7a90a8.

- `tests/test_shein_media_qa.py`: substituída a fixture de estoque Shared Drive por binding 30TB sintético validado; transporte nativo de metadata em memória, sem autenticação. Os validadores reais de owner, ancestry, nome e parent continuam ativos. Cache da pasta e consulta de 02_TESTING continuam conferidos, assim como as duas leituras de asset e a associação exata em advideos. Seis recusas adicionais verificam metadata_clean, checksum, uso anterior, owner, driveId legado e parent errado no segundo asset.
- `tests/test_ares_campaign_v3_daily_cpv.py`: a expectativa do item de token foi alinhada a `Meta BISU - CAR+SHEIN - Digital Trust - G001-G006`, sem restaurar token pessoal ou alterar lookup cache-first. Fonte: registro ativo `ARES-CAR-SHEIN-SHARED-BISU-CUTOVER-20260915` e `data/ares/meta-ads/audit/auth-cutover/shared-car-shein-bisu-20260915.json`.
- Nesse mesmo arquivo, a expectativa global antiga de reader gate foi substituída por `test_cpv_action_readers_keep_writer_gate_but_reports_use_bounded_shared_lane`: Diário e ramo report-only do Intraday usam lock compartilhado com espera limitada e aviso de indisponibilidade, sem herdar lease persistente; Snapshot, first-delivery, reactivation e ramo action-only mantêm o reader gate. Fonte: `Creditoparaveiculo-BR-CAR-BR.json#/reporting_presentation/read_only_isolation`, autorização de 08/10/2026. Comportamento de wrapper, gate 75 e timeout exercitado pela suíte offline existente `test_creditoparaveiculo_report_isolation.py`.

## Execução real

Runtime reutilizado: `/root/.hermes/hermes-agent-port-main-3f2afed3-mgs-20261021/.venv/bin/python`.
Harness local: `work/t_418fdc5d/run_tests.py`; bloqueia DNS externo e sockets não-loopback por audit hook. Loopback é permitido apenas para a integração local do renderer. Não houve mudança de identidade/profile para obter verde.

- Baseline: **3 falhas reproduzidas**. A primeira tentou alcançar o Drive real usando token sintético e foi interrompida no DNS; o HTTP 401 histórico NÃO foi provocado novamente. Logs: `baseline.txt/json`.
- Alvos após ajuste: **3 passed + 6 subtests**, zero tentativas externas. Logs: `targeted.txt/json`.
- Suíte relacionada final, sem exclusões: **85 passed + 19 subtests**, zero falhas/skips e zero tentativas externas. Arquivos completos: `test_shein_media_qa.py`, `test_ares_campaign_v3_daily_cpv.py`, `test_creditoparaveiculo_report_isolation.py`, `test_archive_stock_locations.py`. Logs: `related-final.txt/json`.
- Bateria ampliada IMG/VID/core e os dois módulos adicionais: **516 passed + 312 subtests; 1 failed**, em 41 arquivos sem exclusões. A falha remanescente é independente dos três casos: `test_shein_pipeline_hardening.py::HardeningTests::test_outer_http_failure_keeps_current_usage_headers_and_never_retries_post` usa `act_100` sintético sem isolar o guard de escopo no contexto Ares. Segue em **t_0bb85547**, assignee Zeus, sem modificar a produção. Logs: `regression.txt/json`. Não se declara suíte ampla ou repositório inteiro verde.
- Primeira tentativa de coleta ampla falhou por ausência do root no sys.path do harness; erro preservado em `collection-error.txt/json`, corrigido somente no harness, sem instalação.
- `git diff --check`: passou.

## Coordenação e rastreabilidade

O autosnapshot `8118475d4` incorporou a maior parte dos edits durante a execução. `full-tests.patch` preserva o delta integral dos dois testes contra o parent `c6d8ba519b7793677cd387df0757eba18dce3986`; não usar o diff de HEAD móvel como se fosse a entrega integral. Hashes finais dos testes e da skill em `final-hashes.json`. Mudanças de scripts/dados por outros processos no workspace compartilhado não foram incluídas nem revertidas.

Aprendizado procedural salvo na skill própria `software-delivery-methods`, seção `Contract-drift regressions`, com readback confirmado e teste relacionado final repetido após o último ajuste. Nenhuma memória USER foi alterada. Não houve deploy operacional; os arquivos em work são recibos/harness locais. Sem anexos enviados ao usuário.
