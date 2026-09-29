# Complete WordPress Site Re-audit

## Purpose

Use this branch when the request is broader than one plugin or defect. It produces one coverage ledger across public behavior, SEO/content, accessibility, performance, tracking, edge/origin, WordPress internals, host state, and recovery evidence without treating a green script exit or HTTP `200` as a clean site.

## Phase 1 — Freeze scope and prior baseline

1. Create a new workspace/checkpoint so the re-audit cannot overwrite prior evidence.
2. Read the previous report only to define regressions and known exceptions; collect every current number again.
3. Separate the ledger into: public surface, rendered behavior, control plane, authenticated WordPress/filesystem/database, host, backups, and closure governance.
4. Keep production read-only. A request to audit does not authorize discovered remediation.

## Phase 2 — Public breadth before browser depth

Run the broad crawl first:

1. Discover all sitemap indexes and child sitemaps. Parse only direct `<sitemap><loc>` and `<url><loc>` children for navigation; never collect every namespaced `<loc>` descendant, because image/video sitemap entries will be miscounted as crawlable HTML pages.
2. Crawl every unique sitemap URL plus explicit special routes, aliases, verification paths, REST endpoints, feeds, and security probes.
3. Keep HTML documents and assets as separate populations. Record requested URL, final URL, status, content type, canonical, title, meta description, H1, robots, links, images, ALT, structured-data parse status, and complete-body markers.
4. Build destination → unique referrer maps for every non-2xx destination.
5. Preserve raw counts, then publish an actionable classification. Bare oEmbed without arguments (`400`), deliberately hidden REST users (`404`), and blocked XML-RPC (`403`) are expected controls when their behavior matches the configured policy.

Never print every asset merely because the row lacks an `ok` field. Define failure from the actual status/error predicate first; schema assumptions can turn an entire successful crawl into false failures.

## Phase 3 — SEO, content, template, and legal residue

Aggregate by route class, not only site-wide totals:

- missing/duplicate titles, descriptions, H1, canonicals, and indexability;
- archive, author, tag, category, custom-post-type, layout/template, and pagination routes;
- demo markers such as lorem ipsum, vendor support text, placeholder years, template-company names, and obsolete external policies;
- visible verification text versus the independently working verification method;
- raw shortcodes, legacy hosts, old paths, mixed content, and broken internal aliases;
- privacy/terms/contact pages and whether their text actually describes the live company, processors, hosting, and jurisdiction.

For custom-taxonomy SEO, noindex, or sitemap controls, resolve the **runtime taxonomy identifier** before freezing the filter. Public rewrite bases, body URLs, and Yoast sitemap filenames can omit prefixes that remain present in WordPress internals. Read representative public body classes or the registered/query taxonomy, preserve a route → runtime-taxonomy map, and test the filter against those exact identifiers—for example, a public `team_group` route may actually require `cpt_team_group`. A mock using the friendly rewrite label is not a sufficient canary.

When a theme-generated Open Graph description remains stale and the SEO plugin's protected meta is ignored by REST, test one reversible `excerpt` canary before introducing a file-level override: save the complete `context=edit` object, update only the excerpt, GET the raw excerpt byte-for-byte, and compare canonical plus cache-busted public meta. Keep the write only when the intended OG output changes and no legacy vendor marker remains; otherwise restore the exact prior excerpt and stop that path.

Do not call `/layouts/` or another template namespace a leak from existence alone. Require content, indexability, sitemap inclusion, internal links, canonical behavior, and search visibility. Conversely, a valid canonical does not cure an unnecessary indexable `200` template surface.

## Phase 4 — Representative rendered-browser matrix

Select one route from every materially different class, then run desktop and mobile:

- home and primary commercial pages;
- contact/form route;
- privacy/legal route;
- article/archive route;
- custom-post-type or service route;
- layout/template route when present.

For each run, scroll the full page and record document status, final URL, page errors, console errors, failed requests, response statuses `>=400`, broken images, overflow, form labels, CAPTCHA frames, menus, DOM size, resources, transfer bytes, TTFB, DCL, and load time.

