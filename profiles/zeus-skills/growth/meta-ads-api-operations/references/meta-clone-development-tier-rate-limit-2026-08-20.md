# Meta campaign cloning under development-tier rate limits (2026-08-20)

## Trigger

Use when campaign creation or native copy returns `OAuthException code=17`, `error_subcode=2446079`, or when `X-Ad-Account-Usage` / `X-Business-Use-Case-Usage` reports `ads_api_access_tier=development_access`.

## Confirmed root-cause test

1. Read the live response headers; do not infer the tier from scopes or token validity.
2. Record both limit families separately:
   - `X-Ad-Account-Usage`: `acc_id_util_pct`, `reset_time_duration`, `ads_api_access_tier`.
   - `X-Business-Use-Case-Usage`: `call_count`, `total_cputime`, `total_time`, `estimated_time_to_regain_access`.
3. Match the exact error. Meta documents `17/2446079` as the ad-account API-level score limit.
4. Project the plan before write. Meta states reads generally cost 1 point and writes 3; development tier has a maximum score of 60, while Full Access has 9,000.
5. Treat a plan as incompatible when the projected score already exceeds the tier ceiling before final readback.

Official source: https://developers.facebook.com/docs/marketing-api/overview/rate-limiting/

## MGS failure reconstructed

The Creditoparaveiculo daily runner attempted two 1x1x3 campaigns in one window. Its Ads Management path contained:

```text
10 mutation validate_only calls
16 real Ads Management mutations
26 mutation calls projected at 3 points each
78 projected points before final readback
60-point development-tier ceiling
```

The final batch GET then returned `17/2446079`. `X-Business-Use-Case-Usage` was only 34% on a later successful response, which did not disprove the failure: the helper was not parsing `X-Ad-Account-Usage`, the header carrying the ad-account score/reset/tier.

## Correct operating order

### 1. Structural fix: Marketing API Full Access

Limited/development access is documented as development-only and not for production advertisers. Upgrade the app that issued the User Access Token to Marketing API Access Tier Full Access. The current qualification is at least 500 Marketing API calls in 15 days and under 15% errors in the last 500 calls. Validate success only when a live response says `ads_api_access_tier=standard_access`.

This does not require a Meta System User. MGS continues to use a valid user/app-token route unless Rodolfo explicitly reopens System User scope.

Official source: https://developers.facebook.com/docs/marketing-api/access/

### 2. Quota-aware runner

- Parse and persist `X-Ad-Account-Usage` on every normal response; never add a request just to inspect quota.
- Keep ad-account score and BUC usage as independent gates.
- Budget reads and mutations before write.
- On `17/2446079`, preserve PAUSED objects, mark readback deferred, and resume after `reset_time_duration`; if absent, use the documented 300-second development-tier block.
- Do not clean up structurally valid PAUSED objects solely because the final GET was throttled.
- Move heavy current+archived reconciliation outside the mutation window; use a TTL snapshot plus a bounded delta preflight.

### 3. Native clone: asynchronous deep copy

Use `POST /{campaign_id}/copies` with `deep_copy=true` and `status_option=PAUSED`. Meta permits up to 3 child ads synchronously and 51 asynchronously. For sources above the synchronous threshold, put the copies operation in `/{ad_account_id}/async_batch_requests`, poll the request set with bounded backoff, then use the returned source-to-copy ID map for precise patches and readback.

Official sources:

- https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group/copies/
- https://developers.facebook.com/docs/graph-api/asynchronous-batch-requests/

### 4. Development-tier fallback

While the live header remains `development_access`:

- create one campaign per five-minute window, never two at once;
- pre-upload and cache video IDs by asset checksum outside the campaign mutation window;
- avoid repeated per-ad `validate_only` when the exact payload version already passed a bounded canary;
- fail before the first write if the projected score plus readback reserve exceeds 60.

## Batch pitfall

Standard Graph batch reduces HTTP round-trips but each child operation still counts separately toward call and resource limits. Async batch solves object-count limits and dependency orchestration; it is not a quota bypass.

Official source: https://developers.facebook.com/docs/graph-api/making-multiple-requests/

## Verification

- Live tier header is captured and sanitized.
- Projected score fits the current tier with readback reserve.
- New objects remain PAUSED until full hierarchy validation.
- `17/2446079` causes deferred readback, not immediate cleanup.
- Async copy returns completed request-set state plus copied ID mapping.
- Source and clone hierarchy, budget, start time, attribution, statuses, assets, URLs and UTMs pass GET readback.
