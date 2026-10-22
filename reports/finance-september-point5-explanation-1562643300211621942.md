# Setembro — ponto5/MonetizeMore: explicação e fonte viva

## Pedido e estado

Rodolfo1562643300211621942 solicitou explicar o ponto5. Somente leitura; nenhuma receita, regra, cadastro, rateio ou pagamento alterado. Dashprodutiva workspace-2026-09 revisão1656/cadastro19: M2 sem entradas de receita, os dois segmentosWantabrand comgross0; pontos1–4 preservados.

## Fonte do fechamento confirmada

Spreadsheet1ARyzDDEpVhlED6ndmHs1RC3pUlsJNQ20yTyZ6wSJVtA, abaRede MonetizeMore (M2), gid1868178333, relida ao vivo. O arquivo continua com7abas e sem a abaM2detalhado.

- wantabrand.com:30datas,30dias comreceita positiva, **USD703,20**.
- finance.wantabrand.com:30datas,4dias comreceita positiva emcentavos, **USD1,80**; cabeçalhoC1indica`g001-d`.
- Total de receita brutaGross Revenue: **USD705,00**, ausente naDash. Não é desconto nem ajuste dos pontos anteriores.

Os domínios já existem naDash. Ambos vinculados aoGestorGeorge/G001=Ícaro e redeM2. Principal cadastrado comoWantabrand US-CC-ES + Wantabrand BR-CAR-BR, compaísesUS/BR; FinanceWantabrand tempaísesUS/GB e estáINATIVO/nãoparticipa do rateio. Receita residual não autoriza sua reativação.

## Consulta adicional ao PubGuru, sem exigir outro export

Acesso read-only emapp.pubguru.com pelo handlelocalPubGuru M2 já aprovado. Identificador corporativo e senha preenchida pelovault, sem expor credenciais. Nenhum link comtoken foi persistido.

1. **Profit Attribution:**20janelas únicas e não sobrepostas, até3dias cada,10por domínio, cobrindo01–30/09. Todas as campanhas observadas caem na regraBOT/ChatPion: não apareceu prefixob01. Principal inclui/empty/,pg-13831,pg-13858,pg-13951,pg-16638,pg-19202,pg-19231,pg-22103,pg-22104,pg-22302,pg-5619,wantabrand-tarejta-us-funil. Finance inclui/empty/e pg-19326. Cinco janelasFinance retornaramHTTP204 sem linhas; registradas explicitamente e conciliadas contraNETWORK.
2. **Analytics/NETWORK,USD:** principal30linhas eFinance8linhas deAPI; comparação comos60dias/domínios daSheet, incluindo os diaszerados explícitos, passou60/60emcentavos. Totais somando osdias arredondados:703,20+1,80=705,00.
3. RawNETWORK: principal703.186466999999996 eFinance1.804891. ProfitAttribution somou703,17e1,79 porjanelas/campanhas, total704,96. Preservadas as bases e diferenças; não substituir o fechamento705,00 por704,96 nem criar uma despesa de0,04. A fonteNETWORK diária confirma osvalores daSheet.
4. Limite restante: campanha/BOT não identifica de forma comprovada o país/vertical operacional de cada parcela. O relatórioM2 consolidado não traz país; o cadastro contém múltiplas operações. Não deduzircountry apenas do nome de campanha, da geografia do visitante, do template nem de um rateio aprovado exclusivamente paraagosto.

## Próximo alinhamento

A receita estácomprovada e pode ser lançada pelos dias reais depois de definir aoperação:
- PrincipalUSD703,20: confirmar se pertence integralmente à operaçãoUS-CC-ES/BOT ou se existeparcelaBR-CAR-BR.
- FinanceUSD1,80: G001/Ícaro/BOTconsta na fonte; confirmar país/operaçãoUSouGB.

A indicaçãoBOT foi resolvida na fonte viva; não pedir novamente export somente para essa classificação. O valor devido aÍcaro não aumenta automaticamente emUSD705: aplicar a receita bruta na operação correta e recalcular deduções/imposto/lucro/remuneração pelas regras vigentes. Sem criar pagamento, sem duplicar receita e semreativarFinance no rateio.

## Evidências e recuperação técnica

Arquivos privados em`apps/finance-system/private/september-closing-1562564679400951829/`:point5-source-readback.json,point5-source-analysis.json,point5-before-*.json,point5_profit_september.json,point5_network_september.json,point5-live-m2-verification.json.

A primeira leitura apóslogin encontrouDOMainda em navegação; refeita somente a leitura, sem repetirsubmit. Um loteJavaScript excedeu o timeout5s do IPC; coleta recuperada com progresso porjanela. UmHTTP204 foi inicialmente passado ao parserJSON; identificado porstatus/bodyvazio, preservados6resultados e coletadas apenas14janelas faltantes. Encerramento:20/20janelas únicas,60/60controlesNETWORK/Sheet, nenhuma requisição de escrita financeira e nenhuma consulta pendente.

Aprendizado persistido em`mgs-finance-dashboard/references/pubguru-m2-revenue-reconciliation.md`: consultaexistente antes de exigir export, sanitização deURLs,204explícito, progresso deduplicado e distinção entrearredondamento/classificação/país. Checkpointprincipal atualizado paraexplicação do ponto5.
