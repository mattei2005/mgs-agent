# GAM — análise do consolidado e exceção Yolokfx, setembro 2026

Fonte autorizadora: Rodolfo, Discord `1545426987756298340/1547412068875894815`.
Dono financeiro: Rodolfo. Executor da análise: Zeus.
Escopo executado: leitura integral de quatro exports GAM de 7/8 setembro e do consolidado Claude; leitura Smart Bidding AdGroup e Domain nesses dois dias. Nenhum lançamento financeiro, configuração de e-mail ou backfill produtivo.
Evidência: `/root/mgs-agent/work/gam-claude-1547412068875894815/`.

## Revisão Escalatepower confirmada — 1547688086664908952

Rodolfo confirmou `escalatepower.com` como `us-cc-en` para as linhas01,02e09/09/2026 desta revisão. Aplicar `g002-d`, já confirmado em1547589806559731742, e preservar a receita original GAM CAD0.26152045415777927 por dia. Zeus mantém a vertical completa; Claude usou `us` incompleto. Esta decisão resolve vertical e gestor sem alterar país, moeda, data ou valor. Baselines preservados; aplicar no Excel final revisado. Não extrapolar a país novo em futuros CSVs (regra1547683017462513675). Próximo e último domínio divergente: `mavroa.com`, vertical pendente; gestor `g002-d` já confirmado.

## Revisão Openzed BR confirmada — 1547684367349059627

Rodolfo confirmou a parcela BR de `openzed.com` como `br-car-br` nesta revisão01–09/09/2026. Substituir apenas a inferência `br-cc-br` do baseline Zeus para a linha09/09, mantendo `g003-d` e receita original GAM CAD0.0006066331027935214. GB `gb-cc-en` e US `us-cc-en` continuam separados, preservando as parcelas G001/G003 nos EUA. CAR decorre da confirmação empresarial, não das UTMs vazias. Baselines preservados; aplicar no Excel final revisado. Não inclui `finanzas.openzed.com` nem altera países de futuros relatórios; permanece a restrição1547683017462513675. Próximo domínio: `escalatepower.com`; depois `mavroa.com` e Excel final.

## Revisão Topfeed BR confirmada — 1547683789034102797

Rodolfo confirmou a parcela BR de `finance.topfeed.fun` como `br-car-br` nesta revisão01–09/09/2026. Substituir apenas a inferência `br-cc-br` do baseline Zeus para essas linhas; manter `g004-d`, dias02/09 e03/09 e a receita original GAM integral. US `us-cc-en` e GB `gb-cc-en` continuam separados e inalterados. CAR é confirmação empresarial, não dimensão demonstrada pelas UTMs vazias. Preservar baselines; aplicar no Excel final revisado. Escopo não inclui `finanzas.topfeed.fun`, outros sites, nem autoriza converter países novos em futuros relatórios (regra1547683017462513675). Próximo domínio: `openzed.com`, vertical BR pendente.

## Limite transversal das decisões desta revisão — 1547683017462513675

Rodolfo esclareceu que um site pode passar a operar outro país. Decisões específicas desta revisão não são autorização permanente para remapear países em relatórios futuros. Se aparecer outro país no original GAM, preservar esse país e sua receita, sinalizar a divergência e solicitar decisão somente quando necessária; nunca mover para o país habitual por default, histórico ou confirmação antiga desta revisão. Exceções de país já aprovadas para este conjunto01–09/09 permanecem no escopo exato, sem retroagir nem se propagar a novos períodos/domínios. Se país for claro mas produto/idioma não, preservar o país e deixar apenas a classificação faltante pendente, sem inventar. Regra canônica geral: `context/sources-of-truth.md`, seção Receita GAM. Esta restrição prevalece sobre formulações anteriores que soem atemporais, incluindo Gamezonead/Topfeedfinanzas; não autoriza alterar automaticamente pipelines existentes. Revisão atual continua em finance.topfeed.fun BR.

## Revisão Zytiva Finanças confirmada — 1547682605766414356

