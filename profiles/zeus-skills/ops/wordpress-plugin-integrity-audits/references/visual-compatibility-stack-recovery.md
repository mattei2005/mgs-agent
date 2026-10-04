# Visual compatibility-stack recovery

Use this branch when the site is technically healthy but the owner says the page no longer looks like the original, especially after coordinated theme/plugin/cache updates.

## Procedure

1. **Reject inferred redesign as the first recovery path.** Freeze the current page and recover the oldest trustworthy isolated filesystem/database restore. Compare builder-data bytes and hashes before touching production. A tiny builder-data delta alongside broad theme/add-on/slider drift means the layout source is intact and the rendering compatibility unit changed.

2. **Inventory the complete visual unit.** Record exact versions, tree maps, configuration hashes, and active state for:
   - parent and child themes;
   - theme add-on and updater;
   - slider;
   - builder base/Pro pair;
   - generated CSS and combined asset files;
   - page/minify cache state;
   - MU frontend transforms.

   Keep content/database restoration separate from compatibility restoration. Preserve normalized URLs and current content when the builder-data diff proves that structure did not materially change.

3. **Build the candidate from validated recovery material.** Reject path traversal and symlinks, hash the archive, and create per-component `path -> SHA-256` maps plus file/byte totals. Validate main PHP files and exact version headers. Package only the named compatibility directories; do not widen the canary to unrelated plugins merely because the backup contains them.

4. **Freeze one reversible cutover.** Back up every live target tree, the exact cache/config scopes, and the current active-state manifest. Promote staged trees atomically, change only the named cache option, and move generated page/minify cache scopes into private rollback storage instead of deleting them. Preserve current database, uploads, builder pair, child theme, and compliance controls unless the owner explicitly chooses an exact-original rollback that removes them.

5. **Use route-aware integrity gates after bootstrap.** Some theme ecosystems regenerate combined files on first load. Require identical path sets and exact hashes for every immutable file, but compare known generated bundles separately. For ThemeREX Addons, the generated compatibility set is:
   - `css/__responsive-full.css`
   - `css/__responsive.css`
   - `css/__styles-full.css`
   - `css/__styles.css`
   - `js/__scripts-full.js`
   - `js/__scripts.js`

   Exclude only these six from the immutable core digest, require all six to remain present, and store their post-bootstrap hashes. Do not relax the whole plugin tree because generated files changed.

6. **Separate source placeholders from visible defects.** Slider source HTML can legitimately contain `{{current_slide_index}}` or `{{total_slide_count}}` before JavaScript initializes. Do not fail a source-only gate for those tokens. Require the corresponding runtime assets and global, then fail only if the tokens remain visible in the rendered DOM or the slider has zero dimensions/uninitialized state.

7. **Validate rendered behavior, not stitched pixels alone.** Run fixed viewport browsers from narrow mobile through wide desktop; scroll the page, then require zero overflow, broken images, page errors, internal request failures, and accessibility violations. Exercise consent states, form/reCAPTCHA, and all introduced interactions by keyboard. A full-page screenshot can duplicate fixed/sticky headers or omit cross-origin iframe pixels; classify those as capture artifacts only after DOM rectangles, computed styles, iframe text, and network status prove the live component is correct.

8. **Make owner acceptance a gate.** Automated PASS leaves the canary in `owner_acceptance_pending`, not complete. If the owner says it is not the remembered layout, roll back immediately to the frozen live trees/config/cache, preserve the rejected canary, and stop visual iteration against production. Ask the owner to choose exact-original versus compliance-safe hybrid only when that difference is real and evidenced.

## Builder restoration without subscription renewal

- Separate existing-plugin activation from a vendor update. When an owner supplies a working reference, prove the failed site's builder markup/activation difference and test the existing compatibility unit in an isolated clone before presenting renewal as necessary. Do not copy a commercial tree from the reference without a legitimate package or trusted manifest.
- Derive the element-cache bypass from the installed Elementor source. Current builds may use `elementor_element_cache_ttl=disable` directly in `Document::print_elements()` even when an older experiment switch no longer controls rendering. A cached document can omit a widget that is now correctly registered; compare fresh rendered widget inventory, not registration alone. Prefer a reversible owning-option filter over deleting cached metadata during diagnosis.
- If an old add-on uses removed scheme classes, keep vendor files untouched and test the smallest compatibility adapter separately. Preserve builder-data/content hashes, enable only used widget capabilities, and enumerate the actual anonymous AJAX hooks before deploying containment; prefixes such as `ppe_` differ from `pp_`. Never let an adapter change licensing, entitlement, or billing, and do not call legacy commercial source fully certified merely because rendering passes.
- Reconcile an apparent off-canvas overflow in a stitched screenshot with real viewport screenshots and DOM after fresh load, open, close, and logo navigation. A closed transformed panel entirely beyond `x=innerWidth`, with `scrollWidth=innerWidth` and `scrollX=0`, can be incorporated into full-page capture without being visible to visitors. Fix the validator/capture interpretation, not production CSS, when the exact viewport is healthy.

## Completion evidence

Record candidate and rollback hashes, component versions/tree digests, cache/config before/after, browser matrix predicates, fixed-viewport screenshots, owner acceptance, credential cleanup, and public/origin readback. Report recovered validator failures by mechanism; never hide them because a later retry passed.
