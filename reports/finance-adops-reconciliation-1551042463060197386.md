# Agosto 2026 — AdOps x dashboard: auditoria integral de fontes

Autoridade: Rodolfo `1551042463060197386`; thread `1545426987756298340`.
Fonte: https://docs.google.com/spreadsheets/d/1HoF7ihPzb0_oQIR5cZ0bsWd2b-_5jsHcKBalFi9HG7g/edit — oito abas completas, SA canônica, segunda leitura integral idêntica.
Dashboard: PostgreSQL produtivo MatteiInc01; workspace-2026-08 revision 391; master-ad-accounts revision 6. Fonte/ui-model produtivos coletados; dados de fonte imutável usados somente para resolver inputs legados. Nenhuma escrita financeira.
Execução: 2026-09-20T01:40:29.679955+00:00

## Decisão fornecida e limites

AV consolidado governa o pagamento deste fechamento, conforme Rodolfo. SB1 é CAD, SB2 USD. Comparações USD abaixo presumem AV USD/bruto; o cabeçalho AV não declara moeda nem bruto/líquido, portanto confirmar essa base antes de aplicar descontos. Não houve envio de dinheiro, alteração de billing, parâmetros, contas, receita ou gastos.
Primeiro diagnóstico/lista conforme a opção final do pedido. Correções financeiras aguardam fonte íntegra e resposta sobre as ambiguidades. PEND-092 permanece aberta.

## Bloqueios e inconsistências de fonte

- SB2: A796:E1909 é exatamente igual, linha a linha, à SB1: 1.114 linhas, 122.749,647894028879 CAD. A formatação muda para CA$ na linha 796. Os dados próprios iniciais A2:E795 somam USD 87.151,001420629774 para CPV, Fincgriffin e GameZoneAd. A soma cega da aba (209.900,649314658653) mistura moedas e duplicaria receita. O cálculo isolado dos primeiros 794 registros é hipótese auditada, não exclusão autorizada da fonte.
- AV: consolidado 106.459,31; detalhado recalculado 99.521,91. Falta finanzas.topfeed.fun (6.937,50) no detalhado; os demais sites somam diferença líquida -0,10. Footer literal $99,521,81 diverge do recálculo por 0,10.
- AV: quatro valores são textos malformados: G701=$1,419,47; G914=$1,309,12; G1893=$1,144,90; G2150=$1,145,41. O recálculo interpreta respectivamente 1419.47,1309.12,1144.90,1145.41, sem alterar originais. O total informado acima é condicionado a essa interpretação.
- Google: primeiros 12 dias de cada conta foram convertidos pelo locale pt_BR em 08/jan,08/fev,...08/dez; dias 13–31 permanecem strings US. O total mensal independe da reinterpretação; comparação diária usa explicitamente a hipótese de 01–31/08. Nenhuma data foi escrita.
- M2: consolidado 4.611,87 coincide por arredondamento com o novo detalhado 4.611,868541642177. Não coincide com a captura anterior do browser Profit Attribution (5.148,75), que não governa esta nova fonte automaticamente.
- M2: todos os registros detalhados trazem wantabrand.com, incluindo pg-19326 (7,83112536661), que coincide dia a dia com finance.wantabrand.com no consolidado (desvio máximo 0,004244140909). Origem por domínio deve ser confirmada; não reescrever silenciosamente o Domain.
- LyzmoFinanzas: fonte traz conta -02, USD74,51 (04/08 2,49;05/08 72,02); dashboard traz mesmos dias/valores em -01, ID1818460511984988. Sem Account ID na sheet, coincidência não prova identidade. Resolver ID/nome antes de remapear.
- Cliquet principal/Finanzas: apenas receitas SB a partir de 21/08, sem nenhum domínio Cliquet no AV entregue; dashboard contém receita de 01–20/08. Não substituir receita anterior por zero antes de confirmar o fechamento da antiga rede.
- Fincgriffin: relatório está na SB2/USD, enquanto cadastro de agosto aponta SB Rede1. Separar acerto de receita da correção de cadastro histórico/regras.
- Cinco sites com resíduos SB1 não possuem bloco no workspace de agosto: Boostingecon,Cephyric,DicasFinancas,Escalatepower,Mavroa. Cadastro não pode ativar rateio silenciosamente.

## Gastos — resumo e controle

