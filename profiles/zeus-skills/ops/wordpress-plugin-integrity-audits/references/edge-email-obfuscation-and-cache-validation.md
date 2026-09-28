# Edge email obfuscation and cache validation

Use this branch when the origin contains a normal email/`mailto:` but the public edge injects `/cdn-cgi/l/email-protection`, `email-decode.min.js`, or a visibly broken protected address.

## Procedure

1. **Attribute the transformation.** Download complete HTML from the bare public URL, a unique-query public URL, and the origin via `curl --resolve`. Count `mailto:`, `/cdn-cgi/l/email-protection`, `email-decode.min.js`, and the visible address separately. Do not infer from a truncated body.
2. **Separate application from edge.** If the origin contains the normal address/link and only the edge contains Cloudflare markup, classify Email Address Obfuscation as the transformer. Do not rewrite the database, install another decoder, or blame the theme.
3. **Prefer a localized bypass.** Wrap the complete fragment containing both visible text and its `mailto:` anchor in `<!--email_off-->...<!--/email_off-->`. Protect both parts; wrapping only one can leave a partial transformation. Disable the zone-wide feature only when that broader scope is explicitly intended and confirmed.
4. **Clear every HTML cache layer.** Flush the WordPress page cache first. Purge the affected edge URL only when edge HTML is cached. A Cloudflare purge cannot repair a stale origin full-page cache.
5. **Validate what users receive.** Recheck the public URL without a query string and the origin. Require a legible address, a functional `mailto:`, zero `/cdn-cgi/l/email-protection`, zero `email-decode.min.js`, and no new console/network failure in a rendered browser.

## Header/cache corollary

A query-busted PHP response does not prove the bare URL has the same headers. Static W3TC/Nginx page-cache delivery can bypass WordPress `send_headers` hooks. Compare bare public, query-busted public, and origin headers; if only dynamic responses carry the policy, fix the cache/server layer under its system-config authorization rather than repeating the PHP hook.

## Closure evidence

Record origin and edge counts, cache status, the exact localized fragment or zone-setting diff, public no-query browser result, and rollback. Preserve the raw crawler result but classify protected/control endpoints and redirect aliases before declaring an actionable issue total.
