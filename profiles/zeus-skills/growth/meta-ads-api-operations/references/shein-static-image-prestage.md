# SHEIN static images — central maintenance and operational handoff

Use the existing `ares-shein-campaigns.py` grouped-manager route. Behavioral permission for generic media is not proof that the deployed compiler/uploader supports the requested format; trace intake → pre-stage → registry → schema/prevalidation → compiler → semantic/rendered QA → inventory → status-only activation before changing a validator.

## Installed routing

- Canonical SHEIN `IMG` PNG/JPG/JPEG is a static image, never a video derivative. `VID` remains MP4. Preserve exact filenames, ordered groups and literal copy.
- `ares_campaign_v3.image_prestage` uploads on the exact account's `adimages` edge using the same registered credential. No Page-video upload, personal identity, guard expansion or alternate campaign writer.
- Registry identity remains account + asset + clean checksum. Image records carry `media_type=image`, `image_hash`, `upload_edge=ad_account_adimages`, readiness and verified account association; legacy video records retain their original shape/defaults and video-only consumers reject image records.
- Images compile as `object_story_spec.link_data.image_hash`, preserving source identity/CTA and approved destination/tracking/copy. Never put the image hash into a video ID or inherit video `media_sourcing_spec` into a static image.
- Reconciliation and semantic QA require the exact image hash, including core creative recovery matching. Rendered QA requires actual static image media, not a playable source video or a link-only preview. Existing all-campaign PAUSED QA and central `activate_verified` gates remain unchanged.

## Readback-first image recovery

1. Verify the original bytes by SHA256, Drive MD5/size, clean metadata, static format and current manager-folder/lineage authority before upload. Confirm current Drive MD5 again during handoff.
2. Reconcile the exact account image library by deterministic filename (`V3 IMAGE {asset_id} {checksum-prefix}{extension}`), with complete pagination and no ambiguity. Image names are limited to 100 characters.
3. Persist an upload intent before POST; persist the response hash before readiness commit. After a lost response, resolve that same deterministic filename/hash. An unresolved prior intent blocks replay; never upload again blindly or treat a timeout as proven zero effect.
4. Never persist signed Meta image URLs or use them as creative identity. Use the account-library hash and direct readback; preserve use/test history and the manager's physical folder. No implicit deletion or cleanup.
5. If a hash changes or Meta retains source video fields, fail closed PAUSED and reconcile the same request/IDs through the core. Do not weaken QA to make the first image request pass.

## Verification boundary

- `tests/test_shein_image_media.py` covers real-input intake, IMG/VID/mixed groups, typed schema/registry, core dry-run, ambiguous uploads/idempotency, prepare→handoff→inventory, exact-hash negatives, actual localhost Chromium static-image rendering and the existing status-only activation barrier.
- Offline API fixtures and synthetic image hashes are test inputs only. A real-request contract replay with a synthetic registry is NOT a live prestage or a production-ready manifest. Never save or execute those synthetic manifests.
- The campaign owner must still run real `prepare-media --input <original-request> --confirm-execute`, then `campaign --input <request-ready> --dry-run`, then the authorized central execution. Require all exact images/texts, requested budget/bid/schedule, all rendered previews, and final GET readback before announcing creation/ACTIVE. Preserve original timing and canonical same-day elapsed-start policy rather than editing the intake.
- Keep maintenance separate from the campaign transaction. Stage and test the complete package, check concurrent source/writers, preserve rollback, publish coherently, re-test installed files, and record inventory/audit/REPORT-INFRA. A deferred historical checkpoint is not permission to modify or replay it.
