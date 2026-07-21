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
11. During no-restart staging, keep the rollback stash by immutable SHA, require its untracked third parent, hash every stashed path against the manifest, and prove gateway PIDs did not change.
12. Run `sha256sum -c` from the directory that contains a relative-name checksum manifest. A cwd-only verification failure is not archive corruption; rerun from the correct directory and record the corrected readback.

## Validated 2026-07-21 evidence

- Pre-port surface: 41 paths; final patch: 39 retained paths plus 2 one-shot lifecycle paths absorbed upstream.
- Upstream lifecycle evidence: `bfa7a794c`, `97fc8a4a3`.
- Fresh validation: 804 tests + 6 subtests; post-upstream pack 358; Web/TUI builds; Codex smokes 4/4.
- One new upstream commit arrived after freeze and was intentionally left pending rather than widening the reviewed scope.

The identifiers above are historical evidence, not reusable targets. Every future run must capture fresh SHAs, hashes, paths, stash IDs, and report IDs.