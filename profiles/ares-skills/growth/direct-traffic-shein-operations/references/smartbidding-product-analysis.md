# Análise SHEIN por produto — Meta × Smart Bidding

## Escopo e fontes

Resolver conta/gestor pelo contrato vivo e validar o domínio antes da consulta. Analisar somente o CUSTOMER_ID solicitado. Usar Meta Insights diário e SB Reports > Adgroup, juntando CAMPAIGN_ID + data civil; UTM_ADGROUP preserva o drill-down. Pricing é evidência de monetização por operação/regra, não automaticamente por produto ou gestor.

## Coleta segura

- Nunca imprimir ou salvar o objeto inteiro de GET /company: publishers podem carregar credenciais em vps, panel e wordpress. Projetar somente companyId, publisherId, name e url antes de log ou arquivo. Aceitar publisher.name sem .com; resolver a identidade pelo hostname de url e validar a referência publisherId.
- Adgroup: POST /report/performance_per_campaigns com initialDate, finalDate, publishers e currency. Filtrar DATE novamente depois da resposta e confirmar ausência de linhas/IDs de outra conta.
- Pricing: GET /pricing/{publisherId}?should_update_metrics=1. Snapshot pode estar em BRL; não rotular a receita como USD. valueUSD é piso, não RPS ou receita.
- Histórico Pricing: POST /pricing/{publisherId}/trail/metrics com rule real, days, finalDate ISO e currency=USD; a janela pode incluir dia extra, portanto filtrar date novamente. O RPS retornado é contribuição daquela regra por 1.000 sessões, não RPS de todo o site/produto.
- Aplicar paginação Meta até ausência de next, sem imprimir next URLs autenticadas. Não repetir extrações completas após uma falha só na SB: reutilizar arquivos/IDs já coletados.

## Coleta integral em duas etapas — relatório por produto

Use esta receita para atualizar um consolidado completo, não para substituir a seleção específica de um relatório filtrado por Health.

