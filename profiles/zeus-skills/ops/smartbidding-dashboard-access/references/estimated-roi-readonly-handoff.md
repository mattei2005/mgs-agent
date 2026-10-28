# ROI estimado — bounded read-only projection and Ares handoff

Use only for an explicitly justified scoped current-day ROI_ESTIMATED dependency. Ares owns recovery and communication in the original thread; do not turn403 into a routine Zeus export or a new thread. An authentic handoff can authorize technical investigation under the historical delegation, but does not prove the handoff was the correct operational route. Validate sender, original human request and checkpoint before collecting. Keep Zeus credentials in Zeus; never move an alternate token into Ares or change grants to work around403.

Before projecting data through another identity, diagnose the Ares access layer using its own existing credential and bounded reads. `GET /user/validate` can return HTTP200 while a scoped report returns403: inspect only the exact authorized company's presence and relevant read permissions; never print/save unrelated companies or raw user records. Auth0 `publisher` permission and local catalog ALLOWED are not evidence of the live SB company grant. If that grant is absent, report the proved layer mismatch and request the required explicit confirmation for a narrow permission change, rather than claiming a login refresh or another agent's export repaired Ares access.

After a human updates the SB user, revalidate with Ares' own credential through both `/user/validate` and the actual canonical report client for every approved publisher. Provider HTTP201 alone is not full recovery: `_validate_sb_response` may still reject Facebook CUSTOMER_ID values absent from the separate Meta-account registry. Diagnose that layer without logging unknown account IDs or rows, preserve the guard, and resolve the authorization boundary before changing it. Do not treat an SB site grant as a silent Meta-account grant, or claim the client is usable when its response validator still blocks it.

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
