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

### Conflict and coverage details that must remain explicit

- A consolidated MGS commit may be cherry-picked onto the frozen upstream target instead of applying a raw patch. During conflict resolution, stage 2 is the frozen upstream side and stage 3 is the MGS side; archive both before editing so the semantic decision remains auditable.
- Do not require the final patch path count to equal the original manifest blindly. Compute three sets: original customized paths, final candidate paths, and clean-reproduction paths. Every original path absent from the candidate needs an upstream commit plus behavior-test evidence; every new candidate-only path needs a stated compatibility reason. Candidate and reproduction sets must still be equal and byte-identical.
- When a guard's semantic fallback is broadened for the new candidate, retest it against both the candidate and the untouched legacy runtime. A predicate that recognizes only the new implementation can make the production-active legacy state fail closed even though production itself did not drift.
- For upstream keyword/signature changes, update all affected fakes and fixtures to accept or assert the new contract. If a broad pack fails because another module polluted import state, preserve the broad result and rerun every failed module together in a fresh process. Call the behavior green only when all failures pass in that isolated rerun; do not erase or mislabel the order-dependent broad result.

### Separate candidate defects from external state

- A real provider smoke matrix must preserve the distinction between candidate code, profile config, and profile credential health. If a profile's actual OAuth refresh fails, record that blocker. An additional ephemeral smoke using the same profile config plus a known-valid credential may prove the candidate path, but it never converts the original credential failure into a pass.
- Before activation, classify profiles by runtime role. A credential failure in a non-gateway/default profile may be carried as a bounded exception only when Rodolfo explicitly authorizes that exception, its config check still passes, the candidate path has been proven with isolated valid authentication, and every production gateway profile passes its own exact live smoke. Preserve the failed profile as `known invalid / not modified`, never relabel it as green, and do not mutate its credential during the cutover.
- Classify dependency advisories by the shipped/runtime surface before deciding whether they block a gateway candidate. Do not run an automatic dependency fix against a frozen upstream lock merely to make the audit count green; record upstream Electron/build-chain findings separately from the Python gateway process and keep critical severity explicit.
- Candidate governance writers must be idempotent. A failure after inventory or audit mutation but before summary creation is a partial success: read back each durable target before retrying, deduplicate audit events by artifact/message identity, and allow atomic writers to create a new summary file with a safe default mode.

## 5. Venv/layout compatibility

A modern uv checkout commonly uses `.venv`, while an older MGS restart helper may resolve only `venv/bin/python`. Do not discover this after cutover.

- Prefer updating the resolver to accept both layouts.
- If compatibility with an already validated helper is required, create `venv -> .venv` in the candidate and validate Python, CLI, imports, and the helper's repository resolver through that path.
- Keep that compatibility symlink out of the candidate patch without accepting a dirty checkout: add the exact repository-local entry (for example `/venv`) to `.git/info/exclude`, then require both `readlink venv == .venv` and a clean `git status`. Because `.git/info/exclude` is not part of the candidate commit, freeze and validate the symlink target separately in the activation snapshot/preflight.
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
