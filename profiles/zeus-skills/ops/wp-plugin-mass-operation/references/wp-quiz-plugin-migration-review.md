# WordPress Quiz Plugin Migration Review — Lovable/Supabase → WP

Use this reference when reviewing or preparing a WordPress plugin that replaces an external quiz/lead-capture stack such as Lovable/Supabase.

## Context pattern

External stack often contains:
- public quiz pages/routes
- admin UI for editable quiz config
- DB tables/collections for `quiz_config` and `quiz_leads`
- backend/edge function forwarding leads to SMS Funnel or another CRM
- static HTML generated into WordPress that still calls the external backend

Goal for MGS production: WordPress-owned plugin with no dependency on Lovable/Supabase for public quiz, config, lead storage, or lead forwarding.

## Minimum plugin architecture

Prefer a dedicated plugin over Gutenberg/Elementor snippets or iframe.

Required components:
- activation creates custom tables, e.g. `{prefix}_mgs_quiz_config` and `{prefix}_mgs_quiz_leads`
- rewrite routes for public URLs, e.g. `/quiz-car-parcelas-g001/`
- shortcode fallback, e.g. `[mgs_quiz slug="..."]`
- public REST config endpoint that does **not** expose SMS Funnel URLs/secrets
- public REST lead endpoint that validates, stores lead, forwards server-side, and records delivery status
- WP admin screen to edit quiz config and export leads CSV
- import only configs when the business wants to start leads clean; do not import legacy leads unless explicitly requested

## Review checklist before installing on production WP

1. Package shape
   - ZIP root must contain the plugin folder (`mgs-quiz-carro/`), not loose files.
   - Main plugin file has stable version and PHP/WordPress compatibility metadata.

2. PHP/runtime safety
   - Run `php -l` on all PHP files on an environment with PHP available.
   - Verify activation creates tables and flushes rewrite rules.
   - Verify no fatal path if shortcode slug is missing/not found.

3. Public config secrecy
   - Public config endpoint and localized JS config must remove internal SMS Funnel URLs and any sensitive backend fields.

4. Shortcode completeness
   - Shortcode must enqueue/register CSS and JS.
   - Shortcode must inject REST base and per-quiz config (`MGS_QUIZ_REST`, `MGS_QUIZ_CFG` or equivalent).
   - Shortcode must work inside normal WP pages/posts, not only full-page rewrite templates.

5. Lead success semantics
   - Frontend must not redirect unless `/lead` returns `ok:true`.
   - Meta Pixel/GTM `Lead` event should fire only after confirmed server success, not before fetch completes.
   - If SMS Funnel delivery is operationally required, plugin should support `require_sms_success=true` so delivery failure returns `ok:false` while still logging the lead in WP.

6. SMS Funnel forwarding
   - MGS SMS Funnel add-lead endpoint for this quiz accepts only `{name, phone}`.
   - Send server-side; do not expose list URLs publicly.
   - Store `sms_funnel_status` and a short response body for debugging.
   - Confirm routing precedence: explicit gestor, `utm_medium` (`g002-s` → `G002`), slug, single configured URL, fallback URL.

7. Anti-spam
   - Honeypot must reject if filled.
   - Timestamp should be mandatory; reject absent/invalid, too fast (<3s), and optionally too old (>6h).
   - Avoid heavy CAPTCHA unless spam volume requires it.

8. UTM/redirect preservation
   - Capture all query params into `extra_params`.
   - Preserve `utm_*`, `fbclid`, `gclid`, and unknown params on final redirect.
   - Do not overwrite params already present in redirect URL unless explicitly intended.

9. Imports and lead history
   - If starting clean, remove legacy `quiz_leads.csv` and docs about lead import.
   - For config CSV import, upsert by `slug` and validate JSON fields (`options`, `redirect_variants`, `sms_funnel_urls`).

10. Canary cutover
   - Backup WP DB/files first.
   - Install plugin but do not send full traffic immediately.
   - Import configs.
   - Save permalinks/flush rewrites.
   - Test one quiz URL with UTMs.
   - Submit one lead per gestor/list.
   - Validate WP lead row, SMS Funnel dashboard, `sms_funnel_status`, redirect URL params, and Pixel/GTM events.

## Pitfalls observed

- Generated packages may claim “complete” while shortcode lacks assets/localized config.
- Lead endpoint may save WP lead and return `ok:true` even when SMS Funnel fails; this hides cutover failures.
- Pixel Lead firing before REST success inflates Meta conversions.
- Anti-spam timestamp checks that allow missing `ts` are easy for bots to bypass.
- Documentation may drift on URL naming (`g001` vs default `/quiz-car-parcelas/` as g002). Validate CSV slugs, not prose.
