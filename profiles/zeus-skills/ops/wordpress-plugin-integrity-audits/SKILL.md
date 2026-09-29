---
name: wordpress-plugin-integrity-audits
description: "Use when auditing WordPress integrity or full site behavior."
version: 1.3.3
author: Zeus MGS
license: Proprietary
tags: [wordpress, plugin, checksum, integrity, source-drift, canary, seo, redirects]
metadata:
  hermes:
    tags: [wordpress, plugin, checksum, integrity, source-drift, canary, seo, redirects]
    related_skills: []
---

# WordPress Plugin Integrity Audits

## Purpose

Audit WordPress source integrity and public site behavior without confusing checksum drift, malware, a deliberate functional workaround, an available update, or a broader content/SEO/accessibility defect. Finish with a verified behavior map and one reversible decision boundary; do not mutate production merely to make checksums green or a generic score perfect.

## When to Use

Load this skill for WordPress checksum/source drift, a complete WordPress site audit, unexplained frontend differences between origin and edge, stale page-cache behavior, broken public assets, or a remediation that must be proved through crawl and rendered-browser gates.

## Standing rules for Rodolfo

- Treat public routing, language URLs, canonicals, redirects, cache behavior, and tracking parameters as production behavior. Require explicit confirmation before changing them.
- Keep restoration and version upgrade as separate canaries. Combining both obscures cause and rollback. When Rodolfo wants the failed update corrected rather than abandoned, treat rollback as temporary containment only: closure requires the compatible base/Pro upgrade to pass, or Rodolfo to explicitly defer/accept it. A stable old pair is not completion of the requested update.
- After any provider restore, validate the original visible failure rather than stopping at HTTP 200, restored plugin versions, or a matching database size. Compare page markup with the CSS and JavaScript handles plus runtime globals required by each component: when slider or builder markup exists but its required assets and runtime global never load while raw template placeholders remain visible, isolate that component’s activation, enqueue, and cache path before blaming an unrelated plugin update. A snapshot can faithfully restore the same broken application state.
- Never close a full-site or visible frontend remediation from HTTP, network-error, axe, Lighthouse, or initialized-widget gates alone. After scrolling the complete page, capture full-page screenshots from explicit, fixed browser viewports at representative desktop and mobile widths and inspect geometry explicitly: hero height relative to the viewport, header contrast/alignment, consent occlusion, section gaps, grid wrapping, form-to-submit spacing, and footer/legal-bar composition. Do not use Lighthouse `fullPageScreenshot` as the geometry baseline: fullscreen/`100vh` widgets can inherit a synthetic stitched-page height and make a hero appear thousands of pixels tall even when the fixed viewport behaves differently. Compare against the oldest **trusted healthy** visual reference; first inspect candidate historical screenshots because a previously “validated” image can itself contain an oversized/blank hero, raw slider placeholders, missing media, or a covered footer. When screenshots are not trustworthy, inspect every preserved isolated filesystem/database restore before declaring that no reference exists: compare the builder-data hash/bytes with the current site and inventory the complete visual compatibility unit—theme, child theme, theme add-on, slider, updater, generated CSS, cache/minify state, and MU frontend transforms. A tiny builder-data delta alongside broad component-version drift is a compatibility-stack restoration problem, not permission to redesign. Reconstruct by inference only when no exact source can be recovered and Rodolfo newly authorizes that scope.
- Treat Rodolfo’s visual acceptance as a hard production gate that outranks automated screenshots, geometry, axe, and vision-model judgments. If he says the page is still misaligned or not like before, roll back the visual candidate immediately under its frozen rollback, preserve it as rejected evidence, and stop iterating CSS against the live site. Recover the original compatibility unit from isolated evidence, then present the real decision boundary when exact appearance conflicts with current privacy/SEO/accessibility hardening: exact-original rollback versus a compliance-safe hybrid. Do not call either option complete until Rodolfo accepts the rendered result.
- After any theme/plugin/cache compatibility rollback, restore, or downgrade, treat owner visual acceptance as approval of appearance only—not closure of prior remediation. Build a prior-fix regression ledger and rerun the complete site audit before closure: map every earlier correction to its owning component or storage surface, determine whether the version change could overwrite or regenerate it, and prove the current public, browser, cache/origin, WordPress/database/filesystem, host, and backup predicates. Classify each correction as `preserved`, `regressed`, or `uncertified`; never assume security, accessibility, SEO, legal, performance, or generated-asset fixes survived merely because the home looks correct.
- Treat an in-plugin `License: Active` banner as an entitlement signal, not proof of the paying account or of an unmodified commercial package. Resolve account identity through the vendor account/trusted updater without exposing tokens, and prove source integrity by comparing the complete live tree with a legitimate same-version vendor package or trusted manifest; never infer “official” or “nulled” from the banner alone.
- Evaluate a commercial plan against features the site actually uses and data it must retain—not against the plugin name. Inventory builder widget types/templates plus persisted submissions, popups, custom CSS/code, custom fields/post types, dynamic content and e-commerce use, then map every used capability to the vendor’s current official plan matrix. A plan that includes form rendering but excludes stored submissions does not preserve a site that already relies on the submissions tables.
- If Rodolfo says to stop or announces that he will perform a manual restore, cease login, license, update, and integrity probes immediately; do not race the owner’s control-plane mutation. State whether any production write or background executor is active, preserve the last known evidence, and wait for post-restore readback before resuming.
- Treat source integrity and vulnerability exposure as independent gates: a checksum-clean plugin can still be vulnerable. Correlate the exact installed version with current NVD/CVE and reputable WordPress security advisories, record the affected and patched ranges, and bind any update recommendation to base/Pro compatibility rather than offering a single-component upgrade.
- Treat an executable file written into `wp-content/uploads` through a public or anonymous WordPress path as a critical file-write primitive even when edge and origin currently return `403`. Freeze path, SHA-256, size, ownership and timestamps; correlate them with access/error logs and the exact source path; prove whether any request to the dropped file returned `2xx`; and preserve the artifact outside the webroot before quarantine. Say **contained, not clean** until the drop is removed and the write primitive is closed.
- When visual compatibility requires a plugin downgrade that reopens a security flaw, keep the accepted visual compatibility unit frozen and contain the flaw through a separate, hash-pinned MU plugin with its own rollback instead of editing vendor code or expanding the visual hardening file. If the vulnerable vendor decoder is guarded by `function_exists()`, load a compatible safe definition before normal plugins, decode with `allowed_classes => false`, recursively reject every object graph, and block an anonymous AJAX family only after proving the public site does not use those widgets. Preserve authenticated administrator tooling unless the confirmed scope says otherwise.
- Report in PT-BR with the conclusion first: what differs, whether it is malicious, the observed public effect, update risk, recommendation, and exact confirmation needed.
- For authorized long work, stay silent until the audit is complete or a real decision blocker appears.
- When Rodolfo asks to work one domain at a time, keep the domain—not the first open cross-fleet worksheet row—as the unit of closure. Reconcile its primary row and every residual row, state plainly whether that domain is fully closed, and only then select the next domain-specific case. Treat fleet-wide DNS/alias/plugin programs as separate workstreams; never substitute one for the requested next domain.
- When Rodolfo authorizes “finish everything” or asks for no intermediate approvals, complete every safe/read-only and already authorized write first. Before freezing a Critical artifact, exhaust the live read-only identity gates that could invalidate it—release header/runtime constant equality, registered taxonomy identifiers, public sitemap/body identity, and origin/edge/cache parity—and rerun the complete canary after any correction. Treat intermediate apply/gate/rollback attempts as internal execution rather than user-facing “V2/V3/V4” milestones. Interrupt once with one concise combined confirmation for the fully revalidated Critical manifests; if a changed exact target forces another confirmation, first aggregate every newly learned invariant so the next request is final. Do not turn routine stages into repeated approval prompts, and keep external vendor-license/package blockers separate from the Critical confirmation.
- When Rodolfo excludes one plugin or compatibility unit from a broad remediation, freeze that exclusion as a precondition and make every canary prove its versions, vendor files, and builder data remained unchanged. Authorization to fix “the rest” does not reopen the excluded component.
- Update a commercial plugin only from a legitimate package or trusted vendor updater. If no authorized package is available, preserve the installed tree, document the residual risk, and separate any narrowly validated defense-in-depth control from the vendor update.

