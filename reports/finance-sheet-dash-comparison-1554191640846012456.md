# Planilha versus dash — saldo Geizian agosto

## Escopo e esclarecimento do dono

Pedido somente leitura de Rodolfo1554191640846012456, complementado por1554191811155722261, thread1545426987756298340. Comparar exatamente o saldo da planilha e da dash; não aplicar ajustes. Rodolfo confirmou que os valores atuais da dash estão corretos e retirou o temaUSD451.60 da discussão de agosto: será tratado no **fechamento de setembro, realizado em outubro**. Esse esclarecimento supersede o escopo conversacional anterior de continuar trazendo a ponte bancária de agosto; não autoriza desfazer o fechamento aplicado, registrar crédito/adiantamento ou antecipar desconto. O relato anterior de que o fornecedor descontará no grossRede2 permanece para aquele fechamento, sem lançamento automático.

## Fontes e leitura

- Dois screenshots enviados pelo dono, analisados visualmente.
- Planilha principal16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak, abaAgosto2026, sheetId1736877861, lida inteira via SAcanônica emFORMULA/UNFORMATTED_VALUE/FORMATTED_VALUE. Sem escrita.
- Runtime: workspace-2026-08, revisão551; mesmo resultado dos controles de inválidos aplicados; `ledger()` canônico para Geizian, leitura transacional consistente. Sem escrita.
- Evidência temporária privada: `/root/.hermes/profiles/zeus/cache/scratch/sheet-dash-1554191640846012456/`. Não publicar dumps brutos da planilha: colunas de notas podem conter conteúdo sensível fora do escopo financeiro.

## Extrato: diferença exata exibida

- Recebimento/50% do lucro: planilhaG103=74428.39019009123BRL (74428.39), dashdue=7387362centavos (73873.62). Diferença exibida554.77BRL.
- Saldo anterior: planilhaG129=-1090.0485236818495BRL (-1090.05); dashprevious=-109005centavos. Iguais ao centavo.
- Movimentos: ambos-73316.14BRL. Mesmos sete lançamentos ativos: Canva+104.70; aluguel+405; internet+45.88; energia+284.02; renovaçãoPortal+60; pagamento-80000; estorno+5784.26. Lançamentos anulados na dash excluídos da soma, como no ledger canônico.
- Saldo final: planilhaG132=22.201666409388054BRL (+22.20); dashbalance=-53257centavos (-532.57). O cartão exibe532.57 como **crédito para compensar**, isto é, saldo negativo, não valor adicional devido ao sócio.
- Ponte exibida:22.20−554.77=-532.57. Não falta pagamento nem estorno e não há diferença de câmbio ou carry ao centavo.

## O que está diferente no cálculo

- InválidosRede1: planilhaL1=0.001 (0.10%), dash0.0010492546 (0.10492546%).
- InválidosRede2: planilhaM1=0.0012 (0.12%), dash0.0040106832 (0.40106832%).
- Fincgriffin: planilhaZW84 referenciaL1, eZT84=-1682.83×0.001; fórmulaAAH5 também referenciaL1. A dash usa a regraRede2. Esse vínculo divergente já existia antes do último fechamento e não foi corrigido na planilha nesta tarefa.
- YmonetizeK1: planilha0.0053 versus dash0.00536, sem receita dessa rede no fechamento atual; não é causa monetária material do saldo.
- USD/BRL5.11, USD/CAD1.41708, GBP/USD1.3357, revshare geral10% e imposto5% iguais. M2 continua com o fechamento anterior, não é o objeto de correção.

ConsolidadoUSD da planilha reconstruído dos43 blocos de lucro referenciados porI136, incluindoRV198/AFN198 e folhaO161; valores sem arredondar:

- Gross: planilha404891.635930500759291689; dash404891.6362196718892210669161. Diferença de precisão0.0002891711299293779161USD, menos de um centavo; não explica o saldo.
- Inválidos descontados: planilha519.687477118981697233703; dash780.4281649312594193718866727.
- Revshare descontado: planilha40211.7169505975999850484; dash40185.6429107334870301695024273.
- Receita após inválidos/revshare: planilha364160.231502784177609406897; dash363925.5651440071427715255270.
- Imposto: planilha18208.01157513920819616739; dash18196.27825720035713857627626.
- Mídia: planilha300296.57270058708360; dash300296.5727005870841487279844; igualdade monetária ao centavo.
- Despesas gerais: planilha7949.89612059681810; dash7949.896120596820550535908107; igualdade monetária ao centavo (40623.97BRL).
- Pessoal: planilha8575.265709165044; dash8569.465753424657534246575342. Planilha43819.61BRL versus dash43789.97BRL.
- Nicolas: planilhaP149=11703.763863121165BRL; dash11686.85BRL.
- Isliago: planilhaP151=4615.843910712212BRL; dash4603.12BRL.
- Demais pagamentos de pessoal iguais ao centavo. Percentuais/regras não foram alterados; as bases de lucro divergem depois do recálculo de inválidos.
- Resultado total: planilhaI136=29130.48539729598USD; dash28913.35231219822339943878233USD. Diferença217.13308509775660056121767USD, correspondendo a554.77503242476811443391114685BRL na metade, antes do arredondamento independente da apresentação.

## Ponte causal do último ajuste

Antes do último fechamento, dash mostrava metade74427.70BRL (precisão integral74427.70446973997519445291518). A planilha já estava aproximadamente0.6857203513BRL acima, devido principalmente ao vínculo de inválidosFincgriffin, pequenas diferenças de gross/precisão e arredondamento de pessoal. O último fechamento da dash reduziu a metade em554.0893120735BRL; a planilha não recebeu essas alterações. A diferença bruta integral de554.7750324BRL resulta em554.77BRL entre os dois saldos individualmente arredondados. Não chamar o resíduo preexistente de simples arredondamento: há vínculo de taxa distinto comprovado.

Conclusão: os sete movimentos e o saldo anterior batem; o que difere é a parcela de lucro, porque a planilha mantém os antigos inválidos e as comissões/imposto derivados dessas bases. Nenhuma alteração financeira foi feita nesta comparação, nem na dash nem na planilha.
