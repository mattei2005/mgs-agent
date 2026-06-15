# Hermes controlled update Git hygiene incident — 2026-06-15

## What happened

During validation of the new MGS controlled Hermes update workflow, a precheck generated large runtime artifacts under `/root/mgs-agent/reports/hermes-updates/<timestamp>/`, including `hermes-profiles-backup-*.tar.gz`. Because that path was not ignored yet and `mgs-autocommit.service` was active, the watcher committed update-report/backup artifacts automatically.

## Durable lesson

For update workflows that create backups or evidence directories inside `/root/mgs-agent`, Git hygiene must happen **before** artifact generation:

1. Stop or pause `mgs-autocommit.service` when generating large/sensitive update artifacts during workflow development or validation.
2. Add ignore rules for the artifact paths before the first run:
   - `reports/hermes-updates/`
   - `*.tar.gz`
3. Keep update artifacts local unless explicitly designed as sanitized, lightweight reports.
4. If backup/report artifacts are committed accidentally, treat it as a Git hygiene/security incident: clean local history, force-push with explicit approval, then prune local unreachable objects.

## Recovery pattern used

```bash
cd /root/mgs-agent
systemctl stop mgs-autocommit.service
cp scripts/run-hermes-update-controlled.sh /tmp/run-hermes-update-controlled.clean.sh

git reset --hard <last-clean-commit>
cp /tmp/run-hermes-update-controlled.clean.sh scripts/run-hermes-update-controlled.sh
chmod +x scripts/run-hermes-update-controlled.sh

# add ignore rules before future runs
python3 - <<'PY'
from pathlib import Path
p=Path('.gitignore')
text=p.read_text()
block='''\n# ─── Hermes update reports/backups (runtime, may contain sensitive auth snapshots) ──\nreports/hermes-updates/\n*.tar.gz\n'''
if 'reports/hermes-updates/' not in text:
    p.write_text(text.rstrip()+block+'\n')
PY

bash -n scripts/run-hermes-update-controlled.sh
git add scripts/run-hermes-update-controlled.sh .gitignore
git commit -m "ops: harden Hermes controlled update workflow"
```

If the bad commits already reached GitHub, get explicit Rodolfo approval for history rewrite, then push with an exact lease:

```bash
cd /root/mgs-agent
ASKER=$(mktemp)
cat > "$ASKER" <<'SCRIPT'
#!/bin/bash
case "$1" in
  *Username*) echo "mattei2005" ;;
  *Password*) op item get "GitHub PAT - mgs-agent" --vault "MGS Conteúdo" --fields github_token --reveal ;;
esac
SCRIPT
chmod +x "$ASKER"
set -a
source /root/mgs-agent/.env 2>/dev/null || true
set +a
GIT_ASKPASS="$ASKER" GIT_TERMINAL_PROMPT=0 git push --force-with-lease=main:<known-bad-origin-sha> origin HEAD:main
rm -f "$ASKER"

git fetch --quiet origin main
git reflog expire --expire=now --expire-unreachable=now --all
git gc --prune=now
systemctl start mgs-autocommit.service
```

Notes:

- `gh` may not be installed on the VPS; use the repository's existing 1Password/GIT_ASKPASS pattern instead of assuming GitHub CLI.
- Use an exact `--force-with-lease=main:<sha>` so the push fails if origin changed unexpectedly.
- After pruning, validate `.git` size and free disk (`df -h /`). In this incident `.git` dropped from about 11G to 795M and free disk recovered from about 4.7G to 15G.
- Commit sanitized skill mirrors/config mirror separately after cleanup if they changed during approval/tooling updates.

## Preventive rule

The controlled update script and any future maintenance script must treat local evidence directories as runtime/private by default. Only sanitized final summaries belong in Git, and only when intentionally added.