## Topical references

- For Cloudflare Email Address Obfuscation attribution, a localized `email_off` bypass, and bare-edge readback, load `references/edge-email-obfuscation-and-cache-validation.md`.
- For a complete public-to-internal WordPress re-audit covering crawl, SEO/content, templates, accessibility, Lighthouse, tracking, external links, control plane, and the authenticated evidence gate, load `references/complete-wordpress-site-reaudit.md`.
- For existing WordPress credentials, CAPTCHA-protected admin inspection, exact update inventory, REST limits, and the temporary-SSH boundary, load `references/authenticated-admin-and-no-ssh-fallback.md`.
- For recovering an owner-recognizable original layout from isolated backups and a theme/add-on/slider/cache compatibility unit, load `references/visual-compatibility-stack-recovery.md`.

## Workflow

1. **Freeze the installed runtime.** Capture site, root, owner, plugin slug, active state, installed version, available version, and auto-update state.

   ```bash
   wp plugin list --name=<slug> \
     --fields=name,status,update,version,update_version,auto_update \
     --format=json
   ```

   Block updates during classification because an update can erase the only evidence and silently change behavior.

2. **Run the native checksum gate.** Execute:

   ```bash
   wp plugin verify-checksums <slug> --format=json
   ```

   Preserve stdout even when the command exits non-zero; WP-CLI can place the exact mismatching file in stdout and only a summary in stderr. A checksum failure is an integrity fact, not a malware verdict. When every mismatch is `File was added` and expected files have no missing/modified rows, classify the tree as a mixed-version or residual-file candidate; restore the exact installed package rather than upgrading a deliberately held plugin.

   For failures during a batch update, do not attribute causality to the plugin row that displays the red notice. Capture the complete fatal stack and correlate its timestamp with every plugin changed in the batch; a previous update can break WordPress bootstrap and make the next row merely display the global failure. Compare the highlighted plugin's live tree with the frozen baseline and remove it from causal attribution when unchanged.

   Run `wp core verify-checksums` independently from plugin checks. If it fails only because an intentionally hardened file such as `readme.html` is absent, record that exact exception and require every remaining core file to match; do not convert a known missing non-runtime file into a claim that core PHP is modified. Treat an alarming basename inside a WordPress core path as a heuristic, not a verdict: require the exact official core checksum plus behavior/signature inspection before calling it malware, because legitimate core files can have names that generic scanners flag.

