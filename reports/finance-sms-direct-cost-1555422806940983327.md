# SMS Funnel — reclassificação maio–setembro 2026

Autorizações: Rodolfo `1555422806940983327`; arredondamento individual de centavo `1555431089957376065`. Thread `1554520572950618173`.

## Resultado financeiro

- Compra/recarga e consumo passaram a ser fatos distintos.
- Maio–julho: 18 documentos históricos (principal + cinco gestores por mês) ganharam novas versões imutáveis pelo fluxo owner. Os registros originais de `finance_history` foram preservados.
- Agosto: recarga antiga preservada/arquivada; consumo direto reconhecido em seis fatos BRL, total `R$ 20.450,56`.
- Setembro: três recargas, total `R$ 95.000,00`, preservadas/arquivadas; consumo direto reconhecido em seis fatos BRL, total `R$ 105.669,60`.
- G002 usa `SEM_COMISSAO`: reduz CPV/empresa e não produz comissão externa.
- Nenhum pagamento, transferência ou estorno foi executado.

### Fechamentos históricos autenticados

- Maio: devido Geizian `R$ 215.787,85`; saldo `R$ 319,37`.
- Junho: devido `R$ 163.969,31`; saldo `R$ 752,68`.
- Julho: devido `R$ 76.597,58`; saldo `R$ 4.140,44`.

### Agosto nativo

- Revisão aplicada: `565`.
- 50% devido na Dash: `R$ 74.048,52`.
- Abertura: `R$ 4.140,44`.
- Pagamentos/movimentos preservados: `−R$ 73.316,14`.
- Saldo final: `R$ 4.872,82`.
- A planilha exibe `R$ 4.872,83`; Rodolfo aceitou a diferença de `R$ 0,01`, decorrente do ponto de arredondamento. Nenhum fato compensatório foi criado.
- Remunerações: Joe `R$ 3.000,00`; Nicolas `R$ 11.809,73`; Isliago `R$ 4.629,75`; Kelly `R$ 3.000,00`; Ícaro `R$ 3.000,00`.

### Setembro nativo

O valor segue o câmbio automático. No último readback autenticado da revisão `942`:

- 50% devido Geizian: `R$ 228.940,87`.
- Saldo anterior: `R$ 4.872,82`.
- Pagamento existente: `−R$ 12.310,19`.
- Saldo Geizian: `R$ 221.503,50`.

O dry-run/verify provou consumo fixo em BRL sob FX alternativo. As comissões individuais podem mover `R$ 0,01` dentro dos resultados explicitamente enumerados; a ponte da empresa usa os deltas efetivos e permanece exata.

## Ajustes dos gestores sem dupla contagem

A primeira aplicação registrou o total maio–agosto no ledger. O readback detectou que agosto já era carregado automaticamente pelo saldo anterior, pois o devido de agosto foi recalculado e o pagamento histórico permaneceu intacto. A correção automática editou os mesmos três IDs, com auditoria, para representar somente maio–julho:

- Joe: `+R$ 7,78` — `1988c8e3-ef8b-558b-ab5b-625df4ccb834`.
- Isliago: `+R$ 235,96` — `c4dba803-7d7d-5aae-a9ef-3faca0f8abce`.
- Nicolas: `+R$ 67,26` — `cfc637d7-b143-5ec0-9ba0-c987fc1847ad`.

Agosto completa os acumulados pelo saldo anterior:

- Isliago: `R$ 26,63` de agosto + `R$ 235,96` explícitos = `R$ 262,59`.
- Nicolas: `R$ 122,88` de agosto + `R$ 67,26` explícitos = `R$ 190,14`.
- Joe: agosto zero; acumulado explícito `R$ 7,78`.

O ledger final tem 28 entradas: as 25 anteriores foram preservadas e três ajustes ativos foram adicionados. Descrição pública: `Acerto SMS Funnel maio–julho 2026 · agosto carregado pelo saldo anterior`.

No último readback autenticado, os saldos pagáveis de setembro eram: Joe `R$ 3.043,41`; Nicolas `R$ 28.670,77`; Isliago `R$ 13.815,82`; Kelly `R$ 3.977,85`; Ícaro `R$ 3.000,00`; total `R$ 52.507,85`. Esses valores seguem o câmbio provisório.

## Aplicação e interface

- Novo fato: `direct_monthly_cost`, fechamento mensal fixo em BRL.
- A despesa SMS original fica arquivada, com recarga/cobranças e revisão preservadas.
- A UI mostra `Arquivadas / reclassificadas`, o valor da recarga e o consumo reconhecido.
- Reclassificações não exibem botão Restaurar, evitando reintrodução silenciosa e dupla contagem.
- Manager views recebem os custos dentro de Creditoparaveiculo.
- Pagamentos mostra os ajustes maio–julho e informa que agosto está no saldo anterior.

## Testes e validação

- RED/GREEN para custo direto: 5 testes Python focados PASS.
- Stage PostgreSQL restaurado: dry-run, FX alternativo, apply atômico, reparo do ledger e verify idempotente PASS.
- Node completo final: 228 testes; 227 PASS, 1 SKIP opcional, 0 falhas.
- Stage UI e testes de workspace/review: PASS.
- Browser público owner: recarga arquivada visível, CPV na visão do gestor, ajuste em Pagamentos, 0 erros JS e 0 falhas same-origin.
- APIs autenticadas: histórico, workspaces, cinco gestores e ledgers lidos após a escrita.
- Runtime final: oito arquivos locais/remotos com SHA256 iguais; `mgs-finance-dash.service`, socket e PostgreSQL ativos.
- A suíte Python completa ultrapassou o limite externo de 420 segundos em duas tentativas; os testes Python diretamente afetados, o stage integral, o Node completo e o readback real passaram. Não foi declarado PASS da suíte Python completa.
- Gateway Hermes não foi reiniciado.

## Backups e rollback

Backup remoto e cópia local verificados:

- `/home/zeus/mgs-finance-backups/sms-direct-1555422806940983327/finance-before.dump`
  - SHA256 `29ce6d22c810dcc7eee85873d89ea76c6ae5061d4d7b08eff61425fff4db0d5c`.
- `/home/zeus/mgs-finance-backups/sms-direct-1555422806940983327/code-before.tar.gz`
  - SHA256 `0acb88c505c86bf8ddd9bd5e5ce158b13c385929dc59a667ebd01bd7df37fa27`.
- UI: `/home/zeus/mgs-finance-backups/sms-direct-1555422806940983327/ui-visibility-before.tar.gz`.
- Banco isolado: `mgs_finance_sms_1555422806940983327`.
- Stage: `/var/tmp/mgs-finance-sms-1555422806940983327`.

Rollback de código usa os tarballs. O dump integral é evidência/restauração isolada; nunca deve ser restaurado sobre atividade financeira posterior sem nova reconciliação.

## Evidência

Diretório: `apps/finance-system/private/sms-direct-1555422806940983327/`.

Arquivos principais: `prepared.json`, `stage-dry-run.json`, `stage-fx-test.json`, `stage-apply.json`, `stage-verify.json`, `history-refresh-production.json`, `production-apply.json`, `production-repair-ledger.json`, `production-verify.json`, `production-readback.json`, `public-browser.json`, `final-runtime.json`, `ui-prepared.json`, `ui-stage.json`, `ui-published.json`.
