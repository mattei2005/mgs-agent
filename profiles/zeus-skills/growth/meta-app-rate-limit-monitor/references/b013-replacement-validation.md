# B013 replacement validation and recovery

Apply the main skill's replacement authorization and acceptance gates. Start with this compact dedicated-route sequence; consult the specific replacement sections of route-pack-05 only for additional branches, not its historical cutover narratives.

## 0. Pause while the replacement is not ready

1. Separate the current app from the proposed successor. A future label plus a statement that credentials are not yet stored establishes a pending replacement only; do not rename the active registry, rewrite the runner or initialize successor state.
2. Resolve the current dedicated runner and its vault from the deployed configuration. When a minimal health check needs the exact immutable item, use `/root/mgs-agent/scripts/mgs-op-with-service-account.sh item get <item-id> --vault <resolved-vault> --format json` inside a capturing process. Keep the raw item, token and secret only in memory; print only allowlisted identity and diagnostic fields. Supply the vault explicitly for Service Account item reads so item discovery does not become an avoidable failure.
3. On an explicit pause request, list jobs and select every existing day/night job using the dedicated runner. Call `cronjob_manage(action='pause', job_id=<resolved-id>)` for each; preserve their schedules and all unrelated jobs. Read back the exact jobs and require `enabled=false` and `state=paused` for the complete selected set.
4. Inspect the canonical runner lock separately, without starting another scan. A free lock supports 'no native scan in progress'; if held, identify and reconcile that writer before claiming execution has stopped. Do not equate scheduler pause with cancellation or kill an existing writer implicitly.
5. Record a credential-free receipt, audit, inventory and checkpoint with the pause authority, actual thread, selected job IDs, proposed successor and explicit wait-for-owner gate. Query heterogeneous inventory/checkpoint records with `record.get('id')`, not `record['id']`, because legacy entries may omit that key. Publish and read back the required canonical REPORT-INFRA without duplicating it in the operational thread.
6. Confirm the verified pause briefly. On the owner's later credential-ready notice, resume this same checkpoint at the normal replacement preflight below; do not create duplicate jobs or unpause merely because a successor name is known.

## 1. Resolve identity and preserve rollback

1. Read the active registry entry, its immutable vault item, the dedicated runner, predecessor state, both day/night jobs and unrelated pause sets. Resolve the runner path from live inventory or the job's script resolution rather than assuming it lives in the repository scripts directory.
2. Back up the affected runner, registry, state, pause configuration and any test being changed before production edits. Keep credential values in memory, never in the rollback bundle.
3. Require a different Meta app ID from the saved predecessor snapshot, matching replacement `app_name`, valid app-bound `debug_token`, successful metadata and `/me` reads, and complete applicable role enumeration. Prove DTR capability with the dedicated runner; generic roles do not establish account links.
4. If the exact replacement title and fresh `/me` agree but a non-secret principal-profile note still names the predecessor, correct only that exact profile line in the same item. Preserve every other field by in-memory before/after equality and exact-item readback. Never repair credential values under this metadata exception.

## 2. Validate the candidate and its write contract

1. Resolve the interpreter from the runner's `PYTHON_BIN` configuration and execute the focused regressions through that interpreter. Tie the current-generation assertion to the single active B013 registry entry, preserving immutable-item and dedicated-channel checks; historical suffix assertions otherwise become stale after an approved replacement.
2. Run the full read-only dedicated canary under the canonical lock with isolated state, for example `MGS_B013_DTR_DRY_RUN=1 MGS_B013_DTR_STATE=<isolated-state> bash <candidate-runner>`. Confirm complete composed-identity coverage and healthy capability before exposing the new registry entry.
3. Test the actual Sheet payload, not only a mapping helper: sorting must change the destination row, reassigned identities must receive no write, new assignments must await their own scan, duplicate identities must fail closed, and unknown observations must preserve current markers. Reproduce the stale-row payload against the backed-up implementation, then require the corrected payload and regression suite to pass.
4. Treat a blank auxiliary `PG` count as unavailable, not as an invalid composed account identity or numeric zero. Validate nonblank page counts as bounded plain integers before persisting them, but do not block an otherwise valid account-link scan solely because one page-count cell is empty. If a temporary validator fails before probing/writing, prove the untouched state, preserve that failed receipt, fix only the validator and resume the same cutover without resetting completed work.

## 3. Establish and reconcile the new baseline

1. Start fresh app-scoped state while preserving the predecessor backup. Keep both scheduled jobs paused and notifications contained during baseline and clean repeat; do not inherit predecessor verdicts, restriction incidents or cooldowns.
2. Immediately before marker writes, reload the canonical Sheet and remap each completed observation by composed `User + Segurador` identity to its current row and marker. Reject missing or duplicate identity components. Skip identities reassigned away after capture and leave newly assigned identities for their next scan; preserve unknown markers. Equal identity sets do not establish row stability, and movement alone does not identify who reordered the Sheet.
3. If a scope guard denied stale-row writes, preserve that failed receipt and the completed observations. First prove whether a partial write occurred. When no stale payload landed, repair only the missing Sheet layer using fresh identity mapping, read back exact markers, and run a full clean repeat. Do not reset the app baseline or rerun completed probes merely to retry the denied payload.
4. Read parity through a fresh Service Account consumer. Compare by composed identity, not the stored observation's old row number. Require the clean repeat to need no further marker updates before reactivation.

## 4. Reactivate and prove scheduled execution

1. Resume only the existing day/night jobs on their unchanged schedules and preserve unrelated pauses. Read both jobs back after the writes; successful resume responses alone are not closure.
2. Require a complete native cycle with target observation timestamps after reactivation, healthy capability, no Sheet sync error and fresh identity/marker parity. A lock-skip may return scheduler status `ok` without scanning, so require the target-specific state evidence as well.
3. Verify any genuine automatic alert by exact message readback; do not force an extra notice merely to demonstrate activation. Validate tables larger than 30 rows across every continuation: `fmt_pending_rows` must not silently slice `failures[:30]`. Let the existing `code_blocks` splitter preserve every confirmed row and test row totals plus Discord message-size limits against a realistic high-cardinality state. A renderer repair affects subsequent alerts only; do not claim an older truncated card was retroactively corrected. Close with the current app, preserved channel, scheduled health and latest linked/assigned counts, distinguishing remaining account-link gaps from app health.

## Long-cycle execution

Use a silent tracked process when a full DTR cycle exceeds the foreground transport window, and consume its result before closure or another writer. A bounded process-wait timeout is not an operation failure. After a terminated foreground canary, reconcile side effects and prove no writer remains before retrying under the same lock; preserve the interrupted receipt rather than overwriting it.
