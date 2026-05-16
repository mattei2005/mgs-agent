# WP REST curl hardening pattern

Use this when editing `skills/content-publish-wordpress/scripts/*` or any WordPress REST shell helper that captures HTTP status with curl.

## Problem

The old pattern was:

```bash
http=$(wp_curl_auth "$user" "$pass" -sS -o "$tmp" -w '%{http_code}' URL || echo "000")
```

This preserves transport failures as `000`, but can produce ambiguous output when curl fails on HTTP errors after adding `--fail`/`--fail-with-body` (`404` plus fallback `000`, or caller-specific false-success handling). It also leaves timeout/retry policy duplicated across scripts.

## Preferred pattern

Centralize status handling in `wp-curl-auth.sh`:

```bash
http=$(wp_curl_auth_http "$tmp" "$user" "$pass" \
  -H "Content-Type: application/json" \
  -X POST --data-binary "@$payload" \
  "$wp/wp-json/wp/v2/posts")
```

`wp_curl_auth_http` should:

- keep credentials out of argv via `curl -K` tempfile with mode `600`;
- use `--fail-with-body` so HTTP 4xx/5xx are treated as failures while preserving the JSON body in `$tmp`;
- return exactly one HTTP code on stdout;
- return real HTTP codes for server/client errors (`400`, `401`, `404`, `500` etc.);
- return `000` only for transport-level failures with no HTTP response;
- include bounded timeout/retry defaults:
  - `WP_CURL_CONNECT_TIMEOUT:-15`
  - `WP_CURL_MAX_TIME:-90`
  - `WP_CURL_RETRY:-2`
  - `WP_CURL_RETRY_DELAY:-1`
  - `--retry-connrefused`

## Validation recipe

Before declaring success:

```bash
bash -n skills/content-publish-wordpress/scripts/*.sh

grep -R "wp_curl_auth .* -sS -o" -n skills/content-publish-wordpress/scripts
# expected: no status-capturing legacy calls outside wp-curl-auth internals
```

Use a fake `curl` early in `PATH` to test three cases without touching production WordPress:

```text
HTTP 200        -> returns 200 and preserves body
HTTP 404/500    -> returns real code and preserves body
network failure -> returns 000
```

Do not run a real create/update/delete against production WP just to validate the wrapper unless Rodolfo explicitly asks; use syntax and fake-curl probes first.
