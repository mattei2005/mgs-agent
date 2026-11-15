# Installed recovery — owner handoff

## Boundaries

Maintenance `t_53c187db` installs code only. Delivery `t_bdfc754f` remains sole owner of the existing request/campaign/AdGroup/children, status recovery, manager stock finalization and original-thread/Iris BOT delivery. Do not repeat `prepare`, `execute`, Engine, uploads, PBIA, reservation, numbering or DELETE. No new commercial approval is required for the unchanged request; live authority must still pass.

## Owner commands (NOT executed by maintenance)

Use the original approved runtime/account (Ana USER, app953171080682697), original input, digest and approval:

```
python3 /root/mgs-agent/scripts/ares-eggbev-target-clone.py recover-media --input /root/mgs-agent/data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23189-1571342489162489937/request.json --approved-digest 7fb94557a6302e97bcc5239ad7f7758052555203f3ff15c360e1ffef55c5afba --approval-message-id 1571376388437577861
python3 /root/mgs-agent/scripts/ares-eggbev-target-clone.py finalize --input /root/mgs-agent/data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23189-1571342489162489937/request.json --approved-digest 7fb94557a6302e97bcc5239ad7f7758052555203f3ff15c360e1ffef55c5afba --approval-message-id 1571376388437577861
```

First validate every handoff hash and frozen runtime pin. Do not rewrite the grant, manifest, original proof files, registry or approval. The grant expires 24h after its original attestation; unavailable/stale authority or media blocks without new creation. Respect quota Retry-After and retain the same owner/checkpoint. Source/Page/denylist/scopes are read anew.

## Recovery behavior

- Requires all eleven confirmed journal slots, three seed/final pairs and six bijective variant labels from the pinned owner proofs.
- Parent PAUSED preQA checks commercial, objective/regulatory, AdGroup destination/subevent/targeting/event, Page/PBIA, literal copy/CTA/JSON-AGT, UTM, features, rules, slot/label/creative/seed lineage and rendered proofs.
- Downloads twelve exact requested IDs fresh; validates ready/complete/title/length, bytes SHA256, dimensions/duration and three decoded PNG frames each. Ordered twelve-ID proof coverage is checked before activation.
- Only remote write in recovery is `status=ACTIVE` on existing parent120251246081230629. No budget/start/child writes. After fresh GET the unchanged original comparator runs against an independent in-memory expectation carrying attested derived IDs. Raw GETs and sealed manifest never change.
- Durable intent permits crash-after-status recovery by fresh GET, without replaying a successful ACTIVE write.
- `media-recovery/verified.json` points to a content-hashed `receipt-<digest>.json`, schema `mgs.target.media.recovery.v1`. `receipt.schema.json` documents shape; runtime additionally validates exact grant/approval/request/manifest/IDs/labels/bytes/frames and clock.
- Checkpoint, audit and engine-result gain only independent hash links through backup/CAS. Original Engine failure/error is preserved; no fake COMPLETE Engine result.

## Finalization and retry

Finalization requires a valid independent receipt plus fresh full GET. Inventory records actual final vertical video ID and original/derived lineage, then the manager controller validates/moves the same three stock IDs to Usados. Naming becomes COMMITTED only after real stock receipts and another full GET. Partial movement uses existing same-stock intent/readback; no new files/uploads/aliases or repeated PATCH after successful movement. Terminal retries verify final links, stock and ledger without reopening lease; they repair only a still-blocking lease owned by this exact request after all checks.

If status write outcome is uncertain, rerun only `recover-media`: it GET-reconciles the existing parent and intent. If stock/link finalization is partial, rerun only `finalize` with the same original flags. An unrelated ACTIVE parent without this route's exact intent fails closed.

Completion remains pending until owner validates final real hierarchy/status/IDs, three stock receipts, COMMITTED ledger, source unchanged and final origin/Iris BOT delivery. ACTIVE configuration alone is not delivery or serving verification.

## Validation and rollback

Installed acceptance:637/637 tests =519 previous pertinent +91 new recovery +27 manager-stock/scope, no skips;91 new tests also pass native Python. Shared616 attempts show exactly the same13 pre-existing failed suites in before/candidate; not claimed green. Original138 protected files and175 previous runtime artifacts except the intentionally changed runner are unchanged. Owner supplement provides actual missing GET fields; no positive fixture defaults from manifest.

Rollback code only: under exclusive request lock and after proving no active owner process, CAS installed runner hash and atomically restore `before/ares-eggbev-target-clone.py`. The unused new module may remain inert; do not delete files or roll back live recovery receipts/remote effects implicitly. Preserve first proofs.

Zeus learning saved in its own meta-ads-api-operations reference and synchronized mirror. Ares should update its own target-page-replacement-clone reference with this installed CLI/receipt contract; Zeus did not edit Ares skills.
