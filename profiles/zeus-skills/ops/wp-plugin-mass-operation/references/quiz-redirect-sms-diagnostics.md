# Quiz redirect UI + SMS Funnel diagnostics

Use when maintaining custom WordPress quiz/lead-capture plugins that replaced Lovable/Supabase/static apps.

## Redirect split UI pattern

Do not expose `redirect_variants` as raw JSON to operators. Render redirect split routing as a business UI:

- section title: `URLs de redirecionamento (split de tráfego)`
- button: `+ Adicionar URL`
- each row: URL input + numeric weight input + `Remover`
- first row maps to canonical DB fields `redirect_url` + `redirect_url_weight`
- additional rows serialize into `redirect_variants` as `[{"url":"...","weight":50}]`
- helper text should summarize distribution: `Padrão 50% · URL 2 50%`
- preserve `utm_*`, `fbclid`, `gclid`, and other query params on final redirect

Why: users think in URLs and percentages/weights, not JSON. Raw JSON is acceptable for migration/debug only, not normal operation.

## SMS Funnel routing diagnostics

For every quiz variant/gestor, validate the whole path:

1. Ensure each quiz has a gestor-specific SMS Funnel URL; leave fallback blank when all gestores are configured.
2. Submit a unique test lead through the real public WP REST endpoint, not just by inspecting config.
3. Include explicit `gestor_code` and matching `utm_medium` such as `g003-s`.
4. Query the WP lead table for the created rows.
5. Confirm:
   - `sms_funnel_status` starts with `ok:G00X`
   - stored `sms_funnel_response` contains `success:true`
   - returned `list_id` matches the expected SMS Funnel list for that gestor
6. If WP stores `success:true` + correct `list_id` but the SMS Funnel dashboard still shows zero, report likely vendor dashboard delay/cache/indexing/deduplication rather than a WP backend failure.

Do not resend historical imports to SMS Funnel; only submit fresh synthetic diagnostic leads.

## Operator-facing explanations

- `SMS Funnel fallback`: reserve URL only used if no gestor/UTM-specific URL matches. If every gestor has a URL, keep fallback blank.
- `Redirect split`: one URL with weight 100 means 100% to that URL; two URLs with 50/50 means even split; all tracking params must be passed through automatically.
