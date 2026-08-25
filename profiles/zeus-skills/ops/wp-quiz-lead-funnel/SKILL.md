---
name: wp-quiz-lead-funnel
description: "Use when building WordPress quiz lead funnels or direct one-question landing pages, including UTM-preserving article handoff."
version: 1.0.0
author: MGS Digital Corp / Zeus
license: Internal MGS
metadata:
  hermes:
    tags: [wordpress, quiz, lead-funnel, sms-funnel, redirect, utm, reports, cutover]
    related_skills: [wp-plugin-mass-operation]
---

# WordPress Quiz Lead Funnel

## Overview

Use this skill for MGS quiz funnels that run first-party inside WordPress instead of external builders such as Lovable/Supabase. The canonical lead-funnel pattern is a custom WordPress plugin that owns public quiz routes, lead capture, SMS Funnel delivery, UTM-preserving redirects, admin editing, duplication, reporting, and CSV export.

The first reference implementation is the BR/CAR quiz on `creditoparaveiculo.com`.

## Branch: direct landing without lead or SMS

When Rodolfo explicitly asks for only a landing-page source that operators can create and duplicate, do **not** import the lead-funnel architecture. Keep this branch as a separate lightweight plugin:

1. Admin owns only create, edit, activate/deactivate and duplicate of landing configuration; duplicate configuration only.
2. Public page owns visual model, copy, CTA labels and article destination.
3. Every incoming query parameter is preserved into the CTA URL; parameters already fixed on the destination win and appear once.
4. `utm_campaign` and `utm_adgroup` are defined when the Facebook direct-traffic campaign is created, not inside the plugin.
5. Do not add forms, lead storage, REST submit, SMS, phone/name fields, reports, CSV, campaign setup, Facebook events, pixels or data-layer events.
6. The destination article owns the Facebook event. The landing plugin only renders links and performs the parameter-preserving handoff.
7. If Rodolfo says the landing is standalone and tracking belongs only to the destination article, do not add `wp_head()`, `wp_body_open()` or `wp_footer()` merely to inherit global tracking.
8. Validate with a real browser click: LP HTTP 200, no horizontal overflow, zero forms/inputs, both CTA hrefs contain the exact incoming parameters once, navigation reaches the configured article with HTTP 200, and an unknown manager route returns a real 404.

## When to Use

Use when Rodolfo asks to:

- migrate a quiz/funnel from Lovable, Supabase, iframe, static folders, or another external app into WordPress;
- create, duplicate, edit, or cut over a quiz variant;
- configure SMS Funnel list URLs by gestor/UTM;
- debug leads not appearing in SMS Funnel;
- validate frontend form submit versus direct REST/API submit;
- improve quiz admin/report UI;
- export or import quiz leads/configs;
- preserve UTMs, `fbclid`, `gclid`, or campaign params through final redirect.

Do not use this for normal editorial WordPress posting, REC/P1 publication, or generic plugin updates that do not involve quiz lead funnels.

## Architecture Pattern

Preferred architecture:

1. Public quiz URL served by WordPress/plugin rewrite, not a physical static folder.
2. Frontend quiz submits lead to WordPress REST endpoint.
3. WordPress saves lead locally first.
4. WordPress forwards only required payload to SMS Funnel, normally `{ name, phone }`.
5. WordPress stores SMS Funnel status/response in the lead row.
6. Frontend redirects only after server returns `ok:true`.
7. Redirect preserves all query params: `utm_*`, `fbclid`, `gclid`, and custom params.
8. Admin dashboard provides edit, duplicate, reports, CSV export, filters, and pagination.

## Skill/Reference Organization

Do not create one skill per quiz variant. Variants such as G001/G002/G003 are runtime configuration, not procedural knowledge.

Recommended split:

- Skill: type of system — `wp-quiz-lead-funnel`.
- Reference: country/vertical/site — e.g. `references/br-car-creditoparaveiculo.md`.
- Reference: integration — e.g. `references/sms-funnel-routing.md`.
- Reference: balance monitoring and manual-recharge alerts — `references/sms-funnel-balance-monitor.md`.
- Template/checklist: repeatable execution — e.g. `templates/sms-funnel-test-matrix.md`.

## Operational Workflow

### 1. Preflight

- Confirm target domain, vertical, country, and official quiz URLs.
- Confirm all gestor codes and SMS Funnel list URLs.
- Confirm final redirect URL(s).
- Confirm whether historical leads should be imported into WP reporting.
- Validate admin access and WP-CLI/REST access before mutation.
- Back up plugin directory and database before deployment/import/UI changes.