- Facebook: 825 registros,48 nomes distintos,zero duplicatas account/day/currency;47 matches exatos,36 com diferença mensal,2 com total igual e dias diferentes,9 com todos os dias iguais;1 nome sem match (-02 Lyzmo). Há ainda a contraparte -01 com gasto na dash e ausente da fonte.
- Facebook: dash USD286.088,46; sheet USD286.368,15; delta +279,69. Esse delta trata o valor Lyzmo como mesmo gasto econômico, sem resolver a identidade.
- Google Gamingadx-US-01: R$11.216,30 → R$11.207,23, delta -9,07; Mattei 1/GameZoneAd: R$60.019,90 → R$59.967,01, delta -52,89. Total Google delta -61,96 BRL.
- Controle independente: inputs FB + inputs Google/USDBRL reproduzem o gasto consolidado da dash USD300.082,189594663086 com diferença menor que 1e-20. Nenhum gasto positivo legado ficou sem classificação: os únicos slots monetários sem source_links de conta são os Google R$ dos dois sites.

### Facebook — todas as diferenças mensais, USD (dash → fonte)

- Cliquet-BR-CAR-BR-01: 424,93 → 424,95; delta 0,02; 2 dias diferentes.
- Creditoparaveiculo-BR-CAR-BR-02-G002: 4.863,63 → 4.864,47; delta 0,84; 5 dias diferentes.
- Creditoparaveiculo-BR-CAR-BR-03-G005: 12.862,45 → 12.865,58; delta 3,13; 6 dias diferentes.
- Creditoparaveiculo-BR-CAR-BR-04-G003: 8.745,15 → 8.750,24; delta 5,09; 7 dias diferentes.
- Creditoparaveiculo-BR-CAR-BR-05-G006: 193,38 → 298,98; delta 105,60; 3 dias diferentes.
- Creditoparaveiculo-BR-CAR-BR-06-G004: 6.574,98 → 6.579,61; delta 4,63; 6 dias diferentes.
- Creditoparaveiculo-BR-CAR-BR-07-G001: 0,00 → 12,04; delta 12,04; 1 dias diferentes.
- Creditoparaveiculo-BR-CAR-BR-13-G006: 7.611,94 → 7.613,29; delta 1,35; 6 dias diferentes.
- Creditoparaveiculo-BR-CAR-BR-14-G001: 12.684,32 → 12.677,96; delta -6,36; 7 dias diferentes.
- Creditoparaveiculo-BR-CAR-BR-16-G006: 179,48 → 74,57; delta -104,91; 1 dias diferentes.
- Eggbev-BR-CAR-BR-01: 434,41 → 434,45; delta 0,04; 1 dias diferentes.
- Eggbev-US-CC-EN-01: 1.802,54 → 1.803,15; delta 0,61; 1 dias diferentes.
- Eggbev-US-CC-EN-03 (FAX-US-02): 90.579,91 → 90.626,73; delta 46,82; 7 dias diferentes.
- Financeadx-CA-CC-EN-01: 2.001,92 → 2.002,82; delta 0,90; 3 dias diferentes.
- Financeadx-MX-CC-ES-01: 7.010,88 → 7.014,18; delta 3,30; 3 dias diferentes.
- Financeadx-US-CC-EN-01: 4.250,82 → 4.251,39; delta 0,57; 3 dias diferentes.
- Fincgriffin-US-CAR-EN-01 g006: 1.006,43 → 1.006,97; delta 0,54; 2 dias diferentes.
- Helixenit-MX-CC-ES-01: 18.859,08 → 18.939,81; delta 80,73; 8 dias diferentes.
- Infinitynexx-MX-CC-ES-01: 7.851,59 → 6.914,27; delta -937,32; 21 dias diferentes.
- Infinitynexx-MX-CC-ES-01-G001: 0,00 → 996,08; delta 996,08; 17 dias diferentes.
- Lyzmo-GB-CC-EN-01: 1.293,74 → 1.293,84; delta 0,10; 1 dias diferentes.
- Lyzmo-US-CC-EN-01: 2.885,83 → 2.887,31; delta 1,48; 3 dias diferentes.
- Newsoun-US-CC-EN-01: 1.698,02 → 1.698,15; delta 0,13; 2 dias diferentes.
- Openzed-US-CC-EN-01: 22.900,02 → 22.931,44; delta 31,42; 8 dias diferentes.
- Openzed-US-CC-EN-03: 2.977,47 → 2.987,15; delta 9,68; 3 dias diferentes.
- OpenzedFinanzas-ES-CC-ES-01: 3.355,06 → 3.356,76; delta 1,70; 2 dias diferentes.
- OpenzedFinanzas-ES-CC-ES-02: 2.042,14 → 2.044,82; delta 2,68; 3 dias diferentes.
- OpenzedFinanzas-ES-CC-ES-03: 4.188,69 → 4.190,47; delta 1,78; 5 dias diferentes.
- OpenzedFinanzas-US-CC-ES-01: 9.295,99 → 9.301,74; delta 5,75; 17 dias diferentes.
- Topfeed-US-CC-EN-01: 6.177,21 → 6.180,81; delta 3,60; 5 dias diferentes.
- TopfeedFinanzas-US-CC-ES-01: 5.485,25 → 5.485,68; delta 0,43; 4 dias diferentes.
- Wantabrand-BR-CAR-BR-01: 981,69 → 982,51; delta 0,82; 6 dias diferentes.
- Wantabrand-US-CC-ES-01: 5.819,62 → 5.822,24; delta 2,62; 4 dias diferentes.
- Yolokfx-US-SHEIN-EN-01-G002: 496,72 → 497,89; delta 1,17; 2 dias diferentes.
- Zytiva-GB-CC-EN-01: 15.973,58 → 15.973,66; delta 0,08; 1 dias diferentes.
- Zytiva-GB-CC-EN-02: 7.754,71 → 7.757,26; delta 2,55; 2 dias diferentes.

