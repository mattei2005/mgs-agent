# Revenue and dashboard reconciliation

## Objective

Unificar leitura de mídia, monetização e SMS sem esconder a origem de cada valor. Para aquisição, a unidade mínima é o `UTM_ADGROUP` canônico (`bNNfbNNcNNgNN`). Para SMS, a chave precisa ser traduzida pela configuração de site/campanha/gestor; não assumir igualdade textual com o adgroup.

## Source map

```text
Sistema / tela                     | Dado esperado                              | Autoridade
-----------------------------------|--------------------------------------------|------------------------------
Meta Ads                           | spend, delivery, clicks, events            | custo de mídia/entrega
Smart Bidding > Reports > Adgroup  | performance e receita de aquisição         | monetização por adgroup
Smart Bidding > Reports > SMS      | ganho/receita de SMS                       | receita SMS
SMS Funnel dashboard               | envios/custo real exibido pelo fornecedor   | custo vendor por período
WP > MGS Quiz > Relatório          | leads, custo estimado e receita SMS SB       | estimativa WP + backfill SB separado
```

O acesso às telas é read-only. Não alterar filtros salvos, integrações, usuários, listas, custo, tracking ou configuração.

## Smart Bidding — Adgroup

Caminho informado por Rodolfo: `Reports > Adgroup`.

Operação esperada:

1. Selecionar data/range.
2. Filtrar o domínio no campo ao lado da data.
3. Aplicar filtros adicionais em `Filter`.
4. Localizar o `utm_adgroup`/chave equivalente.
5. Registrar campos e moeda exatamente como exibidos.
6. Somar apenas linhas pertencentes à mesma campanha/estratégia.

A captura fornecida e a validação autenticada read-only em 2026-07-10 confirmaram:

