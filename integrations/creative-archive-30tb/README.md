# Isolated 30 TB archive — copy-only pilot

Status: real owner copy/replay passed. Rodolfo approved Ares rule/integration changes in `1562104715271999589`; both authorized skills were updated conditionally with backups and live/mirror proof. The copy-only queue bridge and pinned owner worker are now staged and a real canary request has been uploaded/read back. No owner queue-worker execution, trigger, public web endpoint, source deletion or production auth change has occurred. The full unattended creative pipeline is not active.

Authority: Rodolfo message 1562087305051902063 in thread 1562078493498540042. Scope and security gates: `docs/ares-creative-30tb-autonomous-requirements.md`.

## Account and deployment gate

- Deploy a standalone Apps Script project owned and initially authorized by `mgsdigitalcorp@gmail.com`, after access is available through the protected login flow. Never restore retired local personal OAuth files or change the agents' canonical Service Account.
- Owner-supplied project: `1NxZ0ZTgZk4f3pzzX3fQQ-Y2wKpunjYbAaxbO8HN1fe9R5gXbEYVLpbUF`; project-file ownership/content have not been directly inspected by Zeus, but owner-executed account/quota and copying results were supplied and independently reconciled against real Drive state. No `.clasp.json` or local user OAuth authorization state exists. The one-file pilot has now run successfully; full unattended integration is a separate remaining stage.
- The manifest enables the Advanced Drive v3 service and requests Drive scope for the isolated connector. Google consent is required; this scope technically permits broader Drive access, so inspect/approve the scope and preserve the code's bounded source/destination checks. It is not a folder-scoped OAuth permission.
- Verify the account's actual quota and create/select a dedicated private destination folder owned by that account. Grant the canonical Service Account Editor on this folder only, with applicable authorization and readback. Allow the Gmail account to read/copy the single source pilot only; do not share the whole corporate Drive just to pass this test.
- Supply the bounded JSON in `pilot-config.json` as Script Properties key `MGS_ARCHIVE_PILOT_CONFIG`. The destination is now pinned to owner-provided folder `1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J`, verified by live canonical SA metadata as private and owned by the target Gmail account. Configuring this property is not deployment or copy proof; source visibility and copying-code gates remain pending.
- Run `runArchivePilot` once after checking permissions. The code verifies the effective account, the exact pinned source/drive/parent/size/MD5 against ancestry previously checked with the canonical SA, media type, destination ownership/access, unchanged source metadata, and copied size/MD5/name/type. It does not require the Gmail account to traverse ancestor folders. Preflight found the Gmail account already had sufficient source access; no new permission was added. Copies use Drive's server-side `files.copy`; no download via Apps Script URL Fetch is used.

## Replay and outcome

A script lock prevents parallel pilot writers. The source ID + MD5 marker identifies the copy. A pending marker is persisted before the non-idempotent copy request; if a copy response is ambiguous and no landed copy is visible, the pilot blocks for reconciliation instead of issuing another copy. More than one matching copy is a blocker. Never remove a pending marker just to force a retry.

A successful script receipt is explicitly `copy_verified_canonical_sa_readback_pending`, not full migration success. Zeus must then read the exact copied file through `/root/mgs-agent/scripts/mgs_google_workspace_auth.py`, compare owner/parents/size/MD5 and download/verify retrieval under the Service Account. Preserve the source. This gate passed for destination `1wz1Lm5l8a-UnbQnm5xFsO1Om0LqAQTkR`: exact-folder/marker enumeration found one copy, both source/copy streams matched in size/MD5/SHA-256, owner/private ACL and source preservation passed. Receipt: `data/ares/creative-ops/30tb-archive/pilot-copy-canonical-sa-verified-1562101859299364936.json`. Next: one real replay reuse test, then queue/inventory integration; never schedule this static single-file pilot as if it were production.

Real replay receipt: `data/ares/creative-ops/30tb-archive/pilot-replay-canonical-verified-1562103182103023729.json`; same destination ID, exactly one copy, original creation time and content preserved, source intact. No further repeated pilot run is needed. The static script status suffix `readback_pending` does not override the independent verified receipts.

No source cleanup is implemented. The additional Critical Subset confirmation for Ares skills was supplied and applied; deletion activation remains separately gated. The CLI stores verified archive mappings laterally and never rewrites primary creative IDs/reservations. Queue processing/recurring reconciliation, consumer/human-permission parity and the complete autonomous intake must be observed before calling production active.

## Queue bridge rollout

`scripts/ares_archive_bridge.py` provides `preflight`, `init`, `publish-worker`, `enqueue-canary`, `enqueue-lineage`, `reconcile`, `status` and `resolve`; writes require `--apply`. Configuration is in `data/ares/creative-ops/30tb-archive/queue-config.json`, with production queue/read cutover/deletion disabled.

The owner replaces Code.gs with `Bootstrap.gs` and runs `mgsArquivoTeste` only. This loads the exact SHA-256-pinned Worker.js from the canonical Drive, processes the immutable canary request and writes a separate Google receipt/heartbeat. The SA then executes `reconcile --apply` to verify full streams and publish an ACK. Only after that real ACK may the owner call `mgsArquivoAtivar`, which installs at most one five-minute trigger. Preserve old pilot properties/code artifacts for rollback; do not schedule `runArchivePilot`.

The queue worker is not a Drive-upload classifier or sanitizer. It consumes already-verified new lineages after Ares completes its normal intake contract. Installing its clock alone does not create a full autonomous UPLOAD MANUAL watcher. Treat those integration layers and recurring verification as separate acceptance gates; never fabricate their readiness from local tests.

## Local verification

`node --check integrations/creative-archive-30tb/Pilot.js`

`node --test tests/test_creative_archive_30tb_pilot.cjs`

These are offline contract tests with labelled fixtures, not a substitute for executing Apps Script or real Google copying. The initial RED run failed because the implementation did not exist; GREEN passed all 16 tests after implementation.