### Diferenças de conta/dia que não devem ser duplicadas

- Infinitynexx conta sem G001 tem 7.851,59 (6.859,76 principal +991,83 complementar), mas fonte 6.914,27. Conta -G001 fonte996,08/dash0. Site total dash7.851,59/fonte7.910,35: aumento líquido58,76, não996,08. Há deslocamento de datas no bloco complementar.
- CPV05-G006: 193,38→298,98; CPV16-G006:179,48→74,57. Em15/08,104,91 pertence à05 no relatório, mas está na16 na dash; os demais deltas da05 somam0,69.
- EggbevFinanzas-US-CC-ES-01: total542,12 igual;38,36 está no15/08 na dash e16/08 na fonte.
- NewsounFinanzas-US-CC-ES-01: total299,86 igual;41,25/38,94/33,56 estão em17–19/08 na dash versus18–20/08 na fonte.

## Receitas por fonte

- SB1: CAD292.199,24.
- SB2: USD87.151,00, somente segmento inicial de794 registros, pendente de confirmação de integridade.
- AV consolidado:106.459,31; moeda/basis bruta assumida para a ponte.
- M2 consolidado: USD4.611,87; detalhado direto518,684613060005 e BOT4.093,183928582172 (inclui pg-19326).
- M2 Wantabrand principal: USD5.150,28→4.604,04; financeiro7,40→7,83; delta combinado-545,81. Separação de país/vertical não existe no novo detalhado e não deve ser inventada a partir de campaign sem regra aprovada.

## Ponte de receita por site — condicionada, não plano de escrita

USD/CAD da dash: 1.39984991. Fórmula: SB1_CAD/H1 + SB2_USD + AV_consolidado_USD + M2_USD. Comparado ao gross USD real da dashboard, incluindo segmentos complementares. Fontes acima incompletas/ambíguas não justificam zerar dados históricos.
Formato: site — dash → soma de fontes; delta. Valores exibidos arredondados individualmente, cálculo interno Decimal completo.