3. **Compare the exact official version.** Download `<slug>.<installed-version>.zip` outside the webroot, hash it, extract to a temporary directory, and compare complete relative-path → SHA-256 maps. For WordPress.org packages, also fetch `https://downloads.wordpress.org/plugin-checksums/<slug>/<version>.json` and require the extracted files to match its SHA-256 values; a valid ZIP alone does not prove canonical contents. Record modified, live-only, official-only, official ZIP hash, and live/official hashes. Never compare an old installation with `latest`; that mixes expected version drift with local customization. Remove the temporary extraction afterward.

   Normalize plugin identity before joining current and historical manifests: resolve WP-CLI name, plugin directory, and main plugin file to one canonical key. Single-file plugins and directory plugins can expose different keys across collectors; a key mismatch is not an added/removed tree until the complete relative-path maps have been reconciled.

4. **Inspect the minimal diff and provenance signals.** Record owner, group, mode, mtime, ctime, and nearby package-file timestamps. Search shell/audit history only for sanitized classifications such as command family and filename; never persist arbitrary history lines because they may contain credentials. Report authorship as unattributed unless a canonical event proves it.

5. **Classify three questions separately.** State independently:
   - **Integrity:** does live source differ from the exact package?
   - **Security:** does the diff add suspicious execution, obfuscation, credential access, or an unexplained file?
   - **Behavior:** what application/runtime action changed?

   A narrow functional diff is not a backdoor merely because the checksum fails.

   For repeated JavaScript or obfuscation heuristics in database rows, cluster identical values by SHA-256 before assigning severity, map the original snippet to builder/meta copies, and compare that source hash with the prior trusted baseline. Inspect decoded behavior, external hosts, dynamic execution, and shell/network primitives; do not count every copied row as a separate injection.