Classify browser network evidence by `(host, path, failure/status)` and first-party versus third-party. Analytics collection aborts are not broken first-party assets. A third-party service-worker `404`, CORS failure, or collector failure is still a tracking-reliability finding when it repeats across route classes; report it separately from rendering health.

Probe response events as well as `requestfailed`: HTTP `404` produces a response but may never appear in the failed-request event.

## Phase 5 — Accessibility and performance

1. Inject a pinned local `axe-core` build after load and full-page scroll.
2. Report rule frequency, impact, affected route classes, and unique violating-node count. Do not present repeated desktop/mobile instances as independent defects.
3. Preserve representative selectors and snippets for remediation, especially unnamed links, color contrast, positive `tabindex`, heading order, missing/duplicate landmarks, iframe titles, invalid ARIA, and keyboard-inaccessible scroll regions.
4. Treat automation as coverage, not WCAG certification; keyboard flow, focus visibility, screen-reader semantics, and form error behavior still need manual confirmation when they matter.
5. Run Lighthouse on a representative page in mobile and desktop profiles. Label the result as a laboratory sample, record FCP/LCP/TBT/CLS and transfer/unused CSS/JS evidence, and keep it separate from availability and real-user Core Web Vitals. If Lighthouse cannot discover a system browser but Playwright is installed, resolve the newest compatible cached executable first and export its exact path as `CHROME_PATH`; do not install or guess a second browser when the validated Playwright Chromium already satisfies the version requirement.

### Preproduction canary for HTML-output transforms

For an MU plugin, output-buffer filter, or hook that rewrites rendered HTML, exercise the candidate against the live frontend runtime before requesting a production cutover:

1. Fetch the complete cache-busted live document and save it as the input fixture.
2. Render that fixture through the exact candidate PHP transform in an isolated harness. First remove only the prior transform's owned style/script/banner/footer-control nodes so the candidate is tested once rather than layered over itself. Include the candidate's `wp_head` output in native hook order near the opening `<head>`; appending head callbacks after the downloaded head can manufacture early JavaScript errors that production will not have. If the live frontend dynamically rewrites owned markup, preserve enough real runtime JavaScript for the canary to reproduce that mutation instead of freezing only the server HTML.
3. In Playwright, intercept only the top-level navigation and fulfill it with the transformed fixture while allowing the site's real CSS, JavaScript, fonts, images, and same-origin requests to continue normally. Build a per-path handler factory that closes over the expected path and body, then assert an unmistakable candidate marker or expected script/style count after navigation. A missed interception can silently exercise live production and manufacture a false canary result.
4. Wait through frontend initialization and delayed mutations, then inspect the **final DOM** for H1 count, landmarks, ARIA, link names, computed contrast, page errors, broken assets, and axe violations. Preserve selectors and computed styles for every remaining node.
   - Keep the raw-response SEO gate and the rendered accessibility gate separate. Require the server document to contain the intended H1 structure, but in the browser count only headings that survive the accessibility-relevant runtime state: reject an element under `[aria-hidden="true"]`, `[hidden]`, or `[inert]`; reject `display:none`, `visibility:hidden`, and `visibility:collapse`; and require a non-empty `getClientRects()`. A DOM query returning one H1 is not a heading pass when a responsive builder has left that node inside a hidden branch.
   - When the remedy inserts a fallback heading, choose a rendered main landmark rather than the first matching `main`/wrapper, because builders commonly retain separate hidden desktop/mobile branches. Require exactly one accessible H1 after the last initialization window; record raw DOM H1 count separately so an inaccessible duplicate does not masquerade as the accessible heading.
   - Reproduce the actual mutation class in the canary. If production hides/reparents the heading, CSS-hide or `aria-hidden` the existing node and exercise the same delayed/observer repair path; deleting the node alone is an insufficient fixture because a repair can pass deletion while incorrectly treating a hidden H1 as valid. Rerun axe after the mutation and require the accessible-H1 count to recover without browser errors.
