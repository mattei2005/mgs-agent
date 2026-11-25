# Outubro2026 — Rede2: auditoria e proposta, sem aplicação

## Escopo

Sequência autorizada na conferência1575041627167391744, apósM2aplicada sob1575050438892585082. Fonte: `rede 2 SB`,gid869925501, spreadsheet `11u9cPHNj2KmpMxOkLNn9Pl8MQS7ALkNQXkjijlTQWNk`, integral e relida idêntica. Usar somente coluna original `Ad Exchange revenue`; helpers de gestor/site efooter são controles, não receitas adicionais.

681linhas deorigem →304grupos site/país/gestor/data;304fatosUSD já salvos naDash. Datas válidas01–31/10, valoresnuméricos, mediumválidog001–g006. GameZoneAdMX/BR segue o destinoBR/G002canônico; nenhum gestoroupaís foi inventado. M2/gastospermanecem preservados.

## Dois problemas distintos

### 1. Fincgriffin já tem dinheiro, mas está fora do cartãoRede2

USD538.63693988095000866768 já estão nos fatosfinanceirosUSD deFincgriffin. Os86fatos herdaram o partnercatalogadoSB Rede1 e não têm `source_network`, então a Conferência os exibe como **Receita sem separação comprovada por rede**, fora do cartãoRede2.

A planilha de fechamentoRede2 identifica a origem dessesUSD. Não adicionar538.64como nova receita: corrigir a classificação de fonte para o cartão e ajustar o gross ao fechamento. Preservar CADFincgriffin, site/catalog/networkmonthly e percentuaisjá configurados. Metadata da origem não autoriza trocar a regra de cálculo de inválidos herdada do catálogo.

Por isso, comparar diretamente o cartãoRede2USD209524.645149672887613645 com a planilha209970.26600474482565033512 aparenta falta de445.62085507193803669012, mas isso mistura exclusão visual e variação monetária. Os fatosUSD correspondentes, incluindoFincgriffin fora docartão, somam210063.28208955383762231863.

### 2. Valores de fechamento inferiores aos fatos diários importados

Valores arredondados para exibição, fonte versus Dashjáregistrada:

- CarCreditAd:0.02vs0.02 — sem correçãomonetária necessária; diferença bruta apenas−4e−18 de representação.
- CreditoParaVeiculo:182043.93vs182072.78.
- Fincgriffin:479.51vs538.64.
- GameZoneAd:27446.81vs27451.84.
- Total:209970.27vs210063.28; diferençadosvaloresexibidos−93.01.

Delta bruto calculado antes doarredondamento: **−USD93.01608480901197198351**, aproximadamente−93.02. Não esconder a diferença de umcentavo entre arredondar cadaendpoint e arredondar odelta. Corrigir pelos valoresdiários originais da planilha, não por um ajuste isolado de93.01/93.02.

63gruposgestor/dia com diferença visível emcentavos, distribuídos por18datas; os304grupos completos foramcomparados. A diferença da fonte de fechamento versus os snapshots diários está comprovada; a causa do reprocessamento no provedor não foi demonstrada e não deve ser inventada.

## Simulação isolada

`rede2-proposal-simulation.json`, semSQL/financewrites. Cópias das adiçõesUSD deCPV/Fincgriffin/GameZoneAd receberam os valores agrupadosfonte;Fincgriffin recebeu `source_network=SB Rede2` somente na cópia. CarCreditAdfoi preservado.302entradas diferem da cópia inicial por valor completo ou metadata (isso não significa302diferenças monetárias visíveis).

- CartãoRede2proposto:USD209970.266004744825650338 →209970.27.
- M2USD21.78, Rede1CAD,AV,Facebook,Google,SMS/recargas, despesasgerais, catálogo e regrasexistentes preservados.
- Todos5controles de gestor passam. RemuneraçõesBRL antes→proposta, mesmo câmbio congelado:Ícaro5930.17→5927.81;Isliago40641.64→40635.91;Joe10041.24→10040.37;Kelly26662.40→26658.48;Nicolas60341.21→60315.01. São efeitos calculados, não pagamentos ou deduções a inserir noledger.
- A simulação não é autorização nem implementação. Naaplicação, preservar osoriginais/linhagem poroverlay ou históricorecoveryauditado, usarbackup/restore/locks, impedirreplayque desfaça ofechamento e validar todososcontroles.

## Precisão de projeção

A primeira igualdade estrita entre a soma completa dosrawinputs e acard+unclassified detectou7.63e−18. Confirmadoque`decimalCompare`projeta cada item em18casas por truncamento. Reproduzindo exatamente essa projeção por item, ocarte orestante reconciliam exatamente. Nenhum dado/guard financeiro alterado; resíduo preservado como representação, não dinheiro faltante.

## Decisão pendente

Solicitar confirmação para corrigir emoutubro os grossUSD deCPV/Fincgriffin/GameZoneAd aosvaloresdiários dofechamento e classificar osUSDFincgriffin como fonteRede2naConferência, sem duplicação, preservandoCAD, atribuições, câmbios/regras e pagamentos. Sóentão aplicar. Rede1nãofoi auditada ainda.

## Evidências

`apps/finance-system/private/october-close-1575041627167391744/`:rede2-source/hash/recheck;rede2-source-rows;rede2-saved-rows;rede2-daily-comparison;rede2-summary;rede2-proposal-simulation;rede2-readback-proof. Baselinefinanceira real pósM2 em `private/m2-october-1575050438892585082/production-verify.json`; readback final manteve M2aplicada eRede2anterior semescrita.
