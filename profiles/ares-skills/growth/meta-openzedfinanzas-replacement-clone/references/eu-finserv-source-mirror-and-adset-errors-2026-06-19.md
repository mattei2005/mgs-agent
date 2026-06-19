# EU financial-services Meta clone diagnostics — source mirror, DSA, regional categories, attribution, page permission (2026-06-19)

## Context

Account: `act_1356770869843984` / OpenzedFinanzas EU/Spain financial-services campaigns.

Rodolfo corrected the workflow: do not say fields are “not found” or keep testing minimal adset payloads. For EU/financial-services accounts, first mirror the source with explicit fields, classify fields, then write one object at a time.

## Source mirror script created

Canonical read-only diagnostic:

```bash
/root/mgs-agent/scripts/ares-meta-source-mirror.py \
  --source-campaign-id <campaign_id> \
  --source-adset-id <adset_1> \
  --source-adset-id <adset_2> \
  --source-ad-id <winner_1> \
  --source-ad-id <winner_2> \
  --source-ad-id <winner_3> \
  --ads-count 3 \
  --daily-budget-usd 25
```

What it does:
- GET-only; no Meta POST/DELETE/PATCH.
- Probes campaign/adset/ad fields explicitly and field-by-field so one unsupported field does not hide the rest.
- Dumps unsupported fields and raw source by level.
- Builds a `PAUSED` clone-source payload candidate in memory.
- Diffs `source vs payload` as `IGUAL`, `SÓ NA SOURCE`, `SÓ NO PAYLOAD`, `VALOR DIFERENTE`.
- Classifies fields as likely writable, compliance, read-only/derived, or legacy/obsolete.
- Converts start time using real `Europe/Madrid` zoneinfo to UTC `Z`, not fixed offset.

## Durable EU/financial-services lesson

For Spain/EU financial-services campaigns, adset compliance fields are not optional and are not reliably visible via default GET.

Always GET explicitly:

```text
dsa_beneficiary
dsa_payor
regional_regulated_categories
special_ad_categories
special_ad_category_country
```

Observed source values for both Patricia and Elena adsets:

```text
Field                           | Value
--------------------------------|---------------------------------------------
dsa_beneficiary                  | Openzed
dsa_payor                        | Openzed
regional_regulated_categories    | SPAIN_FINSERV, VOLUNTARY_VERIFICATION
special_ad_categories            | FINANCIAL_PRODUCTS_SERVICES
special_ad_category_country      | ES
```

Do not rely only on Ads Manager UI labels. UI may display advertiser/beneficiary/payer differently than Graph API field names/values. Copy the exact string returned by API when creating adsets.

## Patricia result — page permission blocker

Source: `Patricia Flores - US - ESP - (pg_22069) - 1`, campaign `120248290297180604`, page `1063171606876651`.

After aligning adset fields, DSA, and regional compliance package, first adset creation still failed:

```text
code: 100
subcode: 1487202
error_user_title: El permiso de la página es insuficiente para publicar anuncios
error_user_msg: Necesitas acceso para crear anuncios para esta Página...
```

Meaning: for Patricia page, token/user lacks permission to create ads for the Page. This is not solved by more adset field tweaking. Need Page access for the token/user or use a different page/campaign where the token can create ads.

When `error_user_msg` appears null in sanitized error, capture raw HTTP response including body and headers; the full Graph error body may contain `error_user_title`/`error_user_msg`.

## Elena result — page permission passed; attribution blocker

Source: `Elena Santana - US - ESP - (pg_22091) - 4`, campaign `120248940367540604`, page `990898360783030`.

Campaign creation `PAUSED` succeeded. First adset with source 7-day click + 1-day view attribution failed:

```text
code: 100
subcode: 1885501
error_user_title: El intervalo de atribución de visualización no es válido
error_user_msg: En función de los objetivos y la optimización que has seleccionado, la combinación admitida para los valores del intervalo de atribución de visualización y de clic es: (1, 0)
```

Meaning: for this create flow, Meta requires attribution `(1,0)`: 1-day click and no view-through window, even if the source GET reports 7d click + 1d view.

Next controlled Elena adset test should use:

```json
"attribution_spec": [
  {"event_type": "CLICK_THROUGH", "window_days": 1}
]
```

Keep DSA and regional compliance package:

```json
"dsa_beneficiary": "Openzed",
"dsa_payor": "Openzed",
"regional_regulated_categories": ["SPAIN_FINSERV", "VOLUNTARY_VERIFICATION"]
```

## Workflow rule added

For EU/financial-services Meta clone/replacement:
1. Source mirror first; no minimal payload guessing.
2. Use explicit GET fields; default Graph GET hides compliance fields.
3. Diff source vs payload before each POST.
4. Create one object at a time, all `PAUSED`.
5. If a write fails, capture raw HTTP response body and headers, not only sanitized safe error.
6. Distinguish blockers:
   - `1487202` + page permission title => Page access issue.
   - `1885501` + attribution title => adjust attribution to `(1,0)` for this create flow.
7. Delete/verify partial campaign if adset creation fails and the partial campaign is not needed for the next checkpoint.