### 2. Cutover

Cutover means the production URL stops using the old stack and starts using the WordPress plugin.

For quiz funnels, cutover is not complete until:

- public URLs return the plugin-rendered quiz;
- no public page HTML references old Lovable/Supabase/static app assets;
- physical static folders no longer shadow WordPress rewrites;
- lead submit saves in WP;
- SMS Funnel response is stored;
- redirect preserves UTMs;
- rollback path exists.

### 3. SMS Funnel Routing

- Prefer one explicit SMS Funnel URL per gestor.
- Use fallback URL only as a safety net when no gestor/UTM-specific URL matches.
- Keep fallback blank if every gestor has its own URL and blank fallback is intentional.
- Store status as `ok:G001`, `ok:G002`, `fail:500`, `error`, `skipped`, or `historical_import`.
- Never resend historical imports to SMS Funnel.
- Treat SMS Funnel as a downstream destination unless vendor docs prove otherwise. The `add-lead` style integration may create/trigger leads but not provide reliable delete/query/sync semantics.
- Do not assume SMS Funnel dashboard visibility is real-time. If WP records `ok:G00X` and the vendor response is success, distinguish API delivery success from dashboard indexing/filter/deduplication.

### 4. Tracking Boundaries: Quiz UTMs vs SMS UTMs

Keep the two attribution paths separate:

1. **Facebook → Quiz → REC:** the WordPress quiz must preserve all incoming query params from the quiz URL into the final REC redirect. This includes `utm_*`, `fbclid`, `gclid`, and custom params. This path measures the original paid click.
2. **SMS Funnel → shortened link → REC:** SMS Funnel automations may define their own fixed `Meu Link` and generate a short URL such as `gosite.cc/...`. Those links should use SMS-specific UTMs such as `utm_source=sms`; they do not need to preserve the original Facebook UTMs.

Operational rule: for normal quiz submit, send SMS Funnel only the fields required by that integration, usually `name` and `phone`. Do not add `customized_url` just to preserve Facebook UTMs when the SMS automation already owns its own link and tracking.

Verification pattern for UTM preservation:

- Fetch the public quiz URL with a synthetic query string such as `?utm_source=facebook&utm_medium=g001-s&utm_campaign=utm_check&fbclid=TEST&custom_x=abc`.
- Confirm production HTML loads the plugin asset, not Lovable/Supabase.
- Confirm the production JS reads `location.search`, includes `extra: all`, and redirects with `buildRedirect(base, all)` or equivalent.
- Simulate the final redirect URL and ensure every input param appears on the REC URL.

See also: `references/sms-funnel-automation-links.md`.

### 4.1 Static Chat Wrapper Contract

When migrating static chat/quiz pages that depend on a third-party ad wrapper, preserve the wrapper contract instead of productizing ad internals. Do not invent plugin fields for auctions, rewarded timeout, interstitial strategy, bids, or fallback behavior unless the wrapper owner explicitly requires them. The plugin/page should load `window.tags`, GPT, and the wrapper in the same effective order as the source HTML, then trigger only the same ad hooks at the same chat steps.

For Ciro/JBF-style chat pages, see `references/static-chat-wrapper-contract.md` before changing ad behavior. Treat wrapper logic as outside the plugin boundary; the plugin may route/render/generate the page, but the wrapper owns monetization behavior.

When investigating a suspicious wrapper suffix or source/country variant such as `_facebook_br.builder.js`, use the read-only diagnostic sequence in `references/static-chat-wrapper-diagnostics.md`: compare live HTML, request-context variations, CDN variant existence, and accessible plugin/theme/snippet code before concluding whether the variant is actively served.

### 5. Redirect Split

Business-facing UI should avoid raw JSON where possible.

Preferred UI:

- section title: `URLs de redirecionamento (split de tráfego)`;
- `+ Adicionar URL` button;
- each row has URL + numeric weight + remove action;
- one URL at `100` = 100%;
- two URLs at `50/50` = even split;
- preserve all incoming params automatically.

### 5. Lead Reports

Reports should be useful to operators, not just technical tables.

Minimum dashboard:

