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

## Final recommendation gate

A direct pull/update is inappropriate when any of these is true:

- upstream is a large untagged delta;
- local tracked or untracked customizations exist;
- `git apply --check` fails;
- local paths overlap critical lifecycle, gateway, Discord, authorization, memory, or restart code;
- the update target or refs moved during the audit.

In those cases freeze one target SHA, port in isolation, prove every local path retained or upstream-equivalent, run targeted tests and profile smokes, then use the canonical safe restart flow.
