# Backup owner archive automation

Use for the approved future-only backup lane; this is not Google agent OAuth fallback or permission to delete backups.

## Owner/SA boundary and acceptance

- Keep the canonical SA uploader, original `_DISASTER_RECOVERY` root/tier IDs, config hash, cadence and source policy unchanged. Freeze a separate immutable backup plan with exact source/archive folder IDs, owner/SA native permission IDs, approved corporate ACL and a Google-created-time future cutoff. Historical migration is a separate manifest; never enqueue it implicitly through future discovery.
- Let the canonical SA publish exact content-bound requests; verify native SA publisher plus raw digest/root/type on the owner side. Private `appProperties` are application-scoped and need not be visible to the owner Apps Script project: the SA freezes its managed metadata, the owner validates native content/ancestry, and the SA verifies those private properties again after the move. Never use editable metadata alone as authority.
- Keep the backup move in the existing script lock and unchanged bulk runtime ledger. Admit at most one move before the existing media scan after its account/root/budget gate; a heartbeat hook may serialize the result but must not execute the lane again. A bulk pause remains a pause. Manual control performs read-only owner/path/pilot-capability validation only. Do not reset accounting, increase limits, install a second trigger or move arbitrary files to prove scheduling.
- Give every request an exact SA-created receipt slot. Validate its scope/schema/publisher before moving, persist an exact-ID move intent first, and publish the owner receipt into that same slot. A lost move response is reconciled through native location/content; an unlanded durable intent is blocked, never replayed blindly. Preserve receipt publication journals and resume publication after a landed move without moving or rolling back again.
- Journal plan/source/request publication before POST. Reuse exact returned IDs and immutable raw bytes; an unresolved create can be adopted by its exact trusted key but must not trigger another POST when lookup remains empty. Native publication plus local tests is staged code, not owner deployment.
- Require deliberate owner repin and two distinct fresh scheduled heartbeats of the new digest/native trigger with a successful read-only backup probe. Then use the existing full whole-drive acceptor to promote both SA/historical pins; only afterward may a canonical-SA activation enable the future-only move producer. Keep old pins/local state for rollback.
- Independently re-read request and owner receipt, verify the same physical backup ID, intended owner/parent/ACL, all frozen native checksums and SA-visible managed properties, stream the archived ciphertext once, publish/read back an SA ACK, and cache only while the current metadata/receipt/request fingerprint matches. Expose the first real verified backup as a stable monitor transition; do not ask for another human pilot to manufacture acceptance.

## Retention is a different gate

Generate retention preview across source and archive IDs without duplicates, using unchanged per-tier counts. Keep source-expired/unverified data and the last restore-proven generation protected. A preview candidate is NOT a trash command. Do not implement/activate owner deletion or reinterpret `canEdit`/`canDownload` as `canTrash`; separately confirmed archive-retention mutation is still required.

## Current entry points

- `scripts/mgs_backup_automation.py prepare|publish|preview|tick`
- `integrations/creative-archive-30tb/BackupArchiveExtension.js`
- Existing Zeus `ares-archive-automation-monitor.py` calls the producer/reconciler; no additional cron is needed.
- `backup-automation-stage.json` distinguishes published, owner accepted, activation and first production verification. `backup-retention-preview.json` is non-destructive.
- Live worker IDs/digests and rollout authority belong in the canonical initiative document/checkpoint, never this procedure. Do not republish a changed immutable worker in place.

Exercise source/publisher/path/content drift, future cutoff, manual/paused execution, priority-before-media, receipt-slot preflight, lost-response reconciliation, publication uncertainty/no replay, ACK caching and retention protections with local fixtures; then verify native plan/source readback and actual scheduled Google execution separately.