Rodolfo confirmou que `finanzas.zytiva.com`, domínio sob revisão, atualmente pode receber receita da Espanha e dos EUA em espanhol. Manter `_es`→`es-cc-es` e `_us`→`us-cc-es` separados conforme o GAM; nesta amostra01–09/09, ambos em `g003-d`, preservando data, moeda e valores originais. Zeus mantém a separação; a fusão ES→US do Claude não se aplica. Encerra a pendência de país desse domínio. Registrar para o Excel final, sem regravar baselines.

A fala1547682068698501172 citando Cliquet/tudo US foi retirada como engano pelo próprio Rodolfo em1547682209022869524 antes de qualquer aplicação; não é regra ativa para Cliquet nem Zytiva. A confirmação atual se refere ao domínio Zytiva Finanças já identificado na revisão, não a novo domínio inferido da grafia informal «zytivia». Cliquet permanece com as decisões anteriores preservadas. Próximo domínio: `finance.topfeed.fun`, vertical BR ainda pendente.

## Revisão Cliquet confirmada — 1547681384653529169

Rodolfo confirmou na revisão de01–09/09/2026: `cliquet.com` mantém GB separado de US; a parcela BR é CAR. Mapeamento ativo: `_gb`→`gb-cc-en`, `_us`→`us-cc-en`, `_br`→`br-car-br`, todos com `g002-d` nesta amostra. Preservar data, moeda e receita original GAM. O país vem do placement; CAR para BR é confirmação empresarial, não informação de UTM inexistente.

Supersede a inferência `br-cc-br` do baseline Zeus e encerra a pendência BR do Cliquet; rejeita a fusão GB→US do Claude. Não altera outros domínios, inclusive `finanzas.cliquet.com`, nem transfere esta decisão CAR aos placements BR ainda pendentes de Topfeed/Openzed. Valores exibidos a seis casas CAD: US1.265556, GB0.002288, BR0.004944; total1.272788. Baselines preservados; aplicar apenas na versão final revisada do Excel. Próximo domínio: `finanzas.zytiva.com`.

## Revisão Autocreditadx confirmada — 1547679210892566578

Rodolfo reafirmou `autocreditadx.com` → `us-car-en` na revisão de01–09/09. Manter a versão Zeus: gestor `g002-d` e receita original GAM preservados. O original possui uma linha em07/09, placement `pl_digital-trust_autocreditadx_us`, UTMs `-`, receita CAD0.022122988410875555; o país US vem do original, CAR da confirmação empresarial. Claude usou `us-game-en`, classificação rejeitada nesta revisão. Não é mudança de valor nem de gestor. Baselines intactos; incluir a confirmação no Excel final após todos os domínios. Próximo domínio: cliquet.com. Esta confirmação reafirma a regra anterior1547441127697678418, sem nova regra concorrente.

## Decisão ativa Yolokfx — 1547678046553636905

Rodolfo confirmou, inclusive por follow-up «exato»: para yolokfx.com de 01–09/09/2026, manter o total original GAM de cada dia/moeda; atribuir a G001, G003, G004, G005 e G006 a receita bruta REVENUE da dashboard SB AdGroup, pelo gestor de ACCOUNT_NAME; atribuir a `g002-s` o total GAM do dia menos a soma dos outros cinco gestores. Preservar `-s` e `us-shein-en`. Calcular por dia, não dividir igualmente o resíduo do período. Não somar de novo G002 ou não identificados da SB: estão absorvidos pelo complemento. Se houver resíduo negativo ou escopo/moeda divergente, bloquear para revisão, sem rateio silencioso.

Esta decisão **supersede somente a atribuição anterior do Yolokfx por ponte campanha→gestor com valores individuais GAM**, inclusive a preservação separada de mediums explícitos daquela regra histórica para este intervalo. O original contém alguns mediums explícitos e muitos ausentes; a fala «tudo pro G002» descreve a concentração do consolidado, não modifica o arquivo bruto. Outras regras de domínio continuam vigentes. A dashboard agora fornece os valores dos outros gestores por exceção expressa; o controle total diário continua sendo o GAM do e-mail.

