# Hermes read-only delta review without worktrees

Use this when another operator is running the mutating/precheck workflow, or when the task explicitly forbids fetches, reports, temporary worktrees, tests, guard execution, and file writes.

## Goal

Assess an installed Hermes revision against an already-present upstream ref and estimate MGS patch risk without changing repository or runtime state.

## Read-only evidence sequence

1. Set `GIT_OPTIONAL_LOCKS=0` for Git inspection.
2. Record exact refs and versions:
   - `HEAD`, `origin/main`, commit dates and subjects.
   - Read `[project].version` from `pyproject.toml` at each ref with `git show <ref>:pyproject.toml`.
   - Do not assume release tags exist locally.
3. Separate the versioned release boundary from moving `origin/main`:
   - Locate version-bump commits with Git history.
   - Count/stat `HEAD..release_commit` and `release_commit..origin/main` separately.
   - If `origin/main` contains post-release commits while retaining the same version, state that the review is valid for the exact reviewed SHA, not every future ref carrying that version.
4. Inventory existing MGS state:
   - tracked, staged and untracked paths;
   - canonical runtime patch and independent patches such as auto-reasoning;
   - guard references and invariants;
   - overlap between upstream-changed paths and MGS-modified paths.
5. Classify risk separately:
   - **textual apply risk**: whether patch old/context blocks still exist;
   - **semantic risk**: upstream and MGS touching the same lifecycle or behavior even when hunks do not collide;
   - **operational risk**: updater autostash/restart/`--replace` behavior.

## In-memory exact-context hunk scan

When worktrees and temporary indexes are forbidden, parse each unified patch in memory and compare every hunk's old-side sequence (context + removed lines) against the target blobs returned by `git show <ref>:<path>`.

Report per-file and total exact matches, for example `51/51`. Run it for:

- the latest `mgs-runtime-customizations-*.patch`;
- independent canonical patches such as `mgs-auto-reasoning-routing.patch`;
- the current tracked live diff.

Interpretation:

- All old-side blocks found exactly: strong evidence of low textual conflict.
- Any missing block: drift requiring actual `git apply --check` or manual inspection.
- This scan is **not** a substitute for the controlled precheck's real `git apply --check`; label it as a static read-only estimate.
- Searching anywhere in a blob can theoretically match duplicate code. For critical same-function overlaps, also compare hunk line ranges and inspect the function-level upstream delta.

## MGS-specific semantic review

Pay extra attention to:

- `gateway/run.py`: drain/restart, `resume_pending`, compression, delegation session routing, fallback refresh and per-turn reasoning.
- `plugins/platforms/discord/adapter.py`: authorization/pairing, slash interactions, approvals, auto-thread naming/member sync, bot-loop suppression, cleanup and captions.
- Tool registry/result-contract changes that can affect custom or plugin tools even without patch overlap.
- New upstream tests covering the changed lifecycle paths.

A clean textual scan can coexist with medium semantic risk. Do not collapse those into one "patch applies" verdict.

## Test recommendation shape

Split the post-update suite into:

1. MGS invariant tests: restart/resume, Discord bot/free-response, display cleanup, auto-reasoning and `py_compile` of critical modules.
2. New upstream intersection tests: cron drain, compression demotion/hygiene, async delegation session binding, fallback reload, Discord slash auth/defer and media caption delivery.

If an old nodeid from a playbook no longer exists, recommend the whole current test file or `pytest --collect-only`; do not present a stale nodeid as authoritative.

## Reporting requirements

- Conclusion first: proceed controlled / defer / port required.
- Give the exact reviewed target SHA.
- Distinguish release commit from post-release main commits.
- State that no files, worktrees, tests, guards, services or refs were changed.
- Re-read final Git status and distinguish pre-existing dirty state from changes made by the reviewer.
- Treat the controlled precheck output as authoritative when it becomes available.
