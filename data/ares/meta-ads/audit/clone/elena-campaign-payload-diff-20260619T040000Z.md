# Elena — campaign payload diff antes de POST

- Audit JSON: `/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-campaign-payload-diff-20260619T040000Z.json`
- Modo: dry-run, sem POST Meta
- Próximo endpoint se autorizado: `POST /act_1356770869843984/campaigns`

## Payload candidato sem token

```json
{
  "name": "Elena Santana - ES - ESP - (pg_22091) - RPL - 20260620 - DIAG01",
  "objective": "OUTCOME_SALES",
  "buying_type": "AUCTION",
  "status": "PAUSED",
  "daily_budget": "2500",
  "bid_strategy": "COST_CAP",
  "special_ad_categories": [
    "FINANCIAL_PRODUCTS_SERVICES"
  ],
  "special_ad_category_country": [
    "ES"
  ],
  "start_time": "2026-06-19T23:00:00Z",
  "pacing_type": [
    "standard"
  ],
  "smart_promotion_type": "GUIDED_CREATION"
}
```

## Diff source → payload

```text
Campo                         | Status             | Decisão
------------------------------|--------------------|-------------------------
bid_strategy                  | IGUAL              | ENVIAR
budget_remaining              | READ-ONLY/derivado | NÃO ENVIAR
buying_type                   | IGUAL              | ENVIAR
created_time                  | READ-ONLY/derivado | NÃO ENVIAR
daily_budget                  | VALOR DIFERENTE    | PERMITIDO
effective_status              | READ-ONLY/derivado | NÃO ENVIAR
id                            | READ-ONLY/derivado | NÃO ENVIAR
name                          | VALOR DIFERENTE    | PERMITIDO
objective                     | IGUAL              | ENVIAR
pacing_type                   | IGUAL              | ENVIAR
smart_promotion_type          | IGUAL              | ENVIAR
special_ad_categories         | IGUAL              | ENVIAR
special_ad_category_country   | IGUAL              | ENVIAR
start_time                    | VALOR DIFERENTE    | PERMITIDO
status                        | VALOR DIFERENTE    | PERMITIDO
updated_time                  | READ-ONLY/derivado | NÃO ENVIAR
```
