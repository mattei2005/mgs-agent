# Análise SHEIN por produto — Meta × Smart Bidding

## Escopo e fontes

Resolver conta/gestor pelo contrato vivo e validar o domínio antes da consulta. Analisar somente o CUSTOMER_ID solicitado. Usar Meta Insights diário e SB Reports > Adgroup, juntando CAMPAIGN_ID + data civil; UTM_ADGROUP preserva o drill-down. Pricing é evidência de monetização por operação/regra, não automaticamente por produto ou gestor.

## Coleta segura

- Nunca imprimir ou salvar o objeto inteiro de GET /company: publishers podem carregar credenciais em vps, panel e wordpress. Projetar somente companyId, publisherId, name e url antes de log ou arquivo. Aceitar publisher.name sem .com; resolver a identidade pelo hostname de url e validar a referência publisherId.
- Adgroup: POST /report/performance_per_campaigns com initialDate, finalDate, publishers e currency. Filtrar DATE novamente depois da resposta e confirmar ausência de linhas/IDs de outra conta.
- Pricing: GET /pricing/{publisherId}?should_update_metrics=1. Snapshot pode estar em BRL; não rotular a receita como USD. valueUSD é piso, não RPS ou receita.
- Histórico Pricing: POST /pricing/{publisherId}/trail/metrics com rule real, days, finalDate ISO e currency=USD; a janela pode incluir dia extra, portanto filtrar date novamente. O RPS retornado é contribuição daquela regra por 1.000 sessões, não RPS de todo o site/produto.
- Aplicar paginação Meta até ausência de next, sem imprimir next URLs autenticadas. Não repetir extrações completas após uma falha só na SB: reutilizar arquivos/IDs já coletados.

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

## Modelo provisório vigente — seis canais SHEIN

Decisão explícita de Rodolfo na thread `1557059385417797723`: enquanto ele alinha os próximos pedidos com Geizian, todos os relatórios on-demand nos canais `shein-g001` a `shein-g006` usam o modelo aprovado na thread `1557056254730436671`. Ordem exata: **Início → Campanha → Custo/Res. → Gasto $ → Est.Health → ROI → ROAS**. Entregar cabeçalho curto com conta, período/snapshot e moeda, tabela alinhada em bloco `text` e rodapé breve com fontes/limitações, sem cards ou preâmbulo extenso por padrão. Campanha = número + rótulo resumido do produto/nome, mantendo qualificadores importantes; o nome não prova produto visual.

O padrão rege apresentação, não filtro, período, cadência ou autoridade. Relatório genérico não herda o filtro Estimated Health <95% de outra pergunta; usar o recorte atual. Mudança apenas visual preserva seleção/valores/snapshot; nova consulta informa snapshot atualizado. Usar início por primeira entrega, custo por Add to Wishlist, gasto separado, ROI líquido SB versus gasto Meta e ROAS de compras Meta; ausentes continuam n/d. O contrato `SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout` é a fonte estrutural da vigência. Não criar cron, entrega automática ou reemitir relatórios antigos por esta decisão.

As seções por conta abaixo preservam o histórico de adoção; suas antigas restrições de não generalizar foram superadas exclusivamente para os seis canais SHEIN por esta autorização. Qualquer revisão futura depende de nova decisão explícita, sem expiração inferida.

## Histórico de adoção — relatório yolo-g003

No relatório on-demand de campanhas com Estimated Health abaixo de 95% da conta `yolo-g003`, usar a ordem aprovada: `Início → Campanha → Custo/Res. → Gasto $ → Est.Health → ROI → ROAS`. Informar USD no cabeçalho e preservar o snapshot e os valores quando o pedido mudar somente a apresentação. Esta ordem é específica desse relatório; não promover automaticamente para outras contas/operações. Fonte: Rodolfo Mattei, thread Discord `1557056254730436671`.

## Ordem de colunas — relatório yolo-g004

No relatório on-demand de campanhas com Estimated Health abaixo de 95% da conta `yolo-g004`, usar `Início → Campanha → Custo/Res. → Gasto $ → Est.Health → ROI → ROAS`, com campanha/produto abreviado na mesma célula e tabela alinhada em bloco `text`, como a referência aprovada na thread `1557056254730436671`. Ao alterar somente o layout, preservar seleção, valores e horário do snapshot; não atualizar a API nem misturar métricas de outra conta. Fonte: Rodolfo Mattei, thread Discord `1557056270404681800`. Escopo exclusivo desse relatório; não promover para outras operações.

## Ordem de colunas — relatório yolo-g005

No relatório on-demand de campanhas com Estimated Health abaixo de 95% da conta `yolo-g005`, usar `Início → Campanha → Custo/Res. → Gasto $ → Est.Health → ROI → ROAS`, com bloco text alinhado, USD no cabeçalho e nomes resumidos mantendo o número identificador. Reproduzir o layout aprovado na thread de referência `1557056254730436671`, sem copiar campanhas, contas ou métricas dela. Pedido apenas de ordem/formato preserva a seleção, os valores e os horários dos snapshots anteriores; manter o grupo sem base de Health separado. Autoridade: Rodolfo Mattei, thread `1557056290688213005`. Não promover automaticamente para outras contas/operações.