Calculado e relido em `work/yolo-approved-1547678046553636905/approved-allocation.json`: nove dias conciliados exatamente, nenhum complemento negativo. CAD: G001-s628.86; G002-s7247.5046364440710968747; G003-s110.10; G004-s4296.23; G005-s2763.18; G006-s1534.73; total16580.6046364440710968747. Baselines preservados; aplicar esta alocação na versão final do Excel ao término da revisão. Próximo domínio: autocreditadx.com.

Rodolfo informa correção de utm_medium a partir de10/09, com expectativa do relatório correto em11/09. É informação/expectativa do responsável, não validação técnica: conferir o próximo original antes de declarar tracking corrigido ou extrapolar esta exceção. Sem coleta de e-mail, cron ou importação financeira autorizados.

## Decisão ativa — GAM por e-mail prioritário, 1547626692745629796

Fonte: Rodolfo, Discord `1545426987756298340/1547626692745629796`. Regra geral registrada em `context/sources-of-truth.md`: priorizar sempre o relatório original GAM recebido por e-mail para a consolidação; dashboard como apoio, não substituição/reclassificação financeira sem vínculo com o original. Na semana do pagamento, conferir com o relatório geral GAM solicitado por Rodolfo à SB ou rede correspondente. Nenhum job de e-mail, cron ou lançamento foi autorizado por essa definição.

**Eggbev encerrado nesta revisão:** manter a classificação do original com as regras aprovadas: `_gb`→`gb-cc-en`, `_us`→`us-cc-en`, gestor `g006-d`. Não retirar/subtrair nem criar linha EMP a partir dos CAD28.32 encontrados apenas na dashboard. A investigação de utm_campaign dessa parcela deixou de bloquear a consolidação; evidência técnica preservada em `work/eggbev-campaign-1547601740734664766/`, mas sem atribuição inventada. A hipótese de navegação do usuário entre URLs de cartão e empréstimo foi levantada por Rodolfo e permanece hipótese, não causa validada.

A decisão supersede os estados anteriores de Eggbev pendente de regra EMP/ponte obrigatória. Não cancela separação GB/US nem outras decisões específicas (incluindo Yolokfx por identidade e valor GAM preservado). Ao fim de todos os domínios, gerar e enviar o Excel atualizado, como solicitado em1547598180990976100; os arquivos-base permanecem preservados até lá. Próximo domínio pendente: yolokfx.com.

## Revisão por domínio — confirmação 1547598180990976100

Rodolfo confirmou manter a versão Zeus para **finanzas.openzed.com**, após leitura live SB: `es-cc-es` e `us-cc-es` separados, valores originais GAM preservados. A consulta SB de 1–9 setembro confirmou `ccr/es` e `ccr/us` em todos os nove dias; evidência em `/root/mgs-agent/work/sb-openzedfinanzas-1547595924346376202/`. Esta confirmação reafirma, não muda, a regra ES/US já vigente.

Ao terminar a revisão de todos os domínios divergentes, **gerar e enviar novamente o Excel Zeus atualizado com todas as decisões confirmadas**, preservando os baselines da comparação. Esse é um entregável pendente autorizado, não um arquivo já atualizado/enviado. Não importar valores em planilha/app financeiro por inferência. A revisão segue um domínio por vez; próximo domínio: eggbev.com.

## Complemento ativo — confirmação 1547589806559731742

Fonte: Rodolfo, Discord `1545426987756298340/1547589806559731742`.

- **Escalatepower e Mavroa → `g002-d`**, confirmado para classificação da receita. Supersede a pendência de gestor das quatro linhas CAD0.26175290822947867783 no Excel Zeus de 1–9 setembro. A vertical do Mavroa não foi confirmada nesta mensagem; não inferir essa confirmação a partir do nome do gestor.
- **`-s` = tráfego direto; `-d` = estratégia do bot.** Não são sufixos intercambiáveis. A identidade-base G00X pode ser usada para localizar a pessoa, mas a estratégia deve continuar separada na receita/comparação; não converter `-s` em `-d` nem fundir valores sem preservar a dimensão de estratégia. Esta definição explícita vence descrições genéricas/históricas que tratam a normalização como suficiente para o relatório financeiro. Não autoriza migração retroativa nem alteração de pipelines produtivos nesta tarefa.
- **Continuidade atual:** original de 1–9 setembro recebido em1547581942474608720, Excel Zeus anexado em1547585024369627156, arquivo Claude recebido em1547589806559731742. As antigas dependências de envio abaixo são históricas e foram cumpridas. Preservar ambos os arquivos para comparação independente; confirmação nova é uma camada de classificação, não regravação do baseline Zeus.

