# WordPress indexability cutovers

Use this reference when approved pages are ready to move from `noindex` to indexable, especially when an MU plugin, Yoast, a custom post type, or page cache controls the effective result.

## Procedure

### 1. Freeze four predicates separately

Build the exact target set by WordPress ID, post type, slug, and public URL. Record these as independent gates:

1. **Content readiness** — real copy, no demo markers, adequate depth, valid H1 and working media/links.
2. **Metadata readiness** — accurate SEO title, meta description, and focus keyphrase where used.
3. **Robots eligibility** — no `noindex` or `nofollow` in HTML or `X-Robots-Tag` for the approved URLs.
4. **Discovery** — each approved canonical URL appears in the correct sitemap, while unrelated protected content remains absent.

Do not call content replacement “SEO complete” when metadata or indexation still fails. A page can be healthy and intentionally `noindex` without being ready for search discovery.

For a broad request such as “index every URL,” first crawl the complete canonical route set and partition it by route class: maintained singular pages, archives/taxonomies/authors, pagination/redirect aliases, internal templates, legacy records, and visible demo content. Deduplicate followed redirects by canonical destination so one alias does not inflate the `noindex` total. Present the exact maintained inclusion set and protected exclusion set before mutation; never interpret “URL” as permission to expose every reachable route when the crawl proves demo or system surfaces are intentionally protected.

### 2. Attribute the effective `noindex` before changing post meta

Check all layers in this order:

- canonical public URL;
- the same URL with a unique cache-busting query;
- origin/no-cache response when origin access exists;
- response headers for `X-Robots-Tag`;
- WordPress/Yoast per-record values;
- post-type defaults;
- `wp_robots`, `wpseo_robots*`, and custom MU/plugin filters;
- `wpseo_sitemap_exclude_post_type`, `wpseo_exclude_from_sitemap_by_post_ids`, taxonomy exclusions, and `robots.txt`.

Search the live custom/MU code for the actual post IDs, post types, `noindex`, `wp_robots`, and sitemap hooks. A blanket MU filter can make every REST meta edit look ineffective because the public directive is added later at render time.

### 3. Repair protected Yoast metadata before removing `noindex`

For a custom post type, probe both an authenticated `GET ...?context=edit` and `OPTIONS` on `/wp-json/wp/v2/<type>/<id>`. If the schema omits `meta`, or a scoped PUT returns `200` while `meta` stays null, stop retrying the core endpoint: the write is being ignored, not accepted.

Then probe the privileged Yoast bulk editor with an existing administrator identity that has `wpseo_manage_options`:

```text
GET  /wp-json/yoast/v1/bulk_editor/posts?content_type=<type>&per_page=100
POST /wp-json/yoast/v1/bulk_editor/update_search
```

The POST body is:

```json
{
  "items": [
    {
      "id": 123,
      "seo_title": "Accurate SEO title",
      "meta_description": "Accurate description",
      "focus_keyphrase": "target phrase"
    }
  ]
}
```

Workflow:

1. Read and save the current bulk-editor rows as a mode-`0600` rollback artifact.
2. Apply one canary item.
3. Read the same row back through the bulk editor.
4. Request the public URL with a cache-busting query and verify the exact meta description.
5. Only then apply the remaining bounded batch and repeat both readbacks.

An editor-level `403` on the Yoast route proves a capability boundary, not that the route is unavailable. Escalate to an existing authorized administrator identity; do not create or rotate credentials merely to bypass the boundary.

### 4. Make selective indexation explicit in code

When custom code blocks an entire post type, keep one ordered allowlist of approved IDs and use it for both robots and sitemap logic.

- In the robots filter, exempt only approved IDs before the blanket post-type block.
- In the sitemap post-type filter, stop excluding only the post types that contain approved records.
- In the per-ID sitemap filter, enumerate published IDs from those reopened post types and exclude every ID not present in the approved allowlist.
- Keep archives, pagination, taxonomies, internal templates, and unrelated custom post types under their existing protection.
- Gate the reopened post type’s archive root and paginated archives separately from singular records. Yoast can prepend the archive URL to the first post-type sitemap independently of `wpseo_exclude_from_sitemap_by_post_ids`; if the archive aggregates demo excerpts, force `noindex,nofollow` with `is_post_type_archive()` and return `false` for that type through `wpseo_sitemap_post_type_archive_link` while leaving approved singular records discoverable.

Never remove a post-type sitemap exclusion without adding the complementary per-ID exclusion: otherwise every old or demo record in that type becomes discoverable. Do not assume the per-ID filter also excludes the archive root—the archive is generated through a different sitemap path.

