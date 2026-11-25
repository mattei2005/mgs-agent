# Outubro2026 — pontoM2: receita ausente na Dash

## Escopo e fontes

Continuação autorizada por Rodolfo1575047241696288920, após a conferênciaFB/Google da iniciativa1575041627167391744. Próximo ponto da ordem éM2; Rede2/Rede1 não foram antecipadas.

Fonte de fechamento: planilha `11u9cPHNj2KmpMxOkLNn9Pl8MQS7ALkNQXkjijlTQWNk`, aba `Rede MonetizeMore (M2)`, gid1868178333, lida inteiraA1:C1911 pela SA e relida sem alteração. Rótulos literais preservados: `finance,wantabrand,com:` e `wantabrand,com:`; são etiquetas com vírgulas, não domínios válidos a cadastrar. Identidades canônicas conhecidas e corroboradas no PubGuru: `finance.wantabrand.com` e `wantabrand.com`.

Destino: PostgreSQL produtivo, workspace-outubro revisão2178, módulo implantado `buildSimpleReview`, todos124fatos dos blocosM2/Wantabrand e adições relacionadas. CartãoM2=no_data/0entradas; nenhum fato positivoM2. Os sites existentes continuamM2, FinanceINATIVO e principalATIVO; não alterar rateio por receita residual.

## Diferenças confirmadas

- Wantabrand principal:01/10USD12.68 +02/10USD8.61 =USD21.29 na fonte; nenhuma receita registradaM2 naDash; faltamUSD21.29.
- FinanceWantabrand:27/10USD0.49; nenhuma receita registradaM2 naDash; faltamUSD0.49. Bloco da fonte marcado `g001-d`.
- Total:USD21.78brutos, três lançamentos positivos em suas datas reais.62controles domínio/data do mês incluem os59dias/domínio com zero numérico, que não precisam virar lançamentos fictícios.

## Conferência independente PubGuru

Login normal com handle de vault `PubGuru M2`, origemapp.pubguru.com. Tokens/URLs autenticados permaneceram somente na memória da página, não nos artefatos. ConsultasGETsóleitura.

- Analytics Report, Revenue SourceNETWORK, USD,01–31/10, doisdomínios: principalUSD21.291640000000001; FinanceUSD0.491522. Cada valor diário publicado na planilha coincide com o NETWORK arredondado a centavos. NETWORK omite7dias do principal e26doFinance; registrados como ausência de linha, em contraste com oszeros explícitos da planilha, não como zeros inventados pela API.
- Profit Attribution,utm_campaign,22janelas únicas de até3dias,31dias exatos por domínio sem lacunas/sobreposição: principalBOTUSD21.3800000000000007, direto0; FinanceBOTUSD0.49. Regra permanente b01*direto; demaisBOT. RevenueSourceNETWORK eplanilha continuam a base monetária, não o subtotal estimado da atribuição.
- A diferença do relatório de atribuição não foi imputada como receita adicional: serve para confirmar a estratégiaBOT, não para substituir o fechamento escolhido por Rodolfo. Não alegar geografia ou gestor exclusivamente a partir dos parâmetros de campanha.

## Decisão necessária antes de aplicar

A fonte traz receita diária e Financeg001-d; não fornece todas as dimensões operacionais do principal. Em setembro, Rodolfo1562663899969617922 autorizou, **somente naquela competência**:
- principal:US-CC-ES / BOT / G001-Ícaro;
- Finance:US-CC-EN / BOT / G001-Ícaro.

Proposta para outubro: mesmos destinos, comUSD12.68 em01/10,USD8.61em02/10 eUSD0.49em27/10, sem nova regra permanente. Requer confirmação explícita da atribuição outubro e da correção21.78. Não reutilizar autoridade de setembro, não criar ajuste no último dia, não alterarCAD, câmbios, gastos, impostos/revshare/invalids, status/rateio ouledger.

Estado: **auditoriaM2 concluída, aplicação pendente de confirmação**. GastosFB/Google já conferidos permanecem preservados. Após correçãoM2validada, continuarRede2→Rede1. AVoutubro já resolvida.

## Evidências e limitações

Diretório `apps/finance-system/private/october-close-1575041627167391744/`:m2-source/recheck/hash,m2-dash,m2-summary,m2-profit-windows.jsonl,m2-profit-summary,m2-network,m2-network-comparison,m2-verification. Espelho sanitizado da coleta no workspace do browser.

A primeira checagem local que presumiu blocos zerados falhou antes de qualquer escrita; a leitura integral revelou os três valores positivos e a soma foi refeita emDecimal. Um erro sintático do harness NETWORK impediu a execução da primeira tentativa e foi corrigido antes da coleta. Nenhuma alteração financeira, de fonteGoogle, credencial ou configuração, nenhuma operação de pagamento.
