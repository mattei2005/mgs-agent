# Matriz UI→API — Elena Santana pg_22091 — clone fiel diagnóstico
- Gerado em: 2026-06-19T03:59:25.429213+00:00
- Source mirror audit: `/root/mgs-agent/data/ares/meta-ads/audit/clone/source-mirror-120248940367540604-20260619T035846Z.json`
- Modo: read-only / GET only / nenhum POST Meta
- Source campaign: `120248940367540604` — `Elena Santana - ES - ESP - (pg_22091) - 4`

## 1. Campaign
```text
Campo UI/API                  | Valor source / decisão clone
------------------------------|-----------------------------------------------
Nome                          | Elena Santana - ES - ESP - (pg_22091) - 4
objective                     | OUTCOME_SALES
buying_type                   | AUCTION
bid_strategy                  | COST_CAP
daily_budget source           | 10000 cents = USD 100
daily_budget clone            | 2500 cents = USD 25 (regra Ares)
special_ad_categories         | FINANCIAL_PRODUCTS_SERVICES
special_ad_category_country   | ES
smart_promotion_type          | GUIDED_CREATION (source; candidato importante)
pacing_type                   | standard
start_time source             | 2026-06-19T00:04:00+0200
status clone                  | PAUSED
```

## 2. Adsets
```text
Adset ID            | Nome                  | Bid | Attr | DSA           | Regional
--------------------|-----------------------|-----|------|---------------|------------------------------
120248940367380604  | Conjunto 02 - VÍDEOS  | 200 | 7/1  | Openzed/Openzed | SPAIN_FINSERV,VOLUNTARY_VERIFICATION
120248940367340604  | Conjunto 01 - VÍDEOS  | 200 | 7/1  | Openzed/Openzed | SPAIN_FINSERV,VOLUNTARY_VERIFICATION
```

Campos comuns dos 2 adsets:
```text
Campo                         | Valor
------------------------------|-----------------------------------------------
optimization_goal             | OFFSITE_CONVERSIONS
optimization_sub_event        | NONE
billing_event                 | IMPRESSIONS
destination_type              | MESSENGER
promoted_object.pixel_id      | 629060785934493
promoted_object.event         | COMPLETE_REGISTRATION
promoted_object.page_id       | 990898360783030 (Elena Santana)
promoted_object.smart_pse     | false
targeting.geo                 | ES, home/recent
targeting.age                 | 18-65
targeting_automation          | advantage_audience=1
brand_safety                  | FACEBOOK_RELAXED, AN_RELAXED
is_dynamic_creative           | false
use_new_app_click             | false
```

## 3. UI screenshot → API mapping
```text
UI screenshot                  | API/source field provável
------------------------------|-----------------------------------------------
Dataset ES-CC-ES-01           | promoted_object.pixel_id=629060785934493
Complete registration          | custom_event_type=COMPLETE_REGISTRATION
Facebook Page Elena Santana    | promoted_object.page_id=990898360783030
Manual destination Messenger   | destination_type=MESSENGER
Performance goal conversions   | optimization_goal=OFFSITE_CONVERSIONS
Cost per result goal $2.00     | bid_amount=200 + campaign bid_strategy=COST_CAP
Attribution 7-day click/1-view | attribution_spec CLICK_THROUGH 7 + VIEW_THROUGH 1
Location Spain                 | targeting.geo_locations.countries=[ES]
Advantage+ audience            | targeting_automation.advantage_audience=1
Advertiser Openzed             | dsa_beneficiary=Openzed
Beneficiary/Payer Digital Trust| UI transparency label; API source GET retornou Openzed/Openzed
Placements automatic           | asset_customization_rules + placement optimization no creative
Excluded placements none       | sem exclusões manuais no GET; brand safety relaxed
```

## 4. Ads/Creatives source
```text
Ad ID              | Adset source        | Nome  | Creative ID        | Estrutura
-------------------|---------------------|-------|--------------------|-----------------------------
120248940367500604 | ver audit           | Ad    | ver audit          | asset_feed_spec com vídeos/labels
120248940367400604 | ver audit           | Ad    | ver audit          | asset_feed_spec com vídeos/labels
120248940367560604 | ver audit           | Ad    | ver audit          | asset_feed_spec com vídeos/labels
120248940367300604 | ver audit           | Ad    | ver audit          | asset_feed_spec com vídeos/labels
120248940367420604 | ver audit           | Ad    | ver audit          | asset_feed_spec com vídeos/labels
120248940367480604 | ver audit           | Ad    | ver audit          | asset_feed_spec com vídeos/labels
```

Campos críticos em creative/ad vistos na source:
```text
Campo                         | Valor/observação
------------------------------|-----------------------------------------------
asset_feed_spec.videos        | 2 vídeos por creative com adlabels
asset_customization_rules     | placement-specific assets; publisher_platforms fb/ig/an/messenger
call_to_action_types          | APPLY_NOW
title                         | TARJETA DE CRÉDITO DISPONIBLE ✅
description                   | ⭐️⭐️⭐️⭐️⭐️
link_url                      | https://fb.com/messenger_doc/
page_welcome_message          | contém template_id e is_user_editing=false na source
degrees_of_freedom            | standard_enhancements OPT_IN na source; campo perigoso em POST
tracking_specs/conversion_specs| existem no ad; candidatos para clone fiel se API aceitar
```

## 5. Diferenças permitidas no clone diagnóstico
```text
Campo          | Diferença permitida
---------------|-----------------------------------------------
name           | novo nome RPL/diagnóstico
budget         | USD 25, por regra Ares
status         | PAUSED, por segurança
start_time     | novo start D+1 01:00 Madrid, em UTC Z
ids            | novos campaign/adset/creative/ad IDs
```

## 6. Campos que NÃO podem ser simplificados no próximo teste
```text
Nível      | Campo
-----------|------------------------------------------------
Campaign   | COST_CAP, smart_promotion_type, pacing_type, categoria ES
Adset      | bid_amount=200, attribution 7/1, DSA, regional categories
Adset      | promoted_object completo, targeting completo, brand safety
Creative   | asset_feed_spec/asset_customization_rules ou reconstrução equivalente
Ad         | tracking_specs/conversion_specs se clone fiel exigir
```