## Comparação independente 1–9 setembro — executada em1547589806559731742

Evidência: `/root/mgs-agent/work/gam-compare-1547589806559731742/`. Original, baseline Zeus e Claude preservados por hash. O overlay da confirmação Escalatepower/Mavroa altera somente a chave de gestor na análise; não regrava os arquivos enviados.

- 27.091 originais; Zeus513 grupos (105USD/408CAD); Claude466 (105USD/361CAD). Todas as18 combinações moeda/dia fecham a centavos. Nenhuma diferença material por site total. Diferenças residuais numéricas são compatíveis com os seis decimais do Claude.
- Todas as466 linhas Claude foram reproduzidas exatamente a seis casas a partir do original com as transformações documentadas em `claude-reproduction.json`. Isso prova as diferenças de classificação, não aprovação das escolhas.
- Diferenças que contrariaram regras já confirmadas: Openzedfinanzas ES→US CAD14126.7522500028941400869; Eggbev GB→US CAD133.21881616814104343838; Autocreditadx CAR→GAME CAD0.022122988410875555; Yolo receita identificada em outros gestores transferida ao G002-s CAD9062.3342684267935311. Zeus aplicou as separações/aprovações vigentes. O Claude preservou mediums explícitos do Yolo, mas seu resultado é integralmente reproduzido colocando todo medium ausente em G002-s, sem a ponte de conta que separa outros gestores.
- Outras diferenças sem confirmação empresarial suficiente para proclamar vencedor: Cliquet GB→US CAD0.002288385297784778; Zytivafinanzas ES→US CAD0.08557962688236341; placements BR de Cliquet/Topfeed/Openzed classificados CAR no Claude e CC no Zeus. O placement prova BR, não CAR versus CC; manter como decisão de vertical pendente em vez de apresentar a inferência de qualquer arquivo como comprovada.
- Escalatepower tem vertical `us` incompleta no Claude contra `us-cc-en` no Zeus, respaldada pelo histórico operacional consultado. Mavroa tem `us-cc-en` no Claude contra `A confirmar` no baseline Zeus; Rodolfo confirmou o gestor, não a vertical. Gestores Escalatepower/Mavroa do Claude coincidem com a confirmação g002-d recebida neste turno.
- A semântica -s/d está agora explícita e preservada: a divergência principal do Yolo é entre gestores dentro de `-s`, não mistura de direto e bot. Sem importação em planilha/app, mudança de campanha ou nova consulta financeira externa nesta comparação.

## Regras ativas confirmadas — mensagem 1547441127697678418

Fonte: Rodolfo, Discord `1545426987756298340/1547441127697678418`. Esta confirmação supersede as dúvidas de classificação e o bloqueio de atribuição do resíduo descritos na análise histórica abaixo. Preservar essa análise como evidência de como o arquivo do Claude foi produzido, não como regra concorrente ativa.