- AutoCreditAdx: 0,00 → 0,02; delta 0,02; SB1 CAD=0.026827498720158483, SB2 USD=0, AV=0, M2=0.
- Boostingecon: 0,00 → 0,00; delta 0,00; SB1 CAD=0.0043464216824949066, SB2 USD=0, AV=0, M2=0.
- Cephyric: 0,00 → 0,70; delta 0,70; SB1 CAD=0.9746921903385862764, SB2 USD=0, AV=0, M2=0.
- Cliquet: 280,53 → 1,25; delta -279,28; SB1 CAD=1.75256413206918916616, SB2 USD=0, AV=0, M2=0.
- Cliquet Finanzas: 188,42 → 6,60; delta -181,81; SB1 CAD=9.2426871054233699345, SB2 USD=0, AV=0, M2=0.
- Contecta Geral: 0,00 → 0,01; delta 0,01; SB1 CAD=0, SB2 USD=0, AV=0.01, M2=0.
- CreditoParaVeiculo: 71.819,60 → 71.815,90; delta -3,70; SB1 CAD=0, SB2 USD=71815.89944941302986215, AV=0, M2=0.
- DicasFinancas: 0,00 → 0,01; delta 0,01; SB1 CAD=0.011813807424636313, SB2 USD=0, AV=0, M2=0.
- Ducapes: 0,07 → 0,07; delta 0,00; SB1 CAD=0.100605846242505327, SB2 USD=0, AV=0, M2=0.
- Ducapes Finance: 11,04 → 11,03; delta -0,01; SB1 CAD=3.280214119808277284, SB2 USD=0, AV=8.69, M2=0.
- Eggbev: 138.660,69 → 138.642,77; delta -17,92; SB1 CAD=110118.0750453818940075753, SB2 USD=0, AV=59978.57, M2=0.
- Eggbev Finanzas: 243,66 → 243,65; delta -0,01; SB1 CAD=192.1596800788564854857, SB2 USD=0, AV=106.38, M2=0.
- Escalatepower: 0,00 → 0,24; delta 0,24; SB1 CAD=0.33307446480275214, SB2 USD=0, AV=0, M2=0.
- FinanceAdx: 15.894,11 → 15.893,45; delta -0,66; SB1 CAD=22248.44027057649760993155, SB2 USD=0, AV=0, M2=0.
- FinanceTopFeed: 7.150,96 → 7.348,47; delta 197,51; SB1 CAD=5689.01755732373957919966, SB2 USD=0, AV=3284.45, M2=0.
- Fincgriffin: 1.682,91 → 1.682,83; delta -0,08; SB1 CAD=0, SB2 USD=1682.833425801682038186, AV=0, M2=0.
- GameZoneAd: 13.654,35 → 13.652,27; delta -2,08; SB1 CAD=0, SB2 USD=13652.2685454150618611535, AV=0, M2=0.
- GamingAdx: 1.481,63 → 1.467,99; delta -13,64; SB1 CAD=2054.967982864882776893, SB2 USD=0, AV=0, M2=0.
- Helixenit: 25.024,18 → 25.022,42; delta -1,76; SB1 CAD=35027.63495893131438722239, SB2 USD=0, AV=0, M2=0.
- Infinitynexx: 10.040,68 → 10.040,99; delta 0,31; SB1 CAD=14055.8791614766574241208, SB2 USD=0, AV=0, M2=0.
- Lyzmo: 4.254,11 → 4.225,87; delta -28,23; SB1 CAD=4533.72603204632749914675, SB2 USD=0, AV=987.15, M2=0.
- Lyzmo Finanzas: 109,15 → 109,13; delta -0,02; SB1 CAD=73.01090104726590716203, SB2 USD=0, AV=56.97, M2=0.
- Marevelx: 273,84 → 273,80; delta -0,03; SB1 CAD=383.28531989531738752369, SB2 USD=0, AV=0, M2=0.
- Mavroa: 0,00 → 0,03; delta 0,03; SB1 CAD=0.04027965486131173, SB2 USD=0, AV=0, M2=0.
- Newsoun: 3.106,33 → 3.095,41; delta -10,92; SB1 CAD=2258.24871317977219526603, SB2 USD=0, AV=1482.2, M2=0.
- Newsoun DE: 550,42 → 549,57; delta -0,85; SB1 CAD=326.9863167684613519409, SB2 USD=0, AV=315.98, M2=0.
- Newsoun Finanzas: 175,89 → 175,88; delta -0,01; SB1 CAD=132.12449010842867663634, SB2 USD=0, AV=81.5, M2=0.
- Openzed: 40.671,17 → 40.550,39; delta -120,79; SB1 CAD=39066.4731078777199419039, SB2 USD=0, AV=12642.77, M2=0.
- Openzed Finanzas: 26.611,42 → 26.491,18; delta -120,23; SB1 CAD=24682.32775899474963128953, SB2 USD=0, AV=8859.06, M2=0.
- Portal Relevante: 0,00 → 0,01; delta 0,01; SB1 CAD=0.0129610924768727044, SB2 USD=0, AV=0, M2=0.
- SPE: 8,53 → 13,89; delta 5,36; SB1 CAD=0, SB2 USD=0, AV=13.89, M2=0.
- TopFeed: 0,00 → 0,01; delta 0,01; SB1 CAD=0.0146855180642164596, SB2 USD=0, AV=0, M2=0.
- TopFeed Finanzas: 8.307,77 → 8.309,98; delta 2,21; SB1 CAD=1921.26539429067199862260, SB2 USD=0, AV=6937.5, M2=0.
- Vizioid: 0,00 → 0,04; delta 0,04; SB1 CAD=0.04920352733113962137, SB2 USD=0, AV=0, M2=0.
- Wantabrand Finance: 7,40 → 7,83; delta 0,43; SB1 CAD=0, SB2 USD=0, AV=0, M2=7.83.
- Wantabrand US-CC-ES + Wantabrand BR-CAR-BR: 5.150,28 → 4.604,04; delta -546,24; SB1 CAD=0, SB2 USD=0, AV=0, M2=4604.04.
- WavesBee: 0,00 → 0,09; delta 0,09; SB1 CAD=0.13161294564043502108, SB2 USD=0, AV=0, M2=0.
- Xyvlov: 1.080,10 → 1.080,20; delta 0,10; SB1 CAD=1512.1194146623062966083, SB2 USD=0, AV=0, M2=0.
- Yolokfx: 548,27 → 548,07; delta -0,20; SB1 CAD=767.213788941438598016, SB2 USD=0, AV=0, M2=0.
- Zuout: 756,65 → 833,29; delta 76,64; SB1 CAD=0, SB2 USD=0, AV=833.29, M2=0.
- Zuout Finanzas: 508,38 → 570,38; delta 62,00; SB1 CAD=7.94967029431720605, SB2 USD=0, AV=564.7, M2=0.
- Zytiva: 32.774,20 → 29.522,54; delta -3.251,66; SB1 CAD=26981.2302014816386951465, SB2 USD=0, AV=10248.17, M2=0.
- Zytiva Finanzas: 165,98 → 165,99; delta 0,01; SB1 CAD=151.1245141904495936081, SB2 USD=0, AV=58.03, M2=0.

