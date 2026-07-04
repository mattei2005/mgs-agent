# WordPress quiz/plugin migration pattern — Lovable/Supabase → WP

Use when Rodolfo wants to remove a Lovable/Supabase dependency and run a quiz/funnel fully inside a WordPress site.

## Durable pattern

1. Treat this as a **plugin/product migration**, not a static page copy.
2. Build/own a WP plugin with:
   - custom tables for quiz config and leads;
   - public rewrite routes for the existing quiz URLs;
   - public REST endpoint for lead submission;
   - admin UI to edit quiz config;
   - lead export CSV;
   - optional report/dashboard UI inside WP admin.
3. Start with clean leads if Rodolfo says not to import historical Lovable/Supabase leads. Keep old exports only as archive.
4. Preserve UTM/fbclid/gclid end-to-end:
   - read from the quiz URL;
   - store in the WP lead row;
   - append to final redirect URL without overwriting existing params.
5. SMS Funnel integration should be **server-side** from WP, not hardcoded public-only front-end logic. For SMS Funnel add-lead endpoints used here, payload is only:
   - `name`
   - `phone`
6. Add lead-delivery guardrails:
   - save lead locally first;
   - store `sms_funnel_status` + truncated response;
   - expose `require_sms_success` admin/config flag, default true for cutover;
   - if SMS fails and `require_sms_success=true`, return `ok:false` and do not redirect.
7. Fire Meta/GTM Lead events only after server confirms `ok:true`; never before the REST call succeeds.
8. Add basic anti-spam before production traffic:
   - hidden honeypot field;
   - required timestamp;
   - reject submissions under ~3 seconds;
   - reject very stale forms, e.g. >6h.
9. Disable old static folders that shadow WP rewrites only after backing them up. Rename, do not delete, e.g. `quiz-car-parcelas-g003.lovable-disabled-YYYYMMDD`.
10. Validate with both direct REST posts and a browser flow. Check the WP DB row, SMS status, and final redirect URL with UTMs.

## Cutover checklist

- Backup DB and existing plugin/static folders.
- PHP lint all plugin PHP files on the target server before activation.
- Install/activate plugin via WP-CLI or admin.
- Import only configs unless lead import is explicitly required.
- Flush rewrites.
- Confirm public config endpoint does not expose SMS Funnel URLs.
- Confirm all public quiz URLs render from plugin, not Lovable/Supabase/static HTML.
- Send one test lead per route/list and verify `sms_funnel_status=ok:Gxxx` with the expected list ID in the stored response.
- Test browser submit + redirect preserving `utm_*`, `fbclid`, `gclid`.
- Implement/verify admin report after core lead flow works, not before.

## Report/dashboard feature shape

A useful first WP admin report does not need pixel-perfect Lovable parity. Include:

- report button per quiz in the quiz list;
- filters: date range, `utm_medium`, parcela, free search by name/phone/campaign;
- cards: total leads, unique phones, average/day, period length;
- breakdowns by day, gestor, parcela;
- recent/table view of leads;
- CSV export respecting slug/date filters.

## Pitfalls observed

- Static folders at the webroot will beat WP rewrite rules. If `https://site/quiz-car-parcelas-g003/` still returns old HTML with Supabase URLs, check physical directories before debugging the plugin.
- A successful HTTP response from SMS Funnel may not appear immediately in their dashboard. Trust the stored response only for delivery acceptance; dashboard visibility may lag/cache/dedupe.
- Repeated test numbers can confuse dashboard checks; use distinctive names/campaigns for each test so the user can search them.
- `wp option get mgs_quiz_db_version` can remain stale if the activation hook does not rerun on update; plugin header/status is the source for active plugin version unless DB migrations depend on the option.
