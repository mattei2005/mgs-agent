# Bulk article SEO and indexing audit

Use the canonical Google Service Account and the Search Console access reference. Keep discovery/submission distinct from indexed status; ordinary editorial articles are not eligible for the job/livestream Indexing API. An authorized bulk indexing request is implemented through valid canonical sitemaps and verified submission, not a promise of Google's acceptance.

## Freeze a complete article scope

- Reconcile public REST pagination against native published WordPress posts and the post sitemap. REST may hide REC/P1 or other published articles; `per_page=100` and an HTTP 200 do not prove complete coverage. Preserve the source inventories and report the actual article denominator, separately from homepages, institutional pages, archives and localized homepage aliases.
- Parse XML sitemap namespace-aware: count only `<url><loc>` and `<sitemap><loc>` direct children. Descendant `.//loc` also collects image locations and inflates article totals.
- Inspect every requested article with URL Inspection and retain per-URL HTTP, coverage, canonical, crawl time and observation time. Append resumable JSONL batches capped near 100 URLs; a transport timeout does not authorize restarting completed calls. Reconcile the artifact and process state before continuing.
- Check public HTTP, canonical, robots meta/header, title, description, language and heading structure. Multiple H1 or missing description are quality findings, not proof of an indexing block. A public search backend result is not proof of Google indexing; prefer Search Console URL Inspection and search-performance evidence. Label page-dimension performance as returned rows, not an exhaustive site total.

## WP Fastest Cache can cache XML sitemaps

When sitemap coverage contradicts published posts:

1. Compare the bare sitemap with the same URL plus a unique query parameter; compare the **URL sets**, not XML order or lastmod alone.
2. Check public cache headers and origin files before blaming Google or Cloudflare. WP Fastest Cache may store stale XML in `wp-content/cache/all/post-sitemap.xml/index.html`; its cleanup glob `sitemap*.xml` can miss `post-sitemap.xml` and similarly named child sitemaps.
3. Read and back up `WpFastestCacheExclude` and preserve every existing rule. The option is a JSON string of records with `prefix`, `content`, `type`; a narrow rule `{"prefix":"contain","content":"sitemap","type":"page"}` prevents new sitemap page-cache generation. Confirm the installed plugin reads that schema before using it.
4. Canary one authorized domain. Archive only matching sitemap cache directories outside the webroot, with hashes and an immutable option snapshot; do not delete files or broadly clear article/ad caches. Preserve all other cache settings and active monetization.
5. Fetch bare sitemap URLs repeatedly, require every authorized published article in their URL sets, and verify the sitemap cache directories are not recreated. Expand only after canary success.
6. Submit the canonical sitemap index and article sitemap once through Search Console when authorized. GET each exact submitted sitemap and verify path and fresh `lastSubmitted`; `isPending=true` means received/awaiting processing, not indexed.

## Closure boundaries

Inventory/report any production cache configuration change. Preserve rollback paths, article/content/URL scope, and raw per-URL evidence. Do not silently remove old financial articles, tags, localized routes or metadata to make a niche audit look clean; separate that strategic/editorial decision from safe sitemap repair. Report actual indexed/not-indexed counts and remaining SEO findings. Domain recategorization and advertising-system learning are not proven by organic indexing, and no fixed 30/60/90-day guarantee should be inferred.
