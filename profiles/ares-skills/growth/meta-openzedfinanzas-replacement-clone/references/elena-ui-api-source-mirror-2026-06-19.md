# Elena UI→API source mirror — 2026-06-19

## Trigger

Rodolfo corrigiu o fluxo de clone/replacement: manter o padrão oficial Ares 1 campaign / 1 adset / 3 ads para operação futura, mas usar um clone fiel da Elena como diagnóstico técnico para descobrir o pacote exato aceito pela Meta na conta EU/financeiro. Não transformar campanhas manuais diferentes em padrão permanente.

## Fonte

Campanha source validada via GET:

```text
Campaign ID  | 120248940367540604
Nome         | Elena Santana - ES - ESP - (pg_22091) - 4
Status       | ACTIVE
Objective    | OUTCOME_SALES
Buying type  | AUCTION
Bid strategy | COST_CAP
Budget       | daily_budget=10000 (USD 100)
Start        | 2026-06-19T00:04:00+0200
Smart promo  | GUIDED_CREATION
Pacing       | standard
Category     | FINANCIAL_PRODUCTS_SERVICES / ES
```

Artifacts:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/source-mirror-120248940367540604-20260619T035846Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-ui-api-matrix-20260619T035846Z.md
```

## Estrutura real Elena

```text
Adset ID             | Nome                  | Bid | Attribution | DSA             | Regional
---------------------|-----------------------|-----|-------------|-----------------|------------------------------
120248940367380604   | Conjunto 02 - VÍDEOS  | 200 | 7d click/1v | Openzed/Openzed | SPAIN_FINSERV,VOLUNTARY_VERIFICATION
120248940367340604   | Conjunto 01 - VÍDEOS  | 200 | 7d click/1v | Openzed/Openzed | SPAIN_FINSERV,VOLUNTARY_VERIFICATION
```

Campos comuns:

```text
optimization_goal             | OFFSITE_CONVERSIONS
optimization_sub_event        | NONE
billing_event                 | IMPRESSIONS
destination_type              | MESSENGER
promoted_object.pixel_id      | 629060785934493
promoted_object.custom_event  | COMPLETE_REGISTRATION
promoted_object.page_id       | 990898360783030
promoted_object.smart_pse     | false
targeting.geo                 | ES, home/recent
targeting.age                 | 18-65
targeting_automation          | advantage_audience=1
brand_safety                  | FACEBOOK_RELAXED, AN_RELAXED
is_dynamic_creative           | false
use_new_app_click             | false
```

## UI screenshot → API mapping

```text
UI Meta                         | API/source field provável/confirmado
--------------------------------|------------------------------------------------
Dataset ES-CC-ES-01             | promoted_object.pixel_id=629060785934493
Complete registration            | custom_event_type=COMPLETE_REGISTRATION
Facebook Page Elena Santana      | promoted_object.page_id=990898360783030
Manual destination Messenger     | destination_type=MESSENGER
Performance goal conversions     | optimization_goal=OFFSITE_CONVERSIONS
Cost per result goal $2.00       | bid_amount=200 + campaign bid_strategy=COST_CAP
Attribution 7-day click/1-view   | attribution_spec 7d click + 1d view
Location Spain                   | targeting.geo_locations.countries=[ES]
Advantage+ audience              | targeting_automation.advantage_audience=1
Advertiser Openzed               | dsa_beneficiary=Openzed
Beneficiary/Payer Digital Trust  | UI transparency label; API GET retornou Openzed/Openzed
Placements automatic             | asset_customization_rules + placement optimization no creative
Excluded placements none         | sem exclusões manuais no GET; brand safety relaxed
```

## Correção de workflow

- Não usar payload padrão Ares para diagnosticar clone fiel de Elena.
- Não alterar attribution para `1-day click / 0 view` só porque a API retornou `1885501`; a UI e o GET source confirmam `7-day click / 1-day view`. Esse erro indica que o contexto novo não equivale à source.
- Para teste diagnóstico, clonar fielmente a estrutura real da Elena: 2 adsets, 6 ads, COST_CAP, bid_amount=200, DSA/regional, attribution 7/1, asset_feed_spec/placement rules.
- Depois que o clone fiel funcionar, extrair o pacote obrigatório EU/Elena e voltar ao padrão operacional Ares 1x3.

## Diferenças permitidas no clone diagnóstico

```text
name        | novo RPL/diagnóstico
budget      | USD 25 por regra Ares, salvo Rodolfo pedir clone até no budget
status      | PAUSED por segurança
start_time  | novo start D+1 01:00 Madrid em UTC Z
ids         | novos IDs Meta
```
