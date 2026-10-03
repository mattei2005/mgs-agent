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

São limites condicionais ao rendimento e à composição atuais, não bids Meta equivalentes nem budgets autorizados. Custo por Add to Wishlist usa a action Meta exata, evitando duplicar aliases. Budget/dia, gasto acumulado e custo/conversão são grandezas diferentes.

## Teste mínimo

Confirmar conjuntos de CAMPAIGN_ID + data entre Meta/SB, contagens e somas; reconciliar diferença de gasto por janela; verificar fórmula HEALTH contra o frontend e uma linha real; confirmar períodos e moeda do histórico Pricing; preservar limitações visuais e do dia parcial no relatório.