- total leads;
- unique phones;
- average/day;
- date range filters;
- when improving date-range UX, prefer one business-facing **Período** control backed by hidden canonical `from`/`to` inputs rather than two exposed native date inputs. Preserve the existing query contract and default dates. The picker should show two adjacent months on desktop and one month on mobile, support start/end range highlighting, month navigation, `Cancelar`/`Aplicar`, and shortcuts such as Hoje, Ontem, Últimos 7 dias, Últimos 30 dias, Este mês, Mês anterior, and Personalizado. Do not add unrelated comparison or maximum-range features merely because the visual reference contains them;
- validate a custom date picker at three levels before production: source markers/PHP lint, a locally rendered browser fixture with real click/readback checks for presets and custom ranges, and the authenticated WordPress report smoke after deployment. If the report smoke matches rendered input markup, update it when visible date fields become hidden canonical fields; otherwise a correct UI can be rejected by a stale assertion;
- gestor filter;
- parcela filter;
- search by name/phone/campaign;
- leads by day, default 5 days visible;
- per-page selector for more days;
- chart block pagination/filtering independent via AJAX when possible, so clicking chart controls does not reload the entire report page;
- table default 5 leads visible;
- table pagination independent via AJAX when possible, so table next/previous controls do not reload the report page;
- per-page selector for more leads;
- responsive report layout: cards must align in a coherent grid, use full available width, collapse cleanly below tablet widths, and avoid awkward empty gaps; explicitly override WordPress admin `.card { max-width: 520px; }` when using custom report cards;
- wide report tables with horizontal overflow when needed, never one-character vertical wrapping;
- CSV export respecting filters.

For Smart Bidding SMS revenue backfill/sync, dashboard metric semantics, BRL centavo storage, API boundary deduplication, and report-scope limits, load `references/smartbidding-sms-revenue-backfill.md`.

## Diagnostic Playbook: SMS Funnel Not Showing Leads

If Rodolfo says a lead is not appearing in SMS Funnel:

1. First distinguish test type:
   - Direct endpoint test only proves WP backend → SMS Funnel.
   - Browser/frontend test proves the actual user flow.
2. Run a real frontend submit through the public quiz page.
3. Query WP lead table for the exact test campaign/name/phone.
4. Check `sms_funnel_status` and stored response.
5. Verify response includes `success:true` and the expected `list_id`.
6. If WP shows `ok:G00X` and SMS response has correct `list_id`, likely issue is SMS Funnel dashboard delay/cache/indexing/filter/deduplication.
7. If WP shows `fail:*`, `error`, or no row, debug WordPress/backend/frontend accordingly.

## Validation Checklist

Before reporting success:

- [ ] PHP lint passes on all plugin PHP files.
- [ ] Plugin active version is correct.
- Public routes return 200.
- Public routes inherit normal WordPress global hooks unless Rodolfo explicitly requested an isolated/static page: WPCode/GTM/Yoast/pixels/head/footer changes should appear on quiz URLs like they do on posts/pages. See `wp-plugin-mass-operation/references/wp-custom-plugin-public-routes-global-hooks.md`.
- If the route is explicitly isolated/standalone, replace global hook capture with a strict plugin-owned allowlist: site-specific GTM container (head + noscript), Analytics through that container, GPT once, and the correct wrapper once. Validate an actual GA4 `page_view` request—not merely the presence of GTM markup—and confirm zero unrelated WordPress/theme assets. See `references/static-chat-wrapper-contract.md`.
- **Direct-landing exception:** when Rodolfo explicitly assigns Facebook events/tracking only to the destination article, the direct-landing branch above overrides that allowlist requirement. Validate zero plugin-owned tracking/events, zero forms/inputs, exact query passthrough and a real CTA click to the article; skip lead/SMS/report checks for this branch.
- Public HTML has no old external stack references.

- [ ] WP lead row created with expected slug/UTM/gestor.
- [ ] SMS status is stored and interpretable.
- [ ] Redirect URL preserves query params.
- [ ] Admin edit screen renders.
- [ ] Reports render with filters/pagination/export.
- [ ] Backup path is recorded.

## Common Pitfalls

1. **Only testing the backend endpoint.** This misses frontend JS, button, timestamp, mask, hidden fields, and browser redirect behavior. Always test at least one real browser submit; test all variants when SMS routing is under suspicion.

2. **Physical folders shadowing WordPress rewrites.** Old static folders such as `/quiz-car-parcelas-g003/index.html` can prevent plugin routes from loading. Rename/backup folders instead of deleting.

3. **Dashboard delay mistaken for backend failure.** SMS Funnel API may return `success:true` with the correct `list_id` while the dashboard still shows zero due to delay/cache/indexing/deduplication.

4. **Copying leads during duplication.** Duplicating a quiz must copy configuration only, never leads/history.

