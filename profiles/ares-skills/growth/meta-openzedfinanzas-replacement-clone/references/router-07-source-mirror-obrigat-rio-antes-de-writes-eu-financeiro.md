## Source mirror obrigatório antes de writes EU/financeiro

Antes de qualquer `POST /campaigns`, `/adsets`, `/adcreatives` ou `/ads` em campanhas EU/financeiro, rodar o mirror read-only:

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

Regra aprendida com correção do Rodolfo: não testar payload mínimo nem reportar “não achei” campos sem antes fazer GET explícito e diff source-vs-payload. Default GET da Meta esconde campos de compliance.

Campos de compliance que devem ser confirmados por API e copiados exatamente no adset quando existirem:

```text
dsa_beneficiary
dsa_payor
regional_regulated_categories
special_ad_categories / special_ad_category_country
```

Para OpenzedFinanzas EU/Spain, valores observados nos adsets Patricia/Elena:

```json
{
  "dsa_beneficiary": "Openzed",
  "dsa_payor": "Openzed",
  "regional_regulated_categories": ["SPAIN_FINSERV", "VOLUNTARY_VERIFICATION"]
}
```

Pitfalls validados:
- `code=100/subcode=1487202` pode esconder erro de permissão de Página. Capturar raw HTTP body/headers; o corpo completo pode conter `error_user_title: El permiso de la página es insuficiente...`. Nesse caso, parar: precisa acesso de criação de anúncios na Página, não mais tentativa de campo.
- `code=100/subcode=1885501` em Elena indicou janela de atribuição inválida **no contexto novo incompleto**. Não trocar automaticamente para `(1,0)` quando a source UI/API mostra `7-day click + 1-day view`; isso é sinal de que a campanha/adset novo ainda não espelha o contexto da source. Primeiro corrigir paridade de campaign/adset (COST_CAP, bid_amount, `smart_promotion_type`, pacing, DSA/regional, promoted_object, targeting) e só mudar attribution se Rodolfo aprovar conscientemente um replacement não-fiel.
- Sempre deletar/verificar campaign parcial quando o adset falha e a campaign não será reutilizada no próximo checkpoint.