1. Resolva conta, gestor, domínio e modelo da conversa pelo catálogo/contrato e pelos apontadores locais; confirme a identidade com `GET act_<account_id>?fields=id,name,currency,timezone_name,account_status`. Use o binding canônico da credencial e os helpers `ares-meta-common.py` e `ares-smartbidding-common.py`; fixe `ARES_META_GRAPH_VERSION=v26.0` antes do import Meta. Determine o dia civil no timezone retornado, não pelo relógio UTC. Use o catálogo e o GET como fontes de lookup; um arquivo individual de conta ausente não demonstra falta de acesso nem justifica procurar credenciais alternativas.
2. Colete em paralelo quatro conjuntos independentes: campanhas (`id,name,effective_status,created_time`), Insights de campanha (`campaign_id,spend,impressions,actions,cost_per_action_type,purchase_roas,action_values`), Insights de anúncio (`ad_id,campaign_id,spend,impressions`) e o relatório SB pelo publisher autorizado. Nos Insights, mantenha o mesmo `time_range` e `use_unified_attribution_setting=true`. Filtre novamente SB por conta, domínio e `DATE`. Retenha o mapa `Future → nome da fonte` fora de `as_completed`; para cada Future, consuma `result()`, persista o conjunto sem segredos e registre seu horário antes de processar o próximo. Não descarte resultados concluídos: executar a requisição sem guardar seu retorno obriga uma segunda coleta e consome quota. Após falha, reconcilie os arquivos do mesmo pedido e repita somente fontes ausentes/inválidas; declare a diferença de horários se a recuperação alongar a janela.
3. Congele a seleção por IDs reais conforme o modelo. Quando o recorte for entrega no dia, selecione `spend > 0 OR impressions > 0`, independentemente do status atual; campanha pausada agora pode ter gasto hoje. Separe receita atribuída a campanhas sem entrega, sem adicioná-las implicitamente às partições do consolidado. Use `campaign_id`, nunca o prefixo numérico do nome, como chave: nomes legados podem repetir números.
4. Com a seleção definida, consulte em paralelo: Insights diários das campanhas desde a menor `created_time` até o dia alvo, conjuntos com `promoted_object` e creatives dos anúncios com entrega. Para Insights/conjuntos, use filtro `campaign.id IN` com os IDs exatos. Para mídia, reutilize os `ad_id` dos Insights e leia os objetos exatos em lotes de até 50 com `meta.graph_batch_get(token, [{'path': ad_id, 'params': {'fields': 'id,account_id,campaign_id,creative{id,video_id,image_hash,object_story_spec,asset_feed_spec}'}}])`. Verifique HTTP externo e o `code` de cada resposta interna, além de conta e campanha de cada anúncio; a listagem padrão de anúncios pode omitir objetos que já entregaram e depois foram arquivados. O envelope batch contém apenas GETs, não mutações de campanha.
5. Aplique as regras de CRV e partição desta referência. Valide o evento web nos conjuntos, derive o primeiro dia com entrega pelos Insights diários e registre separadamente o horário de configuração. Para `Início` de um grupo, use o mínimo das primeiras entregas das campanhas integrantes e explique que a data pertence ao grupo, não a todas as campanhas.
6. Recalcule indicadores pelas somas das partições e execute os testes de cobertura/conservação antes de renderizar; persista o consolidado validado com seleção, grupos, totais e horários. Reaproveite snapshots anteriores apenas para modelo ou evidência histórica; não copie métricas, formato do dia ou contagens para uma nova atualização. Renderize diretamente dos campos estruturados, sem editar/reinterpretar linhas do texto já formatado: datas do cabeçalho e células de largura variável tornam esse reparo frágil. Calcule larguras por coluna usando cabeçalho e todas as células finais, inclusive contagens, sinais e sufixos. Reserve espaço do limite Discord para título, tabela, total e ressalvas; numa falha exclusivamente visual, repita somente a renderização do consolidado salvo. Teste a linha de maior nome/contagem, o cabeçalho `Início`, percentuais negativos e o tamanho de cada parte completa antes de entregar.

### ROAS consolidado sem média de razões

Consulte `action_values` junto com `purchase_roas`. Some somente o valor da action exata `omni_purchase` das mesmas campanhas e calcule `ROAS = Σvalor_de_compras_Meta / Σspend_Meta`; não some aliases de compras nem faça média aritmética dos ROAS individuais. Confira em uma campanha com base disponível que `action_values.omni_purchase / spend` corresponde a `purchase_roas.omni_purchase`, com tolerância de arredondamento. Diferencie ausência de dado de valor explicitamente zero; cobertura incompleta do numerador torna o ROAS consolidado indisponível ou parcial declarado, não zero presumido.

### Aceitação da coleta integral

Exija IDs únicos; igualdade entre seleção e união disjunta das partições; cobertura de todos os anúncios com entrega e de todos os conjuntos relevantes; primeira entrega comprovada; conservação de gasto, receita líquida, receita estimada, resultados e contadores Health. Compare os totais com o mesmo recorte Meta, sem forçar igualdade com campanhas fora da seleção. Valide Custo/resultado e ROAS em linhas reais e o comprimento de cada mensagem com título, cabeçalho e code fences. Esses testes precedem qualquer afirmação de relatório completo.

## Janelas, custo e produto

Separar pré/pós quando o operador indicar mudança material de monetização. Confirmar a mudança na série diária; o marco informado é contexto do operador, não prova do dia exato da inflexão. Usar dias fechados como ranking principal e dia atual como monitoramento parcial. Comparar também uma coorte comum quando houver mistura de campanhas novas e antigas.

Usar NET_REVENUE para ROI com revenue share descontado. Confrontar INVESTIMENT SB com gasto Meta; mostrar divergências e adotar gasto Meta para o resultado reconciliado. Não misturar lucro de mídia/monetização com lucro contábil após impostos/outros custos. Meta purchase ROAS é complementar e pode divergir do ROI da SB.