5. **SMS Funnel config must be single-choice per quiz.** Keep the operator UI simple: when creating/duplicating a quiz, the operator chooses the one SMS Funnel link that this quiz uses. That chosen link wins for every lead from that quiz, regardless of UTMs/campaign/adgroup or whether the visitor returns later with a clean URL. UI may show existing gestor/link rows for convenience, but the primary control must be a single radio/select labeled like `Link SMS desta quiz` / `Usar este link`; avoid routing conditions in the normal UI. Raw JSON may exist only behind a hidden/advanced “Ver JSON técnico” view, never as the primary editing surface.

6. **Historical imports sent to SMS Funnel.** Imports are for WP reporting only; mark rows as `historical_import` and do not POST to external vendors.

7. **Overengineering third-party ad wrappers.** If a static chat page loads a wrapper owned by another tech team, do not convert observed wrapper calls into admin settings. A loop in source HTML is not automatically a configurable `auctions` feature. Preserve the source contract and ask/verify before changing monetization semantics.

8. **Declaring ads working from load checks only.** Seeing `gpt.js`, the wrapper script, or `window.jbftag` only proves the stack loaded. Validate the same user path as the original HTML and compare the generated HTML/JS contract: `window.tags`, script order, ad insertion hooks, CTA rewarded call, and absence of unrelated WordPress/theme pollution when static parity is required.

9. **Quiz routes should not be isolated from the WordPress site by default.** MGS quiz URLs are part of the site. If Rodolfo adds or changes global head/footer/tracking/SEO behavior in WordPress, quiz public routes should inherit it like posts/pages. Audit for `wp_head()`, `wp_body_open()`, and `wp_footer()` when validating plugin renderers; only keep a fully isolated standalone output when explicitly requested or technically required.

10. **Dropping a previously requested follow-on phase.** When Rodolfo requests a multi-phase result (for example, historical backfill plus a daily sync) and later says “faz o 1”, treat that as sequencing the first phase—not as cancelling phase 2—unless he explicitly cancels it. Preserve the remaining phase as an open requirement, verify the original thread/session before claiming it was never requested, and close the task only after each requested phase is either implemented or explicitly deferred by Rodolfo. A compacted summary saying “sem cron” is secondary to the original actionable message.

11. **Reporting template scope as if it were per-quiz scope—or vice versa.** Separate every frontend change into: (a) template-level code/CSS, which affects all quizzes using that `layout_template`; and (b) runtime configuration such as `car_image_url`, which affects only the edited quiz unless configs are deliberately migrated in bulk. Before deployment, query how many active quizzes use the template. In the final report, state both scopes explicitly, including which other visual models were untouched. For transparent-image work, do not imply that adding one asset changes arbitrary configured images; validate the exact quiz config by readback.

12. **Misreading the SMS Funnel dashboard as the integration source of truth.** For a read-only vendor audit, reconcile four separate surfaces: dashboard credits/sends, list counts, selected automation settings, and the WordPress-side `ok:G00X`/`list_id` evidence. An empty SMS Funnel `Integrações` screen does not disprove direct `add-lead` ingestion. On each automation detail screen, read the selected list text, `Enviar apenas para novos leads` versus all leads, active/action toggles, delay, template, ActiveCampaign flag, and quiet-window flag; `innerText` alone is insufficient for selected form values. Timestamp capacity counters, take a second snapshot to detect live consumption, and distinguish confirmed dashboard state from architectural inference. For the secure browser procedure, use `local-browser-automation/references/credentialed-dashboard-readonly-audit.md`.

13. **Server-rendered anti-spam timestamp inside page cache.** If a public quiz embeds `ts` in PHP/HTML and the REST endpoint rejects values older than six hours, page cache can serve a timestamp that is already expired even to a new mobile visitor. Diagnose by extracting the hidden `ts` from the bare URL and comparing it with a cache-busted fetch; `cf-cache-status: DYNAMIC` does not rule out WordPress page cache such as WP Fastest Cache. The durable fix is to reset the hidden timestamp with `Date.now()` when the public JavaScript initializes and again on persisted `pageshow`, while preserving the backend minimum-fill and maximum-age checks. Bump the asset version, purge page cache, then validate every affected bare URL in a real mobile browser: HTTP/JS 200, expected asset version, fresh DOM timestamp, visible form, no horizontal overflow, and no error. A stale-timestamp POST and a fresh-but-invalid POST may verify the two backend branches without creating a lead; confirm the lead-row count is unchanged.