```text
Tela / dado                  | Rota/endpoint
-----------------------------|------------------------------------------------------
AdGroup                      | `https://app.smartbiddingdigital.com/reports/adgroup`
Dados AdGroup                | `POST https://api.jbfdigital.com.br/report/performance_per_campaigns`
Domínios                     | `GET https://api.jbfdigital.com.br/report/performance_per_domain`
SMS                          | `https://app.smartbiddingdigital.com/reports/sms`
Dados SMS                    | `POST https://api.jbfdigital.com.br/report/performance_per_sms`
Última atualização           | `POST https://api.jbfdigital.com.br/report/last_update`
```

A tela AdGroup possui seletor de data, seletor de sites, `Filter` e rótulos/cards como `Investment`, `Conversions`, `Revenue Acquisition` e `Revenue Total`. A validação do bundle oficial e da API autenticada em 2026-08-19 confirmou o contrato usado pela própria tela:

```text
Endpoint  POST /report/performance_per_campaigns
Payload   initialDate, finalDate, publishers[], currency
Conta     CUSTOMER_ID + ACCOUNT_NAME
Campanha  CAMPAIGN_ID + CAMPAIGN_NAME
Junção    UTM_ADGROUP
Spend     INVESTIMENT
Receita   NET_REVENUE quando Discount revenue share está habilitado
ROI       (receita − INVESTIMENT) × 100 ÷ INVESTIMENT
```

A tela inicia com `Discount revenue share` habilitado; portanto, reproduzir o relatório padrão exige usar `NET_REVENUE`, não `REVENUE` bruto. Datas do date picker são objetos JavaScript e são serializadas em UTC. A API pode devolver uma data civil adjacente ao intervalo escolhido; depois da resposta, filtrar `DATE` novamente pelo início/fim pretendidos no timezone operacional e contar os dias inclusivos. Para reconciliar com Meta, filtrar primeiro `CUSTOMER_ID` exato, cruzar `CAMPAIGN_ID` exato, comparar `CAMPAIGN_NAME` normalizado e só comparar spend quando as duas fontes estiverem na mesma moeda. Prefira a API autenticada capturada da própria SPA para extração repetível, preservando sessão/tokens fora de logs e chat. Não inferir valores cortados em captura.

## Smart Bidding — SMS

Caminho informado: `Reports > SMS`.

Use para receita/ganho de SMS das estratégias com captura. O SMS não entra automaticamente no total de toda campanha:

```text
Captura | Evidência de SMS atribuível | Tratamento
--------|------------------------------|-------------------------------------
Sim     | Sim                          | Somar receita SMS
Sim     | Não                          | Marcar receita SMS indisponível
Não     | Não                          | Receita SMS = 0 no modelo
Não     | Sim                          | Investigar tracking antes de somar
```

## SMS Funnel

Objetivo read-only: localizar uma tela/exportação que mostre volume enviado e custo por dia/lista/gestor, e identificar se existe endpoint/API de leitura estável.

Mapeamento read-only do bundle público da dashboard em 2026-07-10 confirmou:

```text
Item                         | Rota/endpoint autenticado
-----------------------------|---------------------------------------------------------------
Tela Performance por Funil   | `/#/analytics/funnel-performance`
Consolidado por período      | `GET /api/analytics/funnel-performance?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
Detalhe por campanha         | `GET /api/analytics/funnel-performance/{campaignId}/sequences?start_date=...&end_date=...`
API base                     | `https://web2.smsfunnel.com.br/api`
```

A tela declara `Receita Total`, `Receita Total SMS`, `Custo Total`, `Total de Conversões SMS`, `Total SMS Enviados` e tabela por funil com `SMS Enviados`, `Custo`, `Conversões`, `Receita` e `ROI`. O tooltip de custo define `quantidade enviada × custo unitário por SMS`. A resposta autenticada usa `data.totals.total_sms_sent`, `data.totals.sms_unit_cost` e `data.totals.total_cost`; validar sempre `total_sms_sent × sms_unit_cost = total_cost`. Esses endpoints exigem sessão; nunca colocar token/cookie em log ou chat.

Checklist de exploração:

- filtros por período;
- filtro/lista/gestor;
- total de mensagens enviadas;
- custo unitário exibido ou derivável;
- custo total;
- moeda;
- export CSV/XLSX;
- chamadas XHR/JSON utilizáveis sem automação visual;
- timezone da plataforma.

Não assuma que lead capturado equivale a SMS efetivamente enviado ou faturado. Se a dashboard não expuser evento cobrado, usar o custo estimado WordPress com rótulo explícito.

## WordPress mgs-quiz-report

Para `creditoparaveiculo.com`, o mapeamento técnico versionado do Zeus registra:

- custo estimado = todas as linhas filtradas do relatório × R$ 0,08;
- cálculo em centavos inteiros;
- mesmos filtros de `report_where()`;
- não filtra por status SMS, telefone válido, duplicidade ou visibilidade no vendor;
- nome correto: `Custo estimado de SMS — base WP`;
- não reconcilia automaticamente com SMS Funnel.

Portanto, esse card é uma estimativa de custo por linha absorvida, não uma prova de faturamento do fornecedor.

O relatório WordPress em produção também exibe **`Receita SMS — Smart Bidding`** a partir do backfill próprio, mas essa receita permanece separada do custo estimado:

- fonte: Smart Bidding `Reports > SMS` / `performance_per_sms`;
- com `Discount revenue share`, usar `NET_REVENUE`/`net_revenue_cents` como receita primária e preservar gross para auditoria;
- atribuição atual: domínio + data + `utm_campaign` do namespace SMS;
- respeita data inicial/final, mas não deve fingir granularidade por quiz, gestor, parcela ou busca sem mapping confiável;
- data atual é provisória; fechamento e backfill devem usar dias fechados e upsert idempotente;
- nunca somar o card de receita SB ao próprio total SB novamente.

No `creditoparaveiculo.com`, a validação autenticada de 2026-07-10 confirmou `mgs-quiz-report` acessível, cards de custo por registro/custo estimado, tabela por quiz e o card `Receita SMS — Smart Bidding`.

## Join keys

A validação live do SB mostrou dois namespaces diferentes:

```text
Relatório SB | Campo de atribuição | Exemplo de formato observado
-------------|---------------------|----------------------------
Adgroup      | `UTM_ADGROUP`       | `b01fb03c01g01`
SMS          | `UTM_CAMPAIGN`      | `s01c01g002`
```

Logo, **não** juntar SMS e Adgroup por igualdade direta das strings. O relatório SMS atual usa namespace de site/campanha/gestor; a aquisição usa BM/conta/campanha/adset. A ponte deve vir do cadastro operacional da quiz/lista/gestor para a campanha Meta e precisa ser demonstrada para o recorte.

Prioridade para reconciliação:

```text
Prioridade | Chave / evidência
-----------|-------------------------------------------------------------
1          | `UTM_ADGROUP` para Meta + receita de aquisição
2          | mapping explícito `SMS sNNcNNgXXX → quiz/lista/gestor → adgroup`
3          | domínio + gestor + janela somente para diagnóstico, nunca fechamento
```

Nunca juntar somente por domínio quando duas campanhas/adsets coexistirem. Se o mapping SMS→adgroup não existir, manter a receita SMS em bucket separado por gestor/site/campanha e marcar a margem por adgroup como não reconciliada.

## Metric model

Para cada adgroup:

```text
meta_spend
acquisition_revenue
sms_revenue
sms_count_vendor
sms_unit_cost_vendor
sms_cost_vendor
wp_report_rows
wp_sms_cost_estimated
```

Derivações:

```text
gross_revenue = acquisition_revenue + eligible_sms_revenue
contribution_before_other_costs = gross_revenue - meta_spend - chosen_sms_cost
roas_gross = gross_revenue / meta_spend
roas_after_sms = (gross_revenue - chosen_sms_cost) / meta_spend
```

`chosen_sms_cost` deve dizer a origem:

- `vendor_actual_or_dashboard`: quando a dashboard/export expõe custo atribuível;
- `wp_estimated`: quando usa linhas WP × R$ 0,08;
- `unavailable`: quando nenhum método é confiável.

Não chamar `contribution_before_other_costs` de lucro líquido: hosting, taxas, chargebacks, impostos e outros custos podem estar fora do recorte.

## Reconciliation gates

1. **Date gate:** todas as fontes cobrem a mesma janela.
2. **Timezone gate:** converter ou declarar diferença.
3. **Currency gate:** não somar moedas diferentes sem taxa/origem explícita.
4. **Key gate:** adgroup/campaign join validado.
5. **Capture gate:** SMS elegível conforme estratégia.
6. **Cost provenance gate:** custo vendor e estimativa WP não são somados entre si.
7. **Completeness gate:** linhas por adgroup fecham com o total consolidado.

## Minimum report

```text
Adgroup | Estratégia | Meta | Receita aquis. | Receita SMS | Custo SMS | Origem custo | Margem parcial | Status
--------|------------|------|----------------|-------------|-----------|--------------|----------------|-------
...     | quiz+cap.  | ...  | ...            | ...         | ...       | vendor/WP    | ...            | OK/divergente
```

Se uma fonte estiver bloqueada, reportar `indisponível` com o motivo; nunca preencher com benchmark presumido.