1. **Infinitynexx, Openzed, Creditoparaveiculo e Gamezonead — confirmados:** Infinitynexx preserva G001/G004 e atribui medium ausente ao G004; Openzed preserva G001/G003 e atribui medium ausente ao G003; Creditoparaveiculo preserva seus seis gestores e atribui medium ausente a `g002-s`; Gamezonead consolida toda a receita em `g002-s`/`br-game-br`, inclusive medium G001-s e o placement `_mx` presentes na amostra. Confirmação de classificação de receita, não alteração de titularidade nem de contas de gasto.
2. **Eggbev — corrigido:** placement `_gb` → `gb-cc-en`; `_us` → `us-cc-en`. Nunca fundir GB em US nesse consolidado.
3. **Finanzas — distinguir site, país e idioma:** Openzedfinanzas opera Espanha (`_es` → `es-cc-es`) e EUA em espanhol (`_us` → `us-cc-es`), mantendo ambos separados no domínio `finanzas.openzed.com`. Topfeedfinanzas opera somente `us-cc-es`; manter essa classificação inclusive para `_es` observado na amostra, no domínio `finanzas.topfeed.fun`.
4. **Autocreditadx — corrigido:** `autocreditadx.com` → `us-car-en`, não `us-game-en`.
5. **Yolokfx, 1 a 9 setembro 2026:** Rodolfo confirmou que esse histórico não voltará do GAM com utm_medium. Mapear o máximo possível pela dashboard, usando utm_campaign e evidência de campanha/conta/ACCOUNT_NAME para identificar gestor. Somente a parcela que continuar sem identificação segura vai para `g002-s`, por decisão expressa de Rodolfo. Registrar separadamente a origem real identificada e esse fallback; não deixar resíduo bloqueado nem transferir todo o site ao G002. Manter o valor original GAM e usar a dashboard como ponte de identidade, sem rateio por gasto ou substituição cega por somas AdGroup que não fecham com o export.
6. **Próxima validação:** Rodolfo enviará os originais referentes ao dia9; Zeus produzirá o consolidado com estas regras antes de receber o resultado do Claude. Comparar posteriormente por moeda/data/site/vertical/gestor e explicar cada divergência. Usar totais do GAM como controle; não reproduzir erros conhecidos para forçar igualdade com Claude. O envio do dia9 ainda é dependência, não relatório já recebido ou job agendado.

A reprodução anterior de todas as102linhas permanece validada como explicação da amostra do Claude. Estas correções mudam a classificação/atribuição do próximo consolidado, não a soma total da receita original por moeda/dia. Nenhum workbook, script de reprodução histórica ou lançamento financeiro foi regravado nesta confirmação.

## Histórico supersedido — primeira decisão de atribuição Yolokfx

Rodolfo informou ausência do cadastro de `utm_medium` no AdOps e determinou verificar a receita do Yolokfx entre 1 e 9 setembro de 2026 usando Smart Bidding Reports > AdGroup, filtrando site/data e resolvendo gestor pelo sufixo do `ACCOUNT_NAME` Facebook. Esta regra supersede a atribuição automática integral do Yolokfx a G002 no consolidado fornecido, para esse intervalo. Não transfere a titularidade do site nem autoriza distribuir resíduo por proporção de gasto.

A correção AdOps foi anunciada para meia-noite do dia 10 de setembro, mas sua ativação e o fuso desse corte ainda não foram verificados. Não declarar UTM confiável a partir dessa data sem inspecionar o primeiro export correspondente. Metadados dos exports examinados: America/Sao_Paulo. Não extrapolar a verificação de 7/8 aos dias 1–6/9. Os arquivos desses demais dias não foram fornecidos nesta fase.

## Resultado da reconciliação integral

`manifest.json` guarda os hashes SHA256 reais dos cinco arquivos; `raw.json` contém todas as 5.943 linhas brutas; `claude.json` contém as linhas do consolidado; `comparison-102.json` e `lineage-102.json` documentam todas as 102 saídas e a origem de cada uma. `reconcile.py` reproduziu exatamente todas as 102 linhas na precisão de seis casas decimais do Claude, atribuindo cada linha original uma única vez. A diferença máxima por grupo antes do arredondamento é 0,0000004995379395. Não houve perda ou duplicação de valor nos agregados por moeda/data. Isso prova reprodução matemática, NÃO aprovação empresarial de todos os mapeamentos.

- `Report_Digital_Trust_adx_2-2.xlsx`: 7/9, USD, 173 linhas, 6.033,113992892633140494.
- `Report_Digital_Trust_adx_2.xlsx`: 8/9, USD, 182 linhas, 5.269,1304295650139761260.
- `Digital_Trust-2.xlsx`: 7/9, CAD, 2.846 linhas, 25.900,32551516956391565567.
- `Digital_Trust.xlsx`: 8/9, CAD, 2.742 linhas, 24.484,51408319241768873309.
- Total USD: 11.302,2444224576471166200; total exibido Claude: 11.302,24.
- Total CAD: 50.384,83959836198160438876; total exibido Claude: 50.384,84.

