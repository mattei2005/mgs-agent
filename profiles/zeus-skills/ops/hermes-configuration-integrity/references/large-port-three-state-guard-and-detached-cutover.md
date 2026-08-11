# Large Hermes ports: three-state guard and detached cutover

Use this reference when a frozen upstream target is hundreds or thousands of commits ahead and the consolidated MGS patch no longer applies cleanly.

## 1. Freeze and preserve before porting

- Freeze one exact upstream SHA; do not chase a moving branch during conflict resolution.
- Leave the active checkout, launcher, gateway PIDs, and profiles untouched.
- Create an independent candidate checkout plus a manifest/archive of every customized path and the original binary diff.
- Fingerprint the active launcher, runtime SHA, profile config hashes, and gateway PIDs before candidate work.

## 2. Port by three-way semantics

1. Apply the consolidated customization patch to the frozen target with `git apply --3way` in the independent candidate.
2. Resolve only actual unmerged files. Preserve upstream mechanisms and reinsert the MGS invariant; never choose an entire side merely because it compiles.
3. Search for conflict markers, stage resolved paths, run `git diff --cached --check`, and prove the staged path set matches the pre-port customization manifest.
4. When tests fail after an upstream refactor, inspect the target's current contract before changing production. Update stale fakes/fixtures only when the invariant remains intact; never weaken the behavioral assertion just to obtain green tests.

## 3. Materialize and test the candidate

- Build a candidate-local environment from the target lock, including the active extras. Prefer `uv sync --frozen` with the required extras.
- Run syntax/import probes from the candidate Python and assert `module.__file__` resolves inside the candidate.
- Run all test modules touched by the customization patch, then the canonical MGS post-upstream regression pack.
- Run `hermes config check` and read-only `status` for every live profile with config hashes before/after.
- Explicitly clear inherited test variables (`HOME`, `HERMES_HOME`, `HERMES_PROFILE`) before profile-aware CLI checks. A false “profile does not exist” after isolated tests is often an inherited test-home problem, not profile loss.
- Check that every procedure-named auditor exists before invoking it. If an optional auditor was retired, label the procedure drift and use the installed executable gates; do not treat `command not found` as a candidate regression or invent a pass.

## 4. Promote a reproducible patch and three-state guard

Generate the new canonical patch from the frozen upstream parent to the validated candidate commit. The guard must recognize three legitimate states:

1. **Legacy active runtime** — reverse-check of the legacy patch passes.
2. **Frozen clean target** — forward-check of the new patch passes.
3. **Validated candidate** — reverse-check of the new patch passes.

Fail closed if no known patch is present or applicable. Verify the guard in all three states. On a disposable clean target, apply the new patch, stage it, run `git write-tree`, and require the tree hash to equal the candidate commit tree. This is stronger than a path count or `git apply --check` alone.

## 5. Venv/layout compatibility

A modern uv checkout commonly uses `.venv`, while an older MGS restart helper may resolve only `venv/bin/python`. Do not discover this after cutover.

- Prefer updating the resolver to accept both layouts.
- If compatibility with an already validated helper is required, create `venv -> .venv` in the candidate and validate Python, CLI, imports, and the helper's repository resolver through that path.
- Keep versioned inactive wrappers such as `hermes-vNEXT-mgs`; make the canonical launcher switch atomic and preserve the exact prior wrapper as rollback.

## 6. Detached activation with rollback

- Never switch/restart inside the active Discord tool chain.
- Prepare an external finalizer, reply to the user first, then schedule it detached.
- Finalizer order: immutable hash preflight → atomic launcher switch → Ares → Atena → Zeus → systemd plus fresh Discord readiness → exact one-shot smoke per profile → inventory/audit/checkpoint → one REPORT-INFRA embed.
- If any restart, readiness, import, or smoke gate fails, atomically restore the prior wrapper and restart all gateways on the old runtime in the same safe order.
- Record `staged`, `scheduled`, `activated_validated`, `activation_failed_rolled_back`, and `rollback_failed` as distinct states.
- Keep external blockers separate: a successful Hermes activation must not close an Ubuntu Pro, vendor-backend, or other unrelated gate.

## Acceptance evidence

- Frozen target SHA and candidate commit
- Pre-port and candidate path-set equality
- Candidate-local dependency check
- Touched-surface tests and post-upstream regression totals
- Three-state guard results plus exact clean-target tree equality
- Profile config/status readbacks with unchanged hashes
- Prior/new wrapper targets and rollback path
- Detached restart order and fresh readiness markers
- Exact profile smokes
- Inventory, audit, checkpoint, REPORT-INFRA message ID and GET readback
