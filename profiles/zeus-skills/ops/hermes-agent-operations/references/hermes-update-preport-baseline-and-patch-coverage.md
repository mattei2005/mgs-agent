# Hermes update — pre-port baseline and patch-coverage gate

Use this reference before porting a large local Hermes customization surface to a moving upstream.

## Why this gate exists

A narrow patch guard can be green while the wider locally modified test surface is already red. Likewise, `ensure-hermes-mgs-patches.sh` can know about newer feature patches that a separately hardcoded updater precheck never tests. Both conditions create false confidence before the port begins.

## Required sequence

1. Fetch once, capture `HEAD`, target upstream SHA, latest public tag, timestamp, and ancestry. Freeze that SHA for the port; do not chase later commits mid-port.
2. Reconcile recently completed agent/thread work before snapshotting the local surface. Use direct operational threads first, then audit log, inventory/REPORT-INFRA, Git, and session history only as needed. Confirm live configs still match versioned mirrors.
3. Capture the complete local surface:
   - tracked, staged, and untracked files;
   - local files also changed upstream;
   - untracked-path collisions with the target;
   - current canonical patch artifacts and guard invariants.
4. Run a **broad baseline suite** over every locally modified production module and its associated tests, not only the tests named by the current patch guard. Record exact passed/failed/subtest counts. The baseline must be green before semantic port work starts.
5. Treat a test-only compatibility failure as a real baseline gate. Example class: production starts passing a new keyword argument such as `suppress_embeds`, but an older fake `channel.send()` has a fixed signature. Update all relevant fakes to accept the production contract (explicit argument or `**kwargs`) and rerun the broad suite. Do not mislabel this as a production outage, but do not port from a red baseline.
6. Eliminate dual patch inventories:
   - derive the updater precheck list from the canonical guard/manifest, or validate exact set equality;
   - require all post-consolidation feature patches to be represented by the newest consolidated runtime artifact or explicitly tested as supplemental patches;
   - fail closed if the guard references artifacts omitted by precheck, or if precheck tests stale artifacts no longer canonical.
7. In a clean worktree at the frozen SHA, require:
   - consolidated patch applies cleanly;
   - no untracked collision;
   - broad baseline plus target-upstream overlap tests pass;
   - fresh-checkout reproduction succeeds.
8. Only then stage the live update without restart. Prefer reversible `git stash push -u` and `git merge --ff-only <frozen-sha>` over `git reset --hard` or a moving `origin/main` target.

## Preservation proof for a large customization surface

Do not equate “patch applied” with “nothing was lost.” Build an explicit preservation proof:

1. Before porting, create a manifest of every tracked modification and untracked MGS file with path, size, SHA-256, and tracked status. Archive those files and the binary Git diff separately; verify both archives by checksum.
2. Materialize the live customization surface as one snapshot commit in an isolated clone based on the installed `HEAD`, then cherry-pick that commit onto the frozen target. Resolve conflicts semantically: retain new upstream behavior first, then reintroduce the MGS invariant with a regression test.
3. Generate the consolidated binary patch from `frozen-target..validated-port`; never synthesize it from a partial list of old patch files.
4. In a second clean checkout, require `git apply --check`, apply, and `git apply --reverse --check`.
5. Compare the pre-port manifest path set with the final port diff. Every original path must either remain in the final patch or be explicitly proven byte/behavior-equivalent to upstream. After live staging, compare every final port path byte-for-byte with the staged checkout.

This separates three claims that must not be conflated: all original paths were accounted for, the consolidated artifact is reproducible, and the live stage exactly matches the reviewed port.

For the concrete semantic-merge pattern, one-shot Honcho teardown diagnosis, exact guard predicates, OAuth gate, and restart-snapshot expansion discovered during a 976-commit port, load `references/hermes-update-2026-07-19-port-lifecycle.md`.

## Test isolation and failure classification