6. **Prove the behavior publicly and at origin.** Probe without following redirects first so status and `Location` remain observable. Then validate final destination, body, canonical/hreflang, and cache at both CDN/public and origin. Exercise the route classes affected by the diff, including language paths, query variants, trailing slash, representative posts, UTMs, `fbclid`, and `gclid` when relevant.

   For REC→P1 or other internal-navigation parameter loss, trace the full chain instead of blaming the theme from the final URL alone:
   1. Read the raw WordPress object and enumerate the destination in every storage surface, including serialized block/LazyBlock attributes and ordinary `<a href>` elements; one CTA can exist in both a dynamic card configuration and a final Gutenberg button.
   2. Inspect the rendered DOM after JavaScript and the responsible URL-forwarding code to establish whether the incoming query was appended before the click.
   3. Request that exact clicked destination with the full representative query **without following redirects** and record status plus `Location`; then request the canonical target directly with the same query.
   4. When an obsolete slug redirects to a clean canonical URL, inspect the destination post's `_wp_old_slug` values. Classify this as a stale internal destination plus query-dropping old-slug redirect—not a missing forwarding function—when the broker appends the query but the first redirect removes it.
   5. Repair every stored representation of the destination, not only the visibly rendered anchor, and validate the clicked URL, every redirect hop, and the final landing URL with all required parameters preserved.

   - Probe root extras and operational residues explicitly: `nginx.conf`, `wp-admin/error_log`, `readme.html`, configuration backups, dotfiles, archive files in uploads, and known backup extensions. A checksum-clean core does not prevent a non-core file from being publicly downloadable.
   - Validate origin TLS separately from origin application behavior. If certificate verification fails, preserve the verify code as its own finding; only then use an explicit insecure probe to inspect origin HTTP behavior, and never report that content probe as TLS health. Before calling the chain broken, read the control-plane SSL method: a valid custom Cloudflare Origin CA certificate is intentionally not trusted by the public OS CA store. In that case, require public edge TLS success plus valid Cloudflare→origin status and report direct-origin trust as an origin-only property, not a public outage or an instruction to replace the certificate blindly.
   - Do not classify a compressed archive as PHP or malware from raw `<?php` bytes in the ZIP stream. Inspect the archive structure without extraction, reject path traversal, enumerate executable entries, and scan only decompressed code entries before assigning a verdict.

   Do not accept a canonical tag as equivalent to a redirect: a non-canonical URL returning 200 still creates duplicate crawl/cache surfaces even when indexing is partially mitigated.

   Pair sitemap/HTTP crawling with a real rendered-browser pass at desktop and mobile widths. Scroll representative long pages to trigger viewport-bound scripts, group network failures by unique URL rather than raw event count, and inspect mixed-content fonts, CSS backgrounds, raw shortcodes, visible verification text, and 404 assets; HTTP 200 and zero broken `<img>` elements do not prove the rendered site is complete. For every non-2xx crawl destination, build a destination → unique referring-page map and classify genuine internal navigation links separately from intentionally blocked/protected, API, form-action, or one-time endpoints. Prioritize genuine broken destinations by inbound-page count and verify each directly plus in a rendered source page; never report one aggregate 404 total without this route classification. When the crawler follows redirects, compare the requested URL with the final URL before grouping duplicate titles or canonicals: a legacy alias that lands on the canonical page is redirect evidence, not a second page defect. Preserve raw probe totals, but publish a separate actionable count after expected protected/control endpoints and redirect aliases are classified.

   Make validators route-class aware. Compute legal/demo-copy findings from rendered visible text with scripts, styles, `noscript`, and hidden builder payloads classified separately; otherwise serialized Elementor or other builder data can fail a corrected page that no visitor sees. For deliberately noindexed internal templates, require the intended robots value and sitemap exclusion rather than forcing the H1/main-landmark contract used for maintained public landing pages.

   Distinguish stale page cache from live source before assigning ownership: request the canonical public URL, the same URL with a unique cache-busting query, and the origin with `--resolve` plus `Cache-Control: no-cache`. Compare status, complete decoded body, and security headers across all three. A base URL and a cache-busted response can carry different headers or markup when page-cache artifacts predate the live configuration; classify that as cache variance until source configuration and cache contents are read back, not as an unexplained concurrent change. For Lighthouse, warm and measure the clean canonical URL as the user-facing baseline, then run cache-busted/origin probes separately for cache diagnostics; a unique query can bypass full-page cache and distort TTFB or performance, so never use that run alone to justify a production optimization.

   When checking visible verification strings, raw shortcodes, footer text, or late-page markup, search the **complete decoded response body** and confirm it in a rendered browser after scrolling. Never rely on a fixed-byte head/sample because page-builder output can place the defect beyond the truncation boundary. For Search Console specifically, validate the selected method independently: a visible body string is not file verification; file verification requires the exact verification URL to return `200` with the exact token, while meta/DNS methods require their own readback. Remove the visible copy only after preserving or establishing a working verification method.

   If a legacy value persists in both uncached public and origin bodies, inspect serialized database values and generated CSS; clearing cache alone cannot fix it. If source is clean but the canonical cached response is stale, purge only the affected application/CDN cache scope and then repeat the three-way comparison.