Produto em SB pode ser um código de funil, como lp, e não o objeto anunciado. Nome comercial é rótulo provisório. Inspecionar thumbnails/preview reais dos grupos relevantes e declarar o alcance da amostra. Se um preview de Tablet parecer smartphone, manter o rótulo da campanha em aspas e marcar produto visual não validado; não corrigir taxonomia sem evidência suficiente. Mídia em creative SHARE pode não ter video_id: buscar object_story_spec/thumbnail_url por creative ID; não abortar todo o relatório por isso.

## HEALTH separado de ROI

Reproduzir a fórmula do frontend vivo; não inferir HEALTH por receita estimada. Fórmula validada na tela Adgroup:

```
r = ΣCDP_IMPRESSIONS × 100 / ΣGAM_CODE_SERVED_COUNT
HEALTH = max(0, r > 100 ? 200-r : r)
```

Sem denominador, mostrar indisponível (a UI pode renderizar zero). Usar HEALTH >=90% como indicador operacional de confiança do estimado conforme orientação de Rodolfo, nunca como garantia de lucro ou ausência de problemas. HEALTH não modifica numerador nem denominador do ROI. Calcular sobre somas, não pela média simples de percentuais. Exibir HEALTH do período e do último dia separadamente para não esconder deterioração.

## Classificação e metas propostas

ROI positivo com gasto residual não prova vencedor. Declarar a régua analítica escolhida de gasto, dias de entrega e consistência; ela não vira regra de corte/escala sem autorização. Diferenciar vencedor consistente, positivo com margem estreita, promissor com janela curta, negativo recente e inconclusivo. Não chamar todas as campanhas pausadas de perdedoras nem todo ROI alto de vencedor.

Expressar RPS claramente: NET_REVENUE / SESSIONS em USD por sessão ou multiplicado por 1.000, com a unidade visível. Para um cenário proposto de ROI q:

```
custo/sessão máximo = receita líquida/sessão / (1+q)
CPC máximo = receita líquida/cliques de link / (1+q)
```

São limites condicionais ao rendimento e à composição atuais, não bids Meta equivalentes nem budgets autorizados. Budget/dia, gasto acumulado e custo/conversão são grandezas diferentes.

## Colunas Custo e Gasto nos relatórios

- Interpretar `Custo` como **custo por resultado**, nunca gasto total. Quando ambas as métricas forem pedidas, separar `Gasto (USD)` e `Custo/resultado (USD/Add to Wishlist)`; manter ROI, ROAS, Estimated Health e início quando solicitados.
- Validar no contrato e no ad set vivo o evento de otimização. Para `ADD_TO_WISHLIST` web, usar somente `offsite_conversion.fb_pixel_add_to_wishlist` em Insights `actions`; não somar aliases como `add_to_wishlist`, `omni_add_to_wishlist` ou `onsite_web_add_to_wishlist`.
- Consultar `spend`, `actions` e `cost_per_action_type` na mesma conta, período e janela de atribuição. Calcular `spend / resultados` e conferir o custo da action correspondente quando retornado pela API. Se esse custo for omitido, derivar dos contadores; se a action exata estiver ausente, consultar a hierarquia/evento e declarar a limitação, sem substituir por compras, cliques ou `CONVERSIONS` genérico do SB.
- Resultado ausente ou zero = `n/d`, nunca custo zero. Gasto total continua sendo o denominador do ROI líquido; custo por resultado não substitui spend. ROI usa receita líquida SB; ROAS de compras Meta é distinto, com fonte declarada.
- Ao apenas completar um relatório anterior, preservar seleção e snapshot de Health/receita e declarar o horário da leitura Meta adicional. Se atualizar o relatório inteiro, declarar o novo snapshot e recalcular todas as métricas na mesma janela.
- A API pode retornar a action web em `actions` e omiti-la em `cost_per_action_type`. Derivar o custo pelos contadores web; conferir `add_to_wishlist`/`omni_add_to_wishlist` somente se a contagem do alias for idêntica à web, nunca somando aliases. Não abortar o relatório por ausência do custo nativo.
- Testar a razão em uma linha real, o comportamento sem resultados, unicidade dos IDs e ausência de soma entre aliases antes da entrega. Arredondar valores monetários exibidos com decimal e `ROUND_HALF_UP`, evitando truncar centavos em empates por representação binária.

