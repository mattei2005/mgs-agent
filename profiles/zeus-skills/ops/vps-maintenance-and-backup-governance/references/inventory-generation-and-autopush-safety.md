# Inventory Generation and Auto-Push Safety

Use this reference when a maintenance job regenerates a large JSON inventory/report inside a Git repository that is automatically committed or pushed.

## Current execution contract — overrides historical snippets

- Keep every temporary component and final staged output outside the watched repository, on the canonical profile scratch/TMPDIR and the same filesystem needed for atomic replace. Do not use `/tmp` or create watched `OUT.tmp.*` artifacts for Hermes sessions.
- Track temporary paths and their provenance explicitly. Retain failed or unfinished components until exact disposal is authorized; do not install automatic trap/finally deletion merely to recover an inventory writer. A validated output and a pending temporary-workspace cleanup are separate outcomes.
- Preserve healthy native batching and wait its remaining configured window. A narrowly authorized producer-startup catch-up is distinct from normal batching; do not manufacture events, replay an old blob or shorten settings just to close an operation faster. The current full-VPS cleanup reference owns synchronization closure.
- Re-read shared inventory immediately before a record-level upsert and preserve all unrelated collections/fields. Stage outside Git, compare the canonical source version before atomic replacement and re-read the exact ID afterward; atomic rename alone does not prevent stale-document lost updates.
- Choose the inventory collection from the real producer contract before creating an operational record. `scripts/infra-discovery.sh` rebuilds `data_files` as generated `{path,size_bytes,md5,modified_at}` rows, while it explicitly preserves `runtime_artifacts`. Store durable custom IDs, approvals, backup dependencies and closure receipts in `runtime_artifacts`, not `data_files`. Loss of a custom `data_files` row after native regeneration is a schema-placement error, not evidence of unauthorized deletion or a stale writer; restoring it to the same generated list only recreates the failure. Migrate only owned IDs from their proven Git/receipt images to the preserved collection, keep immutable receipts unchanged, test the producer's native collection-preservation semantics and verify exact-ID readback.
- If a closure record vanished during concurrent work, first reconcile audit → current inventory → REPORT-INFRA → Git → sessions and inspect whether its collection is generated or preserved. Recover only the exact owned record proven by a prior Git revision and surviving sealed result/approval/report; merge its current validated outcome into the appropriate preserved collection in the latest document, require one matching ID and retain the regeneration/omission commit in a separate recovery receipt. Do not restore the whole old inventory, attribute an unknown writer, replay deletion or resend the already-delivered report. Verify the repaired record and final result hash in the remote-contained commit before closure.

## Canonical checkpoint validation blocked by unrelated metadata

When a canonical checkpoint upsert fails global validation, inspect the exact malformed row and current schema before retrying. Reconcile that row with audit, inventory, its report and committed image; preserve the owning executor, semantic state, next step and authority. If the sole defect is a missing required metadata timestamp, repair only that field through a latest-document compare-and-replace, stamp the actual repair time and audit the provenance. Do not restore an old whole registry, invent the historical write time, change the unrelated business outcome or bypass validation. Then rerun the original canonical upsert and global validator, and disclose the metadata-only repair in the operation evidence.

## Failure class

Two independent hazards can combine:

1. **Process argument overflow:** a shell script stores large JSON documents in variables and passes each one to `jq --argjson`. The kernel counts the expanded payload against `ARG_MAX`, so the final `jq` invocation can fail with `Argument list too long` even though every component is valid JSON.
2. **Auto-push race:** the generator creates a temporary component directory under the repository. A concurrent auto-commit may stage and push that directory before the generator removes it. From that point it is tracked content; later cleanup appears as a Git deletion and must not be treated as ordinary untracked-temp cleanup.

The durable lesson is not that `jq` or auto-push is unreliable. The implementation must avoid transporting large documents through argv and must keep transient work outside the watched repository.

## Safe generator design

