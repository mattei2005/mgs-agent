# SMS Funnel Routing Reference

## Payload

Current MGS quiz funnels send only:

```json
{
  "name": "Lead Name",
  "phone": "11999999999"
}
```

Do not add UTMs or extra fields unless Rodolfo confirms SMS Funnel accepts them.

## Routing Source

Preferred resolution order:

1. Explicit `gestor_code` in request, if provided.
2. Parse gestor from `utm_medium`, e.g. `g003-s` → `G003`.
3. Parse gestor from quiz slug, e.g. `quiz-car-parcelas-g003` → `G003`.
4. If exactly one configured list exists, use it.
5. Fallback URL, only if configured.

## Status Semantics

- `ok:G003` — SMS Funnel accepted and the lead was routed as G003.
- `fail:500` / `fail:4xx` — HTTP failure from SMS Funnel.
- `error` — WordPress/network/WP_Error failure.
- `skipped` — no URL or sending intentionally skipped.
- `historical_import` — imported into WP reporting only; not sent to SMS Funnel.

## Require SMS Success

When enabled:

- WP still saves the lead first.
- The frontend only confirms/redirects if SMS Funnel returns success.
- If SMS Funnel fails, frontend shows an error and does not redirect.

This prevents false-positive conversions during cutover.

## Diagnostic Standard

Always test both layers when the symptom is “I filled the quiz but the lead didn’t arrive”:

1. Direct REST/backend test — proves WordPress → SMS Funnel.
2. Browser/frontend submit — proves actual user flow.
3. DB query — confirms stored `sms_funnel_status` and response.
4. Compare returned `list_id` to the expected list.

If both direct and browser tests return `success:true`, escalate suspicion to SMS Funnel dashboard delay/cache/indexing/filter/deduplication.
