# Controlled Hermes port preservation audit

Use this reference to audit whether a staged Hermes update preserved the complete MGS customization surface when upstream has absorbed part of a local patch.

## Class-level procedure

1. Freeze one upstream SHA and keep `origin/main` as a separate observation. Do not silently chase commits that arrive after the freeze; report their exact count at the activation gate.
2. Manifest every tracked, staged, and untracked local path with size and SHA-256. Archive the files and binary diff separately, then verify the archive and checksum manifest.
3. Build a snapshot commit from the exact local surface and cherry-pick it onto the frozen target.
4. A reduced final patch is valid only when every removed path is explicitly classified as upstream-equivalent. Record the upstream evidence commit, equal-or-stronger behavior, and regression tests for the active path. Unaccounted paths are a hard failure.
5. Update guards to accept either the legacy MGS shape or the complete stronger upstream shape. Do not keep redundant local helpers solely to satisfy an old grep.
6. In a second clean checkout, require apply-check, apply, reverse-check, path-set equality including newly created files, and byte identity against the reviewed port.
7. Run tests from the clean checkout directory and probe `module.__file__`. An editable venv can point imports at another checkout; `PYTHONPATH` without the correct cwd is not sufficient proof.
8. When comparing active and next venvs, reset cwd before import probes. A repository cwd can shadow the editable finder and make an untouched active venv appear repointed.
9. For npm 12 install-script inspection use `npm install-scripts ls --json`; `npm install-scripts ls --all --json` is rejected. Fingerprint Git status around npm commands.
10. Classify `npm audit` findings by deployed surface. Desktop/build/lint-only findings are not automatically gateway blockers, but must be disclosed. Do not run `npm audit fix` automatically.
11. During no-restart staging, prefer a durable independent checkout plus its own venv and alternate launcher. Do not advance the active editable worktree merely to prepare activation: running gateways can lazily import changed files and create a mixed runtime. Keep the active checkout, active launcher, profile hashes, and gateway PIDs byte-for-byte unchanged until the separately authorized cutover. Preserve the complete rollback snapshot regardless; if a workflow must stage the live checkout, keep the rollback stash by immutable SHA, require its untracked third parent, and hash every stashed path against the manifest.
12. Candidate tests must isolate both `HOME` and `HERMES_HOME`. Doctor/install tests may resolve the user bin through `Path.home()` and rewrite `~/.local/bin/hermes` even when `HERMES_HOME` is temporary. Fingerprint the active launcher before and after every regression pack that includes config/doctor/install/update/uninstall paths. For a symlink, the fingerprint must include the literal `readlink` target, resolved target, symlink metadata, entrypoint shebang/editable mapping, and target-file hash: `sha256sum` follows the link and can falsely pass when two different venv entrypoints are byte-identical or when a copied candidate entrypoint still has the active venv shebang. If it drifts, reconcile the source, atomically restore the original symlink target—not merely identical target bytes—verify readlink + resolved runtime + unchanged PIDs, harden the wrapper, and rerun the affected pack.
13. Inspect `pyproject.toml` before building the candidate venv. Do not assume an `all` extra contains test tooling; include the current dev/test extra explicitly when defined, use the locked resolver, and prove imports originate from the staged checkout. If the project intentionally disables wheel builds, validate through the supported editable sync path rather than treating the expected build refusal as a release failure.
14. Path-set equality is accounting, not semantic proof. Upstream can move a behavior into a new branch where Git silently retains an old condition. Run targeted behavior tests for every manual conflict and for each invariant that crossed an upstream refactor boundary before regenerating the canonical patch.
15. A full repository suite may be time-boxed only as supplementary evidence. If stopped, preserve the partial log and label it incomplete; never call it green. Name the completed canonical guard, overlap pack, targeted tests, dependency checks, and builds that actually form the release gate.
16. After promoting the candidate, remove disposable workspaces, require no Git alternates in the durable stage, run `git fsck --full`, and rerun the candidate launcher/import probe. Activation remains a separate critical action with fresh backup, atomic launcher cutover, non-Zeus gateways first, Zeus last, and per-gateway rollback gates.
17. Run `sha256sum -c` from the directory that contains a relative-name checksum manifest. A cwd-only verification failure is not archive corruption; rerun from the correct directory and record the corrected readback.

## Validated 2026-07-26 evidence

- Pre-port and staged surface: 40/40 paths from `ed3c39108` to frozen target `b9ba7c78`; canonical patch reproduced in a second clean checkout.
- Conflicts were limited to `gateway/run.py` and the Discord adapter, but a moved priority-steer condition silently reintroduced text-only behavior. The Telegram photo interruption test caught it; path equality alone did not.
- Upstream curator ownership became fail-closed. The structural-write receipt test fixture was adapted to represent a curator-managed skill instead of weakening the upstream ownership guard.
- `uv sync --extra all` did not include pytest on this target; the validated candidate used the current `dev` extra explicitly. The target was editable-only, so locked sync/import/CLI/dependency checks replaced wheel building.
- A doctor regression rewrote the active launcher while only `HERMES_HOME` was isolated. Isolating `HOME` as well prevented recurrence and 390 overlap tests passed. The initial post-test verification used `sha256sum` only and therefore proved identical entrypoint bytes but not the symlink target; activation preflight later found the link still aimed at the candidate venv entrypoint, whose copied shebang pointed back to the old venv. The pointer was normalized atomically before cutover, with `readlink`, shebang/editable mapping, process command lines, and unchanged PIDs as the corrected proof.
- Final gates: 850 tests + 6 subtests, 390 overlap tests, Web/TUI builds, 103-package dependency compatibility, profile config checks 3/3, independent stage `git fsck`, and unchanged live checkout/launcher/profile hashes/PIDs.
- The full repository suite was stopped on time budget with no observed failure before stop and was reported as incomplete, not green.

## Validated 2026-07-21 evidence

- Pre-port surface: 41 paths; final patch: 39 retained paths plus 2 one-shot lifecycle paths absorbed upstream.
- Upstream lifecycle evidence: `bfa7a794c`, `97fc8a4a3`.
- Fresh validation: 804 tests + 6 subtests; post-upstream pack 358; Web/TUI builds; Codex smokes 4/4.
- One new upstream commit arrived after freeze and was intentionally left pending rather than widening the reviewed scope.

The identifiers above are historical evidence, not reusable targets. Every future run must capture fresh SHAs, hashes, paths, stash IDs, and report IDs.