- Run compatibility tests with a fresh `HERMES_HOME` and remove profile-specific routing variables such as Discord allowlists. Tests must not inherit production channel scope, bot policy, or session state.
- Build an isolated target venv with the exact relevant extras before interpreting provider/platform failures. A missing optional extra is a test-environment gap, not a runtime regression.
- If a broad suite is mostly green but failures suggest module-order pollution or mocked SDK leakage, rerun every failed module together in a fresh Python process. Record both results: broad-suite count and isolated rerun count. Do not call the port green until every port-relevant failure is green in isolation or is proven to fail identically on clean upstream.
- Production keyword changes such as `suppress_embeds`/`suppress` require updating all fake `send()`/`edit()` signatures and assertions. Also isolate tests from live env values rather than weakening production behavior to satisfy old fixtures.
- Filesystem timestamp tests must force a distinct `mtime_ns`; back-to-back writes can share one timestamp tick and create false cache failures.
- Tests for a legacy/fallback data source must mock the new primary source. Otherwise live state (for example `state.db`) can win before the fixture under test is consulted.

## Safe staged dependencies and post-merge hooks

- Do not mutate the active production venv during the no-restart stage. Clone it to a versioned next-venv (prefer `cp -a --reflink=auto` when supported), then use `uv pip install --python <next>/bin/python -e '<repo>[active-extras]'` to upgrade the target while preserving optional packages already present. Avoid repeated `uv sync --extra ...` on that production candidate: extras omitted from a later sync can be uninstalled. Run the full guard/config checks with an overridable `PYBIN`. Swap/activate that venv only inside the separately authorized detached restart window.
- Before staging, fingerprint `HEAD`, porcelain status, tracked binary diff, cached diff, service PIDs, patch SHA, and target SHA. Abort on any drift.
- A Git post-merge hook may automatically run the MGS guard and apply the consolidated patch. Therefore, after `merge --ff-only`, inspect the guard log and run reverse-check before issuing a second explicit `git apply`. If the second apply returns nonzero because the patch is already present, do not replay or roll back blindly: verify target `HEAD`, patch reverse-check, expected status count, and byte identity against the reviewed port. Record the wrapper nonzero honestly while classifying the actual staged state from readback.
- Keep the pre-update stash by immutable commit hash; never pop it during staging. Prove it is a complete rollback artifact: require the third parent created by `stash push -u`, compare tracked and untracked path sets with the pre-port manifest, and hash every stashed file against that manifest. Rollback must avoid `git reset --hard` and preserve the stash until post-restart acceptance is complete.
- Treat `npm install-scripts approve --dry-run` as potentially mutating on npm 12: it can still add `allowScripts` entries to `package.json`. For read-only inspection, prefer `npm install-scripts ls --all --json`. If an approval dry-run is used, fingerprint Git status first and inspect `git diff -- package.json` immediately; restore any unintended write before accepting the staged surface.
- Classify blocked npm install scripts by deployed surface instead of treating every warning as a gateway blocker. Run actual import/version probes for the packages MGS uses, rerun Web/TUI builds and `npm audit`, and isolate Electron/node-pty native failures as desktop-only unless an active service imports them. Do not weaken npm script policy merely to make optional desktop modules load.
- Repeat the attribution and freeze gate immediately before activation: audit log → inventory → REPORT-INFRA → Git → session history. Require no uncommitted or in-flight concurrent profile/skill/runtime work. An authorized concurrent change is not an anomaly, but it invalidates the previous activation snapshot; extend the finalizer target set, rerun affected validation, and freeze new hashes before scheduling any restart.

## Verification output

Report separately:

- upstream delta from installed `HEAD`;
- newly arrived commits since the prior plan;
- commits since the latest public tag;
- local tracked/untracked counts;
- overlap files;
- patch guard artifact count versus updater-precheck coverage;
- broad baseline result;
- remaining gate before live staging.

A plan is not ready when either patch coverage or the broad baseline is unresolved.