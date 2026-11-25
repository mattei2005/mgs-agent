# Moedas de exibição — novembro/2026 em diante

## Autoridade

Thread `1545426987756298340`, Rodolfo Mattei (`344196393512075265`):

- Pedido `1575221953269072054`: confirmar o entendimento antes de aplicar; retirar valores em BRL das visualizações desde novembro/2026, para todos os perfis. Despesas Gerais preserva moedas originais e conversão para USD; o cartão USD/BRL fica somente nessa área.
- Esclarecimento `1575224733438574733`: **CAD pode permanecer**. Supersede apenas a interpretação anterior de retirar CAD, não as fontes ou os cálculos.
- Escopo corrigido apresentado por Zeus em `1575224973071491083` e execução aprovada por Rodolfo em `1575226305702797474`.

## Política aprovada

- USD nos resultados, previsões, remunerações, comissões, saldos, pagamentos, gráficos e totais desde `2026-11`.
- CAD permanece nas receitas, relatórios e Conferência onde já é relevante, inclusive o equivalente USD e a cotação USD/CAD.
- BRL visível somente em Despesas Gerais, com a moeda original e o equivalente USD da despesa.
- Cartão USD/BRL com data/hora e controle existente somente em Despesas Gerais, não nos demais painéis.
- Outubro/2026 e competências anteriores conservam sua apresentação histórica.
- Não mudar faturamento, lançamentos originais, pisos, faixas de comissão, rateios, pagamentos, spreads ou inválidos. Exibição em USD não congela estimativas.

Isso supersede apenas os requisitos antigos de BRL visível para as novas competências: cartões, colunas secundárias, seletores, remuneração, extratos e observações SMS. As regras financeiras e a conservação das moedas originais continuam vigentes.

## Conversão, edição e fonte

1. Preferir o USD já calculado e salvo. Em particular, consumo SMS usa o débito USD registrado, agregado e por site; não aplicar uma segunda conversão ao seu BRL. Preservar correções assinadas e a separação entre consumo e crédito pré-pago.
2. Pagamentos/extratos continuam armazenados em centavos BRL. A interface desde novembro apresenta equivalentes USD pelo câmbio da competência selecionada, com a base explicitada; isso não transforma saldos antigos em contratos fixos USD nem modifica pagamentos registrados.
3. Novos valores digitados em USD e alterações intencionais convertem para a unidade original. O servidor valida a equivalência em centavos e rejeita uma cotação vencida, mantendo confirmação, beneficiário, competência e versão do lançamento.
4. Editar sem mudar o valor exibido deve conservar exatamente o original, mesmo quando a exibição em USD foi arredondada. Entradas nativas e despesas de funcionários mantêm fonte, conta, moeda de cobrança e precisão armazenada. Não renomear falsamente uma moeda de cobrança como USD.
5. Piso e faixas mostrados em USD devem ser identificados como **equivalentes**, não como novos valores fixos ou uma nova política de remuneração.
6. Recargas na Conferência são equivalentes informativos pelo câmbio da competência; os originais permanecem em Despesas Gerais e no armazenamento. Não criar consumo ou dedução a partir dessa observação.
7. Agrupar componentes convertidos antes de apresentar um total na mesma moeda. Ausência de conversão é indisponibilidade, não zero.

## Histórico e projeções auxiliares

Visões anuais usam USD no contexto `2026-11+`. A opção histórica em BRL, quando disponível no contexto anterior, não mostra competências desde novembro nem inclui seus valores silenciosamente em um total anual BRL. Usar os valores e câmbios próprios de cada mês, sem reconverter o ano inteiro pela taxa atual.

Textos livres e provas originais não são reescritos para inventar moedas. Campos monetários estruturados de aprovação/auditoria são projeções de exibição, nunca alteração do payload original; não inferir a competência financeira pela data em que o evento foi gravado. A revisão de uma proposta deve continuar mostrando exatamente o que será autorizado.

## Estado da execução

- Checkpoint: `ZEUS-FINANCE-USD-NOV-1575226305702797474`.
- Pacote isolado: `apps/finance-system/private/usd-display-1575226305702797474/`.
- Preparação e validação em andamento; publicação não deve ser inferida deste documento. Consultar o checkpoint e os recibos reais.
- Nenhuma migração monetária, transferência bancária ou lançamento financeiro produtivo integra este pacote.

## Fila posterior, separada desta publicação

Rodolfo `1575238236975014088` pediu concluir este trabalho antes de:

1. Verificar vestígios de **Gustavo - Gestor** e **Rafael - Gestor** em outubro e novembro, após as exclusões que ele informou ter feito. Auditoria inicialmente somente leitura; não apagar histórico ou inferir autorização para nova exclusão, credencial ou permissão.
2. Discutir metas de remuneração fixadas em USD em lugar da base atual. Não alterar piso, patamares, percentuais ou vigência durante a mudança de apresentação; os parâmetros da futura política ainda precisam ser definidos e confirmados.
