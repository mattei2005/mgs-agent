# Meta Ads EU/Finserv — ad-level token scopes and clone diagnostic

Use when Meta campaign/adset creation works but ad creation fails, especially on EU/financial products + Messenger/page identity campaigns.

## Session learning

In OpenzedFinanzas-ES-CC-ES-03 / Elena Santana, the API could create:

- campaign (`OUTCOME_SALES`, `COST_CAP`, `FINANCIAL_PRODUCTS_SERVICES`, country `ES`)
- adset (`OFFSITE_CONVERSIONS`, `MESSENGER`, DSA, regional categories)

…but `POST /act_<id>/ads` failed with:

```text
code=31
error_subcode=3858385
error_user_title=Autentica tu cuenta
message=This request requires the user to take a pending action
```

The BM UI looked normal: ad account assignment had Manage campaigns; Page Elena had full control/access visible. The real blocker was token scope coverage for Page/Messenger/ad identity, not BM assignment.

Adding these scopes to the user token resolved ad creation:

```text
pages_manage_ads
pages_messaging
pages_manage_metadata
pages_manage_posts
```

Keep the normal ads/business scopes too:

```text
ads_management
ads_read
business_management
pages_show_list
pages_read_engagement
read_insights
instagram_basic
pages_read_user_content
pages_manage_engagement
```

Validate before retrying writes:

```text
GET /me/permissions
```

Do not rely only on Ads Manager UI. Campaign/adset may succeed with insufficient Page/Messenger scopes; the failure can appear only at ad creation because the ad binds page identity, Messenger template/conversation, creative/page post and tracking.

## Diagnostic sequence

1. Confirm token identity with `/me` and scopes with `/me/permissions`; never expose token.
2. Check ad account assigned users/tasks if BM permissions are questioned.
3. Check the Page with user token and page token. A suspicious pattern is `can_post=false` with user token but page token exists.
4. If campaign/adset POST succeeds but ad POST fails with `31/3858385`, regenerate token with the Page/Messenger scopes above.
5. Retry only one ad PAUSED first, then validate GET.

## EU finserv fields to preserve

For Openzed/Spain financial campaigns, keep campaign/adset compliance fields explicit:

```text
special_ad_categories=FINANCIAL_PRODUCTS_SERVICES
special_ad_category_country=ES
dsa_beneficiary
dsa_payor
regional_regulated_categories, e.g. SPAIN_FINSERV + VOLUNTARY_VERIFICATION
```

## Operational pitfall from the session

Do not call this a production standard change until Rodolfo approves. This clone was a diagnostic bridge to prove API creation. The official Ares replacement pattern remains separate from source-mirror diagnostics.
