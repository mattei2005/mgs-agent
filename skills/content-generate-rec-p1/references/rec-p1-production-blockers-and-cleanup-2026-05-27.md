# REC+P1 production blockers and cleanup lessons — 2026-05-27

## Why this reference exists

During the first live post-refactor REC+P1 publish, the operation succeeded mechanically but Rodolfo identified two production-quality failures:

1. The requested card name and official URL were inconsistent.
   - Requested: `Nationwide Balance Transfer Credit Card`
   - Supplied URL: `/purchase-credit-card/`
   - Correct URL: `/balance-transfer-credit-card/`
   - Lesson: even if the user supplied the URL, the runner/orchestrator must detect obvious card ↔ official URL mismatch and stop before publishing.

2. The manual card image was invalid/low-quality, and automatic fallback selected an unsuitable card image.
   - Lesson: for `publish`, do not continue with automatic fallback if the supplied image fails or the exact card image cannot be verified.
   - Correct behavior: stop, report the image blocker in the thread, ask Raquel/Rodolfo for a corrected image URL, and resume only after a new approved image is supplied.

A third technical cleanup was also identified:

3. `mgs-rec-api` was a legacy FastAPI path tied to the old Anthropic-era generation route and is intentionally masked/inactive. REC runner should not attempt it or emit noisy `article_api_unavailable_local_generator_used` warnings; use the approved local deterministic generation path from current official facts instead.

## Durable production rules

### 1. Official URL/card mismatch is a preflight blocker

Before REC+P1 publish, compare requested card terms against the official URL path/title. If the URL appears to advertise a different product type, stop.

Examples:

```text
Card: Nationwide Balance Transfer Credit Card
URL:  /purchase-credit-card/
Result: BLOCK — URL path contains purchase but requested card does not.
```

Do not treat this as user intent. Ask for the corrected official URL.

### 2. Card image is a hard gate for publish

For `status=publish`, an approved card image URL is required. If the manual image is low-quality, wrong product, debit instead of credit, vertical, cropped badly, or otherwise not confidently the requested card:

```text
STOP
Do not publish REC
Do not start P1
Ask Raquel/Rodolfo for a corrected image URL
```

Automatic image search can be useful for draft/debugging, but not as silent production fallback after a manual image failed.

### 3. Cleanup after bad publish

If a bad publish occurred, cleanup should remove the complete operation footprint:

```text
- move/trash the REC post
- move/trash the P1 post
- delete media created by that operation
- remove any fingerprint/similarity record created for the bad REC
- do not delete technical caches such as wp-term-cache.json
```

Because this is destructive production cleanup, ask for explicit confirmation with post IDs/media IDs before executing.

Implementation notes from Eggbev cleanup:

```text
- Python requests with resolved app-password may return 401 for delete/update even when create-post works.
- Prefer the existing WordPress helper auth path for destructive cleanup:
  source skills/content-publish-wordpress/scripts/wp-curl-auth.sh
  resolve-credentials.sh <site>
  wp_curl_auth_http ... -X DELETE "$wp/wp-json/wp/v2/posts/<id>?force=true"
  wp_curl_auth_http ... -X DELETE "$wp/wp-json/wp/v2/media/<id>?force=true"
- Delete/trash posts first, then media.
- Verify media through REST returns 404.
- Verify bad fingerprint rows are 0.
- If normal public URLs still return 200 but `Cache-Control: no-cache` or querystring returns 404, WordPress origin is clean and Cloudflare APO edge is serving stale HIT. Report this separately as external cache/purge pending; do not claim origin cleanup failed.
```

### 4. mgs-rec-api legacy behavior

`mgs-rec-api` should be treated as legacy and intentionally disabled. Do not restart it during REC/P1 production unless Rodolfo explicitly approves reintroducing/rebuilding that service under the current GPT-5.5/OpenAI-Codex policy.

Expected REC behavior:

```text
current official facts + explicit request facts
→ deterministic local REC generation
→ validators/QA
→ publish only if all gates pass
```

No Anthropic-era API call and no noisy fallback warning.

## Reporting expectation

If a blocker occurs, report the exact blocker and stop. Do not summarize the run as a success with a caveat if the blocker affected source identity or card image identity.
