# Meta Ads account-wide UTM audit

## Trigger

Use this procedure when Rodolfo asks whether any current ad in a specific Meta ad account contains an exact UTM value such as `utm_medium=g002-d`.

## Read-only workflow

1. Validate account visibility with the normal Ares user/app token route and a GET of `act_{account_id}`. Confirm the returned account ID and name before interpreting results.
2. Read `act_{account_id}/ads` with at least:
   - `id,name,status,effective_status`
   - `campaign{id,name}`
   - `adset{id,name}`
   - `creative{id,name,url_tags,object_story_spec,asset_feed_spec,effective_object_story_id}`
3. Request `summary=true`, paginate with `paging.cursors.after`, and stop only when no cursor remains.
4. Assert `ads_scanned == summary.total_count`. If they differ, do not declare a complete account audit; retry or report incomplete coverage.
5. Recursively inspect every string under the creative object. Destination and tracking values may live in `object_story_spec`, `asset_feed_spec`, nested CTA/link fields, or `url_tags`.
6. Decode URL-encoded values with bounded repeated `urllib.parse.unquote_plus` passes (maximum five) so nested redirect/query strings are inspected without an unbounded loop.
7. Match the requested parameter exactly and case-insensitively with query boundaries. For example, require `utm_medium=g002-d` as a complete value, not merely a loose `g002-d` substring. Run a raw substring check as secondary evidence for unexpected encodings.
8. Independently enumerate all observed `utm_medium` values and count both ads and occurrences. This makes a zero-match conclusion auditable—for example, proving that every scanned ad used `g002-s` rather than only saying `g002-d` was absent.
9. Report matching ad ID/name, effective status, campaign, ad set, creative ID, field path, and sanitized destination value. Never output access tokens or token-bearing Graph paging URLs.

## Interpretation and scope

- Describe the result as the **current ad inventory returned by the Meta Ads edge**. Deleted objects may be omitted by Meta and must not be implied as covered unless explicitly queried through a supported deleted-object route.
- Date filters present in an Ads Manager reporting URL do not limit this structural creative-link audit unless Rodolfo explicitly asks for ads delivered during that period.
- If every returned ad has an embedded creative specification or tracking field, state that coverage. If some ads expose only `effective_object_story_id`, resolve those story attachments separately before declaring no match.
- This is read-only. Do not rewrite links or creatives unless Rodolfo separately requests the write and its normal authorization gates are satisfied.

## Validated example — 2026-09-01

For account `1753257812779707`, the live paginated audit returned and reconciled 141/141 ads across three pages. All 141 exposed candidate link/tracking fields. Exact and raw checks found zero `g002-d` values; the observed `utm_medium` inventory was `g002-s` on all 141 ads. No Meta objects were changed.
