# Custom WordPress plugin cutover — lead/quiz apps

Use for migrations where an external/static app (Lovable/Supabase, static folders, iframe-like pages) is replaced by a first-party WordPress plugin that owns public routes, lead capture, redirects, and reporting.

## Durable workflow

1. **Validate access separately**
   - Validate WP REST/Application Password with `GET /wp-json/wp/v2/users/me?context=edit` before relying on wp-admin browser login.
   - Browser/cookie login can fail because of custom login paths or cookies while REST admin still works.

2. **Patch locally, lint remotely, then install**
   - Build the plugin package locally.
   - Copy to the RunCloud server and run `php -l` on every PHP file before activation.
   - For RunCloud sites under `/home/runcloud2`, run WP-CLI as `runcloud2`, not `runcloud`.

3. **Back up before each production mutation**
   - DB export before plugin install/update or bulk data import.
   - Backup existing plugin directory before overwriting.
   - Backup/rename static folders instead of deleting them.

4. **Watch for static folders shadowing WordPress rewrites**
   - Physical folders like `/quiz-car-parcelas-g003/index.html` beat WordPress rewrite rules.
   - If plugin routes are not appearing, inspect the webroot for matching physical directories.
   - Disable by renaming, e.g. `quiz-car-parcelas-g003.lovable-disabled-YYYYMMDD`, and keep a tar backup.

5. **Lead capture cutover pattern**
   - Public REST `/lead` should save lead in WP first, then forward server-side to the vendor (SMS Funnel, etc.).
   - Store vendor response/status in the lead table for audit (`ok:G003`, `fail:500`, `historical_import`).
   - Add `require_sms_success` behavior: when true, block success/redirect unless vendor returns success; when false, allow WP-saved lead to redirect despite vendor failure.
   - Fire Meta/GTM Lead only after server returns `ok:true`, not before submit completion.
   - Preserve all query params (`utm_*`, `fbclid`, `gclid`, custom) through the final redirect.

6. **Historical import pattern**
   - Do not resend historical leads to external vendors during import.
   - Mark imported rows with status like `historical_import` and response text explaining source.
   - Map old config IDs to current slugs; if legacy rows have missing config IDs, use an explicit fallback and report the count.
   - Make import scripts idempotent enough to avoid duplicate rows when rerun (match created_at + phone + name + quiz_slug).

7. **Operational validation**
   - Test each public route with cache-busting headers and browser automation.
   - Verify page HTML no longer references the external stack (e.g. no Supabase/Lovable URLs).
   - Submit test leads for every route/list and verify DB `sms_funnel_status` plus stored vendor `list_id`.
   - Validate dashboard/report render via WP-CLI `eval` before telling Rodolfo it is ready.

## UI/reporting lessons

- A functional WP admin table is not enough for business-facing quiz operations. Prefer human-readable cards and grouped sections:
  - Identificação
  - Textos da página
  - Formulário
  - SMS Funnel
  - Mensagem de sucesso & redirecionamento
  - Imagens/SEO
  - Tracking
- For reporting dashboards, include lead counts, unique phones, average per day, date/gestor/parcela/search filters, CSV export, and per-quiz drill-down.
- Order quiz cards alphabetically by internal name when users manage multiple variants (G001–G006).
- Make WP admin forms visibly business-friendly, not default-WP tiny: increase max content width, input font size, min-height, padding, textarea height, and focus states. Include bare `input:not([type])` in CSS because PHP templates often render `<input name="...">` without a type, and those otherwise keep the cramped WordPress default styling.
- For cloned campaign variants, implement a first-class **Duplicar** operation instead of telling the operator to import/export CSV. Duplication should open a modal asking for the new internal name and slug/path, copy quiz configuration only, reset/clear integration endpoints that must be unique (e.g. SMS Funnel list URL), and never copy leads/history.
- Treat CSV import/export as a technical migration/backup feature. Hide it behind a details/advanced block or label it clearly; the normal operator path for a new quiz variant is Duplicate → rename → set slug → paste new SMS Funnel URL.
- Rename technical fields into business-readable labels while preserving storage schema. Example: `sms_funnel_url` should render as “URL SMS Funnel padrão (fallback opcional)” with helper text explaining it is only used if no gestor/UTM-specific URL matches; `redirect_variants` should render as “URLs extras de redirecionamento (JSON técnico)” with helper text explaining it is optional split-test routing and `[]` means use only the main redirect URL.

## Pitfalls

- A vendor API returning `success:true` can still take time to show in its dashboard. Trust the server response and stored `list_id` first, then note possible vendor dashboard delay/cache/deduplication.
- Physical static folders from the old stack are the most common reason a newly installed plugin route appears not to work.
- Do not import historical leads into SMS Funnel again; import them only into WordPress for reporting.