Test at least one approved and one unapproved singular record from each reopened post type, plus the archive root and a real pagination URL. Freeze the old file hash, new file hash, exact allowlist, and the expected sitemap membership before production.

### 5. Cut over reversibly

For an existing hash-pinned MU plugin:

1. Require the live version/hash/owner/path to match the frozen precondition. If the hash differs, stop before writing and reconcile audit log → inventory → infra report → Git/session evidence; an authorized concurrent agent may already have deployed a newer release. Never overwrite that release with the stale candidate—rebase from the actual live bytes, validate the merged scope, and remove only your own hash-pinned staging residue.
2. Preserve an exact private backup.
3. Replace the file atomically; never use delete-only rollback.
4. Purge only the affected application/page-cache scope.
5. If temporary SSH credential creation is required, stop at the Critical Subset confirmation with the exact `0 → 1 → 0` lifecycle.
6. Roll back immediately if any target remains `noindex`, any unrelated record becomes discoverable, or sitemap coverage is partial.

### 6. Validate the real search surface

For every target URL, require:

- HTTP `200` at public and origin/no-cache where available;
- self canonical;
- no `noindex`/`nofollow` in HTML or headers (explicit `index,follow` is optional because absence of restrictive directives has the same effect);
- exact SEO title and meta description;
- inclusion in the expected sitemap;
- absence from the target set of every unrelated protected record;
- preserved content hash/media set when the cutover is metadata/robots-only;
- desktop and mobile rendered-browser passes after scrolling: no demo text, broken images, internal-link failures, or horizontal overflow.

Also revalidate the security predicates owned by the modified MU plugin; a small SEO diff must not silently weaken unrelated hardening.

After the sitemap set passes, crawl the internal link graph beyond sitemap membership. Indexable pagination, archives, and ordinary pages can expose demo text, repeated placeholder excerpts, or raw shortcodes while remaining absent from XML sitemaps; classify these as separate residuals instead of calling the entire site clean from a sitemap-only audit. Confirm visible text in a rendered browser because serialized builder payloads and raw HTML regexes can both misclassify demo content.

Do not equate sitemap presence with Google indexation, and do not submit URLs manually to Search Console unless that action was requested separately. Report the cutover as **eligible and discoverable**, not “indexed by Google.”

### 7. Reconcile Google Search Console without weakening identity controls

Use the canonical corporate Service Account and project only; never fall back to a personal Google browser session, refresh token, or alternate identity when API or property access is missing.

1. Read `searchconsole.googleapis.com` through Service Usage before calling Search Console. If it is disabled, have an actor with `serviceusage.services.enable` enable it in the canonical project, then read the state back as `ENABLED`. A Service Account may be able to read service state yet lack permission to enable it; an enable `403` is an IAM boundary, not proof that the API name or project is wrong.
2. Mint a token with `https://www.googleapis.com/auth/webmasters.readonly` through the canonical Service Account helper.
3. Call `GET https://www.googleapis.com/webmasters/v3/sites` and require the exact property plus a sufficient permission such as `siteFullUser`. API enablement and property membership are separate gates.
4. Call `GET .../sites/{url-encoded-property}/sitemaps`. Require the intended sitemap index, `isPending=false`, and zero warnings/errors; preserve submission and download timestamps.
5. Call `POST https://searchconsole.googleapis.com/v1/urlInspection/index:inspect` for the approved target set, then for the current sitemap set when Rodolfo asks about the whole site. Persist one row per URL and aggregate verdict, coverage, indexing state, robots state, fetch state, last crawl time, user canonical, and Google canonical.
6. Compare Search Console with the live release. `Submitted and indexed` can describe an older crawl, so it does not prove Google has processed newly published copy. Likewise, `Discovered`, `Unknown to Google`, or `INDEXING_STATE_UNSPECIFIED` is processing state—not a technical robots failure—when current public HTML, headers, canonical, and sitemap gates pass.
7. Treat sitemap summary counters such as `contents.submitted` and `contents.indexed` as asynchronous telemetry, not per-URL acceptance evidence. When they disagree with the current live sitemap or direct URL Inspection, report the mismatch explicitly, anchor current eligibility to the live sitemap/HTML gates, and anchor Google state to one inspection row per current sitemap URL plus its `lastCrawlTime`; never overwrite the direct-inspection count with a stale aggregate zero.
8. Do not invent a bulk indexing request path. Sitemap submission/discovery is the supported scalable handoff; report the split between technically eligible URLs and Google’s current indexed/crawled/discovered/unknown counts.

For closure, state all three layers separately: **live technical eligibility**, **sitemap discovery**, and **Google’s historical processing state**.
