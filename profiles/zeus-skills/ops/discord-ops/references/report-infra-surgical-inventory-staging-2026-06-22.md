# REPORT-INFRA — Surgical inventory staging when worktree has unrelated drift

## Trigger
Use this when processing a REPORT-INFRA and `/root/mgs-agent/data/infra-inventory.json` already has unrelated unstaged changes from another monitor/agent/auto-discovery run.

## Lesson
Do not commit the whole current worktree version of `infra-inventory.json` just because the report requires an inventory update. A dirty inventory can contain unrelated state updates (for example Honcho monitor sizes/state hashes) and will pollute the REPORT-INFRA commit.

## Safe pattern
1. Validate the reported artifacts normally: syntax/JSON checks, runtime checks when safe, hashes, and semantic confirmation.
2. Build the intended inventory mutation from `HEAD:data/infra-inventory.json`, not from the already-dirty worktree.
3. Generate a patch that contains only the report-specific inventory hunks.
4. Stage reported artifacts normally, then apply only that patch to the index:
   - `git reset -- data/infra-inventory.json`
   - `git apply --cached /tmp/<report>-infra-only.patch`
5. Inspect `git diff --cached -- data/infra-inventory.json` before commit. It should contain only:
   - `_meta` update for the report;
   - inventory entries for the reported paths/IDs;
   - no unrelated monitor/state/runtime drift.
6. Run `git diff --cached --check` and commit only the staged report scope.

## Recovery if already committed too broad
If you notice the commit included unrelated inventory hunks:
1. `git reset --soft HEAD~1`
2. `git reset -- data/infra-inventory.json`
3. Re-apply the report-only inventory patch to the index with `git apply --cached`.
4. Reinspect cached diff and recommit.

## Pitfall
`git commit -- <paths...>` still commits the entire staged version of a listed path. If `infra-inventory.json` is staged with unrelated hunks, path-limited commit is not enough. The index must be surgical before committing.