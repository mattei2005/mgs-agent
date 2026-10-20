# Isolated 30 TB archive — copy-only pilot

Status: local preparation only. Not deployed. No trigger, public web endpoint, source deletion or production authentication change.

Authority: Rodolfo message 1562087305051902063 in thread 1562078493498540042. Scope and security gates: `docs/ares-creative-30tb-autonomous-requirements.md`.

## Account and deployment gate

- Deploy a standalone Apps Script project owned and initially authorized by `mgsdigitalcorp@gmail.com`, after access is available through the protected login flow. Never restore retired local personal OAuth files or change the agents' canonical Service Account.
- Owner-supplied project: `1NxZ0ZTgZk4f3pzzX3fQQ-Y2wKpunjYbAaxbO8HN1fe9R5gXbEYVLpbUF`; ownership/content remain unverified by Zeus. No `.clasp.json` or local user OAuth authorization state exists. Start with the read-only `CheckAccount.js` function `verificarContaMGS` and obtain its real safe account/quota output. Do not deploy/run the copying pilot yet. Later deploy `Pilot.js` plus `appsscript.json` only after the source/destination gates.
- The manifest enables the Advanced Drive v3 service and requests Drive scope for the isolated connector. Google consent is required; this scope technically permits broader Drive access, so inspect/approve the scope and preserve the code's bounded source/destination checks. It is not a folder-scoped OAuth permission.
- Verify the account's actual quota and create/select a dedicated private destination folder owned by that account. Grant the canonical Service Account Editor on this folder only, with applicable authorization and readback. Allow the Gmail account to read/copy the single source pilot only; do not share the whole corporate Drive just to pass this test.
- Supply the bounded JSON in `pilot-config.json` as Script Properties key `MGS_ARCHIVE_PILOT_CONFIG`. The destination is now pinned to owner-provided folder `1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J`, verified by live canonical SA metadata as private and owned by the target Gmail account. Configuring this property is not deployment or copy proof; source visibility and copying-code gates remain pending.
- Run `runArchivePilot` once after checking permissions. The code verifies the effective account, the exact pinned source/drive/parent/size/MD5 against ancestry previously checked with the canonical SA, media type, destination ownership/access, unchanged source metadata, and copied size/MD5/name/type. It does not require the Gmail account to traverse ancestor folders. Preflight found the Gmail account already had sufficient source access; no new permission was added. Copies use Drive's server-side `files.copy`; no download via Apps Script URL Fetch is used.

## Replay and outcome

A script lock prevents parallel pilot writers. The source ID + MD5 marker identifies the copy. A pending marker is persisted before the non-idempotent copy request; if a copy response is ambiguous and no landed copy is visible, the pilot blocks for reconciliation instead of issuing another copy. More than one matching copy is a blocker. Never remove a pending marker just to force a retry.

A successful script receipt is explicitly `copy_verified_canonical_sa_readback_pending`, not full migration success. Zeus must then read the exact copied file through `/root/mgs-agent/scripts/mgs_google_workspace_auth.py`, compare owner/parents/size/MD5 and download/verify retrieval under the Service Account. Preserve the source.

No source cleanup is implemented. After the pilot, validate operational consumers, lineage, scheduling/quotas/large-video behavior, recovery and an exact bounded cleanup policy before requesting the destructive activation confirmation.

## Local verification

`node --check integrations/creative-archive-30tb/Pilot.js`

`node --test tests/test_creative_archive_30tb_pilot.cjs`

These are offline contract tests with labelled fixtures, not a substitute for executing Apps Script or real Google copying. The initial RED run failed because the implementation did not exist; GREEN passed all 16 tests after implementation.
