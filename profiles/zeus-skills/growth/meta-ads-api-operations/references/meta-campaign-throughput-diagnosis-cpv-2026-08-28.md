# Meta campaign throughput diagnosis — CPV live test 2026-08-28

## Use this reference when

Use after a campaign batch completes correctly but takes far longer than the operator benchmark, especially when someone says another app has the “same permissions.” Diagnose measured wall time, access tier, engine-enforced waits and workload shape separately before proposing another live test.

## Live evidence from the CPV C36–C38 test

The authorized run created three campaigns, one ad set and three ads per campaign with new Drive assets. Integrity passed, but wall time was unacceptable:

```text
Total                              45m22s
Cooldowns/esperas                  33m16s  (73.3%)
Preflight + preparation             5m20s
Effective execution                 6m46s
Observed time without waits        12m06s
```

The initial media pre-stage consumed about 3m27s. It was material, but not the cause of a 45-minute run.

The decisive read-only Meta probe returned HTTP 200 and `X-Business-Use-Case-Usage.ads_api_access_tier=development_access`. Historical App Dashboard evidence showed `Marketing API Access Tier: Limited access` while required ad/Page permission scopes were present. Therefore authentication and scope coverage were healthy; high-volume capacity was not.

## Critical distinction: permission scopes are not access tier

Treat these as independent gates:

```text
Permission scopes/access     ads_management, ads_read, pages_manage_ads, etc.
Marketing API access tier    Limited/development vs Full/standard
Asset assignment             actual account/Page/business access
Token validity               user/app authentication and expiry
```

Two apps can expose the same permission names while having different throughput because their Marketing API access tiers differ. Never infer a peer operator’s tier from “same permissions”; require its App Dashboard tier or a live usage header. No System User is required merely to promote the Marketing API tier.

## Engine-side amplification confirmed

The guarded runtime reserved 30 logical points per campaign. Two campaigns filled the local 60-point development lane and triggered a static 305-second cooldown.

Transient `OAuthException code=2` failures amplified the wait:

```text
First bundle   2 missing ads + 6 ad normalizations = 8 recovery mutations
Second bundle  1 missing ad  + 3 ad normalizations = 4 recovery mutations
```

Each recovery write forced a fresh 305-second wait. A subsequent consolidated readback received `code=17/subcode=2446079`. A concurrent Intraday reader then delayed a later resume. Reader exclusion during a persisted resumable request prevents that contention, but it does not remove the underlying development-tier cooldown.

The transport returned any failed batch child as `BatchTransportError`; it had no bounded per-child transient retry. Safe optimization must still preserve successful child IDs and reconcile ambiguous children before retrying—never blindly replay a write.

## Benchmark math

For the current two-campaign bundle and 305-second forced cooldown shape, 40 campaigns cannot match a 15–20 minute benchmark:

```text
40 campaigns / 3 accounts   largest lane = 7 bundles   35m35s forced-wait floor
40 campaigns / 2 accounts   largest lane = 10 bundles  50m50s forced-wait floor
```

This is only the engine-enforced wait floor; it excludes API latency, media preparation and recovery. A 40-campaign comparison is meaningful only when workload, media readiness, access tier and number of independent account lanes match.

## Correct remediation order

1. Promote the MGS-controlled app’s Marketing API Access Tier from Limited to Full as applicable in the Meta dashboard; validate with a fresh live header showing `standard_access` before changing local safeguards.
2. Make cooldown behavior tier-aware. `development_access` keeps the conservative 300/305-second fallback. `standard_access` uses live utilization/reset headers and must not inherit a fixed development cooldown.
3. Do not raise the local hard score from 60 to 120 without server-side evidence. A larger client constant removes protection; it does not increase Meta capacity.
4. Preserve every successful child ID immediately. For `code=2`, perform a targeted lineage/slot readback after a short bounded backoff, then retry only children proven missing. Treat ambiguous writes as readback-required.
5. Normalize names/status only when live state differs. Do not update every existing ad during missing-only recovery.
6. Move media preparation upstream: when assets enter READY, render derivatives, upload through the ad-account `advideos` edge, wait for ready state and commit the registry. The campaign hot path should consume ready IDs.
7. Execute independent `app_key + ad_account_id` lanes concurrently; do not use a global lock across accounts.
8. Canary in increasing order: 1 campaign, 3 campaigns, 10 campaigns, then an explicitly authorized 40-campaign multi-account benchmark. Compare p50/p95 per lane and total wall time.

## Operational targets

Use these as acceptance targets derived from the observed run, not promises:

```text
3 campaigns, fresh media       <=12–15m after tier/cooldown correction
3 campaigns, media pre-staged   approximately 5–10m target
40 campaigns / 3 accounts       15–20m only after matched-workload canaries prove it
```

## Audit and reporting checks

- Report wall time as preparation, effective execution and engine/API waits; do not label Discord conversation time as API execution time.
- Separate measured evidence from projections and peer claims.
- Verify skill, executor constant, config release metadata and operation source all report the same release. Version drift does not explain latency by itself, but it indicates incomplete rollout bookkeeping.
- Do not run another production benchmark merely to reconfirm a known development-tier wait floor.