5. Convert every reproduced defect into a deterministic unit fixture and rerun PHP lint, transform tests, and the browser canary. Before freezing the production hash, add an exact release-identity gate that loads the candidate through the real bootstrap path and requires every declared version surface—plugin header, runtime constant, CLI/readback value, and manifest—to agree byte-for-byte. A behavioral canary can pass while stale version metadata still causes the production bootstrap gate to reject the file; test the identity invariant explicitly rather than inferring it from functional tests. Freeze the plugin hash only after all behavior and identity gates pass.

Never accept a clean static regex transform as proof of browser accessibility: builder JavaScript can recreate invalid ARIA or unnamed controls after load, and late-injected plugin CSS with equal specificity can override an earlier `!important` rule. Repair the semantic source when possible; when a third-party runtime mutation must be contained, observe the final DOM and use the narrowest idempotent mutation repair, then prove it after the last expected initialization window.

Bind the acceptance threshold to the requested outcome. A zero-critical gate is acceptable only when the authorized objective is critical-risk reduction; when Rodolfo asks for complete remediation, retain every axe rule/node count and continue until the scoped matrix reaches zero violations or an excluded component/decision gate is named explicitly. Do not report a green threshold as “everything corrected” while serious or moderate nodes remain.

## Phase 6 — Forms, cookies, and tracking

- Verify labels, required-state behavior, visible CAPTCHA, iframe accessibility names, and client-side validation without creating a real lead.
- For a custom consent layer, set the root consent state synchronously in `wp_head` and parse the banner early enough that it does not become a late LCP candidate. On themes with skip links before the header, insert the banner after those skip links and immediately before the header: appending it near `</body>` can delay LCP, while inserting a labeled section as the first body child can make axe treat the preceding skip links as content outside landmarks.
- Treat footer/legal controls as runtime state when Elementor or another builder rewrites the footer. Use one idempotent ensure routine that repairs both the container and required child controls; checking only that the legal nav exists can miss a removed Cookie preferences button. Re-run it after observed child-list mutations, bind each control once, and prove Essential → reopen settings → Accept all in a fresh browser lifecycle.
- Do not submit a production form merely to make an audit “complete”; a live submission is a side effect and needs explicit scope plus a clearly synthetic record and cleanup plan.
- Record cookies created on first load and whether consent/choice UI appeared. The absence of a consent layer while analytics/advertising cookies are placed is a compliance-risk finding; identify the observed mechanism and jurisdictional uncertainty instead of issuing an unsupported legal verdict.
- Separate Google/Meta browser collection from server-side tagging. A failing custom collection host can coexist with successful page rendering and must be diagnosed as a measurement defect.

## Phase 7 — External links and control plane

1. Deduplicate external destinations and retain all referring pages.
2. Probe conservatively with bounded concurrency. Recheck `0`, `403`, and `429` outcomes before calling them broken; bot controls and rate limits are not link death.
3. Treat reproducible `404`/`410` and DNS/TLS failures as actionable, prioritized by unique referrer count.
4. Read RunCloud/server/webapp identity, temporary credential count, current provider snapshots, Cloudflare zone/DNS status, and available settings without exposing secrets.
5. If the Cloudflare token can see DNS but receives `403` for zone settings, report the settings coverage gap; do not infer their values from public behavior.

## Phase 8 — TLS, headers, cache, and origin

Apply the three-path matrix from the RunCloud edge/origin reference: bare public, cache-busted public, and direct origin with Host/SNI. Validate HTTP→HTTPS, `www` canonicalization, TLS 1.0/1.1 rejection, TLS 1.2/1.3 support, public certificate validity, origin certificate class, cache markers, and all security headers.

Duplicate headers on cache-busted responses are a layer-composition finding even when browsers tolerate them. Attribute the duplicate before editing WordPress, Nginx, or Cloudflare.

When a public health probe runs from the origin, do not use a default Python client identity as the only acceptance gate. A WAF may return `403` to `Python-urllib` while browsers and the canonical curl/browser validator receive `200`; send the explicit validator User-Agent and corroborate any non-2xx with the external browser path before triggering rollback.

## Phase 9 — Authenticated evidence gate

Public REST metadata can enumerate routes and versions but cannot certify filesystem or database integrity. If no approved SSH route exists:

