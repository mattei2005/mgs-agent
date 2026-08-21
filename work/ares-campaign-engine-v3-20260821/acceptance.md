# Ares Campaign Engine v3 — acceptance

Date: 2026-08-21
Authorization: Rodolfo message `1540202751387246664`

## Installed

- Central CLI: `/root/mgs-agent/scripts/ares-campaign-engine-v3.py`
- Package: `/root/mgs-agent/scripts/ares_campaign_v3/`
- Config: `/root/mgs-agent/data/ares/meta-ads/engine-v3/config.json`
- CPV contract: `/root/mgs-agent/data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR-v3.json`
- Ares skill: `meta-campaign-engine-v3` v3.0.0
- Official Meta documentation: all 18 URLs supplied by Rodolfo are in the Ares reference and v3 config.

## Behavior validated

- Two campaigns per account bundle.
- Independent lanes by app key + ad account.
- Soft cap 100 / hard cap 120.
- Development tier retains a 300-second rolling reservation.
- Full/standard access releases a completed bundle only when live account utilization is below 80%.
- Pure clone and clone with pre-staged media.
- Exactly three replacement ads per CPV campaign.
- Graph batch dependencies for creative → ad.
- Zero intermediate GET.
- One consolidated campaign/adsets/ads readback per two-campaign bundle.
- Tamper-evident manifest prevalidation.
- Media upload/processing occurs outside the campaign hot path and is guarded by `media_upload_enabled`, `--confirm-upload`, Page `ADVERTISE`, checksum and dual-video ready readback.
- Per-lane checkpoints preserve known object IDs; a failed request is blocked from blind replay until reconciliation.
- App-secret proof supported but disabled pending app setup.
- No token/credential value in code, config, manifests or audits.

## Execution evidence

- Python compilation: PASS.
- Combined current suite including v3, fixed reports, v2/common and activation rollback: 96 passed.
- Independent Ares handoff reproduction of the requested v3/v2 set: 68/68 passed.
- CPV offline E2E: 2 campaigns, 6 ads, prevalidated, c14/c15 UTMs, no legacy c08 UTM, one readback batch, zero intermediate GET.
- Synthetic full-access benchmark: 40 campaigns, 3 account lanes, 7 waves, 6 campaigns maximum per global wave, zero intermediate GET.
- Live read-only source refresh: Graph v26 campaign/adset/3 ads HTTP 200; 3 sanitized creative templates; no `standard_enhancements`; no credential persisted.
- Installed production gates: engine enabled, write enabled and media upload enabled under `development_access` guards.
- Five-campaign active-mode offline E2E: planner produced 2+2+1; development quota deferred/resumed 2→4→5 without replay; final status `COMPLETE_FUTURE_ACTIVE`.
- V2 runner and Meta common helper hashes unchanged from pre-v3 backup.
- V2 creation/activation crons remain paused and are explicitly classified as rollback/frozen.

## No production side effects

No Meta campaign/adset/ad/creative/media write, budget change, credential change, deletion or gateway restart was performed during installation.

## Active production state

V3 is the active route for the next authorized campaign request. The request can contain 1–100 campaigns; CPV materialization requires three ready media assets per campaign, the planner chunks 2+2+…+1, and under current `development_access` it defers/resumes bundles every quota window without replay. Full Access removes the development bottleneck but is not required to use v3.
