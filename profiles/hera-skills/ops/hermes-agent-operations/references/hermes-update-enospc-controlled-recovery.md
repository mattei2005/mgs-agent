# Hermes update ENOSPC controlled recovery — MGS

Use when `hermes update` or dependency repair fails with `ENOSPC`/`No space left on device`, especially after repeated profile backups.

## Durable pattern

1. **Stop rerunning update blindly.** First verify actual state:

```bash
repo=/root/.hermes/hermes-agent
df -h /
hermes --version || true
git -C "$repo" fetch origin main --quiet
echo "local:    $(git -C "$repo" rev-parse --short HEAD)"
echo "upstream: $(git -C "$repo" rev-parse --short origin/main)"
echo "behind:   $(git -C "$repo" rev-list --count HEAD..origin/main)"
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service || true
```

2. **Inventory large backups before deleting.** Keep the newest known-good backup; remove redundant Hermes profile/repo backups only after the user confirms the retention target.

```bash
find /root -xdev -type f \( \
  -iname '*backup*' -o -iname '*backups*' -o \
  -iname '*.tar' -o -iname '*.tar.gz' -o -iname '*.tgz' -o -iname '*.zip' \
\) -printf '%s\t%TY-%Tm-%Td %TH:%TM\t%p\n' 2>/dev/null | sort -nr | head -80
```

3. **If a new full operational backup is requested, create it first**, then prune older backups. Practical backup scope:
   - `/root/.hermes/profiles/`
   - `/root/.hermes/hermes-agent/` excluding `node_modules`, `ui-tui/node_modules`, `.git`
   - `/root/mgs-agent/` excluding bulky `backups/` and `logs/`
   - relevant systemd units and root crontab
   - manifest with disk, Hermes version, git status, and service status

4. **Repair the partial update without restarting services.** When git is already at upstream (`behind=0`) but update failed during npm, run dependency repair only:

```bash
set -euo pipefail
repo=/root/.hermes/hermes-agent
cd "$repo"
uv pip install --python "$repo/venv/bin/python" -e '.[all]'
npm install --no-fund --no-audit
if [ -f "$repo/ui-tui/package.json" ]; then
  (cd "$repo/ui-tui" && npm install --no-fund --no-audit)
fi
"$repo/venv/bin/python" -m py_compile \
  "$repo/gateway/run.py" \
  "$repo/gateway/platforms/base.py" \
  "$repo/plugins/platforms/discord/adapter.py" \
  "$repo/tools/discord_tool.py"
git fetch origin main --quiet
echo "behind: $(git rev-list --count HEAD..origin/main)"
git status --short
df -h /
```

5. **Restart is a separate explicit step.** Give the command only after install validation succeeds:

```bash
systemctl restart zeus-gateway.service atena-gateway.service ares-gateway.service
sleep 10
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service
```

6. **Interpret restart logs correctly.** `Failed with result 'exit-code'` at the exact restart timestamp often reflects old processes exiting under systemd. Treat it as active incident only if new PIDs are not running or warnings/errors continue after the new start timestamp.

## Success criteria

- `/` has healthy free space, ideally >8–10G before repair/update.
- `git rev-list --count HEAD..origin/main` is `0`.
- Python compile passes.
- `npm install` and `ui-tui npm install` complete without ENOSPC.
- Gateways restart to active/running with `NRestarts=0` and no warnings/errors after the new start timestamp.
