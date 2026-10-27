# Meta native clone vs rebuild — standard_enhancements pitfall (2026-06-18)

## Context

Rodolfo corrected the operating assumption for Ares replacement campaigns: for the MGS Meta workflow, the target route is **clone existing ads/campaigns**, not create campaigns/ads from zero. Creating from zero can hit Meta account/app/page/authentication checkpoints and is outside the intended flow. System User is also explicitly out of scope for Rodolfo unless he reopens that path.

## Evidence from the thread

Thread: `1517244349891608607` (`Status Operacional do Ares - Rodolfo`).

Observed sequence:

- New token was valid for read/dry-run.
- Manual/rebuild route could create some objects (`campaign`, sometimes `adset`, sometimes `adcreative`) but failed at page permission or `POST /ads` checkpoint.
- Native clone/copy route was then tested and revealed a different blocker:
  - `code=100`
  - `error_subcode=3858504`
  - Spanish title: `El anuncio no debe incluir mejoras estándar`
  - Meaning: source ad includes legacy/obsolete `standard_enhancements`; Meta wants individual creative feature controls instead.

## Durable lesson

Do not collapse these into one diagnosis:

```text
Route                         Meaning
----------------------------- --------------------------------------------
Create from zero / rebuild    Wrong primary path for MGS replacement clones
Native Meta copy/clone         Correct primary path to pursue
Manual rebuild                Fallback/diagnostic only, not success criterion
System User                   Out of Rodolfo's scope
```

If native clone fails with `standard_enhancements`, the blocker is likely the **source ad's legacy creative features**, not proof that cloning is impossible.

## Recommended next tests

1. Prefer native Meta copy endpoints (`/{campaign_id}/copies`, `/{adset_id}/copies`, `/{ad_id}/copies`) over hand-building campaign/adset/ad payloads.
2. Keep all copied objects `PAUSED`.
3. Select another source ad/campaign that does not carry the legacy `standard_enhancements` field, preferably a newer clean ad.
4. If all promising source ads carry the field, research/test copy parameters that suppress or normalize standard enhancements into the newer individual creative feature controls.
5. Do not keep creating/deleting partial campaigns from scratch unless the test is explicitly diagnostic and approved.

## Populated Messenger native copies: isolate and restore the CTA subtype

When native bulk deep-copy returns generic code 2, do not infer that the token/profile is restricted or that duplication is impossible. Within the already authorized one-copy scope, reconcile account ID sets and use the canonical Engine's explicit-ad `pure_clone` representation: source campaign/adset IDs, adset name, source ad IDs and preserved creative payloads. This compiles shallow campaign/adset copies followed by native ad copies, exposes the failing layer and avoids the synchronous total-object limit. Never create additional campaigns as diagnostic probes, replay existing shells or silently change the source strategy/budget.

A native copy of a Messenger ad can fail with `100/1815675` (`Non-Messenger Ad in Messenger Ad Set`) even though the source ad worked and the token can copy the campaign/adset. Graph can return `asset_feed_spec.call_to_action_types=["APPLY_NOW"]` while omitting `call_to_actions`; native implicit copying or resubmitting that incomplete projection can lose the required Messenger subtype.

For the exact source after verifying its Page, pixel/event, subtype and historical/canonical payload:

1. Preserve the partial target campaign/adset IDs, verify them PAUSED and enumerate the ads edge before writing only missing source-linked slots.
2. Preserve live `object_story_spec`, complete AFS video/title/body/description/label/rule payload, `url_tags`, supported feature flags and Messenger JSON. Remove Graph output-only `reasons_to_shop` and `shops_bundle` from the outgoing AFS.
3. Restore `asset_feed_spec.call_to_actions=[{"type":"APPLY_NOW","value":{"app_destination":"MESSENGER"}}]` from the operation's approved builder/source evidence. Do not rewrite copy, JSON, Page, UTM or media to hide the error. In Eggbev the canonical builder is `ares_campaign_v3/eggbev_create.py`.
4. Submit native `/{source_ad_id}/copies` with the same destination adset, `status_option=PAUSED` and the preserved normalized payload in `creative_parameters`. Journal each receipt before continuing and normalize only the copied ad's display name when needed.
5. Read back all three levels and validate exact count, source lineage, configured PAUSED, issues, budget/strategy, targeting/attribution, Page/pixel/event, text/CTA/UTM/JSON and unchanged source. New creative, video and post IDs are possible; they do not prove a different visual or preserved social proof. Compare rematerialized variants by labels, dimensions and protected downloaded binary hashes (or decoded frames). Use an ephemeral Page token derived from the same approved advertiser when the User token omits video `source`; never persist that token or signed media URLs.
6. Treat extra returned creative-feature flags as equivalent disabled defaults only after verifying every source flag is preserved and every extra flag is `OPT_OUT`. Report `PENDING_REVIEW` separately from configured PAUSED, and never equate successful creation with review approval or auction entry.

Confirmed source-specific evidence: `data/ares/meta-ads/audit/eggbev/diagnostics/zeus-eggbev-canary-1564670170285473863/recovery-final-proof.json`. The same source's earlier successful recovery is `data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01-recovery-summary.json`. These establish the actionable Messenger compatibility boundary; they do not expose the internal cause hidden by the bulk code-2 response.

## Reporting language

Use precise wording:

- Good: `Clone nativo bloqueou por standard_enhancements legado no source ad.`
- Bad: `Meta não deixa clonar.`
- Bad: `Precisa de System User.`
- Bad: `Vamos criar do zero com payload limpo.`

## Safety

Require authorization for the exact technical write scope and the operation's applicable execution gates. Keep partial test objects `PAUSED`, record their IDs and reconcile them by GET before retrying. A failed test does not authorize cleanup: delete/archive only under separate explicit authorization and any required critical confirmation, then verify the exact terminal status. Report a blocked test or a completed test with preserved residue honestly rather than making deletion a prerequisite for reporting its result.
