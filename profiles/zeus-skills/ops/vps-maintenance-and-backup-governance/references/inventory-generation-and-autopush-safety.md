# Inventory Generation and Auto-Push Safety

Use this reference when a maintenance job regenerates a large JSON inventory/report inside a Git repository that is automatically committed or pushed.

## Current execution contract — overrides historical snippets

- Keep every temporary component and final staged output outside the watched repository, on the canonical profile scratch/TMPDIR and the same filesystem needed for atomic replace. Do not use `/tmp` or create watched `OUT.tmp.*` artifacts for Hermes sessions.
- Track temporary paths explicitly. The shell cleanup traps and `rm` commands below are historical examples, not current deletion authorization; exact disposal follows AGENT.md/Critical Subset. Do not add automatic trap/finally deletion merely to recover an inventory writer.
- Preserve healthy native batching and wait its remaining configured window. A narrowly authorized producer-startup catch-up is distinct from normal batching; do not manufacture events, replay an old blob or shorten settings just to close an operation faster. The current full-VPS cleanup reference owns synchronization closure.
- Re-read shared inventory immediately before a record-level upsert and preserve all unrelated collections/fields. Stage outside Git, compare the canonical source version before atomic replacement and re-read the exact ID afterward; atomic rename alone does not prevent stale-document lost updates.
- Choose the inventory collection from the real producer contract before creating an operational record. `scripts/infra-discovery.sh` rebuilds `data_files` as generated `{path,size_bytes,md5,modified_at}` rows, while it explicitly preserves `runtime_artifacts`. Store durable custom IDs, approvals, backup dependencies and closure receipts in `runtime_artifacts`, not `data_files`. Loss of a custom `data_files` row after native regeneration is a schema-placement error, not evidence of unauthorized deletion or a stale writer; restoring it to the same generated list only recreates the failure. Migrate only owned IDs from their proven Git/receipt images to the preserved collection, keep immutable receipts unchanged, test the producer's native collection-preservation semantics and verify exact-ID readback.
- If a closure record vanished during concurrent work, first reconcile audit → current inventory → REPORT-INFRA → Git → sessions and inspect whether its collection is generated or preserved. Recover only the exact owned record proven by a prior Git revision and surviving sealed result/approval/report; merge its current validated outcome into the appropriate preserved collection in the latest document, require one matching ID and retain the regeneration/omission commit in a separate recovery receipt. Do not restore the whole old inventory, attribute an unknown writer, replay deletion or resend the already-delivered report. Verify the repaired record and final result hash in the remote-contained commit before closure.

## Failure class

Two independent hazards can combine:

1. **Process argument overflow:** a shell script stores large JSON documents in variables and passes each one to `jq --argjson`. The kernel counts the expanded payload against `ARG_MAX`, so the final `jq` invocation can fail with `Argument list too long` even though every component is valid JSON.
2. **Auto-push race:** the generator creates a temporary component directory under the repository. A concurrent auto-commit may stage and push that directory before the generator removes it. From that point it is tracked content; later cleanup appears as a Git deletion and must not be treated as ordinary untracked-temp cleanup.

The durable lesson is not that `jq` or auto-push is unreliable. The implementation must avoid transporting large documents through argv and must keep transient work outside the watched repository.

## Safe generator design

1. Create the final temporary output beside the canonical file only when same-filesystem atomic rename is required.
2. Create all bulky component files outside the repository, preferably under `/run/<job>.parts.XXXXXX` for short root jobs or `/tmp/<job>.parts.XXXXXX` otherwise.
3. Install an exit trap immediately after creating temporary paths. The trap must remove both the final temporary output and the external component directory.
4. Write each JSON component to a separate file and validate it.
5. Use `jq --slurpfile name component.json` (or `--rawfile` for text), then reference `$name[0]` in the assembly expression. Keep only small scalar metadata in `--arg`/`--argjson`.
6. Validate the assembled JSON with `jq -e .` before replacing the canonical file.
7. Use `mv`/`os.replace` only after validation; remove the external component directory; disable the trap after explicit cleanup.
8. Re-run the generator and verify both the canonical readback and absence of leftover component directories.

### Minimal assembly pattern

```sh
PARTS="$(mktemp -d /run/inventory.parts.XXXXXX)"
TMP_OUT="$(mktemp "${OUT}.tmp.XXXXXX")"
trap 'rm -f "$TMP_OUT"; rm -rf "$PARTS"' EXIT

printf '%s\n' "$CRONS_JSON" > "$PARTS/crons.json"
printf '%s\n' "$SCRIPTS_JSON" > "$PARTS/scripts.json"

jq -n \
  --arg updated_at "$NOW" \
  --slurpfile crons "$PARTS/crons.json" \
  --slurpfile scripts "$PARTS/scripts.json" \
  '{updated_at: $updated_at, crons: $crons[0], scripts: $scripts[0]}' \
  > "$TMP_OUT"

jq -e . "$TMP_OUT" >/dev/null
mv "$TMP_OUT" "$OUT"
rm -rf "$PARTS"
trap - EXIT
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
8. After authorized removal, validate the canonical auto-commit/auto-push path and confirm the remote commit no longer contains the artifact. Do not treat a short passive wait as proof of failure: inspect the watcher's real batching controls first. A watcher may remain healthy while intentionally waiting for `BATCH_TARGET` or `BATCH_MAX_WAIT_SECONDS` (for example, one batch with a 600-second maximum will not flush during a 120-second poll).
9. If authorized changes are already dirty but the watcher is waiting for more batches—or started after those events—use the canonical catch-up path instead of committing manually. Prefer one byte-identical rewrite of the **latest readback** of an already-authorized dirty file, then wait through the configured quiet/max-wait boundary. If operational timing truly requires several separated events, re-read and hash the file immediately before **each** rewrite, verify the intended record is still present, and write back only those freshly read bytes. Never cache one blob and replay it across multiple quiet intervals: inventory/checkpoint files have concurrent writers, and a stale replay can overwrite an authorized update.
10. After every catch-up attempt, compare the pre/post content hashes and inspect audit → inventory → REPORT-INFRA → Git. Any unexpected hash change stops acceleration and triggers reconciliation; do not retry from the stale blob. If the operation's exact record is already present in a remote-contained commit, a later scoped dirty state from another attributed writer does not invalidate that closure and must not be forced clean. Record the containing commit and leave the concurrent writer's state untouched.
11. A timeout followed by successful canonical catch-up is a resolved convergence delay, not a persistent auto-push outage. Record the timeout and the final readback honestly, without turning the transient delay into a durable negative claim about the watcher.

## Verification checklist

- [ ] Generator syntax check passes
- [ ] Large components travel through files, not argv
- [ ] Component workdir is outside the Git repository
- [ ] Final output validates before atomic replacement
- [ ] A normal run leaves zero component directories
- [ ] Canonical inventory contains the expected new scripts/crons/data
- [ ] Git status and recent auto-push commits are reconciled
- [ ] No tracked artifact is deleted without Critical Subset confirmation
- [ ] Backup/tree hash exists before authorized tracked cleanup
- [ ] Inventory, audit event, checkpoint, and REPORT-INFRA readbacks agree

## Session-derived example

An MGS infrastructure inventory grew until preserved runtime-artifact JSON pushed the final `jq --argjson` invocation beyond `ARG_MAX`. Replacing large arguments with component files plus `--slurpfile` fixed generation. A temporary component directory had initially been placed under `data/`; auto-push committed it during the run. The safe correction was to move future components to `/run`, restore the tracked directory before auto-push could publish an unreviewed deletion, preserve a validated backup, and defer removal to explicit Critical Subset confirmation.
