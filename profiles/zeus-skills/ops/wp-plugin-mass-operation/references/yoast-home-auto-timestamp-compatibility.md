# Yoast home repair — automatic timestamp compatibility

## Diagnose before another deployment

- When a pinned native-repair audit rejects `unreviewed_automatic_column_update`, inspect the exact guard and installed migration adapter before treating the database schema as anomalous. Yoast's migration adapter can declare `updated_at` as `timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`; installed source proves intended DDL, not the complete live column definition.
- Collect read-only table metadata for the exact installation/table: column name, type/precision, nullability, default, EXTRA and generated expression, plus server version, session timezone and SQL mode. A failure at a loop over EXTRA proves an automatic-update clause exists, not which column caused it. Do not certify live compatibility from source or doubles alone.
- A blanket ON UPDATE rejection can correctly prevent an unsafe probe: an UPDATE that changes only permalink may implicitly change updated_at and fail an otherwise exact full-row comparison. Never remove the rejection alone, change schema or omit the timestamp from preservation checks.

## Prepare the replacement locally, preserving one writer

- Keep the original ZIP, hash, remote readback and failed receipts immutable. Prepare a separately versioned local candidate; do not patch the executor's active work or deploy concurrently.
- Replace a blanket rejection only with a reviewed positive compatibility check for the exact certified timestamp definition; reject any additional automatic/generated column or unreviewed precision/default/expression.
- For a target-only probe, explicitly bind the original locked-row updated_at as a prepared scalar literal alongside permalink and temporarily permit exactly those assignment columns. Do not use `updated_at=updated_at` or CURRENT_TIMESTAMP when the pinned SQL parser admits literals only. Parser acceptance is not proof of timestamp preservation on the live server.
- After the probe, require full-row equality except for the intended permalink and exact restoration after ROLLBACK TO SAVEPOINT. Retain the original baseline, row locks, concurrency checks, connection identity, native watcher limit, protected-state hashes and journal/CAS restoration checks. Restoration must explicitly write the original timestamps and reject newer third-party state.
- Test with an old timestamp and a separate current time, both apply/restore probes, rollback failures, forbidden extra automatic columns, precision/null/default changes and concurrent-state rejection. A fast same-second test can hide automatic timestamp changes. Distinguish parser/source tests, simulated DB tests and real transactional recovery.

## Immutable approval and handoff

- An explicitly approved ZIP hash is not automatically superseded by a repaired candidate. Preserve the old approval; finish local diagnosis, diff, tests and new manifest before delimiting any genuinely protected replacement decision. Never present an unreviewed new hash as covered by the old pin or request a generic continue/OK instead of resolving the technical issue.
- Keep the original executor as the sole production writer and preserve canary order, target IDs, protected posts, paused targets and WP2FA finally/readback requirements. A failed audit before apply is not a reason to replay apply or deploy the same incompatible package.