1. Create component files and the final staged output outside the watched repository, using the current execution contract's scratch/staging location.
2. Before planning atomic publication, compare the staging and destination filesystem devices. If they differ, choose an approved same-filesystem staging location outside the repository; do not fall back to a watched temporary sibling.
3. Record every temporary path, creation purpose and owning phase. Preserve components on failure; disposal is a separate exact-target gate, not an exit trap.
4. Write each JSON component to a separate file and validate it.
5. Use `jq --slurpfile name component.json` (or `--rawfile` for text), then reference `$name[0]` in the assembly expression. Keep only small scalar metadata in `--arg`/`--argjson`.
6. Validate the assembled JSON with `jq -e .` before publication.
7. Publish through the producer's established lock/version-comparison path. For a shared inventory, re-read and merge only owned records into the latest document before atomic replacement; do not overwrite unrelated concurrent fields.
8. Read back the exact published IDs and values, then verify their remote-contained revision. Record preserved temporary components separately and remove them only under the applicable disposal authorization.

### Minimal assembly pattern — preparation only

```sh
PARTS="$(mktemp -d "${TMPDIR:?canonical profile scratch required}/inventory.parts.XXXXXX")"
TMP_OUT="$PARTS/final.json"

# Fail with the workspace preserved if atomic publication would cross devices.
test "$(stat -c %d "$PARTS")" = "$(stat -c %d "$(dirname "$OUT")")" || exit 1

printf '%s\n' "$CRONS_JSON" > "$PARTS/crons.json"
printf '%s\n' "$SCRIPTS_JSON" > "$PARTS/scripts.json"

jq -n \
  --arg updated_at "$NOW" \
  --slurpfile crons "$PARTS/crons.json" \
  --slurpfile scripts "$PARTS/scripts.json" \
  '{updated_at: $updated_at, crons: $crons[0], scripts: $scripts[0]}' \
  > "$TMP_OUT"

jq -e . "$TMP_OUT" >/dev/null
printf '%s\n' "$TMP_OUT"
# Hand this validated artifact to the producer's guarded publication path.
# Keep PARTS recorded; publication does not authorize workspace deletion.
```

## Auto-push reconciliation after a failure

Before cleaning a leftover path inside the repository:

1. Check current Git status and the latest local/remote commits.
2. Determine whether the path is untracked, staged, committed locally, or already present on the remote.
3. Reconcile concurrent provenance using the MGS order: audit log → infra inventory → REPORT-INFRA → Git → session history.
4. If still untracked and definitely generated by the current run, normal temporary cleanup rules apply subject to current authorization policy.
5. If tracked or pushed, **do not continue the original cleanup blindly**. First restore/reconcile any in-flight deletion so auto-push cannot publish a partial cleanup.
6. Preserve a copy outside the repository and validate file count, bytes, and a deterministic tree hash.
7. Request the Critical Subset confirmation required for removing tracked files/directories, naming the exact root, count, bytes, operational impact, backup path, and rollback method.
8. After authorized removal, validate the canonical auto-commit/auto-push path and confirm the remote commit no longer contains the artifact. Inspect effective batch target, quiet period, maximum wait and the current batch's start before choosing a polling deadline. Allow the remaining configured window plus push/readback margin, but keep each foreground observation below the actual enclosing tool deadline rather than assuming a larger requested timeout extends it. Return a structured pending result when that observation window expires, preserve completed predicates, and continue against the same native batch. After a transport timeout, reconcile any surviving observer and receipt before launching another loop; never repeat deletion or manufacture watcher events to repair a readback delay. A short wait proves only that convergence was not yet observed, not an outage or permission to change batching.
9. Use canonical catch-up only for a proven missed-event/startup gap, not to accelerate a healthy active batch. After current-PID readiness, make one byte-identical rewrite of the **latest readback** of an already-authorized dirty file, then wait through its configured boundary. Re-read and hash immediately before any separately justified retry, verify the intended record is still present, and write only those fresh bytes. Never replay a cached inventory/checkpoint blob across quiet intervals: another authorized writer may have updated it.
10. After every catch-up attempt, compare the pre/post content hashes and inspect audit → inventory → REPORT-INFRA → Git. Any unexpected hash change stops acceleration and triggers reconciliation; do not retry from the stale blob. If the operation's exact record is already present in a remote-contained commit, a later scoped dirty state from another attributed writer does not invalidate that closure and must not be forced clean. Record the containing commit and leave the concurrent writer's state untouched.
11. A timeout followed by successful canonical convergence is a resolved delay, not a persistent auto-push outage. Before escalating to manual versioning, and again when its approval arrives, run `git fetch origin main`, resolve one concrete remote revision with `git rev-parse origin/main`, compare scoped files using `git show REV:PATH`, and read the exact owned inventory/checkpoint IDs from that same revision. If delivery already passed, do not create a redundant manual commit; the approval permits the scoped intervention but does not require repeating an effect already achieved.
12. Preserve the earlier blocked receipt and sealed operational result unchanged; write a separate resolution receipt with the containing revision, exact checked artifact count, method actually used and whether manual intervention remained necessary. Supersede stale blocked fields in the owned inventory/checkpoint and reconcile the existing report rather than publishing a duplicate. Treat these newly written closure records as a second delivery boundary: wait through native batching, fetch again and verify their actual remote blobs and intended record fields before declaring the synchronization pendency closed. Do not create another versioned receipt solely to attest to the delivery of the previous receipt, because that creates an endless closure chain.

