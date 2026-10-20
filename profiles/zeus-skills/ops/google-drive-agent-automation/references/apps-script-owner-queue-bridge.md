# Isolated Apps Script owner queue — copy-only bridge

Use only after Rodolfo explicitly approves a separate owner-authorized cloud connector. This is not a personal OAuth fallback for agents: they continue using the canonical Service Account/helper. The Apps Script API cannot be managed/executed with a Service Account, so initial owner-side setup/consent remains a separate gate.

## Minimal authority-preserving design

- Keep uploads and sanitization in the canonical Shared Drive. Put technical request/receipt files in a dedicated control folder, not the creative candidate pool.
- Have the SA publish immutable, content-hashed JSON requests. Require Google-output `lastModifyingUser.permissionId` to match the pinned native ID of the canonical SA before interpreting a request; pin the owner similarly for receipts/heartbeats. Derive bindings from authenticated Drive `About.user` and the already-approved private archive root's owner, not from a request or its editable properties. Google can hide another principal's `emailAddress`; when visible, it must also match. Missing/mismatched native IDs always fail closed, even if email/displayName looks correct. A property hash alone is not provenance because another editor could rewrite both content and property.
- Bind source Drive/root, archive owner/root, media-only roles, exact sources/parents/hashes and allowed relative paths. Keep the deletion flag false. Separate an exact historical canary from future lineage requests; enforce timezone-aware first-seen/source-created cutoffs and never scan old inventory into the queue implicitly.
- The owner worker creates copies in that owner's My Drive. It checks effective account, scope, raw request digest, source state, destination ownership/path and copy integrity, then writes its own receipt. The SA independently streams/verifies both source and copy, records a sidecar mapping and publishes an ACK. Do not replace primary creative IDs or reservations merely because a receipt exists.
- Preserve original/clean lineage, manager reservation and eligibility. Keep source deletion and primary-ID/read cutover separately gated until consumer and human-permission parity pass.

## Explicit OAuth scopes — mandatory before owner execution

Apps Script infers scopes by statically scanning project code. A hash-pinned loader using `new Function`, `eval` or remote source hides the worker's Drive writes from that scan; authorizing the inferred read-only scope again cannot grant a missing requested write scope. An error such as `You do not have permission to call drive.files.create` is an OAuth-scope gate, not evidence that Drive folder Editor access or the account password is wrong. Granular consent may also leave a declared scope ungranted; inspect both declaration and grant rather than blaming the user.

Before the first owner run, explicitly declare `https://www.googleapis.com/auth/drive` and, when the installer manages triggers, `https://www.googleapis.com/auth/script.scriptapp` in `appsscript.json`. Preserve existing timezone/runtime and Advanced Drive v3 dependencies. Add `ScriptApp.requireScopes(ScriptApp.AuthMode.FULL, [...])` in the bootstrap before reading/compiling/executing the worker. Test the manifest and guard together; local mocked Drive success cannot establish Google consent completeness. Full Drive is required for this pre-existing cross-folder source/DriveApp flow; do not choose AppData or `drive.file` merely because the exception lists them as method alternatives.

If the remote manifest has not been read, obtain its current content through the supported owner UI and make a narrow scope edit. Do not replace unknown project settings blindly, revoke grants, delete script properties, rotate credentials, expand file ACLs or create another project to cure a consent loop. Reconcile real request/receipt/heartbeat/copy state before retrying the same request. Explicitly distinguish a locally prepared fix from Google-side recovery verified after consent.

## Publish without exposing credentials or a public endpoint

Publish a versioned worker source blob in the Shared Drive and verify its raw bytes/SHA-256 after upload. Pin that exact source ID, SHA-256, project ID and bounded config in a small owner-side bootstrap. Check the code digest before dynamic compilation. This lets other existing Drive editors cause only a blocked integrity check, not silently replace code executed with the owner's account. A code update requires a deliberately repinned version; never auto-trust a changed source file.

The bootstrap's manual test must be exercised before scheduling. Its installer must require a canary ACK published by the canonical SA, refuse duplicate triggers and create at most one recurring trigger. Do not interpret a prepared installer, local VM test or published code file as a live Google trigger.

## Cross-principal Drive publisher identity

Request `lastModifyingUser(emailAddress,permissionId)` explicitly in both `files.get` and `files.list`; selecting email alone can yield an empty modifier object across accounts. Verify both directions: the owner reads SA requests/ACKs, and the SA reads owner receipts/heartbeats. The Google User reference documents that email may be absent depending on visibility; the stable native permission ID is Google output, not an editable file marker. Treat IDs as opaque strings and preserve leading zeros. Do not authorize by display name, a body field or an email-only fallback. A changed native ID for the same email is a different binding requiring investigation/authorization, not an automatic pin refresh.

Cover hidden emails, wrong/missing IDs, contradictory visible emails, unknown expected principals and replay of receipt/heartbeat with privacy-shaped fixtures. Verify Google-derived bindings live before pinning. Updating the representation of the same already-approved principal is not an ACL grant or a new authorized user; retain and audit the binding evidence. Publish a new immutable worker version and deliberately repin its file ID/hash; retain the previous version for rollback. Until the owner runs that new pin, its local tests and source publication do not prove Google recovery.

A worker summary with `status:"ok"` but nonempty `blocked` is not a completed archive operation. Require an empty block list, actual per-job receipt, canonical binary verification/ACK and separate scheduled-heartbeat proof at their respective gates.

## Replay, concurrency and recovery

- Use one local producer lock plus the worker's script lock. Immutable request bodies and separately owned receipts avoid competing writers on the same JSON content.
- Derive job identity from frozen source IDs/checksums/paths, not a fresh request timestamp. Reuse the original local/remote request on retry and verify exact content.
- Mark intent before a non-idempotent copy. A lost response must reconcile a landed marked copy; if none is visible, stop instead of replaying blindly. Completed jobs/receipts must reuse the same archive IDs.
- After canonical verification, let the SA mark the request metadata verified so the worker polls only queued requests; preserve the immutable body. This avoids rescanning every completed job indefinitely.
- Reset per-item `job`/`prior` state at the start of every JavaScript loop iteration. Function-scoped `var` can otherwise carry a trusted previous job into a later untrusted request's error handler and overwrite the wrong receipt. Cover this with an interleaving regression.
- Release locks in a nested `finally` even when budget/state persistence fails. Invalid budget state must fail closed, not reset runtime accounting. Bound jobs per tick, execution time, rolling runtime budget, retries and provider cooldowns.

- Emit an owner-authored heartbeat with the pinned worker hash, timestamp, work/error summary and the installable event's `triggerUid` when present. A manual execution must keep that field null. Read back provenance/hash through the SA so publishing code, running a manual test and observing a scheduled tick remain distinct proofs.

## Proof levels

Report separately: offline contract/orchestration tests; real SA queue transport/readback; owner worker execution; canonical receipt/binary verification; scheduled tick observed; operational Ares intake/consumer integration; destructive cleanup activated. Do not collapse these into one success claim. A paused `queue_enabled=false` stage is intentional deployment state, not active unattended processing.

Current reusable implementation: `/root/mgs-agent/scripts/ares_archive_bridge.py` and `/root/mgs-agent/integrations/creative-archive-30tb/`. Live rollout state and authority remain in the canonical initiative document/checkpoint; this reference does not grant new access or deployment authority.