## ROI normal e ROI estimado separados

- Quando o operador pedir uma coluna adicional de ROI estimado, preservar o ROI normal (`NET_REVENUE`), a seleção, a ordenação solicitada e o snapshot; não duplicar nem renomear o ROI normal como estimado. Usar `REVENUE_ESTIMATED` do mesmo snapshot por `CUSTOMER_ID` + `CAMPAIGN_ID` + `DATE`.
- Conferir a fórmula no frontend vigente do relatório Adgroup antes de aplicar ajustes: a versão baseada em `defaultMetrics` define ROI normal por `NET_REVENUE` e ROI estimado por `REVENUE_ESTIMATED`, ambos menos investimento e divididos por investimento. O relatório reconciliado MGS mantém gasto Meta como denominador das duas colunas e declara a diferença para `INVESTIMENT` SB. Não aplicar revenue share adicional presumido nem derivar receita estimada de Health; versões legadas do frontend podem possuir outra projeção.
- Sem receita estimada ou denominador positivo, mostrar `n/d`. Testar uma linha real, unicidade/contagem da seleção, conservação do snapshot e ordem de ROI; adicionar a coluna ao lado de ROI sem mudar as demais colunas por inferência.

## Recuperação do modelo vigente na conversa

- Aplicar primeiro a seção `Continuidade e alterações incrementais do relatório` do SKILL.md: ela define precedência do modelo da conversa, atualização versus complemento e preservação de colunas. Usar as definições específicas abaixo somente dentro do seu recorte.
- Na thread `1558147479432601670`, conta `1583000095650153` / Yolokfx Conta 02 G006, o modelo específico solicitado por Rodolfo e reafirmado por Geizian é **Início → Produto (camp.) → CRV → Custo → Gasto $ → Health → ROI → ROI est. → ROAS**, consolidado por produto + formato real, com ROI decrescente. Referência: relatório de 12/10/2026 às 22:13 EDT citado na própria conversa. Selecionar campanhas com entrega Meta no dia; receita SB de campanhas sem entrega fica separada, fora do consolidado. Manter o agrupamento por produto, salvo drill-down expresso para campanhas individuais; não adicionar ativos sem entrega às partições financeiras. Ausência de um produto no dia não autoriza copiar linha do dia anterior.
- O runner `shein-health-report.py` é específico para filtro de Health e não comprova um relatório genérico completo: ele separa campanhas sem denominador e não inclui automaticamente toda a seleção Meta. Em consolidação por produto, validar cobertura dos IDs com entrega, formato nos anúncios com entrega, partições disjuntas, somas financeiras/resultados, primeira entrega, receita estimada independente e tamanho do bloco Discord. Exigir em cada consulta teste de IDs únicos, cobertura integral de mídia e conservação de gasto/receita/resultados; não congelar contagens de consultas anteriores nem executar mutação Meta para completar um relatório.

## Padrão vigente — todas as contas de anúncio SHEIN

Rodolfo promoveu o relatório de doze colunas desta conversa a padrão de **todas as contas de anúncio SHEIN, independentemente de domínio, gestor, canal ou solicitante autorizado**, incluindo Geizian e os seis gestores. Origem: thread `1560303769680355525`; referência dos rótulos: mensagem `1560305388837150800`; a mensagem posterior de generalização não teve ID fornecido. Ordem e grafia exatas: **Início → Nº → Produto → Quiz → Gasto → Receita → Saldo → Est.Health → ROI → ROI est. → ROAS → Lance**.

