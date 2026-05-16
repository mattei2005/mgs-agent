# WP REST curl wrapper hardening

Use this when changing scripts under `skills/content-publish-wordpress/scripts/` that call WordPress REST with Basic auth.

## Problem

Plain `curl -sS -o "$tmp" -w '%{http_code}' ... || echo "000"` can blur two different cases:

- HTTP 4xx/5xx from WordPress, where the REST body is useful and the HTTP code should be preserved.
- Transport failure, where there is no reliable HTTP code and `000` is appropriate.

If `curl --fail` is added naively, curl exits 22 on HTTP errors and callers may append fallback `000`, causing ambiguous output or hiding the real HTTP code.

## Preferred pattern

Centralize status handling in `wp-curl-auth.sh` with a helper like `wp_curl_auth_http`:

```bash
http=$(wp_curl_auth_http "$tmp" "$user" "$pass" \
  -H "Content-Type: application/json" \
  -X POST --data-binary "@$POST_JSON" \
  "$wp/wp-json/wp/v2/posts")
resp=$(cat "$tmp")
rm -f "$tmp"

if [ "${http:0:1}" != "2" ]; then
  echo "ERROR: WP REST HTTP $http: $(echo "$resp" | head -c 500)" >&2
  exit 1
fi
```

Helper behavior:

- Still calls `wp_curl_auth` so credentials remain in a `curl -K` tempfile with mode 600, not visible in argv.
- Adds `--fail-with-body` to preserve REST error body on 4xx/5xx.
- Adds bounded `--connect-timeout`, `--max-time`, `--retry`, `--retry-delay`, `--retry-connrefused`.
- Returns the real 3-digit HTTP code when curl got one.
- Returns `000` only for transport failures with no HTTP code.
- Always returns shell status 0 so caller logic branches on `http`, not curl rc.

## Validation checklist

Before reporting success:

1. `bash -n skills/content-publish-wordpress/scripts/*.sh`
2. Fake-curl test for:
   - HTTP 200 with body preserved
   - HTTP 404 with body preserved and `http=404`
   - network failure with `http=000`
3. Grep for old status-style calls:
   ```bash
   grep -R "wp_curl_auth .* -sS -o" -n skills/content-publish-wordpress/scripts
   ```
   Expected: no remaining callers except implementation/comments if intentionally retained.

## Pitfalls

- Do not print WordPress Application Passwords in logs or chat. Log only site key, endpoint class, HTTP code, and response head.
- Do not replace the `curl -K` credential approach with `-u user:pass`; that exposes credentials in process argv.
- Do not make HTTP 4xx/5xx become `000`; downstream diagnostics need the real REST status and body.