7. **Check current evidence without overclaiming.** Search error logs for the plugin symbol, redirect loops, and fatals. The absence of errors does not prove a workaround is obsolete; the patch may be suppressing the original failure.

8. **Choose a reversible decision path.**
   - If unnecessary: back up the current plugin/file, restore only the official diff in a canary, test all affected routes and tracking parameters, then keep or roll back.
   - If required: reproduce the behavior through the plugin's documented hook/filter or a narrow mu-plugin, restore the vendor package, and require checksum PASS.
   - If upgrading: act only after the customization decision, with a separate backup, canary, and rollback.
   - Treat a public base plugin and its Pro/custom extension as one compatibility unit. Require a canonical package or trusted manifest for both sides; do not combine a checksum-clean public core with an unverified Pro tree or infer compatibility from version headers alone.
   - Use a known-working snapshot as rollback material, not as proof of a clean vendor package. Verify the snapshot tree against the canonical source before using it for reconstruction, because a functional site can still contain mixed-version files.
   - Distinguish first creation from in-place revision when freezing rollback. For an existing hash-pinned MU plugin or control file, require the exact old hash, create one temporary hash-verified copy before atomic replacement, and restore that old file/version on failure; do not use delete-only rollback because path absence would remove the last validated behavior. Remove the temporary copy only after full acceptance, but preserve it if rollback itself fails.