Pedido genérico usa essas doze colunas, não um modelo antigo da conta. Pedido explícito diferente pode adaptar o relatório, sem redefinir o padrão global. Cabeçalho curto com conta/período/moeda, tabela `text` alinhada e rodapé breve; sem Custo/Res., orçamento ou cards adicionais por padrão. Não inferir período, filtros ou ordenação pela imagem nem herdar Health <95%. Ausência de fonte preserva a coluna com `n/d` e limitação declarada. Domínio independente para o layout não amplia permissões nem dispensa o gate de domínio.

Definições: Início = primeira entrega comprovada; Nº = número literal da campanha; Produto = rótulo do nome, não prova visual; Quiz = versão nos destinos reais dos anúncios; Gasto = Meta; Receita = `NET_REVENUE` SB; Saldo = Receita − Gasto; Est.Health = fórmula Adgroup sobre somas; ROI = 100 × (Receita − Gasto) / Gasto; ROI est. = 100 × (`REVENUE_ESTIMATED` − Gasto) / Gasto; ROAS = compras Meta; Lance = estratégia live MAXVOL/COCAP/BIDCAP, misto ou n/d. As receitas de consulta abaixo continuam aplicáveis; não inferir Quiz/Lance pelo nome. Sem denominador, n/d.

A fonte estrutural é `SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout`, registro `ARES-SHEIN-ALL-ACCOUNTS-REPORT-12COL-20261015`. A decisão substitui explicitamente o default provisório de sete colunas aprovado na thread `1557059385417797723` e os defaults históricos por conta abaixo; preserva histórico, sem duas versões ativas do mesmo padrão. O renderizador legado `shein-health-report.py` é fonte de coleta parcial, não apresentação final vigente; completar campos faltantes antes de entregar. Não criar cron, automação ou reemitir relatórios antigos por esta decisão.

### Histórico supersedido — modelos por canal/conta

Todos os layouts abaixo que antecedem `Lance e descrição curta de campanha` são evidência histórica, não defaults ativos. O modelo anterior por produto/CRV em `Recuperação do modelo vigente na conversa` também não substitui genericamente o padrão de doze colunas; somente um pedido explícito daquele recorte/modelo autoriza a adaptação. Complementos do mesmo relatório preservam seu snapshot conforme o pedido.

## Histórico de adoção — relatório yolo-g003

No relatório on-demand de campanhas com Estimated Health abaixo de 95% da conta `yolo-g003`, usar a ordem aprovada: `Início → Campanha → Custo/Res. → Gasto $ → Est.Health → ROI → ROAS`. Informar USD no cabeçalho e preservar o snapshot e os valores quando o pedido mudar somente a apresentação. Esta ordem é específica desse relatório; não promover automaticamente para outras contas/operações. Fonte: Rodolfo Mattei, thread Discord `1557056254730436671`.

## Ordem de colunas — relatório yolo-g004

No relatório on-demand de campanhas com Estimated Health abaixo de 95% da conta `yolo-g004`, usar `Início → Campanha → Custo/Res. → Gasto $ → Est.Health → ROI → ROAS`, com campanha/produto abreviado na mesma célula e tabela alinhada em bloco `text`, como a referência aprovada na thread `1557056254730436671`. Ao alterar somente o layout, preservar seleção, valores e horário do snapshot; não atualizar a API nem misturar métricas de outra conta. Fonte: Rodolfo Mattei, thread Discord `1557056270404681800`. Escopo exclusivo desse relatório; não promover para outras operações.

## Ordem de colunas — relatório yolo-g005

No relatório on-demand de campanhas com Estimated Health abaixo de 95% da conta `yolo-g005`, usar `Início → Campanha → Custo/Res. → Gasto $ → Est.Health → ROI → ROAS`, com bloco text alinhado, USD no cabeçalho e nomes resumidos mantendo o número identificador. Reproduzir o layout aprovado na thread de referência `1557056254730436671`, sem copiar campanhas, contas ou métricas dela. Pedido apenas de ordem/formato preserva a seleção, os valores e os horários dos snapshots anteriores; manter o grupo sem base de Health separado. Autoridade: Rodolfo Mattei, thread `1557056290688213005`. Não promover automaticamente para outras contas/operações.

