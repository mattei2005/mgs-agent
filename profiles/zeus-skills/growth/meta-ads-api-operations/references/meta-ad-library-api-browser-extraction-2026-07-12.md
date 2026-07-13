# Meta Ad Library API vs browser payload extraction — 2026-07-12

## Operational question

Assess whether the official Meta Ad Library API makes it easier to enumerate advertiser Pages, domains, and downloadable creatives for Brazilian commercial ads found by keyword/domain searches.

## Authoritative API behavior observed

Current Ad Library documentation states:

- Worldwide API coverage is available for social-issue, election, and political ads for the past seven years.
- Ads of any type are available when delivered to the UK or EU during the past year.
- For all currently running ads across Meta technologies, Meta directs users to the normal Ad Library interface.
- Useful filters include `search_page_ids` (up to 10), `search_terms`, country, dates, platform, and `media_type` (`IMAGE`, `VIDEO`, etc.).
- Useful result fields include Library ID, `page_id`, `page_name`, dates, creative text/title/caption/description, and `ad_snapshot_url`.
- `ad_snapshot_url` displays archived, uncompressed creative media, but the API does not provide bulk archived-ad downloads. Individual creative download is subject to analysis/storage terms.

Practical conclusion: the API is a structured discovery/catalogue layer, not a direct bulk JPG/MP4 endpoint. For ordinary Brazilian commercial ads, its coverage is materially weaker than the public Ad Library UI.

## Token authorization probe

Two existing valid MGS Meta user tokens were tested read-only against Graph `v25.0`:

- Both returned granted Marketing API permissions including `ads_read`.
- Both returned the same `GET /ads_archive` rejection:
  - HTTP 400
  - `OAuthException`
  - code `10`
  - subcode `2332002`
  - `Application does not have permission for this action`

Durable interpretation: `ads_read` and a valid Marketing API token do not imply Ad Library API authorization. The Facebook identity/app must be separately eligible/authorized for Ad Library API access. Never rotate or replace a working Marketing API token merely because `/ads_archive` returns this boundary.

Safe probe shape:

1. Resolve exactly one token internally from 1Password; never print it.
2. Call `/me/permissions` and report only permission names/statuses.
3. Call `/v25.0/ads_archive` with a small read-only query.
4. Print only HTTP status, safe error fields, counts, Page IDs, and Page names. Do not print `ad_snapshot_url`, because it may contain an access token.

## Browser payload extraction for Brazilian commercial ads

For a normal Ad Library keyword URL, the rendered page contains serialized search data in the HTML. The useful fields include:

- `search_results_connection.count`
- `ad_archive_id`
- `collation_count`
- `page_id`
- `snapshot.page_name`
- `snapshot.page_profile_uri`
- `snapshot.link_url`
- creative display format and media URLs

Important distinction:

- The numeric identifier in `page_id` is the operational Page ID used for Ad Library/API queries.
- A `page_profile_uri` may contain a different Facebook profile URL identifier beginning with `615...`; do not report that URL identifier as the Page ID.

Proven extraction sequence:

1. Open the exact Ad Library keyword/domain URL in a real browser.
2. Wait for the rendered results.
3. Inspect the serialized HTML payload, not only visible cards. Visible results can be collated/grouped.
4. Deduplicate by `page_id`; join `snapshot.page_name` and `snapshot.page_profile_uri` only for context.
5. To inventory each Page, open a Page-specific Ad Library URL with `view_all_page_id=<page_id>` and the same country/active filters.
6. Parse every `snapshot.link_url` hostname.
7. Also recursively inspect destination URLs embedded in query parameters such as `url=https://...`; otherwise redirect/quiz architectures undercount domains.
8. Report both:
   - unique registrable/root domains;
   - unique hostnames/subdomains.

Session validation for the `finctime.com.br` keyword search found five unique Pages in the payload. The active Page-specific links used one registrable domain (`finctime.com.br`) and two hostnames (`quiz.finctime.com.br` as click entry and `es.finctime.com.br` as nested destination).

## Pitfalls

- Do not equate the search result count with visible card count; Meta collates multiple ads/versions into summary cards.
- Do not assume a valid `ads_read` token can call `ads_archive`.
- Do not describe the official API as a bulk creative downloader.
- Do not claim Brazilian commercial coverage from API documentation that limits non-political global availability.
- Do not print raw snapshot URLs or Graph paging URLs when they may embed access tokens.
- Browser payload fields are internal and can change; validate field presence on every run and fail honestly if the structure changes.
