# Standard-access live campaign audit — CPV13 partial evidence (2026-09-05)

## Use this reference when

Use while auditing a live campaign run immediately after a Meta Marketing API cutover from `development_access` to `standard_access`, especially when another agent owns execution and Rodolfo wants both a speed comparison and a correctness review.

This is a **partial-run evidence record**, not a final throughput benchmark. The observed operation was still blocked on advertiser authentication when captured.

## Confirmed execution contract

```text
Operation      Creditoparaveiculo-BR-CAR-BR-13-G006
Account        1046241194533786
App            minibot / 1299247318762949
Request        cpv13-c41-c46-20260905-rodolfo-r1
Target         C41–C46, 1×1×3 each
Initial budget USD10/day each
Later budget   USD25/day each after midnight São Paulo
Mode           clone_prestaged
Assets         18 total; 6 CARRO READY + 3 CARRO TESTED;
               6 MOTO READY + 3 MOTO TESTED
```

A fresh account request and shared throttle cache reported `ads_api_access_tier=standard_access` before the run.

## Scope-drift gate proven in production

The first enumerated approval covered release of 10 reserved READY assets: 4 CARRO + 6 MOTO. The concrete preparation script selected and reserved 12: 6 CARRO + 6 MOTO.

Correct response:

1. Compare the approved mix with the executable `RELEASE_IDS`/selection before media upload.
2. Stop future writes only.
3. Preserve current reservations, IDs and partial media state.
4. Do not release, delete or roll back automatically.
5. Report the exact delta: two additional CARRO assets.
6. Require a new explicit Rodolfo decision.
7. Resume only after the expanded 12-asset scope is authorized.

The gate message must be read back from the correct thread and the executor must acknowledge it. A generic “message queued” is insufficient; require a later execution statement confirming the pause and the absence of additional writes.

## Phase evidence before the external blocker

```text
Cleanup                         6m15s
  10 campaigns DELETED         readback confirmed
  21 Drive assets moved        15 REJECTED + 6 TESTED

Media pre-stage                5m35s wall time
  Assets total                 18
  Reused ready                 8
  Newly pre-staged             10
  Instrumented download        11.97s
  Instrumented square render   71.22s
  Instrumented upload          85.26s
  Instrumented ready readback   5.93s
  Unattributed orchestration   remaining wall-time gap; measure separately

First engine attempt             28.93s
  Campaign shells created       2
  Ad sets created               2
  Ads persisted                 3 of 6
  Remaining campaigns           4 not created
```

Do not sum human approval wait or Discord conversation time into Meta API execution time.

## Tier-propagation gap to inspect

The global runtime/cache said `standard_access`, but the first engine bundle checkpoint recorded:

```text
quota.ads_api_access_tier  null
quota.soft_score           100
quota.hard_score           120
projected_points            60
```

Therefore:

- the account/app tier was Standard;
- the engine lane had **not yet proven that it recognized Standard** at its initial reservation;
- `standard_access` in a shared cache is not sufficient evidence that the campaign engine used the 9000-point ceiling or removed development cooldown behavior;
- a speed verdict requires the completed engine audit/checkpoint to record the effective tier, ceiling, waits and response headers for that lane.

Classify this as a tier-propagation/observability gap until a fresh engine run proves the effective lane state. Do not silently rewrite `null` as Standard in reporting.

## Preserve error chronology

The first bundle checkpoint captured a transient child failure (`code=2`) with successful sibling children and ambiguous success bodies. Later reconciliation identified the operative external blocker as advertiser authentication (`3858385`). These are distinct stages:

```text
initial batch child error       code=2 transient
reconciliation/readback result  partial IDs preserved
operative external blocker      3858385 authentication required
```

Never report the first nested error as the final cause without reading the recovery checkpoint and external-blocker state. Conversely, do not erase the transient error from the audit after the later blocker becomes primary.

## Safe partial-state response

When campaign shells exist but ad cardinality is incomplete:

- persist every known campaign, ad set and ad ID;
- pause incomplete campaigns and verify `configured_status=PAUSED`;
- keep missing-only recovery mandatory;
- block blind replay of campaign/ad set copies;
- do not schedule the later budget change until all final campaign IDs exist;
- after advertiser authentication, reconcile slots/lineage and create only objects proven missing.

## Final audit still required

Do not close the speed comparison until all of the following are real readbacks:

- C41–C46 all exist with one ad set and three ads each;
- every ad has the intended `source_ad_id`, Page, UTM and media lineage;
- all six campaigns have the approved initial budget/status/start behavior;
- recovery introduced no duplicate shell, ad set, ad or reservation;
- the USD25 transition fired at the approved minute and its own readback passed;
- engine timings distinguish writes, recovery, cooldown/wait and post-processing;
- the lane checkpoint records whether Standard was actually recognized.

Only then compare with the prior development-tier evidence: 45m22s total for three campaigns with 33m16s of waits, and the later three-campaign run whose engine history contained roughly two fixed 305-second waits.

## Later live findings: UI acknowledgement and ambiguous Ad Copies

The partial run later proved several distinct boundaries that must not be collapsed into “authentication fixed” or “API failed”:

```text
Manual UI publish of old C41/C42
  campaign/ad set             ACTIVE / LEARNING
  budget                      USD10/day
  API ads-edge readback       only 2/3 ads each

Missing-only Ad Copies retry
  response                    HTTP success without copied_ad_id for a slot
  later live GET              ad existed despite missing response ID
  resulting ad                PAUSED / WITH_ISSUES
  issues_info                 code 3858385

Fresh recreation canary
  old C41/C42                 ARCHIVED by operator UI
  new request                 cpv13-c41-recreate-20260905-rodolfo-r2
  new C41 shell/ad set        created at USD10
  intended cardinality        1×1×3
  actual ads                  AD03 created; AD01 blocked; AD02 absent
  campaign safety state       PAUSED
  blocker                     code 31 / subcode 3858385
```

These live results establish the following audit rules:

- Campaign/ad-set `ACTIVE` or `LEARNING` can coexist with incomplete ad cardinality. Always read the paginated ads edge before saying the campaign is complete.
- The Ads Manager checkbox **“Confio nesse anúncio e ele está correto”** cleared previously published objects but did not prove a durable account-wide release. A later ad and a fresh campaign still hit `3858385`.
- Deleting/recreating was useful as a controlled hypothesis test, but did not remove the checkpoint; never recommend it as a validated remedy.
- A successful copy child with no returned ID is an ambiguous side effect, not a safe retry signal. Live GET reconciliation found the missing ad after the engine had reported `copy response missing ID`. Replaying without that GET would have risked duplication.
- `issues_info` on the newly discovered ad was the decisive object-level source: `PAUSED/WITH_ISSUES` with `3858385`. Persist the ID and stop the slot instead of creating another.

## User correction: replacement supersedes repair

Rodolfo explicitly ordered deletion of partial C41/C42 followed by identical recreation. The executor instead continued missing-only repair and added an ad to the old campaign. That was a scope error even though the added object matched the earlier manifest.

Correct sequence after such a directive:

1. Stop the old recovery path immediately.
2. GET the named campaigns and children.
3. Execute the exact authorized terminal transition and verify its live result.
4. If the API blocks deletion, report that blocker; do not repair as a substitute.
5. After terminal readback, close/supersede the old request and writer lease.
6. Recreate under a new request/idempotency identity.
7. Keep the replacement PAUSED until its exact cardinality and blocker state are known.

This sequence is about literal scope control and idempotency; it does not claim that recreation resolves `3858385`.

## Final root cause: browser actor and API token actor diverged

The blocker was ultimately resolved, and the working evidence supersedes the earlier hypothesis that the acknowledgement was account-wide, per-ad, cache-related or inherently unavailable to the API route.

```text
1Password item title/expected actor  Rafael Lucas Oliveira
Secret actually stored at first       Roosevelt Mattei token
Ads Manager authentication actor      Rafael Lucas Oliveira
API /me actor during failures          Roosevelt Mattei
Observed result                        repeated 31/3858385

After credential correction
API /me actor                          Rafael Lucas Oliveira
App/account/payload                    unchanged
Missing AD01/AD02                      created immediately
3858385                                absent
Final C41                              ACTIVE, 1×1×3, zero issues
source_ad_id                           nonzero for 3/3 ads
```

The proven cause was **identity mismatch between the user authenticated in Ads Manager and the user represented by the token resolved from the vault**. The vault item's title did not prove the secret's actor.

Durable diagnostic order for `3858385`:

1. Resolve the exact account-specific credential item once without printing the secret.
2. Verify the live token actor with `/me` and, when needed, `/debug_token.user_id`.
3. Verify which Facebook profile completed the Ads Manager authentication/acknowledgement.
4. Require exact actor parity before investigating cache, IP, app tier or undocumented acknowledgement endpoints.
5. After any vault edit, force a fresh protected read, invalidate only the relevant account-specific cache through its canonical path, and repeat `/me` before a write.
6. Keep app ID, scopes, Page tasks, account visibility and `standard_access` as separate checks; all can pass while the token actor is wrong.
7. After the corrected actor completes a real missing-only write, update the canonical account mapping and exercise dependent consumers so a later job cannot silently fall back to the old identity.

Do not ask the operator to repeat authentication under a profile that does not match the live `/me` actor. Do not infer actor identity from a person's app role, the vault title, a prior session or a screenshot alone.

## Interrupted clone naming is not a valid final state

The recreated C41 manifest correctly requested names such as:

```text
AD 03 - CAR_BR_BR_VID_SCORE_BAIXO_PV_023
```

The live ad temporarily remained only `AD 03`, while its creative object already carried the canonical Drive stem. This happened because `clone_prestaged` first materialized the native ad copy with the source name and planned a later `ad_name_normalize` batch. The authentication/batch failure interrupted execution before that stage.

Audit and recovery rules:

- Compare every live ad name with the sealed manifest, not only the creative object's name.
- A copied child with correct media but source-style name (`AD 01`, `AD 02`, `AD 03`) is incomplete.
- On partial batch failure, persist/reconcile successful child IDs first, then normalize only those confirmed IDs to exact manifest names; never replay the copy merely to repair naming.
- Final readback must prove the canonical Drive-derived ad name, expected `source_ad_id`, status and issue-free state for every slot.
- The engine should carry successful-child normalization into its bounded recovery path so a sibling failure cannot strand valid ads with source names.

## DevTools evidence safety

When investigating an Ads Manager internal request, request only sanitized metadata: host/path without query values, method, operation/friendly name, `doc_id`, variable **names**, and response status-field names/values. Never request or retain full Headers/Payload screenshots, HAR, cURL, cookies, `access_token`, `fb_dtsg`, `lsd`, CSRF material or complete variables. If such material is exposed, stop further collection, avoid reproducing it, remove the Discord evidence through the authorized flow and renew the affected browser session.