Os quatro originais têm abas Properties/Propriedades, período real e moeda explícitos. O primeiro par é All Digital Marketing/USD; o segundo é 00-JBF Digital Server/CAD. Todos foram gerados no dia seguinte ao período informado, às 09h BRT. Não são duplicatas por idioma. O consolidado tem somente valores estáticos, sem fórmulas; a implementação original do Claude não foi fornecida. A reconstrução descreve regras compatíveis com todas as saídas, não acesso ao raciocínio interno dele.

## Mecanismo observado, não nova regra financeira

1. Ler a receita bruta Ad Exchange; não usar eCPM médio como receita nem descontar share/imposto/inválidos.
2. Manter CAD e USD separados, sem câmbio entre as abas.
3. Extrair site/país de Placement/Posição (`pl_digital-trust_<marca>_<pais>`), traduzir marca para domínio real e construir Vertical. Esses exports não têm dimensão geográfica independente de país do visitante.
4. Usar `utm_medium` válido como gestor, preservando `-s`/`-d` no arquivo de saída. A identidade G00X é distinta do sufixo de tráfego; isso não supersede a normalização de gestor de outros pipelines.
5. Aplicar fallback e exceções observadas abaixo.
6. Somar por moeda, data, site, vertical e gestor; agrupar campanhas/content/term no total, arredondar os grupos para seis casas, exibir TOTAL a duas casas. Colunas auxiliares não são necessárias para reproduzir esses cinco arquivos, mas não se conclui que Claude nunca as use em outros relatórios.

Mapeamento de domínio observado: `*finanzas` → `finanzas.<marca>.com`; Topfeed → `finance.topfeed.fun`; Topfeedfinanzas → `finanzas.topfeed.fun`; Newsounde → `de.newsoun.com`; demais marcas → `<marca>.com`. A matriz de defaults e exceções completa está em `reconcile.py`, apenas como reprodução da amostra.

### Escolhas que afetam atribuição e merecem validação

- Medium `-` ou `mg01-d` foi atribuído ao gestor padrão inferido do site, não descartado. Em sites compartilhados isso não prova origem. Infinitynexx preserva G001 e G004, mas linhas `-` vão a G004. Openzed preserva G001 e G003, mas `-` vai a G003. Creditoparaveiculo preserva os seis gestores, mas `-` vai a G002-s.
- Gamezonead: tudo foi para `br-game-br`/G002-s, incluindo USD310,55463977553199601 explicitamente marcados G001-s e USD0,041198554494 do placement `_mx`. Reproduzível, mas não presumir aprovação por totals corretos.
- Eggbev: placements `_gb` e `_us` foram consolidados em `us-cc-en`; CAD31,56301220201214047 do `_gb` entrou no US. Necessita validar a intenção de classificação.
- Openzedfinanzas e Topfeedfinanzas: `_es` e `_us` unificados em `us-cc-es`; CAD3.215,91137441190000974063 originários de placements `_es`. Idioma e país não são sinônimos; classificação pode ser comercial, mas não demonstrada pelo Excel isolado.
- Newsounde: G002-d CAD0,2314639938224172 foi transferido para G005-d, compatível com a regra histórica documentada desse site.
- Autocreditadx: saída `us-game-en` com CAD0,022123; o original identifica apenas placement `_us`. O arquivo não comprova a vertical GAME. Não corrigir automaticamente para CAR nem promover GAME por inferência.
- Vizioid e Yolokfx: valores sem medium foram atribuídos a G002-s e `us-shein-en`; Yolokfx exige a exceção ativa acima.

## Yolo — bruto GAM confirmado e dashboard não idêntica

Original 7/9: CAD2.605,5630324995379395, 47 linhas, todas com medium `-`.
Original 8/9: CAD2.929,678978045648383496, 51 linhas, todas com medium `-`.
Claude manteve esses valores em seis casas e atribuiu todos a G002-s por fallback; o próprio original não traz esse gestor.

