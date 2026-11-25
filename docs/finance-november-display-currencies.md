# Moedas de exibição — novembro/2026 em diante

## Pedido e esclarecimento

Rodolfo1575221953269072054, thread1545426987756298340, pediu entendimento antes de aplicação: retirar valores emBRL das visualizações a partir de novembro2026, para todos os perfis, mantendo Despesas Gerais como exceção para moedas originais e conversão paraUSD. O cartãoUSD/BRL deve aparecer somente emDespesas Gerais.

Rodolfo1575224733438574733 esclareceu: **CAD pode permanecer**. Isso supersede exclusivamente a interpretação anterior de retirarCAD; não autoriza remover fontes/moedasoriginais nem modificar cálculos.

## Escopo de apresentação alinhado

- USD como moeda dos resultados, previsões, remunerações, comissões, saldos, pagamentos, gráficos e totais desde2026-11.
- CAD permanece nas receitas/relatórios/conferência onde jáé relevante, inclusive suas conversõesUSD e cotaçãoUSD/CAD.
- BRL visível somente emDespesas Gerais, preservando moedaoriginal da despesa e equivalenteUSD.
- CartãoUSD/BRL comdata/hora somente emDespesas Gerais; não nos demais painéis.
- Outubro2026 e anteriores permanecem comapresentaçãohistórica atual.
- Não alterar faturamento, registrosoriginais, piso/faixasdecomissão, rateios oupagamentos porinferência. A retirada deBRL da apresentação não elimina variações de estimativas emUSD.

## Estado

Execução autorizada porRodolfo1575226305702797474 após o esclarecimentoCAD. Preparação isolada em `apps/finance-system/private/usd-display-1575226305702797474/`;checkpointZEUS-FINANCE-USD-NOV-1575226305702797474. Nenhuma migração monetária autorizada.

## Critérios de conversão e edição

Pagamentos/extratos nativos continuam armazenados emBRLcentavos. De2026-11em diante, a interface mostra equivalentesUSD pelo câmbio da competência selecionada, explicitando a base; isso não transforma saldos históricos em contratosfixosUSDnemaltera dados de pagamentos. Novos/alterados valoresdigitadosemUSDconvertem para a unidadeoriginal pelo mesmo câmbio, com guarda servidor contra cotação vencida. Edição semmudançadevalor conservaexatamenteo valororiginal, mesmoque oUSDexibido tenhaarredondamento. Nenhuma transferênciaoulançamento real faz parte desta publicação.

Despesas de funcionários e entradas nativasBRL usam conversão deexibição reversível; fonte,conta,moeda de cobrança eprecisãooriginalpersistem. Despesas Gerais mantêmBRL eUSD e recebem o controleUSD/BRL existente. Moedas de cobrança preservadas internamente não devem ser falsamente renomeadas comoUSD.

Visões anuais usamUSD porpadrão quandoabertas no contexto2026-11+;opçãohistóricaemBRL, quando disponível no contexto anterior, não exibe valoresnovembro+ nem os inclui silenciosamente emtotalanualBRL. Valores históricos por competência continuam preservados. CADpermanece nasreceitas/relatórios. Textoslivres eprovasoriginais não são reescritos para inventar moedas; camposmonetários estruturados deaprovação/audit são projeções, nunca mudanças no payloadoriginal.