## Modelo específico — Diretoria YOLO G002, thread 1560303769680355525

Rodolfo aprovou por imagem e esclarecimento explícito na mensagem `1560305388837150800` os rótulos e a ordem **Início → Nº → Produto → Quiz → Gasto → Receita → Saldo → Est.Health → ROI → ROI est. → ROAS → Lance** para o relatório YOLO G002 desta conversa. Inicialmente esta decisão substituía somente o layout anterior desta thread. Rodolfo a promoveu depois a padrão para todas as contas de anúncio SHEIN, independentemente do domínio, conforme a seção vigente acima; a limitação inicial à thread fica supersedida.

- Separar número e produto do nome; produto é rótulo, não validação visual. Não transportar qualificadores de lance, data, quiz, LP, áudio ou COPY para Produto quando o modelo pede somente produto.
- Receita = receita líquida SB (`NET_REVENUE`); Saldo = receita líquida SB menos gasto Meta; ROI est. usa `REVENUE_ESTIMATED`, separado do ROI normal.
- Quiz e Lance exigem readback real dos anúncios/creatives e campanhas/conjuntos, conforme as receitas abaixo. Lance mostra MAXVOL/COCAP/BIDCAP; não inferir a estratégia pelo nome nem adicionar cap/orçamento sem pedido.
- Pedido de corrigir rótulos/colunas é complemento: preservar seleção, métricas, totais, ordenação e horário financeiro já emitidos; consultar somente configurações faltantes e informar seu horário separado. Não adotar a ordenação ou valores da imagem por inferência.
- Validar as doze colunas, contagem/IDs, cobertura de anúncios e conjuntos, fórmulas e conservação do snapshot antes da renderização. Manter todas as campanhas, com blocos Discord dentro do limite e sem anexo não pedido.

## Ordem de colunas — relatório yolo-g002

Nos relatórios on-demand da conta `yolo-g002`, usar `Início → Campanha → Custo/Res. → Gasto $ → Est.Health → ROI → ROAS`, em tabela alinhada no bloco `text`, reproduzindo somente o layout da thread `1557056254730436671`, nunca seus dados ou seu recorte. Pedido “como está agora” exige atualização integral de métricas no período atual; não manter o filtro abaixo de 95% de uma pergunta anterior sem novo pedido. Informar USD, snapshot e primeira entrega; abreviar nomes preservando o número e produto. Fonte: Rodolfo Mattei, thread `1555776339431391265`. Escopo exclusivo dessa conta.

## Layout on-demand yolo-g001 — Estimated Health <95%

Para este relatório da `yolo-g001`, usar tabela `text` alinhada na ordem `Início → Campanha → Custo/Res. → Gasto $ → Est.Health → ROI → ROAS`, igual ao modelo de referência da thread `1557056254730436671`. A coluna Campanha deve conter número + produto do nome da campanha, preservando qualificadores relevantes; não mostrar somente Cxx nem tratar o nome como produto visual validado. Usar cabeçalho curto com conta/período/moeda, sem preâmbulo extenso acima da tabela. Preservar a seleção/snapshot em mudanças apenas visuais e informar em rodapé eventuais leituras adicionais e limitações. Fonte: Rodolfo Mattei na thread `1557056236187422731`. Verificar ordem das sete colunas, número + produto em cada linha, contagem/IDs únicos e custo por resultado separado do gasto antes de entregar.

## Lance e descrição curta de campanha

