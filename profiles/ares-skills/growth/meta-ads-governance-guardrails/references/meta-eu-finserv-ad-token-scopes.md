# Meta EU financial-services: compliance and token scope

Use when campaign/adset creation succeeds but ad creation fails on EU financial-products campaigns using Messenger/page identity.

## Diagnostic order

1. Validate token identity and app with read-only `/me` and account GET.
2. Read source campaign, adset and ad fields before building a payload.
3. Confirm page access and the exact app-scoped page ID relationship.
4. Preserve compliance fields returned by the source instead of inventing values.
5. Create or copy only PAUSED objects during diagnosis.
6. Retry only one PAUSED ad after fixing the proven missing layer, then validate by GET.

## Compliance fields

The operation contract must explicitly define and source-validate:

```text
special_ad_categories
special_ad_category_country
dsa_beneficiary
dsa_payor
regional_regulated_categories
optimization_goal
destination_type
promoted_object
attribution_spec
```

Values vary by country, advertiser and source campaign. A historical EU payload is not a template for another account.

## Token/page scopes

Validate the minimum permissions actually needed for the requested action. Do not treat readable account insights as proof that the token can create an ad with a page identity. Keep token values secret; audits record only item, field, length and API status.

## Failure handling

- Parameter/compliance errors do not receive blind retries.
- Preserve Meta `error_user_title`, `error_user_msg`, `error_data` and `blame_field_specs` in sanitized audit.
- Reconcile partial campaign/adset/ad objects before retry.
- Never broaden permissions, swap advertiser identity or use another credential without explicit authorization.