## Ordem de colunas — relatório yolo-g002

Nos relatórios on-demand da conta `yolo-g002`, usar `Início → Campanha → Custo/Res. → Gasto $ → Est.Health → ROI → ROAS`, em tabela alinhada no bloco `text`, reproduzindo somente o layout da thread `1557056254730436671`, nunca seus dados ou seu recorte. Pedido “como está agora” exige atualização integral de métricas no período atual; não manter o filtro abaixo de 95% de uma pergunta anterior sem novo pedido. Informar USD, snapshot e primeira entrega; abreviar nomes preservando o número e produto. Fonte: Rodolfo Mattei, thread `1555776339431391265`. Escopo exclusivo dessa conta.

## Layout on-demand yolo-g001 — Estimated Health <95%

Para este relatório da `yolo-g001`, usar tabela `text` alinhada na ordem `Início → Campanha → Custo/Res. → Gasto $ → Est.Health → ROI → ROAS`, igual ao modelo de referência da thread `1557056254730436671`. A coluna Campanha deve conter número + produto do nome da campanha, preservando qualificadores relevantes; não mostrar somente Cxx nem tratar o nome como produto visual validado. Usar cabeçalho curto com conta/período/moeda, sem preâmbulo extenso acima da tabela. Preservar a seleção/snapshot em mudanças apenas visuais e informar em rodapé eventuais leituras adicionais e limitações. Fonte: Rodolfo Mattei na thread `1557056236187422731`. Verificar ordem das sete colunas, número + produto em cada linha, contagem/IDs únicos e custo por resultado separado do gasto antes de entregar.

## Lance e descrição curta de campanha

- Quando o operador pedir coluna Lance, ler `bid_strategy` das campanhas e de todos os ad sets da seleção exata. Resolver MAXVOL=`LOWEST_COST_WITHOUT_CAP`, COCAP=`COST_CAP` e BIDCAP=`LOWEST_COST_WITH_BID_CAP` pelo contrato vivo; nome contendo BID/MAXVOL/COCAP não prova configuração. Divergências ficam explícitas como mistas, campos ausentes ficam `n/d`; declarar horário dessa leitura separado do snapshot financeiro preservado.
- Quando Camp. for solicitada como somente número + produto, retirar data, quiz, lance/cap, tracking, COPY, LP e qualificadores de anúncio como IMG/audio new/new ad da descrição visível, preservando números/variantes que identificam o produto (ex.: EBIKE 2). Produto segue sendo rótulo do nome, não validação visual. Testar cobertura/IDs, contagem por tipo de lance, ordem ROI e limite de cada bloco.

## Quiz e compactação do relatório

- Para informar qual quiz uma campanha usa, consultar todos os anúncios da seleção exata e seus creatives completos; extrair destinos em `object_story_spec` (link/CTA) e `asset_feed_spec.link_urls[].website_url`. `link_url` pode complementar a leitura. Nome de campanha, LP NORMAL/NOVA e COPY não provam o quiz atual. Mapear somente rotas verificadas `/quiz/us/sh([123])-gNNN/` para v1/v2/v3 conforme o plugin corporativo; validar hostname pelo gate. Destinos divergentes na mesma campanha são mistos, e campos ausentes são `n/d`, nunca um quiz inferido.
- Ao adicionar Quiz a um snapshot anterior, conservar métricas, seleção e ordem, informar separadamente o horário do readback de destinos e inserir a coluna na posição solicitada. Testar cobertura de campanhas/anúncios, ausência de destinos não mapeados e unicidade da seleção.
- Quando o operador pedir menos partes no Discord, empacotar o máximo de linhas inteiras por mensagem após contabilizar título, cabeçalho e code fence dentro do limite real de 2000 caracteres. Abreviar nomes com legenda sem perder número/produto/qualificadores materiais; remover do nome apenas qualificadores já representados em coluna verificada. Repetir cabeçalho completo por bloco e não cortar tabelas ou linhas. Validar comprimento programaticamente e reconciliar todas as linhas; minimizar partes não autoriza omitir campanhas nem anexar arquivo sem pedido.

## Data de início nos relatórios

Incluir `Início` em cada card e na tabela consolidada. Consultar Insights diários da campanha desde a criação até a data do relatório e escolher a primeira data com impressões ou gasto; `created_time` delimita a busca, mas não prova entrega. `start_time` é schedule e pode mudar após reativação. Não inferir início pela data no nome. Para teste de formato com amostra, declarar quais campanhas foram selecionadas e separar os totais da conta dos números da amostra, sem representar a amostra como relatório completo.

## Teste mínimo

Validar que cada início exibido corresponde ao mínimo diário com entrega, que todos os IDs da amostra pertencem à conta autorizada e que card e tabela usam a mesma data. Confirmar conjuntos de CAMPAIGN_ID + data entre Meta/SB, contagens e somas; reconciliar diferença de gasto por janela; verificar fórmula HEALTH contra o frontend e uma linha real; confirmar períodos e moeda do histórico Pricing; preservar limitações visuais e do dia parcial no relatório.
