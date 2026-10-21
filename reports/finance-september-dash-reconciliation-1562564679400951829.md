# Setembro — relatório AdOps × Dash financeira

## Escopo e correção de condução

Rodolfo1562564334129905745 e1562564679400951829 esclareceu que o relatório `1ARyzDDEpVhlED6ndmHs1RC3pUlsJNQ20yTyZ6wSJVtA` é a fonte para conferir e ajustar setembro na Dash financeira. A planilha geral está fora do escopo. A leitura de fonte do primeiro turno não substituiu essa comparação. Mantida a instrução original de analisar primeiro: este turno entrega a comparação real e as decisões de atribuição necessárias, sem escrita financeira. Não houve alteração de agosto, da fonte, de pagamentos ou de parâmetros.

## Fontes reais e controles

- Todas as sete abas da fonte de setembro, SA canônica, relidas integralmente em FORMULA e UNFORMATTED_VALUE sem delta contra a captura inicial.
- Produção remota MatteiInc01: `workspace-2026-09`, revisão1643, draft; cadastro de contas revisão19. SELECT em transação REPEATABLE READ READ ONLY, role mgsfinance, sem autenticação alternativa ou consultas à planilha geral.
- Projeção executada no runtime implantado: mesma `buildSimpleReview` de `/api/monthly-conference`, mais modelo de inputs/fatos e `traceRows`.4243 fatos e2030 additions congelados para a análise; nenhum material de autenticação capturado.
- Segunda captura produtiva integral idêntica à primeira, incluindo revisão, overrides, additions, resultados, cadastro e hashes dos módulos.
- Evidência privada, ignorada pelo Git antes de capturar: `apps/finance-system/private/september-closing-1562564679400951829/`.

## Comparação de totais, diferença = relatório − Dash

- SB Rede1 CAD: relatório778884.56398680319913306997; Dash783034.417308482153521658; diferença−4149.85332167895438858803, exibição−4149,85.
- SB Rede2 USD: relatório209644.93420635515299812711; Dash209676.662810136973384249; diferença−31.72860378182038612189, exibição−31,73.
- M2 USD: relatório705,00; Dash sem receita M2; diferença+705,00. Wantabrand principal703,20 e Finance1,80.
- Facebook USD: relatório500749,61; Dash500713,57; diferença+36,04.
- Google BRL: relatório111547,89; Dash111547.927996; diferença−0.037996, exibição−0,04. TODAS as43 linhas coincidem quando a precisão original da Dash é arredondada para centavos por dia. Diferença de precisão/soma, não gasto ausente; recomendação preservar micros e explicar, sem ajuste artificial.
- AV: sem receita fornecida e sem receita registrada na projeção da Dash. Não há delta positivo identificado a corrigir, mas ausência não é certificação externa de receita zero.

## Receita — diferença em moeda nativa por site

Rede1, CAD: Zytiva−3580.7260395934698148706; Openzed Finanzas−235.22445318323055642464; Lyzmo−167.04656264473979993066; Openzed−125.97871783030320648296; Newsoun−17.96824638771199458953; Yolokfx−9.4908488737561591445; FinanceTopFeed−5.85448251772234566865; Eggbev−3.7020600586186654236; Infinitynexx−1.6042934852712021730; Helixenit−1.271103819420556970; FinanceAdx−0.9865132847103122939. Outros controles de site não mudam o centavo exibido.

Rede2, USD: Creditoparaveiculo−30.242921410532718228; GameZoneAd−1.4856823712876753839. Fincgriffin e CarCreditAd não têm divergência em centavos.

São44 controles rede/site/moeda,15 divergentes em centavos incluindo os dois domínios M2. Todos os3728 registros SB foram resolvidos por placement→domínio→site; zero linhas sem mapping de site. Preservados subcentavos. A decomposição nativa por dia e gestor reconcilia com os totais da projeção implantada;1298 grupos união da fonte/Dash,205 com diferença em centavos. A etapa não valida cada decisão futura de vertical nem autoriza remapear automaticamente o histórico.

A maior diferença, Zytiva, concentra-se em10–17/09, com resíduos em21 e25/09. A Dash preserva os GAM diários importados anteriormente; o fechamento enviado contém outros valores. Esse fato prova a divergência entre capturas, não prova a causa externa da revisão nem um defeito de cálculo. Não atribuir automaticamente a inválidos: a comparação é de gross na moeda original.

## Facebook — lacunas resolvidas sem pedir outro export

1. C24 em texto`5045.00` é comprovadamente USD5045,00 também na API da conta26246776234981414. O footer da fonte495704,61 omite esse texto; fonte não foi editada. A Dash já contém esse gasto, portanto NÃO adicionar5045 à Dash novamente.
2. O nome de Vizioid divergia: fonte`Vizioid-US-SHEIN-EN-02-G002`; cadastro Dash`...-01-G002`. GET oficial da conta536294549227786 confirmou nome atual`...-02-G002`, USD eAmerica/New_York. Mesma identidade, não conta nova nem gasto adicional2153,08. Cadastro não foi alterado.
3. Consultadas37/37 contas via coletor oficial read-only,01–30/09: todas retornaram HTTP/cobertura válidos, zero falhas. Tanto agregado mensal quanto soma dos dias coincidem EXATAMENTE com o valor de cada linha do relatório; total500749,61. O detalhe diário ausente da planilha foi recuperado sem inventar datas e sem substituir a autoridade do relatório.
4. Comparação com as folhas efetivamente usadas na Dash:27 contas/38 dias diferem, somando+36,04. Dez contas sem mudança. Nenhum gasto positivo sem classificação ou conta ficou fora do controle. IDs, dias e antes/depois completos em`dimensional-comparison.json`.
5. A conferência de Facebook não está mais bloqueada por ID de Vizioid, valor textual ou ausência de export diário. A aplicação posterior deve preservar IDs/bindings, usar cada dia real e não lançar o delta no último dia.

