# Pre-update review workflow

Use this when Rodolfo asks whether a Hermes update is worth applying before approving the update.

## Goal

Produce an executive comparison between the installed Hermes checkout and upstream without changing system state.

## Checks performed in the 2026-05-16 review

```bash
hermes --version 2>&1 | head -20

git -C /root/.hermes/hermes-agent fetch --quiet origin main

git -C /root/.hermes/hermes-agent status --short

git -C /root/.hermes/hermes-agent rev-parse --short HEAD

git -C /root/.hermes/hermes-agent rev-parse --short origin/main

git -C /root/.hermes/hermes-agent log --oneline --decorate --no-merges HEAD..origin/main | head -120

git -C /root/.hermes/hermes-agent diff --shortstat HEAD..origin/main

git -C /root/.hermes/hermes-agent diff --name-only HEAD..origin/main | wc -l
```

Classify commits with a small Python script that shells out to git directly, not by piping git output into an interpreter:

```bash
python3 - <<'PY'
import subprocess, collections, re
repo='/root/.hermes/hermes-agent'
logs=subprocess.check_output(['git','-C',repo,'log','--format=%s','HEAD..origin/main'], text=True)
cats=collections.Counter()
scope=collections.Counter()
for s in logs.splitlines():
    if s.startswith('feat'):
        cats['features'] += 1
    elif s.startswith('fix'):
        cats['fixes'] += 1
    elif s.startswith('perf'):
        cats['performance'] += 1
    elif s.startswith(('docs','doc')):
        cats['docs'] += 1
    elif s.startswith(('test','ci','chore','refactor','remove','Revert')):
        cats['maintenance'] += 1
    else:
        cats['other'] += 1
    m = re.match(r'[^(:]+\(([^)]+)\)', s)
    if m:
        scope[m.group(1)] += 1
print('categories', dict(cats))
print('top scopes', scope.most_common(20))
print('total', len(logs.splitlines()))
PY
```

## Local patch conflict dry-run

A clean working tree does not imply stock Hermes: MGS customizations may already be committed in a controlled port. Resolve the active repo from the canonical launcher and live gateway PID, freeze its validated upstream base plus the public target, and inventory committed `base..HEAD` changes, canonical patch/guard manifests, staged/unstaged changes and untracked paths.

Use `vps-maintenance-and-backup-governance/references/git-update-delta-and-patch-portability.md` as the single owner of the complete-surface exported-target precheck. Its base-to-working-tree diff preserves committed tracked customizations; staged-only and untracked material is inventoried separately. Require current reverse checks and frozen-target forward checks; report textual applicability separately from semantic/lifecycle validation.

Create probe artifacts only under the current session's canonical scratch. Never use hardcoded `/tmp`, automatic `rm`/trap/finally cleanup or a raw-deletion fallback for Git worktrees. Record exact temporary paths; disposal is a separate confirmed Critical Subset operation. Without that confirmation, retain and report the artifacts.

If upstream relocated a module such as Discord, locate the required symbols and tests in the frozen target rather than blindly replacing path strings. Prepare any authorized port only in an inactive candidate, compile and exercise its behavior, and keep production unchanged until activation gates pass.

Interpretation:
- Forward-check success proves textual applicability only, not semantic compatibility or permission to activate.
- Failure identifies the exact port blockers; module relocation may be resolvable but is not a reason to apply a patch to production.
- Compilation and targeted behavior tests are independent gates; neither a clean working tree nor a path-only substitution closes full MGS preservation.

## Reporting shape

For Rodolfo, report:
- current version/commit/date vs upstream version/commit/date
- number of commits behind and changed files/line delta
- categorized commit counts
- top operationally relevant improvements
- local patch risk and dry-run result
- clear recommendation: update now / defer / update only in controlled window

Use aligned `text` tables for comparable data. Keep the conclusion direct.