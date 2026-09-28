# Agosto — prévia de atribuição C/D/E sem UTM

Autoridade: Rodolfo1551308976061419554, thread1545426987756298340. É prévia para conferência ANTES de aplicar; nenhuma escrita financeira está autorizada por esta etapa de preview. As autorizações anteriores de reconciliação permanecem abertas, agora com a regra explícita de fallback para o subconjunto.

## Regra e extração

Filtro exato AND: campaign = term = content = `-`; não inclui `null`, `/empty/`, um ou dois campos ausentes. Sheets API/SA lê todas as linhas independentemente do basic filter. Confirmados21domínios,329linhas eUSD722,61, inclusive dois domínios de valorzero. Snapshots completos em FORMULA/UNFORMATTED/FORMATTED no diretório privado ignorado `apps/finance-system/private/attribution-preview-1551308976061419554/`.

Cada valor terá gestor responsável pelo domínio/subdomínio e a vertical de maior receita acumulada no mês. São receitas já presentes no total AV, NÃO receita adicional a somar novamente. Preservar domínio, data de origem, moeda e medium original na linhagem. `-d` éBOT, `-s` é estratégia direta; não apagar essa distinção só porque C/D/E estão ausentes.

## Prévia, não aplicada — USD

```
conectageral.com                 0,01  G001 Ícaro    us-cc-en
de.newsoun.com                   4,37  G005 Kelly    de-cc-de
ducapes.com                      0,00  G001 Ícaro    us-cc-es
eggbev.com                     407,90  G006 Nicolas  us-cc-en
finance.ducapes.com              0,43  G001 Ícaro    us-cc-en
finance.topfeed.fun             14,93  G004 Joe      us-cc-en
finanzas.eggbev.com              1,67  G006 Nicolas  us-cc-es
finanzas.lyzmo.com               0,64  G006 Nicolas  us-cc-es
finanzas.newsoun.com             7,91  G005 Kelly    us-cc-es
finanzas.openzed.com            32,21  G003 Isliago  es-cc-es
finanzas.zuout.com               1,56  G002 MGS      us-cc-es
finanzas.zytiva.com              0,30  G003 Isliago  us-cc-es
lyzmo.com                        8,77  G006 Nicolas  us-cc-en
newsoun.com                     12,50  G005 Kelly    us-cc-en
openzed.com                     97,25  G003 Isliago  us-cc-en
portalrelevante.com              0,00  G001 Ícaro    us-cc-en
seuprimeiroempregoam.com         1,52  G006 Nicolas  us-job-en
zytiva.com                      28,77  G003 Isliago  gb-cc-en
finanzas.topfeed.fun            39,96  G004 Joe      us-cc-es
cliquet.com                     45,95  G002 MGS      br-car-br
finanzas.cliquet.com            15,96  G002 MGS      us-cc-es
```

## Pontos que precisam da conferência da prévia

1. **Openzed:** USD97,25 paraG003/Isliago/us-cc-en, inclusiveUSD1,76 cujo medium original éG001-d. A aplicação literal da nova regra de dono substitui a atribuição de gestor somente nessas linhas sem tracking. O total AV anterior deG001 USD5,00 passaria aUSD3,24, enquantoG003 recebeUSD1,76; o total do domínio não muda. Não alterar os demais lançamentos identificados deG001.
2. **Cliquet:** maior vertical global atual/identificada éBR-CAR-BR (AV diretoUSD149,33), enquanto o subconjuntoUSD45,95 éG002-d/BOT. O total AVBOT inteiro éUSD129,78, inferior ao diretoBR, e a parcelaSB não inverte a liderança. Pela regra literal global, préviaBR-CAR-BR, preservando suffix-d; confirmar se Rodolfo quer isso ou restringir a escolha às verticaisBOT (US-CC-EN). Não trocar-d por-s silenciosamente.
3. **Openzed Finanzas:** maior vertical suportada pelas fontes corrigidas éES-CC-ES, NÃO a distribuição antigaUS da dash. SB convertido:ES11153,18998960657225694788951;US6478,934413640879915470745005. AV:US3761,57 eES4363,85 por conteúdo com país ou campanha que só aparece com um país identificável neste mês;USD733,46 permanecem sem atribuição nesse cruzamento. Mesmo todo o indefinido indo paraUS, USmáx10973,96441364087991547074500 < ESmín15517,03998960657225694788951. Não usar os valores velhos da dash para inverter esse resultado. A ligação campanha→país é evidência inferida da própria fonte; não modifica o literal da fonte.
4. **Eggbev:** total filtradoUSD407,90 = USD406,19g006-d + USD1,71g006-s. GestorNicolas e verticalus-cc-en na prévia; preservar as duas estratégias, não chamar os407,90inteiros deBOT.
5. **Zuout Finanzas:** préviaG002/MGS para a competênciaagosto, coerente com source mediumg002-d. A regra posterior de defaultNicolas a partir18/09 não é retropropagada automaticamente. Confirmar esta atribuição na prévia, pois o cadastro atual de ownership usaNicolas.
6. Dois domínios de totalzero (ducapes.com eportalrelevante.com) não geram lançamento positivo; a vertical mostrada é sua operação documentada.

## Fechamento mensal institucional

Rodolfo explicou que conferir no mês seguinte entre20e25 é rotina: atrasos/refunds podem rever gastosFacebook/Google; redes/GAM podem revisar gross, inclusive deduções que aparecem até15–20. Não tratar divergência com captura diária anterior como falha por si só. Relatórios posteriores de fechamento governam a reconciliação centavo a centavo, mantendo data/moeda/domínio/vertical/gestor e sem nova dedução de revshare/clawback na comparação gross. Não foi criado cron nem regra de ajuste no último dia.

A skill financeira foi atualizada: `references/adops-monthly-source-reconciliation.md`, com supersessão explícita do bloqueioAdOps para o subconjuntoC/D/E=`-`, prévia antes de aplicar e fluxo mensal20–25. Fora desse subconjunto, regras existentes de atribuição continuam vigentes.

## Estado final deste passo

Workspaceagosto392 e accounts7 consultados, sem escrita financeira. A prévia não significa correção aplicada. Aguardar aprovação dos destinos/exceções e depois continuar a aplicação integral autorizada; PEND-092permaneceaberta. Não pedir aoAdOps recuperação do tracking que Rodolfo já confirmou indisponível.
