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
2. Check public cache headers and origin files before blaming Google or Cloudflare. Inspect both `wp-content/cache/all/post-sitemap.xml/index.xml` and `index.html`, plus numbered post-sitemap children: real XML caches may use `index.xml`. Compare the cached bytes/hash and namespace-aware URL set with the bare public response. The cleanup glob `sitemap*.xml` can miss `post-sitemap.xml` and similarly named child sitemaps. A unique query is diagnostic, not guaranteed cache bypass: static cache routing can serve the same old category/article HTML regardless of query while XML correctly bypasses it. Distinguish fresh-only membership from bare canonical acceptance, and do not infer that taxonomy relations or publication failed from a stale archive.
3. Read and back up `WpFastestCacheExclude` and preserve every existing rule. The option is a JSON string of records with `prefix`, `content`, `type`; a narrow rule `{"prefix":"contain","content":"sitemap","type":"page"}` prevents new sitemap page-cache generation. Confirm the installed plugin reads that schema before using it.
4. Canary one authorized domain. Archive only matching sitemap cache directories outside the webroot, with hashes and an immutable option snapshot; do not delete files or broadly clear article/ad caches. Preserve all other cache settings and active monetization.
5. Fetch bare sitemap URLs repeatedly, require every authorized published article in their URL sets, and verify the sitemap cache directories are not recreated. Expand only after canary success.
6. Submit the canonical sitemap index and article sitemap once through Search Console when authorized. GET each exact submitted sitemap and verify path and fresh `lastSubmitted`; `isPending=true` means received/awaiting processing, not indexed.

## Exact approved cache-file execution and recovery

- Treat an approval of an exact file manifest as bounded to those paths and hashes, not all diagnostic URLs or subsequently discovered category caches. Preserve the immutable proposal and create a separate execution record with the human confirmation ID; do not rewrite historical evidence as if approval existed earlier.
- Before deleting any approved file, revalidate native installation identity, non-symlink path, owner, size, mtime, file hash and bare public representation. Back up outside the webroot in a private per-operation directory, verify the backup hash, and run separate XML and HTML canaries. Persist each completed deletion before public validation so a retry cannot replay it.
- Accept only canonical bare-URL readbacks: exact expected sitemap URL membership, localized visible author biography and Person schema, and unchanged native body, media, dates and SEO inputs. Check author visibility at real desktop/mobile viewports; a query parameter is diagnostic, never acceptance. Restore only the approved original path on a failed canary; do not escalate silently into profile, SQL, renderer or global-purge changes.
- Import task helpers by their verified absolute file path under a unique module name. Generic names such as `collect` can resolve to another workflow after a helper modifies `sys.path`; inspect top-level code first because importing a collector can execute a fleet scan and create misleading local failure artifacts. If this happens, retain and explicitly supersede the diagnostic artifacts, reconcile actual remote writes, fix the import, and resume only incomplete stages.
- Distinguish a successful cleanup from recurrence prevention. If `WpFastestCacheExclude` is absent and only post-specific update invalidation is configured, document the coverage gap without declaring the complete root cause proven. A targeted exclusion/configuration change and a new native-trigger test require their own authorized production scope.

## Closure boundaries

Inventory/report any production cache configuration change. Preserve rollback paths, article/content/URL scope, and raw per-URL evidence. Do not silently remove old financial articles, tags, localized routes or metadata to make a niche audit look clean; separate that strategic/editorial decision from safe sitemap repair. Report actual indexed/not-indexed counts and remaining SEO findings. Domain recategorization and advertising-system learning are not proven by organic indexing, and no fixed 30/60/90-day guarantee should be inferred.