## Deliberately ignored observations versus undelivered artifacts

Before constructing or running a remote-closure poller, classify every required path. Run `git status --short -- PATH`, `git ls-files --error-unmatch -- PATH` and `git check-ignore -v -- PATH`; a clean working-tree status does not prove the path is tracked or remotely preserved. Build separate acceptance predicates for versioned artifacts, exact records inside shared JSON stores, and deliberately local evidence. An intentionally ignored audit log requires local exact-event readback, not an impossible remote-blob condition. Check every `git show REV:PATH` return code before decoding JSON or testing membership in its output; retain independently completed predicates when one path is unavailable instead of crashing the whole collector or treating missing output as success.

If an ignore rule deliberately excludes raw operational state, do not force-add it, rename it to evade the rule or loosen the policy merely to satisfy a closure assertion. Preserve the raw observation in a private durable evidence store, verify its size/hash and publish only an allowed compact provenance index with the retained location and recovery purpose. Keep any needed working copy labeled as active preparation state, not pre-existing reclaim. Verify the public index remotely and the private counterpart locally; disclose that split instead of claiming the raw observation was uploaded or that local preservation proves offsite recovery.

For shared inventories and checkpoint stores, read the exact owned IDs from the remote revision and compare their intended final fields. Before starting a wait loop, exercise its acceptance predicate once against the just-written local records and inspect the controller's normalization: `mgs-knowledge-control.py checkpoint-upsert` persists lowercase state values, so comparing a mixed-case input enum literally can leave an already-delivered checkpoint falsely pending. Derive the expected persisted fields from the controller contract plus exact local readback, then compare those same fields at one frozen remote revision; do not broadly lowercase arbitrary identifiers or accept a different semantic state. If artifact blobs and owned records are present but closure still fails, project only the failing field names and expected/actual non-secret values and repair the comparator before waiting again. Do not demand byte identity of an entire concurrently changing registry or force unrelated writers clean when the operation's own records are already preserved.

## Verification checklist

- [ ] Generator syntax check passes
- [ ] Large components travel through files, not argv
- [ ] Component workdir is outside the Git repository
- [ ] Final output validates before atomic replacement
- [ ] Every component workspace is recorded as active, retained evidence or pending separately authorized disposal; no implicit deletion occurs
- [ ] Canonical inventory contains the expected new scripts/crons/data
- [ ] Git status and recent auto-push commits are reconciled
- [ ] No tracked artifact is deleted without Critical Subset confirmation
- [ ] Backup/tree hash exists before authorized tracked cleanup
- [ ] Inventory, audit event, checkpoint, and REPORT-INFRA readbacks agree

## Why the boundaries matter

Large JSON passed through external-command arguments can exceed `ARG_MAX`; component files plus `--slurpfile` avoid that transport limit. Watched temporary directories can become committed artifacts before a generator finishes, turning casual cleanup into tracked deletion. Stage outside the repository, publish only validated final artifacts through the guarded writer, and reconcile tracked remnants before separately authorized disposal.