- Para coluna `Bid` ou `Lance`, fazer GET dos IDs exatos com `fields=id,name,bid_strategy,status`; consultar também `act_<account_id>/adsets` com `fields=id,campaign_id,bid_strategy,bid_amount,bid_constraints,status`, filtro `campaign.id IN` para a seleção e paginação bounded. Usar o transporte `ares-meta-common.py` com a versão Graph da operação e a credencial do binding da conta; não reconsultar receita para acrescentar configuração.
- Resolver a estratégia do conjunto quando exposta; se omitida, usar a estratégia live da campanha CBO. Ler o valor de `bid_amount` no conjunto, não presumir que ele existe na campanha. Converter unidades menores com `Decimal` conforme a moeda validada; na conta USD, dividir por 100. Resolver MAXVOL=`LOWEST_COST_WITHOUT_CAP`, COCAP=`COST_CAP` e BIDCAP=`LOWEST_COST_WITH_BID_CAP`. Mostrar MAXVOL sem cap; cap ausente fica `n/d`, nunca zero.
- Exigir cobertura de todos os conjuntos de cada campanha. Valores ou estratégias diferentes ficam explícitos como mistos; não selecionar arbitrariamente um conjunto. Quando todas as linhas usam a mesma estratégia, mostrar o valor na coluna Bid e explicar COCAP/BIDCAP uma única vez no rodapé. Nome, gasto e Custo não comprovam lance configurado. Declarar horário dessa leitura separado do snapshot financeiro preservado.
- Quando Camp. for solicitada como somente número + produto, retirar data, quiz, lance/cap, tracking, COPY, LP e qualificadores de anúncio como IMG/audio new/new ad da descrição visível, preservando números/variantes que identificam o produto (ex.: EBIKE 2). Produto segue sendo rótulo do nome, não validação visual. Testar cobertura/IDs, contagem por tipo de lance, ordem ROI e limite de cada bloco.

## Orçamento diário como coluna de configuração

1. Reutilizar os IDs, a ordem e o snapshot financeiro do relatório a complementar. Fazer GET da conta para confirmar moeda e identidade e dos mesmos IDs de campanha com `fields=id,name,status,daily_budget,lifetime_budget`; agrupar leituras independentes sem ampliar a seleção.
2. Em CBO, usar `daily_budget` da campanha e converter unidades menores conforme a moeda; para USD, `Decimal(valor) / 100`, exibido com `ROUND_HALF_UP`. Nomear `Orç./dia` e inserir após `Gasto $` quando solicitado. Orçamento é configuração diária, não gasto já realizado, saldo restante ou projeção.
3. Sem `daily_budget` na campanha, verificar o nível real: orçamento vitalício não vira orçamento diário; em ABO, consultar `daily_budget` e `lifetime_budget` dos conjuntos. Se exibir uma soma de budgets diários ABO, identificar explicitamente que é soma dos conjuntos, não budget CBO. Configuração mista ou desconhecida fica explícita, sem orçamento inferido.
4. Persistir a leitura adicional sem credenciais e registrar seu horário separado dos horários financeiro e de Bid já preservados. Conferir cobertura exata, nomes/IDs, moeda, posição da coluna e manutenção dos valores e totais anteriores. Esta consulta não altera budget, bid ou status.

## Quiz e compactação do relatório

- Para informar qual quiz uma campanha usa, consultar todos os anúncios da seleção exata e seus creatives completos; extrair destinos em `object_story_spec` (link/CTA) e `asset_feed_spec.link_urls[].website_url`. `link_url` pode complementar a leitura. Nome de campanha, LP NORMAL/NOVA e COPY não provam o quiz atual. Mapear somente rotas verificadas `/quiz/us/sh([123])-gNNN/` para v1/v2/v3 conforme o plugin corporativo; validar hostname pelo gate. Destinos divergentes na mesma campanha são mistos, e campos ausentes são `n/d`, nunca um quiz inferido.
- Ao adicionar Quiz a um snapshot anterior, conservar métricas, seleção e ordem, informar separadamente o horário do readback de destinos e inserir a coluna na posição solicitada. Testar cobertura de campanhas/anúncios, ausência de destinos não mapeados e unicidade da seleção.
- Quando o operador pedir menos partes no Discord, empacotar o máximo de linhas inteiras por mensagem após contabilizar título, cabeçalho e code fence dentro do limite real de 2000 caracteres. Abreviar nomes com legenda sem perder número/produto/qualificadores materiais; remover do nome apenas qualificadores já representados em coluna verificada. Repetir cabeçalho completo por bloco e não cortar tabelas ou linhas. Validar comprimento programaticamente e reconciliar todas as linhas; minimizar partes não autoriza omitir campanhas nem anexar arquivo sem pedido.

