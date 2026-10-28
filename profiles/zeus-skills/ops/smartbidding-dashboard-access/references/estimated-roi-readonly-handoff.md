# ROI estimado — bounded read-only projection and Ares handoff

Use for a scoped current-day ROI_ESTIMATED dependency. Validate authentic Ares sender, original human request and checkpoint before collecting. Keep Zeus credentials in Zeus; never move an alternate token into Ares or change grants to work around403.

## Collection

- Resolve exact approved publishers, currency and ISO dates. Use Zeus canonical headed/Xvfb session, session lease and governed browser budget. Suppress unsolicited SPA API requests; authenticated direct requests remain in memory. Do not fetch a global company catalog when the exact authorized identities are already resolved.
- POST `/report/performance_per_campaigns` with `initialDate`, `finalDate`, `currency`, `publishers:[exact_id]`; project scalar identity/UTM fields and `INVESTIMENT`, `REVENUE`, `NET_REVENUE`, `REVENUE_ESTIMATED`, `CDP_IMPRESSIONS`, `GAM_CODE_SERVED_COUNT`. Enforce exact DATE/PUBLISHER/DOMAIN; count and exclude spillover before saving.
- GET `/report/performance_per_domain` using identical dates/currency plus `publishers[]=exact_id` (Axios array query convention). This is the Domain UI source. Validate identities/date independently. Do not silently replace Campaigns totals with Domain totals: coverage, attribution, rounding or collection times can differ, and the actual cause requires proof.
- POST `/estimated/delay` separately per publisher with `publisherIds:[exact_id]`, currency. Preserve collection time, totalMinutes and currentFillTime. Zero minutes with null fill time is inconclusive freshness, not proof of no delay.

## Live column semantics

Discover current public frontend asset paths from the app's script/import graph; never freeze hashed bundle filenames as permanent endpoints. Public `fields-*.js` and Domain definitions expose `ROI_ESTIMATED = INVESTIMENT ? 100*(REVENUE_ESTIMATED-INVESTIMENT)/INVESTIMENT : null`. Acquisition imports its metrics from that field graph. Save short exact code evidence/URL, not full authenticated page/runtime responses.

The `Discount revenue share` switch defaults true and maps realized REVENUE to NET_REVENUE; the native REVENUE_ESTIMATED field is not multiplied by another share factor by this column. Reproduce the live estimated column from its native estimate without applying an extra0.90. A row-level NET_REVENUE/REVENUE ratio is empirical evidence, not independent proof of the backend estimate's gross/net composition or a commercial contract. Label that remaining uncertainty explicitly; do not invent an estimate formula from CDP/GAM ratios.

## Grain, acceptance and delivery

- Inspect DATE/PUBLISHER/UTM_ADGROUP groups and CUSTOMER_ID/CAMPAIGN_ID/ADGROUP_ID collisions. Revenue and site counters must be counted once per tracking group/day when repeated across ads; sum only true native delivery spend. Fail closed on varying revenue or cross-identity collisions rather than selecting a max/first blindly.
- A report can already be one row per tracking group with empty AD_NAME and no AD_ID. Preserve exact supplied IDs/names/UTM, record unavailable ad identity, and never claim ad-level coverage. No duplication today does not establish that every future response has this grain.
- Keep unattributed rows/monetization separate from named campaign totals and ranking. Do not turn zero-investment or missing rows into0% ROI; return unavailable.
- Validate via Decimal totals, no-duplicate fixture and conflicting-revenue negative fixture; enforce exact publisher set/dates/currency and a credential-free allowlist. Freeze projection + validation file, generate SHA256 in shell, then deliver paths/hash/timestamps/status to the original thread with an explicit Ares-only mention and read back the exact Discord target.
- Technical projection ready is not the original performance analysis complete. Ares retains analysis and functional closure; do not close its pending request or substitute yesterday's data.