## Atribuição a gestores — decisões não podem ser escondidas no total

Há diferenças de atribuição mesmo em sites com total mensal igual:
- Newsoun DE: relatório atribui CAD90,795476379394158396 adicionais a G005/Kelly, hoje em G002/MGS.
- Zuout: fonte desloca aproximadamente CAD25,84738 de G006 para G002; Finanzas aproximadamente CAD5,72599. Respeitar decisão já existente de preservar os tags de setembro, sem reintroduzir cutoff19/09.
- WavesBee e WavesBee Finanzas: resíduos na fonte G002, na Dash G003; valores pequenos não autorizam política universal de dispensa.
- Yolokfx é o principal conflito com regra já aprovada: entre01–09/09, o import anterior usa SB por gestor G001/G003/G004/G005/G006 e complemento GAM em G002, conforme1547692440574627921. O novo relatório majoritariamente marca G002. Aplicar cegamente o novo rateio deslocaria CAD9037,3402165185966561675 para G002/MGS; reduziria G0044159,81958410852526, G0052675,46714577578668, G0061499,509359637505436, G001610,089371028585636 eG00396,716839907600895. A diferença TOTAL de gross de01–09 é só−CAD4,2620839394072508325. Portanto, não confundir gross atualizado com autorização para revogar a exceção de atribuição. Recomendar preservar a regra já aprovada até Rodolfo escolher explicitamente o critério para esse trecho.

## Gates restantes e próximo passo

- Concluir com Rodolfo se a exceção Yolokfx01–09 continua ativa ou se a distribuição do novo relatório a supersede. Não alterar comissão por inferência.
- M2: total/domain/date disponível, mas falta campanha/vertical para separar o principal entre operações. Obter detalhe ou regra explícita, sem inventar alocação. Finance tem rótulog001-d; principal não tem identificação equivalente.
- Ajustes determinísticos identificados para preparar transação: valores SB por fontes/dimensões confirmadas e Facebook38 dias; Google não requer perda de precisão. Ainda não foram aplicados.
- Antes de aplicar: congelar plano de dimensões e baseline de comissões, backup privado restaurável, rehearsal no motor atual, concorrência/revisão, transação bounded, readback dos fatos e reflexos nos gestores. Preservar taxas e regras, SMS, despesas, ledger de pagamentos, agosto e outros meses.

## Aprendizado persistido

Skill`mgs-finance-dashboard/references/adops-monthly-source-reconciliation.md`: analisar primeiro bloqueia escrita, não a comparação real com a aplicação; usar consultas oficiais já autorizadas para resolver IDs/nomes/detalhes antes de exigir novo export; preservar Google micros quando todos os valores diários arredondados coincidem. Essa correção de procedimento não é alteração financeira.

## Retomada ponto a ponto — somente ponto1/Rede1

Autoridade1562572094657798335: explicar detalhadamente o ponto1 antes de ir corrigindo; manter os demais pontos fora da sequência atual. Nenhum ajuste autorizado/aplicado nesta etapa de explicação.

Readback atual: fonte Rede1 integralmente idêntica; Dash revisão1644, cadastro19. Additions idênticas; únicos overrides alterados foram cotaçõesUSD/CAD eUSD/BRL, acompanhadas por audit4931/AUTO_QUOTES_UPDATED. Receita CAD e diferenças da conferência permanecem iguais. Não é uma alteração de receita não atribuída.

Zytiva explica86,2856048643% da diferença Rede1.183 linhas da fonte, linhas2813–2995, todasg003-d. Gross mensalCAD37610,2761827352945763544 na fonte versus41191,002222328764391225 na Dash; redução3580,7260395934698148706. GB representa3580,43420902338160000674 da diferença;US0,29183057008821487276. Os dias com divergência visível são10–17,21 e25/09.

Exemplo verificável:14/09/GB. Plan preservado `private/gam-email-runs/20260915T093604-0400/plan.json` contém119 registros de linhagem somandoCAD2236,490724081084830403, exatamente o valor da entrada ainda presente na Dash. O fechamento atual somaCAD1558,094727047071667586, diferença−678,395997034013162817. Na fonte nova sãoE2820+E2862+E2863, respectivamente direct0,057101307655867586,facebook1022,8741016504656,mct535,1635240889502. O arquivo XLSX apontado pelo plan histórico não existe mais naquele caminho local; a prova recuperada nesta etapa é do plano/linhagem preservado e do readback da entrada, não uma nova validação do binário original. Não afirmar motivo de revisão do fornecedor, fraude ou inválidos a partir disso.

Recomendação de primeira correção dentro do ponto1: Zytiva, valoresCAD nos dias/países exatos, preservando G003/Isliago e as verticais registradas; nunca inserir uma despesa/abatimento no total geral ou no último dia. Motor deve recalcular descontos/impostos/lucro/remuneração; redução de gross não é a mesma redução de lucro ou de pagamento. Após Zytiva, restante Rede1 éCAD569,12728208548457371743. Aguardando alinhamento do primeiro ajuste; nada foi escrito na Dash ou na fonte.

Evidências adicionais:`point1-*-readback.json`, `point1-snapshot.json`, `point1-zytiva-detail.json`, `point1-zytiva-origin-proof.json` no workspace privado da iniciativa.
