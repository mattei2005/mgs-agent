# Hermes large-port lifecycle case — 2026-07-19

Use this supporting case when a large upstream fast-forward overlaps the MGS runtime patch, or when a short-lived `hermes -z` smoke prints the expected answer but exits abnormally.

## Case boundary

- Installed base: `2ccfdb2db4eedf385f6c5b3fe722e183cee1b6de`
- Frozen target: `26480e6c57c3558442a73c2dffe313996b19417f`
- Upstream delta: 976 commits / 1,364 files
- Preserved pre-port surface: 37 paths, including 6 untracked paths
- Final consolidated surface: 39 paths after adding the one-shot lifecycle fix and its tests

These SHAs and counts are evidence for this case, not reusable target values.

## Reproducible port pattern

1. Run the live guard and broad baseline before porting.
2. Create a NUL-safe path list from tracked, staged, and untracked files. Save a binary diff, per-file SHA-256 manifest, and tar archive.
3. In an isolated shared clone at the installed base, materialize the exact live surface and commit it as one snapshot.
4. Cherry-pick the snapshot onto the frozen target. Resolve conflicts semantically rather than choosing whole-file `ours`/`theirs`, which would discard auto-merged non-conflicting customizations.
5. Preserve new upstream structure first, then reintroduce the MGS invariant at the new abstraction point. In this case:
   - upstream extracted Discord admission/dispatch, so MGS bot-loop guards moved into admission instead of restoring the removed inline handler;
   - upstream added asynchronous image-routing decisions, while MGS mid-turn steering still had to bypass native upload and emit local image markers;
   - reasoning resolution retained the new provider/model arguments plus MGS auto-routing;
   - restart recovery retained upstream helper structure but enforced silent chronological continuation for synthetic recovery events.
6. Generate one binary patch from `frozen-target..validated-port`.
7. Validate it in a second clean checkout with apply-check, apply, reverse-check, path-set comparison, and byte-for-byte comparison.
8. Stage live with `git stash push -u` plus `merge --ff-only <frozen-target>`. Preserve the stash by immutable SHA and verify all manifest hashes, including the third untracked parent.

## Short-lived CLI lifecycle failure

### Symptom

A real OpenAI Codex one-shot printed the expected final text, then CPython aborted with exit 134. Treating text presence as smoke success would have missed the failure.

### Diagnostic technique

Wrap `hermes_cli.main.main()` in a temporary Python launcher, catch `SystemExit`, enumerate live threads, flush the result, and use `os._exit(0)` only for diagnosis. The remaining threads identified the leak:

- `honcho-async-writer`
- `mem-sync_0`
- `honcho-sync`

A clean-up implementation already existed in `AIAgent.shutdown_memory_provider()`, but `hermes_cli.oneshot._run_agent()` returned without calling it.

### Durable fix

Wrap `agent.run_conversation()` in `try/finally` and call a dedicated lifecycle helper that:

1. snapshots `agent._session_messages`;
2. calls `shutdown_memory_provider(messages)`;
3. calls `agent.close()` afterward;
4. keeps cleanup best-effort so one cleanup failure does not hide the real one-shot result.

Memory shutdown must precede `agent.close()` because close clears the session messages. Add unit tests for call order and for close-after-memory-failure. A real provider smoke must require both the exact response and exit code 0.

## Patch-guard lessons

- A repair predicate must match the exact broken assignment or marker. A broad search such as any occurrence of `getattr(event, "internal", False)` can misclassify valid unrelated code and enter a repair branch that expects one replacement but finds zero.
- Keep source-level guard phrases contiguous when the guard uses line-oriented `grep`; splitting a required invariant across adjacent Python string literals makes the runtime text correct while the guard fails.
- Whenever the consolidated patch adds a runtime file, extend the detached restart finalizer's hash snapshot and `py_compile`/import surface before scheduling activation. For this case, `hermes_cli/oneshot.py` had to be added.

## OAuth and activation gates

For root or profile OpenAI Codex readiness:

1. `hermes auth status openai-codex` without printing credential values;
2. if invalid, run `hermes auth add openai-codex --type oauth --no-browser` and deliver the device URL/code immediately;
3. require `logged in` readback;
4. run a real exact-response one-shot and require rc=0.

Activation remains separate from staging. Freeze runtime/config hashes, schedule the detached finalizer with non-Zeus agents in caller order and Zeus last, and use a separate post-restart validator before marking the inventory item active.

## Acceptance evidence from this case

- Clean apply/reverse and 39/39 byte comparison: PASS
- Guard: 774 tests + 6 subtests PASS
- Web and TUI builds: PASS
- npm audit: 0 vulnerabilities
- Root/Zeus/Atena/Ares Codex smokes: exact response and rc=0 after lifecycle repair
- Profiles' config/SOUL: byte-identical to the pre-update backup