9. **Validate closure.** Capture plugin counts, statuses, versions, manifests, HTTP state, and log position dynamically immediately before the cutover; never hard-code historical counts into the validator. Require exact file hash/readback, plugin checksum result, public/origin route matrix, no loop/regression, cache behavior, and absence of test residue. Persist the complete post-cutover evidence and the pass/fail value of every predicate before automatic rollback, because discarding the failed state turns an invariant mismatch into blind retries. A successful file write is not completion.

   Treat rollback as a second public deployment, not merely source-file removal. If a canary can generate full-page cache, freeze the exact application-cache scope and its purge action in both the apply and rollback manifests before mutation. On failure, preserve the failed validator artifact, remove only the hash-approved target, purge only that application's generated cache, and require the canonical URL, a unique cache-busting URL, and origin to agree with the prior behavior before revoking temporary access. Target-path absence alone is not rollback closure because cached transformed HTML can remain public after the source is gone.

   For consent changes, use two fresh browser contexts. Before any choice, require the banner plus zero optional analytics/advertising cookies and zero optional tracking requests; after **Essential only**, require those signals to remain absent; after **Accept all**, require the preference cookie and at least one successful real measurement request. A service-worker helper returning `404` is not by itself a tracking outage when the documented browser fallback sends the collection request successfully—report the helper failure and the successful transport separately.

   For W3 Total Cache, read every approved option after environment repair and reconcile drop-ins: `db.php` must agree with `dbcache.enabled`, `object-cache.php` with object-cache intent, and the live values override the remembered profile. For Elementor, search generated CSS and cache trees for legacy hosts even when a database dry run returns zero; generated local-font CSS can preserve an obsolete HTTP host until CSS is regenerated. Back up before regeneration and validate unique font URLs in a browser afterward.

   After a Slider Revolution update, verify the active rendering engine as well as the plugin version. A release can automatically set `revslider-global-settings.getTec.engine=SR7` and `revslider_set_v7_engine=1` while an existing slider still requires the SR6 frontend path; HTTP 200 and emitted `<sr7-module>` markup do not prove initialization when the corresponding assets are absent. First use the plugin-supported read-only `?srengine=6` request override as a compatibility canary. Require `rbtools.min.js` and `rs6.min.js`, an initialized `rs-module` with nonzero dimensions, no **visible** `{{current_slide_index}}`/`{{total_slide_count}}` tokens, and zero internal request/page errors on desktop and mobile. Do not reject SR6 merely because those placeholders exist in raw source: the runtime replaces or hides them after initialization. If the canary passes, freeze and back up the exact global-settings value, change only `getTec.engine` to `SR6`, preserve `revslider_set_v7_engine=1` so the automatic hook does not overwrite the choice, quarantine the exact stale page-cache file without deleting it, and validate canonical, cache-busted, public, and origin responses before considering a plugin downgrade.

   Do not declare a frontend visually healthy from HTTP, accessibility, console, or network gates alone. Capture and inspect full-page screenshots plus geometry metrics at fixed desktop/mobile widths, compare against every available historical screenshot, and state explicitly when no known-good visual reference exists. Build visual repairs as non-production CSS/JS overlays first; require a bounded matrix spanning narrow mobile through wide desktop, fresh and persisted consent states, zero horizontal overflow, preserved content, keyboard/ARIA behavior for new interactions, and a final production screenshot gate after the exact hash cutover. Treat a blank-looking cross-origin reCAPTCHA or a repeated fixed/sticky header in a stitched full-page screenshot as ambiguous until DOM rectangles, computed styles, iframe text, viewport screenshots, and network responses are inspected; screenshot compositing can omit cross-origin pixels or repeat fixed elements even when the live viewport is correct.

   Count serialized URL drift without writing by using `wp search-replace <old> <new> --all-tables-with-prefix --precise --dry-run --report-changed-only --format=count`. Use the returned count as a precondition, back up the database before the real replacement, and require the post-write dry run to return zero; do not depend on JSON/CSV output modes that this command may not support.

## No-SSH fallback boundary

Load `references/authenticated-admin-and-no-ssh-fallback.md` before using WordPress REST/admin credentials or proposing temporary provider SSH. Keep the complete fallback decision tree, credential hygiene, CAPTCHA-safe read-only login, structured update inventory, REST rollback gates, and one-shot SSH lifecycle in that reference.

## Polylang-specific branch

- Enumerate languages with `pll_languages_list()` and derive homes with `pll_home_url($slug)`. Do not pass an array-valued `fields` argument; invalid shapes can emit array-to-string warnings and return nulls.
- Commenting `wp_safe_redirect()` and `exit` disables Polylang's canonical 301 while leaving canonical calculation available to other rendering layers.
- If no-redirect behavior must remain, evaluate `pll_check_canonical_url` in a mu-plugin rather than editing `frontend/canonical.php` in place.
- Test default-language hiding, language roots, `?lang=...`, post URLs, slash variants, and tracking parameters before deciding.

## Completion output

Use short sections:

1. **Resultado:** exact scope of drift and malware verdict.
2. **Efeito:** verified public/origin behavior.
3. **Risco:** what an update or restoration would change.
4. **Recomendação:** minimal canary or supported extension point.
5. **Decisão:** one exact authorization question; state that production remained unchanged when applicable.
