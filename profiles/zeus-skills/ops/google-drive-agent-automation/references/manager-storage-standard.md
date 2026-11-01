# Registered manager storage standard

## Trigger and authority

Use for `01_READY`, manager Exclusivos/Usados destinations, scoped manager delivery, or post-campaign usage reconciliation. Read `context/creative-manager-storage-standard.md` and the live `data/ares/creative-ops/manager-storage-standard.json` first. An approved design is not an active binding; require `phase=active` plus real native preflight/canary receipts. The original UPLOAD MANUAL identity remains unchanged.

## Procedure

1. Resolve exact operation, IMG/VID and registered manager through `ares_manager_storage_standard.py resolve --operation <OP> --format <IMG|VID> --manager <name> [--state exclusive|used]`. Reject cross-manager/operation IDs, arbitrary names, ambiguous folders and wrong native ancestry/owner. Never infer actual use from a folder label or original uploader.
2. New manager batches remain exclusive and ineligible to the common pool. General distribution requests may end at READY; the sender's name alone is not authority to release inventory reservations.
3. Use `ares_manager_delivery.py` for exact same-lineage delivery after native archive ACK/stock transfer. Retain original providers and existing requests/receipts; no parallel manual PATCH, recopy or rewrite of immutable evidence.
4. The SHEIN finalizer performs the registered same-ID Exclusivos→Usados move only after actual assignment readback. Other campaign routes call `ares_manager_storage_standard.py confirm-use --asset-id <asset_id> --request-id <request_id>` first without apply, then `--apply`. This command reads the existing Meta ad and checks account/campaign/adset/creative/media, exact reservation and Drive hashes/parent. It never creates Meta objects or changes budget/credentials/ACL. Failed campaigns and unselected assets remain exclusive. Preserve legacy in-flight requests instead of silently changing their destination or ownership.
5. Share queue→inventory lock ordering for writes. Persist the CAS intent before PATCH, reconcile actual parent after ambiguity and repeat only a missing operation. A successful PATCH is not acceptance until exact ID/parent/hash and inventory readback pass. Preserve original delivery evidence when adding usage evidence.
6. For provisioning, use `mgs_provision_manager_storage.py --operation <OP> --apply` in bounded foreground batches. It calls the existing isolated owner component; SA remains the verifier. Creating folders directly with SA can produce the wrong owner even when the request succeeds. Reuse exact existing folders and persisted intents, reject ambiguous creates, and verify the entire expected operation×format×manager membership before activation.
7. A native canary may reuse an existing validation-only shortcut, move it through registered destinations and restore its original parent, verifying the unchanged provider stream/hash and same IDs. Never promote that technical job into a production catalogue record or call it a completed real campaign. Record technical readiness, the first real new-flow use and historical reorganization separately. `manager-standard/first-production-use.json` is written by the actual usage helper after real assignment/stock readback; a fixture or manual label is not a substitute.
8. Do not merge physical archive trees, stock aliases and historical retained binaries by filename. Folder standardization does not prove deduplication, historical usage attribution, source retirement, or resolution of earlier COPIED_PATH/COPIED_METADATA incidents.

## Regression execution

Resolve the Python executable from the live Ares gateway; renderer-bearing tests need its existing dependencies. Run focused modules in separate interpreters with both project `scripts` and `tests` on PYTHONPATH: some test modules import sibling fixtures directly, while others monkeypatch shared module identities. A test harness import error is not a production failure and does not justify installing packages.

Include manager storage/delivery, grouped media, image identity, archive storage/consumer/automation/layout and historical consumer tests. Keep pre-cutover Shared-Drive fixtures explicitly isolated from the live location flag; reproduce a suspected pre-existing failure against untouched code before changing only its fixture. Preserve failed receipts and label focused passes as focused, not the whole repository suite.

## Closure

Read back live/mirror Ares skill equality under the explicit cross-agent skill approval. Inventory changed scripts/data/skills/context, checkpoint remaining gates, record audit and publish one canonical REPORT-INFRA embed with exact-message readback. Do not restart a gateway merely for CLI modules or newly read skill references. Do not claim a running conversation's cached prompt or a productive campaign has changed solely from the file edits.
