# SHEIN IMG sourcing maintenance — t_9bf5723f

## Confirmed diagnosis

The four failed `ad_copy_with_creative` bodies were reconstructed from their exact sealed slots and confirmed target adset IDs; all four body digests match the pre-HTTP central write journal. Each target creative specified `object_story_spec.link_data.image_hash` but omitted `media_sourcing_spec`. Meta rejected those exact hashes with HTTP400/code100/subcode4931013, explicitly saying that the story image was absent from sourcing. Fresh source-ad GETs confirm source002 is video with `media_sourcing_spec.videos`/titles/bodies. Meta's official multi-media contract requires the primary image to also occur in `media_sourcing_spec.images`, with `hash`, `source=multi_media`, `opt_in_status=opt_in`.

Thus the missing explicit image sourcing is confirmed at our compiler/payload boundary. The exact internal mechanism by which Ad Copies carries source sourcing is not directly exposed; inheritance remains a supported inference, not a claim of Meta-internal root-cause visibility. No write probe was used.

Official source: https://developers.facebook.com/documentation/ads-commerce/marketing-api/ad-creative/multi-media-ads (retrieved during maintenance). Web search's configured backend was unavailable; its built-in keyless failover returned the official source successfully, and direct extraction succeeded. No credential/config/install change was needed.

## Installed correction

- `shein_general.py`: new `clone_prestaged` IMG definitions explicitly bind exactly the selected image hash and literal title/body/description in sourcing. VID branch retains its original fields. Source campaign/ads are not changed.
- `image_sourcing.py`: central effective-payload resolver for legacy already-sealed IMG manifests. It binds operation/account/mode/PAUSED, sealed-manifest digest, campaign idempotency key, source ad, slot, asset/checksum/hash and exact target adset. It GET-validates exact PAUSED shells and complete ZERO ads, then persists an immutable resolution receipt before the existing transport submits any effective mutation. Only the missing sourcing field is added; sealed manifests and their digests remain unchanged. Existing conflicting/any ads, pagination, drift, missing journal or a changed receipt fail closed.
- The same central resolver handles the failed first bundle and the six unattempted campaigns when their new shallow shells exist. It is not a second writer or a new campaign route. The additional three GETs per affected campaign are included in the engine's quota reservation.
- `schema.py` and `creative_media.py`: reject mismatched/extra images, source videos/related media, changed copy and unapproved media customizations.
- Consolidated, runner and activation readbacks now request sourcing. The status-only activation barrier separately checks image sourcing and rejects sourcing drift against the verified PAUSED proof before an ACTIVE POST.
- Dry-run explicitly discloses recipe `shein-static-image-sourcing-v1` and legacy-slot count; it does not label Meta acceptance as verified.

## Installed verification

543 tests +347 subtests passed across41 named regression files, with no exclusions, no external-network attempts and no installed-module origin mismatch. The same stage suite passed before installation. Reproduction starts with a synthetic4931013 rejection, resumes the exact same manifest/request/IDs, creates only missing ads through the core and verifies terminal idempotent replay with no calls. Negatives cover account/slot/source/hash/payload/status/mode drift, incomplete/active/foreign shells, existing ads, pagination, missing journal, changed receipt, bad sourcing and activation before QA. Existing IMG/VID/mixed, prestage/idempotency, queue, generic engine and scope tests remain covered. This is the named offline Zeus-context regression, not a whole-repository or live Meta/Ares write claim.

The installed GET-only real-request diagnostic verified:
- Original intake SHA256 `7ff01bbaa739f9422d869e6a0419ea8def04209ee9d9cc16fff9af9950844faf`; request-ready preserves every original field.
- Live Nicolas authority and Rodolfo confirmation1565763298602000577; no authority edit by Zeus.
-8 campaigns x2 images, USD25 each/USD200 batch, COST_CAP/bid95, source002120250750964580629, original11:45 ET intent/SLA preserved; PAUSED creation +ACTIVE target manifests both retain valid seals.
- All16 real registry hashes/asset checksums, reservations belonging to this request and the exact16 hashes still present in this account's live image library.
-008120250943717650629/adset120250943718090629 and009120250943717660629/adset120250943718150629 remain PAUSED, USD25/COST_CAP95, ZERO ads. History006/007 remains PAUSED with USD35/bid90 and its previous ads.
- Central resolver succeeds read-only for the four missing first-bundle slots using fresh real GETs and a DIAGNOSTIC COPY of the checkpoint. Those diagnostic receipts are not production state or an executable manifest.
- Canonical real-manifest dry-run identifies16 legacy slots and four bundles; queue remains foreground-owned.
- Exact hashes of intake, sealed manifest, runner state, engine checkpoint/audit and historical state remain unchanged after maintenance.

Zero Meta/Drive writes, media uploads, asset reservations, operational-state rewrites, source changes, activation, manager replies or gateway/worker restarts were made by this maintenance. No new executable manifest was generated. Infrastructure/checkpoint/audit bookkeeping and the single required infrastructure report are separate authorized writes.

## Ares dry handoff — same request only

From Ares's existing genuine profile, with no profile impersonation and no second writer:

`python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1565747351543480374/request-ready.json --dry-run`

Require the disclosed recipe and16 legacy image slots, same8x2/four bundles, same source/account/request and original parameters. Then resume the SAME command with `--confirm-execute` instead of `--dry-run`, exclusively through the central runner. Do not rerun prepare-media/upload, re-reserve, rebuild/reseal manifests, recreate008/009, switch IDs, reset SLA/start intent or touch historical006/007. The first bundle uses existing shells and adds only missing ads; future bundles use the same sealed request and corrected effective sourcing. Every correction is journaled before transport. If any live ad appears or the zero-ad/identity gate fails, reconcile and stop; never bypass it to replay a partial correction.

Ares owns live execution and origin-thread communication. Full rendered media QA, all eight complete hierarchies and final Meta readback remain mandatory before claiming creation/ACTIVE. This maintenance does NOT prove Meta acceptance, delivery/serving or campaign completion.

## Evidence and rollback

- `deployment-receipt.json`: exact installed module/test SHA256 and atomic exchange receipt.
- `regression-stage.json`, `regression-installed.json`: executed tests with origins/network counters.
- `real-readonly-readiness.json`: sanitized fresh real GET proof, slot mapping and DIAGNOSTIC_ONLY receipts.
- `preserved-state-readback.json`, `baseline-hashes.json`: unchanged operational state seals.
- Own skill updated/read back: `meta-ads-api-operations/references/shein-static-image-prestage.md`; canonical/mirror SHA256 identical. No Ares skill changed.
- Original package retained at `/root/mgs-agent/work/t_9bf5723f/rollback/atomic-original-package`; test originals also retained.

Rollback is code-only and coordinated: block new execution, reconcile current Ares state/ownership and any effects first, then acquire the same request/account locks and atomically exchange the retained original package. Never restore an old runner/checkpoint/manifest/reservation snapshot. Do not remove newly created infrastructure implicitly or reset IDs. If Ares has started using resolution receipts, do not restore code that cannot interpret them until recovery is reconciled. Original sealed payloads still require corrected sourcing; restoring old code does not fix the deterministic Meta rejection. No deletion is authorized.
