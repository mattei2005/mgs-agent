# Hermes update ENOSPC / partial-update recovery

Use when `hermes update` or a manual Hermes update fails with `ENOSPC: no space left on device`, especially during npm install/build, and the gateway comes back with `OSError [Errno 28]` or SQLite `disk I/O error`.

## Key lesson

Do **not** rerun `hermes update` blindly after ENOSPC. First determine whether the repo already advanced, whether local patches were restored, whether services are still running old PIDs, and whether dependency/build steps failed midway.

A common state after ENOSPC:

- `git rev-list --count HEAD..origin/main` returns `0` — code is already at upstream.
- `hermes --version` says up to date.
- `git status --short` shows restored MGS local patch files.
- gateways are `active` but still running from old uptime/PIDs, not necessarily restarted onto the updated code.
- old update log contains npm `ENOSPC`; Python files may still compile.

## Read-only triage

```bash
repo=/root/.hermes/hermes-agent

df -h /
df -ih /
du -xhd1 /root 2>/dev/null | sort -h | tail -20
ls -lh /root/hermes-profiles-backup-*.tar.gz /root/hermes-update-*.log /root/hermes-local-diff-*.patch 2>/dev/null | tail -30 || true

hermes --version || true
git -C "$repo" fetch origin main --quiet
echo "local:    $(git -C "$repo" rev-parse --short HEAD)"
echo "upstream: $(git -C "$repo" rev-parse --short origin/main)"
echo "behind:   $(git -C "$repo" rev-list --count HEAD..origin/main)"
echo "ahead:    $(git -C "$repo" rev-list --count origin/main..HEAD)"
git -C "$repo" status --short
git -C "$repo" stash list | head -10
git -C "$repo" diff --stat || true

systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service || true
journalctl -u zeus-gateway.service -u atena-gateway.service -u ares-gateway.service --since '2 hours ago' --no-pager -p warning..alert | tail -80 || true
```

## Space recovery pattern

Profile backups are often the largest safe target. Keep the newest known-good profile backup and remove redundant older tarballs. Moving files inside `/root` does **not** free space; it only quarantines them for review. Actual free space appears only after deletion.

Target before retrying dependency repair: at least 8–10 GB free on `/`.

Example quarantine then delete pattern:

```bash
mkdir -p /root/cleanup-quarantine-YYYYMMDD
mv /root/hermes-profiles-backup-OLD*.tar.gz /root/cleanup-quarantine-YYYYMMDD/ 2>/dev/null || true

df -h /
du -sh /root/cleanup-quarantine-YYYYMMDD /root/hermes-profiles-backup-LATEST.tar.gz

# After confirming only redundant backups were moved:
rm -rf /root/cleanup-quarantine-YYYYMMDD
sync
df -h /
```

## Repair after space is available

If repo is already at upstream (`behind: 0`) but npm failed, do not update again. Repair dependencies/build directly, then compile-check and only then restart gateways.

```bash
set -euo pipefail
repo=/root/.hermes/hermes-agent
cd "$repo"

df -h /

uv pip install --python "$repo/venv/bin/python" -e '.[all]'
npm install --no-fund --no-audit

if [ -f "$repo/ui-tui/package.json" ]; then
  cd "$repo/ui-tui"
  npm install --no-fund --no-audit
fi

cd "$repo"
"$repo/venv/bin/python" -m py_compile \
  "$repo/gateway/run.py" \
  "$repo/gateway/platforms/base.py" \
  "$repo/plugins/platforms/discord/adapter.py" \
  "$repo/tools/discord_tool.py"

git fetch origin main --quiet
echo "local:    $(git rev-parse --short HEAD)"
echo "upstream: $(git rev-parse --short origin/main)"
echo "behind:   $(git rev-list --count HEAD..origin/main)"
git status --short

df -h /
```

Then restart and validate:

```bash
systemctl restart zeus-gateway.service atena-gateway.service ares-gateway.service
sleep 10
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service
journalctl -u zeus-gateway.service -u atena-gateway.service -u ares-gateway.service --since '10 minutes ago' --no-pager -p warning..alert | tail -120
```

## Reporting guidance

Report the state as a matrix: disk free, git HEAD/upstream/behind, service active states and whether they are old or restarted, local patch diff, compile result, and the exact failed phase from logs. Avoid calling the update successful until dependency repair and restart validation both pass.