## Tipo de criativo em relatório consolidado

- Ao pedir coluna de formato (por exemplo `CRV`), preservar o snapshot financeiro, a seleção e a ordem; consultar anúncios/creatives da conta exata e informar separadamente o horário do readback de mídia. Não inferir formato por nome IMG, produto ou thumbnail.
- Para formato usado no dia, cruzar os anúncios com Insights no nível ad (impressões ou gasto positivos no período). Exigir cobertura de todas as campanhas selecionadas. Insights de campanha podem incluir conversões atribuídas no dia sem impressões/gasto e sem linha no nível ad; conferir o ID exato e manter essa campanha na reconciliação, com `CRV=n/d` para ausência de entrega no período. Não inferir formato de hoje pela configuração nem descartar a receita atribuída. Com gasto zero, Custo/ROI/ROI estimado/ROAS permanecem `n/d`; denominador Health ausente também fica `n/d`. Testar a conservação de campanhas/receita e a separação entre formato configurado e formato com entrega. Classificar vídeo por `video_id`, `object_story_spec.video_data` ou `asset_feed_spec.videos`; imagem por `image_hash`, imagem de `link_data` ou `asset_feed_spec.images`. `video_data.image_url` é thumbnail, não um segundo asset de imagem. Inspecionar os itens de carrossel individualmente e manter `n/d` se faltar evidência.
- Consolidar a união dos formatos dos anúncios com entrega: Imagem, Vídeo ou Misto (imagem + vídeo), sem dividir o grupo financeiro nem recalcular as suas métricas, salvo pedido explícito de separação. Testar vídeo com thumbnail como somente Vídeo, feed com ambos como Misto e link com image_hash como Imagem; conferir unicidade dos ads, cobertura das campanhas, posição da coluna e limite de caracteres.
- Se o operador pedir linhas separadas por Imagem/Vídeo, particionar produto + formato usando IDs reais e recalcular indicadores pelas somas do mesmo snapshot. Quando cada campanha tem somente um formato com entrega, somar integralmente seu gasto Meta, receita SB, contadores Health e resultados na partição correspondente; exigir IDs disjuntos, cobertura integral e totais preservados. Se uma campanha realmente entrega ambos os formatos e a receita SB não identifica anúncio/asset, não ratear receita nem duplicar ROI: mostrar indisponibilidade do ROI por formato e manter o total reconciliado. A renomeação `TIPO` → `CRV` não altera as métricas nem o agrupamento.

## Data de início nos relatórios

Incluir `Início` em cada card e na tabela consolidada. Consultar Insights diários da campanha desde a criação até a data do relatório e escolher a primeira data com impressões ou gasto; `created_time` delimita a busca, mas não prova entrega. `start_time` é schedule e pode mudar após reativação. Não inferir início pela data no nome. Para teste de formato com amostra, declarar quais campanhas foram selecionadas e separar os totais da conta dos números da amostra, sem representar a amostra como relatório completo.

## Teste mínimo

Validar que cada início exibido corresponde ao mínimo diário com entrega, que todos os IDs da amostra pertencem à conta autorizada e que card e tabela usam a mesma data. Confirmar conjuntos de CAMPAIGN_ID + data entre Meta/SB, contagens e somas; reconciliar diferença de gasto por janela; verificar fórmula HEALTH contra o frontend e uma linha real; confirmar períodos e moeda do histórico Pricing; preservar limitações visuais e do dia parcial no relatório.
