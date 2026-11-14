# B013 replacement validation and recovery

Apply the main skill's replacement authorization and acceptance gates. Start with this compact dedicated-route sequence; consult the specific replacement sections of route-pack-05 only for additional branches, not its historical cutover narratives.

## 1. Resolve identity and preserve rollback

1. Read the active registry entry, its immutable vault item, the dedicated runner, predecessor state, both day/night jobs and unrelated pause sets. Resolve the runner path from live inventory or the job's script resolution rather than assuming it lives in the repository scripts directory.
2. Back up the affected runner, registry, state, pause configuration and any test being changed before production edits. Keep credential values in memory, never in the rollback bundle.
3. Require a different Meta app ID from the saved predecessor snapshot, matching replacement `app_name`, valid app-bound `debug_token`, successful metadata and `/me` reads, and complete applicable role enumeration. Prove DTR capability with the dedicated runner; generic roles do not establish account links.
4. If the exact replacement title and fresh `/me` agree but a non-secret principal-profile note still names the predecessor, correct only that exact profile line in the same item. Preserve every other field by in-memory before/after equality and exact-item readback. Never repair credential values under this metadata exception.

## 2. Validate the candidate and its write contract

1. Resolve the interpreter from the runner's `PYTHON_BIN` configuration and execute the focused regressions through that interpreter. Tie the current-generation assertion to the single active B013 registry entry, preserving immutable-item and dedicated-channel checks; historical suffix assertions otherwise become stale after an approved replacement.
2. Run the full read-only dedicated canary under the canonical lock with isolated state, for example `MGS_B013_DTR_DRY_RUN=1 MGS_B013_DTR_STATE=<isolated-state> bash <candidate-runner>`. Confirm complete composed-identity coverage and healthy capability before exposing the new registry entry.
3. Test the actual Sheet payload, not only a mapping helper: sorting must change the destination row, reassigned identities must receive no write, new assignments must await their own scan, duplicate identities must fail closed, and unknown observations must preserve current markers. Reproduce the stale-row payload against the backed-up implementation, then require the corrected payload and regression suite to pass.

## 3. Establish and reconcile the new baseline

1. Start fresh app-scoped state while preserving the predecessor backup. Keep both scheduled jobs paused and notifications contained during baseline and clean repeat; do not inherit predecessor verdicts, restriction incidents or cooldowns.
2. Immediately before marker writes, reload the canonical Sheet and remap each completed observation by composed `User + Segurador` identity to its current row and marker. Reject missing or duplicate identity components. Skip identities reassigned away after capture and leave newly assigned identities for their next scan; preserve unknown markers. Equal identity sets do not establish row stability, and movement alone does not identify who reordered the Sheet.
3. If a scope guard denied stale-row writes, preserve that failed receipt and the completed observations. First prove whether a partial write occurred. When no stale payload landed, repair only the missing Sheet layer using fresh identity mapping, read back exact markers, and run a full clean repeat. Do not reset the app baseline or rerun completed probes merely to retry the denied payload.
4. Read parity through a fresh Service Account consumer. Compare by composed identity, not the stored observation's old row number. Require the clean repeat to need no further marker updates before reactivation.

## 4. Reactivate and prove scheduled execution

1. Resume only the existing day/night jobs on their unchanged schedules and preserve unrelated pauses. Read both jobs back after the writes; successful resume responses alone are not closure.
2. Require a complete native cycle with target observation timestamps after reactivation, healthy capability, no Sheet sync error and fresh identity/marker parity. A lock-skip may return scheduler status `ok` without scanning, so require the target-specific state evidence as well.
3. Verify any genuine automatic alert by exact message readback; do not force an extra notice merely to demonstrate activation. Close with the current app, preserved channel, scheduled health and latest linked/assigned counts, distinguishing remaining account-link gaps from app health.

## Long-cycle execution

Use a silent tracked process when a full DTR cycle exceeds the foreground transport window, and consume its result before closure or another writer. A bounded process-wait timeout is not an operation failure. After a terminated foreground canary, reconcile side effects and prove no writer remains before retrying under the same lock; preserve the interrupted receipt rather than overwriting it.