Consulta autenticada e somente leitura da rota `/reports/adgroup`, endpoint observado `POST /report/performance_per_campaigns`. Filtro publisher `digital-trust_yolokfx`, currency `CAD`, datas 7/8 com instante seguro 15:00Z. `REVENUE` é usado como bruto, não `NET_REVENUE` nem `REVENUE_ESTIMATED`. Foram recebidas 100 PKs únicas: 47 no dia7 e 53 no dia8. Reconsulta separada de cada dia reproduziu todos os registros exatamente; não houve corte em 100 linhas.

Somas de REVENUE CAD por ACCOUNT_NAME/sufixo:
- G001/Ícaro: 7/9 119,73; 8/9 75,65.
- G002/MGS: 7/9 832,68; 8/9 875,47.
- G003/Isliago: 7/9 12,79; 8/9 23,39.
- G004/Joe: 7/9 701,18; 8/9 920,19.
- G005/Kelly: 7/9 501,78; 8/9 634,43.
- G006/Nicolas: 7/9 356,23; 8/9 377,16.
- Sem ACCOUNT_NAME: 8/9 0,02, UTM_ADGROUP `b01fb01c12g01`; não atribuído por prefixo.

AdGroup total: CAD2.524,39 no dia7 e CAD2.906,31 no dia8. Abaixo dos originais em CAD81,1730324995379395 e CAD23,368978045648383496 respectivamente. Não é reconciliação exata.

Verificação independente no `GET /report/performance_per_domain`, mesmo publisher/datas/CAD: CAD2.603,49 e CAD2.931,77. São valores diferentes tanto dos exports recebidos quanto da soma AdGroup. A causa exata da diferença entre snapshots/moedas/cobertura não foi comprovada; não atribuir a câmbio, rounding ou tráfego inválido sem evidência adicional.

### Ponte por campanha, sem rateio inventado

`yolo-campaign-lineage.json` cruza exatamente o `utm_campaign` do GAM com o código de campanha extraído do UTM_ADGROUP e validado contra CAMPAIGN_NAME, no mesmo dia, para obter ACCOUNT_NAME/gestor. Os valores continuam sendo do GAM original, não substituídos pelo AdGroup.

Ficaram sem atribuição segura no original:
- 7/9: CAD76,7543806023048, campanha `-`.
- 8/9: CAD25,577226841288223, campanha `-`, mais CAD0,019396225562649496 de `b01fb01c12`, sem ACCOUNT_NAME na dashboard.

A receita identificada por campanha também não é idêntica à dashboard: a diferença GAM menos AdGroup após retirar campanha `-` é CAD4,4186518972331395 em7/9 e CAD-2,208248795639839504 em8/9. Não explicar toda a diferença apenas por ausência de campanha. Não distribuir resíduo aos gestores ou sobrepor valores financeiros até haver regra autorizada e conciliação apropriada.

## Estado atualizado após confirmação 1547441127697678418

Análise da amostra e conferência SB concluídas. Classificações dos itens1–4 e fallback do Yolo agora têm decisão explícita registrada na seção ativa. Próxima dependência: originais do dia9 para consolidado Zeus e posterior comparação com Claude. Demais dias históricos não foram reprocessados; ativação do medium pós-correção AdOps e arquitetura de e-mail ainda não validadas. A diferença entre os totais SB e GAM permanece observada, mas não impede classificar o resíduo do GAM conforme a decisão de Rodolfo. Nenhum lançamento ou coleta ativado.

Incidentes técnicos locais recuperados: consulta inicial a pack de continuidade no skill errado (resolvida lendo o pack canônico de mgs-company-os-architecture); `inspect.py` sombreou stdlib inspect (execução corrigida com Python safe-path `-P`); helper shell inicialmente invocado com Python (corrigido com Bash); sessão SB cache expirada (login pela credencial canônica 1Password concluído, identidade Zeus - Agent validada). Sem bloqueio restante de acesso ou cálculo por esses incidentes. Na finalização, uma entrada legada do inventário sem `id` causou KeyError no readback; a leitura foi corrigida para chave opcional, a entrada desta análise foi relida e o registro idempotente foi reexecutado sem duplicação.