Total condicional: dash USD411.192,71 → fontes USD406.958,30; delta USD-4.234,41.
Não é lucro/pagamento final: falta confirmar fontes, atribuição e bases antes de recalcular inválidos/revshare/imposto/comissões.

## Evidência e validação

- Planilha: metadata.json, oito snapshots com sheetId, formatted-anomalies.json; segundo GET integral idêntico.
- Dashboard: dashboard-db.json,source.json,ui-model.json; revisão produtiva391/cadastro6.
- Análise: spend-reconciliation.json (todas as diferenças diárias),revenue-source-reconciliation.json,revenue-vs-dashboard.json.
- Parser inicialmente recusou AV strings monetárias inválidas (Decimal ConversionSyntax), foi corrigido para interpretação explícita/registrada e reexecutado; nenhum fallback silencioso e nenhuma mutação na fonte.
- Modelo real do turno: logs mostram openai-codex/gpt-6-astra-900k e política financeira aplicada à thread.
- Continuidade: checkpoint ZEUS-FINANCE-ADOPS-1551042463060197386; procedimento adops-monthly-source-reconciliation.md; autoridade AV consolidado registrada.

## Respostas necessárias para aplicação

1. Confirmar o descarte lógico do trecho duplicado SB2 A796:E1909 e se os primeiros794 registros são o relatório completo da rede2.
2. Confirmar AV USD/bruto antes de aplicar novamente inválidos/revshare; consolidado já escolhido como autoridade.
3. Obter a receita anterior de Cliquet/principal e Finanzas (01–20/08) ou confirmar a ausência efetiva de pagamento.
4. Identificar numeric Account ID de LyzmoFinanzas-02; não presumir que é a -01 cadastrada.
5. Confirmar pg-19326 como Finance Wantabrand e os critérios de país/vertical para M2 caso o fechamento exija essa distribuição.
6. Definir cadastro dos pequenos resíduos de agosto sem rateio e ajuste da rede histórica de Fincgriffin.
As diferenças determinísticas de gastos foram quantificadas integralmente para o lote de correção, sem mudar o sistema antes desta lista solicitada.
