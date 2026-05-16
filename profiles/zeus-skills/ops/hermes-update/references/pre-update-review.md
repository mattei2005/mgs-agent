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

If the Hermes checkout is dirty, preserve and test local patches before recommending an update:

```bash
set -euo pipefail
repo=/root/.hermes/hermes-agent
tmp=/tmp/hermes-update-conflict-check-manual
patchfile=/tmp/mgs-local-hermes.patch
rm -rf "$tmp"
git -C "$repo" diff > "$patchfile"
printf 'patch bytes: '; wc -c < "$patchfile"
git -C "$repo" worktree add --detach "$tmp" origin/main
cd "$tmp"
if git apply --check "$patchfile" >/tmp/apply_check.out 2>&1; then
  echo "APPLY_CHECK=OK"
else
  echo "APPLY_CHECK=FAIL"
  cat /tmp/apply_check.out
fi
cd /
git -C "$repo" worktree remove --force "$tmp" || rm -rf "$tmp"
```

Interpretation:
- `APPLY_CHECK=OK` means the local patch probably reapplies cleanly after update; still validate behavior after restart.
- `APPLY_CHECK=FAIL` means update should not proceed until conflicts are inspected manually.

## Reporting shape

For Rodolfo, report:
- current version/commit/date vs upstream version/commit/date
- number of commits behind and changed files/line delta
- categorized commit counts
- top operationally relevant improvements
- local patch risk and dry-run result
- clear recommendation: update now / defer / update only in controlled window

Use aligned `text` tables for comparable data. Keep the conclusion direct.