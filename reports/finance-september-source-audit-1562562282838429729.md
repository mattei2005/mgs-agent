# Setembro 2026 — conferência preliminar integral da fonte AdOps

## Autoridade, escopo e status

- Rodolfo, mensagem `1562562282838429729`, thread `1545426987756298340`: analisar tudo primeiro, sem aplicar correções.
- Fonte setembro: `1ARyzDDEpVhlED6ndmHs1RC3pUlsJNQ20yTyZ6wSJVtA`, sete abas completas; gid565588781 = `rede 1 SB`.
- Referência agosto concluído, não reaberto: `1HoF7ihPzb0_oQIR5cZ0bsWd2b-_5jsHcKBalFi9HG7g`, oito abas completas.
- Drive e Sheets HTTP200, identidade canônica `mgsagent@mgs-core-prod.iam.gserviceaccount.com`, projeto mgs-core-prod. Nenhuma escrita remota, canário ou alteração financeira.
- Leitura de userEnteredValue, effectiveValue, formattedValue e formato numérico de todas as abas; segunda leitura integral em FORMULA e UNFORMATTED_VALUE idêntica, 30 verificações aba/modo aprovadas.
- Zero erros de fórmula exibidos em setembro; 51 fórmulas inventariadas. Isso não valida completude nem semântica.
- Modelo real do turno confirmado em agent.log: sessão20261021_162440_11e71b8f, openai-codex/gpt-6-astra-900k.
- Fase concluída: auditoria da fonte. Não foi feita neste pedido a conciliação com o estado atual da Dash nem o fechamento de setembro.

## Totais recalculados — moedas nativas separadas

- SB Rede1: 3.050 linhas, 61 placements, CAD778.884,56398680319913306997; exibido CAD778.884,56. Datas01–30/09, todos os dias representados. E3058 soma o conjunto; diferença numérica subcentes compatível com floating point.
- SB Rede2: 678 linhas, quatro placements, USD209.644,93420635515299812711; exibido USD209.644,93. Datas01–30/09, todos os dias representados. E683 soma corretamente mas usa formato CA$, enquanto as678 receitas usam $; tratar como inconsistência visual, não converter para CAD.
- SB2 por placement: Creditoparaveiculo182745.689853767099227391; GameZoneAd26656.2778742671767604441; Fincgriffin242.966406320607010292; CarCreditAd0.00007200027000000001, todos USD.
- M2 consolidado diário: finance.wantabrand.com USD1,80, wantabrand.com USD703,20; total USD705,00;30 datas por domínio.
- Facebook:37 nomes únicos,36 valores numéricos e um valor em texto. SUM mostrado USD495.704,61; recálculo incluindo literal decimal `5045.00` = USD500.749,61.
- Google:43 linhas; Mattei1 R$106.197,30, Gamingadx-US-01 R$5.350,59; total R$111.547,89. O total soma corretamente; as datas requerem saneamento interpretativo antes de conciliar por dia.
- AV: não há receita fornecida. Não reportar zero efetivo como fato de negócio.

## Achados e disposição recomendada

1. **Facebook C24 fora do total.** Account name `OpenzedFinanzas-ES-CC-ES-01`, CurrencyUSD, Amount spent string literal`5045.00`. C41=`SUM(C2:C39)` ignora o texto. Diferença exata USD5.045,00. Recomendar interpretação explícita como USD5.045,00 na análise; fonte permanece read-only, não corrigida.
2. **Facebook sem detalhamento diário e sem numeric Account ID.** Cabeçalhos atuais:Account name/Currency/Amount spent; agosto tinha Day. Permite comparação mensal por nome, mas não substituição diária nem verificação independente de identidade.37 nomes atuais versus48 em agosto, oito novos e19 ausentes; isso não prova falta de gasto, pois a operação pode ter mudado. Solicitar relatório diário01–30/09, preferencialmente com IDs, para fechamento diário; não redistribuir diferença no dia30.
3. **AV em branco.** `rede AV - detalhado` contém somente cabeçalho. No consolidado,C2:C23 está vazio;D/E preservam22 vínculos de agosto apontando para antigas posições agora vazias;C26:E26 mostra zero por fórmulas. Perguntar se não houve operação/receita AV em setembro ou se o relatório ainda falta. Não reutilizar agosto nem classificar ausência como receita zero.
4. **M2 sem aba detalhada.** Setembro não tem `Rede MonetizeMore (M2) detalhado`. O consolidado tem60 valores por dia/domínio mas não campanha para dividir direto/BOT nem vertical para wantabrand principal; C1 do subdomínio contém g001-d. Total diário/domain é verificável; atribuição operacional completa ainda não. Obter detalhe de setembro; não herdar percentuais ou decisões excepcionais de agosto.
5. **Google datas interpretadas pelo locale.** A5:A16 e A18:A29 são24 seriais convertidos como09/jan,09/fev,...09/dez.22 saem de setembro;09/set aparece correto por coincidência em cada conta. A17 e A30:A47 são strings US`9/13/2026` etc. A apresentação parece MM/DD, mas o valor interno é dia09 de meses diferentes. Interpretar o relatório original como MM/DD somente com confirmação da base de setembro; preservar originais. Exemplo:A5 serial46031=2026-01-09, exibição9/1/2026, provável intenção2026-09-01.
6. **GamingAdx cobertura limitada.** Pela interpretação US explícita, há13 datas01–13/09 e nenhuma14–30/09. Mattei1 tem30 datas01–30/09. Perguntar se a conta parou de gastar após13/09 ou se o export está incompleto; ausência não vira zero automaticamente.
7. **SB apresentação e granularidade.** E683 SB2 exibe CA$ incorreto frente às linhas em USD;F/G, receita por gestor/total do site, estão vazias nas duas redes. Agregados podem ser reconstruídos da colunaE preservando moeda/placement/dia/gestor/fonte. Existem298 grupos SB1 e73 SB2 com a mesma chave visível(date/placement/medium/source), mas valores diferentes: nenhuma duplicata exata de fato foi detectada, nem cópia de fatos entre redes. Não deduplicar essas linhas nem afirmar erro de origem por chave repetida; preservar e somar a granularidade entregue, verificando o relatório original caso necessário. Todos os medium recebidos pertencem a G001–G006 com -d/-s. Isso não comprova sozinho a atribuição correta.

## Próximo passo

Alinhar com Rodolfo as lacunas de fonte:AV vazio, M2 detalhado, Facebook diário e GamingAdx14–30/09. Explicitar o defeito numérico FB e a interpretação de datas Google antes do uso diário. Depois, sob continuidade do pedido, preparar comparação fonte×Dash sem editar a fonte; qualquer aplicação financeira depende de autorização separada. Agosto continua concluído e preservado.

## Evidências e continuidade

- Evidências locais:`work/finance-september-source-audit-1562562282838429729/`.
- `analysis.json`:todos os totais, tipos, datas literais/propostas, fórmulas, agrupamentos e repetições.
- Snapshots por aba com hashes em`august-manifest.json`/`september-manifest.json`.
- `source-readback-receipt.json`:30/30 comparações sem diferenças.
- Checkpoint:`ZEUS-FINANCE-SEPT-CLOSE-1562562282838429729`.
- Aprendizado persistido:skill`mgs-finance-dashboard`, referência`adops-monthly-source-reconciliation.md`:SUM ignora texto monetário válido; descobrir granularidade e abas faltantes em cada novo fechamento.
