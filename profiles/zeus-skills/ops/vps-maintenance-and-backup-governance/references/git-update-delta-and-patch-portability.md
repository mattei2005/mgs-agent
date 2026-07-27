# Git Update Delta and Local-Patch Portability

## Goal

Decide whether a Git-based application update is routine, untagged development, or a controlled port. The live checkout remains untouched.

## Freeze the graph

Run fetch first, then capture all comparison anchors once:

```bash
repo=/path/to/repo
git -C "$repo" fetch --quiet origin main --tags
observed_at=$(date -Is)
installed=$(git -C "$repo" rev-parse HEAD)
upstream=$(git -C "$repo" rev-parse origin/main)
tag=$(git -C "$repo" for-each-ref --count=1 --sort=-creatordate --merged=origin/main --format='%(refname:short)' refs/tags)
```

Verify ancestry before presenting a simple behind count:

```bash
git -C "$repo" merge-base --is-ancestor "$installed" "$upstream"
git -C "$repo" rev-list --left-right --count "$installed...$upstream"
git -C "$repo" rev-list --count "$tag..$installed"
git -C "$repo" rev-list --count "$tag..$upstream"
git -C "$repo" diff --shortstat "$installed..$upstream"
```

Report three different dimensions when available:

- pending in the installed checkout: `installed..upstream`;
- untagged development after the latest public tag: `tag..upstream`;
- new since a prior audited SHA: `prior..upstream`.

A large `main` delta with no newer public tag is not a new stable release. Name it as untagged upstream development and default to a controlled port/defer recommendation unless an operational need justifies targeting that SHA.

## Measure the local customization surface

Capture both tracked and untracked paths:

```bash
git -C "$repo" diff --name-only HEAD
git -C "$repo" ls-files --others --exclude-standard
git -C "$repo" diff --name-only HEAD..origin/main
```

Compute the intersection between locally modified paths and upstream-changed paths. This is a review surface, not a conflict count.

For each untracked local path, test whether upstream now owns the same path:

```bash
git -C "$repo" cat-file -e "origin/main:path/to/file"
```

A successful lookup is a path collision requiring explicit review; a missing path is not proof that the file is compatible with surrounding upstream changes.

## Dry-run the tracked patch against a clean target

Use an exported target rather than mutating or stashing the live checkout:

```bash
set -euo pipefail
repo=/path/to/repo
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

git -C "$repo" diff --binary HEAD > "$tmp/local.patch"
git -C "$repo" archive origin/main | tar -x -C "$tmp"

git -C "$tmp" apply --check "$tmp/local.patch"
```

Interpretation:

- `apply --check` succeeds: tracked hunks apply textually; semantic tests are still required.
- `apply --check` fails: report the exact files/hunks as real port blockers.
- Upstream/local path intersection without apply failure: review risk, not a proven conflict.
- Untracked local files require separate collision and behavior review because they are absent from `git diff`.

Do not leave the temporary export or patch behind. Registered worktrees are unnecessary for this precheck; if one is used, remove it through Git and prune metadata.

## Editable-package version drift

A Git checkout can run as an editable package while package metadata remains stale. Compare all three:

```bash
python -m pip show <package>
python -c 'import importlib.metadata as m; print(m.version("package-name"))'
git -C "$repo" show HEAD:pyproject.toml
python -c 'import package; print(package.__file__)'
```

If `package.__file__` points to the live checkout but metadata reports an older version, describe it as **metadata drift**, not proof that old code is running. Reinstall/rebuild the editable package during the controlled update and verify both source and metadata afterward.

## Turn a large commit range into an executive capability review

Do not equate commits with features. For a large range, report at least:

- all commits, first-parent commits, and merge commits;
- diff files/insertions/deletions;
- subject categories such as `feat`, `fix`, `perf`, `test`, `docs`, and `refactor`;
- top changed path domains;
- deduplicated PR titles, using the merge body title when the merge subject is only `Merge pull request ...`.

Check the tag relationship explicitly. A public release tag may already be an ancestor of the installed SHA. In that case, release-note features at the tag are **not new in `installed..target`**, even when the target still prints the same release version. Report `tag..installed`, `installed..target`, and `tag..target`; call the latter post-release untagged development when no newer tag exists.

For business recommendations, classify capabilities into three states:

1. **Active runtime benefit** — fixes or behavior already loaded by the deployed target, such as reconnect supervision, profile isolation, or compaction correctness.
2. **Available but not operationalized** — commands/configuration that exist but still need MGS policy, credentials, a pilot, or a rollout gate.
3. **Surface-specific/low priority** — desktop or UI features that do not help a Discord/VPS operation until that surface is adopted.

Tie each recommendation to exact commit subjects or changed code, then rank by company impact: reliability/isolation, cost/context visibility, security/secrets, orchestration, media/channel behavior, and optional UI. A capability present in code is not proof that it is configured, credentialed, or safe to enable. Existing company authorization and Critical Subset rules always outrank upstream “smart approval” or automation features.

## Final recommendation gate

A direct pull/update is inappropriate when any of these is true:

- upstream is a large untagged delta;
- local tracked or untracked customizations exist;
- `git apply --check` fails;
- local paths overlap critical lifecycle, gateway, Discord, authorization, memory, or restart code;
- the update target or refs moved during the audit.

In those cases freeze one target SHA, port in isolation, prove every local path retained or upstream-equivalent, run targeted tests and profile smokes, then use the canonical safe restart flow.
