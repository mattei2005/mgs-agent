# Rechecagem não-SHEIN e prints outubro/novembro

Pedidos Rodolfo na thread1545426987756298340:1569045389707841771(pergunta sobre outras contas),1569045803060699278(quatro prints de outubro) e1569046077095547043(três prints01–07/11). Somente leitura financeira neste turno.

## Comparação dos prints

Foram transcritas as sete imagens, preservando nomes e moedas exibidas; o período vem da confirmação do usuário, pois o seletor não aparece. As identidades foram resolvidas por nomes exatos únicos contra as coletas oficiais anteriores, com IDs/currencyUSD comprovados pela API. Sobreposições entre imagens foram deduplicadas em código; contagens52outubro/46novembro conferem com os rodapés.

- Outubro:52contas, somaUSD869020.28; todas as52linhas coincidem com a fonte aplicada e com a Dash corrigida. Zero diferença por conta.
- Novembro01–07:46contas, soma dos printsUSD140835.57; Dash salvaUSD140830.86; diferençaUSD4.71.
- Nova consulta oficial de detalhes dos mesmos46IDs, sem redescoberta global: soma diária=aggregateUSD140835.64, zero erro. Difere dos prints emUSD0.07, concentrados emMavroaG003+0.03,YoloG005+0.02,YoloG004+0.01,YoloG003+0.01. Diferença da fonte nova paraDashUSD4.78. Esta atualização não foi aplicada neste turno.
- A leitura inicial deHelixenit/outubro foi corrigida mediante ampliação real da imagem:USD3370.51, não3570.51. Nenhuma alteração financeira foi feita a partir do OCR inicial. IDs naURL sofreram leituras inconsistentes nas descrições de imagem e não foram usados como identificadores de linha; osIDs vieram daAPI.

Evidência: `screenshots.txt`, `screenshots-deduped.json`, `screenshot-comparison.json` e `november-fresh-details.json` em `apps/finance-system/private/non-shein-review-1569045389707841771/`.

## Contas fora de SHEIN

Leitura nova doPostgreSQL eaccountModel implantado, mesesoutubro/novembro, revisões1509/289. Outubro22contas positivasforaSHEIN;novembro16. Custos positivos abrangem509/89registros conta/dia. Todos chegam ao sitecorrespondente. A conferência completa deve distinguir esse destino de atribuição individual.

Mapeamentos conferidos:
- CPV: códigosG001Ícaro,G002MGS,G003Isliago,G004Joe,G005Kelly,G006Nicolas. O nome contémBR; o modelo legado mantém âncora internaUS, mas o renderizador canônico remapeia o bloco e apresenta Gastos·BR para todososgestores. Não classificar esse identificador interno isolado como novo erro de atribuição.
- Eggbev,FinanceAdx,Lyzmo:Nicolas.
- Openzed,OpenzedFinanzas,Zytiva:Isliago.
- Helixenit:Kelly.
- Topfeed-US-CC-EN-01→FinanceTopFeed:Joe.
- Infinitynexx semG:Joe;conta-G001:Ícaro, conforme exceção explícita previamente confirmada.

## Pendência real: Zuout

Conta`908704754163659`,nomeexato`Zuout-US-CC-EN-01`,sem sufixoG:
- Outubro:USD1534.43;
- Novembro01–07:USD203.28.

Valor/conta/data/siteUS conferem;gasto está efetivamente debitado do siteZuout. Porém oinput tem `managers:[]`,o catálogo/fato mantêm `NÃO MAPEADO`,não há `manager_bindings` e a visão deNicolas mostra Gastos·US=0paraZuout. Portanto não é correto declarar toda a atribuição foraSHEIN validada.

A regra canônica de receita `data/finance-gam-revenue-rules.json` identifica `zuout.com`/`finanzas.zuout.com` com donoG006. As decisões de receita de setembro também preservam G002/G006conforme tags; isso não fornece por si só uma autorização nova para deslocar o custo desta conta semG. Evidência operacional histórica associa oBOTZuoutaNicolas. Recomendação: confirmar/aplicar o vínculo desta conta aNicolas/G006nos doisperíodos, preservando os valores/total do site e receitas. Não inferirMGSautomaticamente a partir do vazio.

A consulta direta da mensagem antiga1549590981836275724retornou404no destino consultado; foram usados registry,fontescanônicas e história recuperada como referência. Essa lacuna de mensagem individual não apaga a regra canônica ativa nem prova uma decisão de custo diferente.

## Retificação da conclusão anterior

Os2108/455controles anteriores reconciliaram as contas que já tinham gestor mapeado; o construtor deexpectativas pulava `managers:[]`. A igualdade dos controles não cobria a completude da propriedade das contas. As correções efetivas nos três sitesSHEIN continuam verificadas, mas a afirmação ampla de ausência de pendências fora deles precisa ser qualificada porZuout. Não reexecutar as correções já concluídas nem chamar esta conta de gasto faltando no total.

Procedimento atualizado e validado na skillmgs-finance-dashboard/references/current-manager-tabs-reconciliation.md:todo gasto positivo semgestor é uma exceção explícita;validar regra independente e não promover ausênciaaG002 ou zero esperado. Acrescentado cuidado com país legado versus grupo renderizado.

## Estado e decisão

Nenhum valor financeiro,credencial,campanhaoupagamento alterado. Pendentes:decisão sobre vínculo deZuout e autorização para novo refreshnovembroUSD4.78,sem forçar um screenshot já ultrapassado pela fonte. A auditoria dos prints está completa. Evidência de destinos atuais em `live-account-destinations.json` e `non-shein-account-summary.json` no pacote privado.
