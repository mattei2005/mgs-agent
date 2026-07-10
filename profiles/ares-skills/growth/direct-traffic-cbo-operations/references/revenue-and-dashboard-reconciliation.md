# Revenue and dashboard reconciliation

## Objective

Unificar leitura de mídia, monetização e SMS sem esconder a origem de cada valor. A unidade mínima de análise é o adgroup canônico (`bNNfbNNcNNgNN`) no mesmo período, timezone e moeda.

## Source map

```text
Sistema / tela                     | Dado esperado                              | Autoridade
-----------------------------------|--------------------------------------------|------------------------------
Meta Ads                           | spend, delivery, clicks, events            | custo de mídia/entrega
Smart Bidding > Reports > Adgroup  | performance e receita de aquisição         | monetização por adgroup
Smart Bidding > Reports > SMS      | ganho/receita de SMS                       | receita SMS
SMS Funnel dashboard               | envios/custo exibido pelo fornecedor        | custo vendor, se disponível
WP > MGS Quiz > Relatório          | leads absorvidos e custo estimado base WP   | estimativa interna de SMS
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

A captura fornecida confirma tela AdGroup com seletor de data, seletor de sites e cards como `Investment`, `Conversions` e `Revenue Acquisition`; valores estavam cortados e não devem ser inferidos.

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

## Join keys

Prioridade para reconciliação:

```text
Prioridade | Chave
-----------|---------------------------------------------
1          | utm_adgroup completo (`bNNfbNNcNNgNN`)
2          | utm_campaign + adset confirmados
3          | domínio + gestor + janela, apenas diagnóstico
```

Nunca juntar somente por domínio quando duas campanhas/adsets coexistirem.

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
