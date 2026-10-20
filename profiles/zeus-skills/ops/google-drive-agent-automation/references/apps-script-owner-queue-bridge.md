# Isolated Apps Script owner queue — copy-only bridge

Use only after Rodolfo explicitly approves a separate owner-authorized cloud connector. This is not a personal OAuth fallback for agents: they continue using the canonical Service Account/helper. The Apps Script API cannot be managed/executed with a Service Account, so initial owner-side setup/consent remains a separate gate.

## Minimal authority-preserving design

- Keep uploads and sanitization in the canonical Shared Drive. Put technical request/receipt files in a dedicated control folder, not the creative candidate pool.
- Have the SA publish immutable, content-hashed JSON requests. Verify `lastModifyingUser.emailAddress` from Google metadata is exactly the canonical SA before interpreting a request; reject missing or different publishers. A property hash alone is not provenance because another editor could rewrite both content and property.
- Bind source Drive/root, archive owner/root, media-only roles, exact sources/parents/hashes and allowed relative paths. Keep the deletion flag false. Separate an exact historical canary from future lineage requests; enforce timezone-aware first-seen/source-created cutoffs and never scan old inventory into the queue implicitly.
- The owner worker creates copies in that owner's My Drive. It checks effective account, scope, raw request digest, source state, destination ownership/path and copy integrity, then writes its own receipt. The SA independently streams/verifies both source and copy, records a sidecar mapping and publishes an ACK. Do not replace primary creative IDs or reservations merely because a receipt exists.
- Preserve original/clean lineage, manager reservation and eligibility. Keep source deletion and primary-ID/read cutover separately gated until consumer and human-permission parity pass.

## Publish without exposing credentials or a public endpoint

Publish a versioned worker source blob in the Shared Drive and verify its raw bytes/SHA-256 after upload. Pin that exact source ID, SHA-256, project ID and bounded config in a small owner-side bootstrap. Check the code digest before dynamic compilation. This lets other existing Drive editors cause only a blocked integrity check, not silently replace code executed with the owner's account. A code update requires a deliberately repinned version; never auto-trust a changed source file.

The bootstrap's manual test must be exercised before scheduling. Its installer must require a canary ACK published by the canonical SA, refuse duplicate triggers and create at most one recurring trigger. Do not interpret a prepared installer, local VM test or published code file as a live Google trigger.

## Replay, concurrency and recovery

- Use one local producer lock plus the worker's script lock. Immutable request bodies and separately owned receipts avoid competing writers on the same JSON content.
- Derive job identity from frozen source IDs/checksums/paths, not a fresh request timestamp. Reuse the original local/remote request on retry and verify exact content.
- Mark intent before a non-idempotent copy. A lost response must reconcile a landed marked copy; if none is visible, stop instead of replaying blindly. Completed jobs/receipts must reuse the same archive IDs.
- After canonical verification, let the SA mark the request metadata verified so the worker polls only queued requests; preserve the immutable body. This avoids rescanning every completed job indefinitely.
- Reset per-item `job`/`prior` state at the start of every JavaScript loop iteration. Function-scoped `var` can otherwise carry a trusted previous job into a later untrusted request's error handler and overwrite the wrong receipt. Cover this with an interleaving regression.
- Release locks in a nested `finally` even when budget/state persistence fails. Invalid budget state must fail closed, not reset runtime accounting. Bound jobs per tick, execution time, rolling runtime budget, retries and provider cooldowns.

## Proof levels

Report separately: offline contract/orchestration tests; real SA queue transport/readback; owner worker execution; canonical receipt/binary verification; scheduled tick observed; operational Ares intake/consumer integration; destructive cleanup activated. Do not collapse these into one success claim. A paused `queue_enabled=false` stage is intentional deployment state, not active unattended processing.

Current reusable implementation: `/root/mgs-agent/scripts/ares_archive_bridge.py` and `/root/mgs-agent/integrations/creative-archive-30tb/`. Live rollout state and authority remain in the canonical initiative document/checkpoint; this reference does not grant new access or deployment authority.