1. Finish every public/control-plane phase first.
2. Freeze one complete collector and acceptance manifest before asking for credential creation.
3. Include OS/services/packages, full filesystem hashes and heuristics, WordPress core/plugin/theme checksums, MU plugins/drop-ins, database/users/sessions/WPCode/cron, logs, exact app-scoped config hashes, and recovery archive/provider-snapshot evidence.
4. Render every embedded Python/PHP/shell payload as a standalone artifact and lint it before freezing the manifest. Probe optional WP-CLI subcommands instead of assuming they exist: if theme or commercial-plugin checksums are unavailable, retain exact full-tree SHA-256 maps and classify canonical-package comparison as uncertified rather than failing the whole collector.
5. Scan database content in bounded PHP/WP batches and emit only row IDs, content hashes, signature classes, sizes, and external hosts. Do not interpolate page-builder or attacker-controlled content into SQL `REGEXP`; escaping, collation, and binary values can turn a read-only coverage probe into false gaps or parser leakage.
6. Discover the actual firewall owner before choosing a command. Treat UFW, nftables, firewalld, provider rules, and the RunCloud API as distinct evidence layers; an unavailable or hanging UFW frontend does not invalidate verified nft/API rules plus external port probes.
7. When historical forensic rows, revisions, or users disappear between audits, reconcile authorized account-consolidation/user-deletion operations before declaring tampering. WordPress user deletion with reassignment can change revision cardinality even when published posts are reassigned; require the authorization/audit event, exact per-site receipt, and preserved pre-operation backup before classifying the delta as an authorized concurrent change.
8. Use one temporary provider credential lifecycle only. Validate zero/known prestate, exact server/webapp identity, credential GET, one collector execution, `finally` deletion, exact-ID `404`, return to the initial count, deleted-key authentication refusal, and local-key deletion.
9. If the collector is missing a probe after confirmation, stop rather than manufacturing a second credential request; expand and freeze a new manifest only through a new explicit decision gate.

## Phase 10 — Exact-version vulnerability correlation

1. Join every active plugin's normalized slug and exact installed version to current NVD/CVE records plus a reputable WordPress-focused advisory source. Search results are discovery only; extract the advisory or CVE record before asserting affected or patched ranges.
2. Record authentication level, required role, impact, severity, affected-through version, and first patched version. Compare required roles with the live WordPress user-role inventory so an authenticated issue is not dismissed merely because it is not unauthenticated.
3. Keep four verdicts separate: checksum integrity, malware evidence, known-version vulnerability exposure, and update compatibility. A clean tree is not a security pass, and no malware finding does not erase a confirmed CVE.
4. Treat a base plugin and its Pro/add-on component as one update unit. If only one side has an available package, preserve the running pair and report the package/compatibility blocker; never recommend applying the lone offered update directly to production.
5. For ThemeREX-managed themes and commercial plugins, snapshot the exact updater/plugin/theme transients and component trees before the first write, then update the commercial child packages before updating ThemeREX Updater/Addons. A ThemeREX update may deactivate itself or clear the custom update list: reactivate and read back each component, and if the still-authorized package disappears, restore only the exact pre-write updater list from the validated database backup rather than guessing a package URL. After all targets reach their exact versions, invalidate the restored list and verify that stale update rows disappear. New ThemeREX Addons/theme packages may already contain the current QW extension or skin; verify the embedded `@version` and `skins.json` before issuing redundant AJAX updates.

## Phase 11 — Consolidation

A script exit `0` means collection completed, not that the site passed. Inspect every artifact and publish:

- **Healthy:** availability, first-party rendering, TLS/headers, backups, checksums, or controls actually verified;
- **Actionable:** content/SEO/accessibility/performance/tracking/security defects with exact evidence;
- **Expected non-2xx:** protected/API/control behavior excluded from actionable totals;
- **Uncertified:** gated or technically unavailable coverage;
- **Decision boundary:** one minimal remediation scope, with production explicitly unchanged during the audit.

Use fresh current totals only. Keep Lighthouse lab scores, axe violations, crawl issues, and host/integrity verdicts as separate dimensions; no single score represents overall site health.
