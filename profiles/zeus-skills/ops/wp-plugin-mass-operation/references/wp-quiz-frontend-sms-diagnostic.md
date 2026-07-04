# WordPress quiz frontend SMS diagnostic

Use when a business operator reports: “I filled the quiz, but the lead did not appear in SMS Funnel.” Endpoint-only tests are not enough for this complaint; reproduce the same public UI path the operator used.

## Test levels — name which one you ran

1. **Vendor API direct** — posts directly to SMS Funnel. Useful only to prove the vendor endpoint is alive.
2. **WordPress REST endpoint** — posts to `/wp-json/mgs-quiz/v1/lead`. Proves WP saves + forwards server-side.
3. **Full browser/frontend flow** — opens the public quiz URL with UTMs, clicks an answer, fills name/phone, submits the form button, then verifies redirect and DB status. This is the decisive test for “when I fill the quiz.”

## Required frontend diagnostic flow

For each quiz route:

1. Open the public URL with explicit UTM medium for that gestor, e.g. `?utm_source=zeus-browser&utm_medium=g003-s&utm_campaign=frontend-diagnostic-YYYYMMDD`.
2. Click one answer option.
3. Fill a unique test name like `Zeus Browser G003` and a unique phone.
4. Click the form submit button.
5. Confirm the page redirects to the configured REC URL.
6. Query the WordPress lead table by the diagnostic campaign/name.
7. Verify:
   - `quiz_slug` is the expected route;
   - `utm_medium` carries the gestor code;
   - `sms_funnel_status` starts with `ok:G00X`;
   - `sms_funnel_response` contains `success:true`;
   - response `list_id` matches the configured SMS Funnel list for that gestor.

## Interpreting results

- If browser submission returns `ok:G00X` and the stored SMS Funnel response has `success:true` + correct `list_id`, the WordPress/frontend/backend path is working.
- If the SMS Funnel dashboard still shows zero, suspect vendor dashboard indexing/cache/filter/deduplication before changing WP code.
- Ask the operator to search the exact unique test lead name in SMS Funnel; list counters can lag behind accepted API writes.

## UI lesson: redirect split

Do not expose split redirect as raw `redirect_variants` JSON to business operators. Render a Lovable-style editor:

- heading: `URLs de redirecionamento (split de tráfego)`;
- button: `+ Adicionar URL`;
- each row: URL input + numeric weight input + optional `Remover`;
- helper: show distribution text such as `Padrão 50% · URL 2 50%`;
- preserve UTMs/`fbclid`/`gclid` on the final redirect.

Backward-compatible save pattern:

- row 1 → `redirect_url` + `redirect_url_weight`;
- rows 2+ → JSON array in `redirect_variants`.
