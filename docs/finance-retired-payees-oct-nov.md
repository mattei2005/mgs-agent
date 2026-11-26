# Beneficiários excluídos — outubro e novembro/2026

## Autoridade e limite

Rodolfo1575374541897601075, thread1575312872190382223, autorizou corrigir somente o vestígio visual dos cadastros `personnel|150` (Gustavo) e `personnel|152` (Rafael) na lista deBeneficiário emPagamentos de2026-10 e2026-11. Pedidooriginal de conferência1575238236975014088; auditoria1575364424246763643 comprovou arquivamento/inatividade/devidozero e ausência de movimentos dessascontrapartes nosdoismeses.

A autorização não inclui apagar cadastros,histórico,ledger,credenciais ou permissões; não muda salários/comissões,cotações,saldos,novascompetências oua regra de metasUSD.

## Contrato de apresentação

- Filtrar somente os dois IDs exatos, nos dois meses exatos, no renderizador `public/operations.js`. Não depender de nome, prefixo ou comparação numérica deIDs.
- Outros beneficiários e demais meses permanecem inalterados. Geizian e os cinco gestores continuam selecionáveis conforme o escopo existente de cada identidade.
- Payloads daAPI,partes financeiras,histórico e validações do servidor permanecem intactos. A filtragemvisualnãoérevogaçãodeacesso.
- Se um cadastro antigo já estiver selecionado numa consulta histórica e o usuário mudar de mês, preservar a identificação verdadeira da contraparte. Mostrar a opção corrente como hidden/disabled em vez de selecionar silenciosamente Geizian enquanto os valores pertencem a outra pessoa; não oferecer o cadastro excluído como nova escolha.
- Não regravar qualquer cenário financeiro ou lançamento para produzir esse efeito visual.

## Estado

Candidato isolado eTDD verificados: dois novos testes falharam no original e os17testesfocados passaram após o ajuste. Stage com38visões autenticadas1440/390,owner/Geizian/cincogestores,agosto/setembro preservados,outubro/novembro filtrados,quatro consultas históricas diretas mantidas,seleção histórica preservada,zeroerroJS/POSTfinanceiro. Auditoria de dependências deprodução:zero vulnerabilidades.

Publicado e validado em produção: release `payment-party-filter-1575374541897601075` em estado `committed`, com backups exatos e readback dos três destinos. Gates completos: Node320/320 ePython259/259, semskips, no mesmo candidato congelado. Stage38visões e produção38visões HTTPS seminterceptação, nosdoisviewports e seteidentidades viaownerpreview; quatro consultas históricas diretas mantidas emcadafase. Sessões temporárias encerradas e401confirmado.

Fingerprint sob os próprios locks da publicação comprovou os326cenários,40registros dehistórico eledgerdepagamentos exatamente inalterados. Não houveescritafinanceira,reprocessamento,cadastro,credencialoumudançadepermissão. Únicosarquivosativosalterados: `public/operations.js` local/remoto e oteste local existente `tests/finance-ops.test.mjs`. Serviço financeiro reiniciado pelocontrolador; nenhumgateway,bancoousocket reiniciado.

Evidência final:`reports/finance-retired-payees-1575374541897601075.md`;pacote:`apps/finance-system/private/payment-party-filter-1575374541897601075/`;journal/backups:`apps/finance-system/private/releases/payment-party-filter-1575374541897601075/`. Ponto1encerrado;nenhumponto2 aplicado.

O ponto2 (piso/meta nominalUSD,percentuais evigência) continua separado,semdefiniçãoouaplicação.
