# VPS update, npm recovery, and backup retention — 2026-05-24

## Context

During an MGS VPS maintenance window, the system was updated through a root terminal command with backups first. APT and Hermes completed, but the terminal disconnected while updating npm. Validation showed the main update succeeded, while npm remained at 10.9.7. A normal `npm install -g npm@latest` failed with `MODULE_NOT_FOUND: promise-retry`, but npm 10.9.7 still responded.

## Durable techniques

### 1. Post-update validation first; do not rerun the full updater

When a terminal disconnects mid-maintenance, verify state before repeating anything:

```bash
mgs-updates
repo=/root/.hermes/hermes-agent
git -C "$repo" fetch --quiet origin main
git -C "$repo" rev-parse --short HEAD
git -C "$repo" rev-parse --short origin/main
git -C "$repo" rev-list --count HEAD..origin/main
systemctl is-active zeus-gateway.service atena-gateway.service
node -v
npm -v
npm outdated -g --depth=0 || true
```

If APT/Hermes/services are clean and only npm is pending, isolate npm; do not run the full update script again.

### 2. Manual npm replacement when self-update is broken

If `npm install -g npm@latest` fails inside npm internals but the current npm still works, use a critical-operation confirmation before replacing `/usr/lib/node_modules/npm`.

Pattern:

1. Backup current npm to the active maintenance backup directory.
2. Fetch official package metadata from `https://registry.npmjs.org/npm/<version>`.
3. Extract `dist.tarball` and `dist.shasum`.
4. Download tarball and verify `sha1sum -c`.
5. Extract to temp and verify `package.json.version`.
6. Move current `/usr/lib/node_modules/npm` to a timestamped rollback directory.
7. Move extracted package into `/usr/lib/node_modules/npm`.
8. Validate `npm -v`, `npm exec`, `npm outdated -g --depth=0`, `mgs-updates`, and Zeus/Atena services.

Minimal command skeleton:

```bash
set -euo pipefail
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP_ROOT="/root/mgs-backups/update-YYYYMMDD-HHMMSS"
WORK="/tmp/npm-manual-update-$TS"
mkdir -p "$WORK" "$BACKUP_ROOT"

tar -C /usr/lib/node_modules -czf "$BACKUP_ROOT/npm-before-manual-$TS.tgz" npm
curl -fsSL https://registry.npmjs.org/npm/11.15.0 -o "$WORK/npm.json"
TARBALL="$(python3 - <<'PY' "$WORK/npm.json"
import json,sys
print(json.load(open(sys.argv[1]))['dist']['tarball'])
PY
)"
SHASUM="$(python3 - <<'PY' "$WORK/npm.json"
import json,sys
print(json.load(open(sys.argv[1]))['dist']['shasum'])
PY
)"
curl -fsSL "$TARBALL" -o "$WORK/npm.tgz"
echo "$SHASUM  $WORK/npm.tgz" | sha1sum -c -
mkdir -p "$WORK/extract"
tar -xzf "$WORK/npm.tgz" -C "$WORK/extract"
node -p "require('$WORK/extract/package/package.json').version"

mv /usr/lib/node_modules/npm "/usr/lib/node_modules/npm.before-manual-$TS"
mv "$WORK/extract/package" /usr/lib/node_modules/npm
chmod -R a+rX /usr/lib/node_modules/npm
hash -r
npm -v
npm exec --yes -- node -e "console.log('npm exec ok')"
npm outdated -g --depth=0 || true
systemctl is-active zeus-gateway.service atena-gateway.service
mgs-updates | sed -n '/NPM global/,+14p'
```

Keep both rollback handles in the final report:

- tar backup under `/root/mgs-backups/.../npm-before-manual-*.tgz`
- moved directory `/usr/lib/node_modules/npm.before-manual-*`

### 3. Backup inventory and retention cleanup

For MGS backup cleanup, do not start by deleting. First produce a read-only inventory:

- `/root/mgs-backups`
- `/root/mgs-agent/backups`
- `/root/backups`
- `/root/.hermes/backups`
- `/root/.hermes/profiles/*/state-snapshots`
- standalone `/root/*backup*` and `/root/*rollback*`

Classify into:

- **Keep:** current full update backup; previous system-update backup; latest standalone Hermes profiles snapshot; monthly/oldest anchor until an external backup exists; small config/provider backups; state snapshots.
- **Delete candidates:** redundant Hermes profile tarballs covered by current full backup + one standalone snapshot; old tiny preflight/runtime backups; empty directories.

Deletion is critical-subset. Present an exact numbered list with size/path/justification and ask for confirmation, e.g. `confirmo remover itens 1-8`.

When executing deletion:

```bash
set -euo pipefail
TARGETS=( ...exact paths... )
LOG="/root/mgs-agent/logs/backup-cleanup-$(date +%Y%m%d-%H%M%S).log"
{
  date
  df -h /
  total=0
  for p in "${TARGETS[@]}"; do
    test -e "$p"
    sz=$(stat -c %s "$p")
    total=$((total+sz))
    printf 'TARGET %s bytes %s\n' "$sz" "$p"
  done
  for p in "${TARGETS[@]}"; do
    rm --one-file-system -f -- "$p"
    echo "DELETED: $p"
  done
  for p in "${TARGETS[@]}"; do
    test ! -e "$p"
  done
  df -h /
} 2>&1 | tee "$LOG"
```

Report before/after disk usage, bytes freed, preserved backup paths, and log path.

## User preference observed

For VPS maintenance, Rodolfo prefers Zeus to execute read-only checks directly when tool access allows it. Provide terminal commands only when a guardrail/access issue prevents direct execution or when he explicitly asks to run it himself.
