# MGS full maintenance validation + manual npm update

Use after a combined VPS/Hermes/APT/npm maintenance window, especially when Rodolfo asks “confere se tudo está estável” or npm self-update failed mid-run.

## Validation scope

Run against live state and report only validated facts:

```bash
set -euo pipefail

# System/update state
mgs-updates
apt list --upgradable 2>/dev/null | tail -n +2 || true
if [ -f /var/run/reboot-required ]; then cat /var/run/reboot-required; else echo 'no reboot-required'; fi
needrestart -b 2>/dev/null | sed -n '1,120p' || true

# Hermes git/version
repo=/root/.hermes/hermes-agent
git -C "$repo" fetch --quiet origin main
echo "HEAD=$(git -C "$repo" rev-parse --short HEAD)"
echo "ORIGIN=$(git -C "$repo" rev-parse --short origin/main)"
echo "BEHIND=$(git -C "$repo" rev-list --count HEAD..origin/main)"
echo "AHEAD=$(git -C "$repo" rev-list --count origin/main..HEAD)"
git -C "$repo" status --short
hermes --version

# Gateways
systemctl is-active zeus-gateway.service atena-gateway.service
systemctl show zeus-gateway.service atena-gateway.service \
  -p Id -p ActiveState -p SubState -p NRestarts -p MainPID -p ActiveEnterTimestamp --no-pager
systemctl --failed --no-pager || true
journalctl -u zeus-gateway.service --since '15 minutes ago' --no-pager -p warning..alert || true
journalctl -u atena-gateway.service --since '15 minutes ago' --no-pager -p warning..alert || true

# Syntax/runtime smokes
py="$repo/venv/bin/python"
"$py" -m py_compile "$repo/plugins/platforms/discord/adapter.py" "$repo/gateway/run.py" "$repo/tools/discord_tool.py"
bash -n /root/mgs-agent/scripts/mgs-updates.sh
python3 -m py_compile /root/mgs-agent/scripts/mgs-rec-runner.py /root/mgs-agent/scripts/mgs-p1-runner.py

# Profile auth/config without secrets
python3 - <<'PY'
import json, yaml, pathlib
for prof in ['zeus','atena']:
    base=pathlib.Path('/root/.hermes/profiles')/prof
    cfg=yaml.safe_load(open(base/'config.yaml')) or {}
    auth=json.load(open(base/'auth.json')) if (base/'auth.json').exists() else {}
    model=cfg.get('model',{}) or {}
    p=(auth.get('providers',{}) or {}).get('openai-codex',{}) or {}
    toks=(p.get('tokens',{}) or {}) if isinstance(p,dict) else {}
    print(f'{prof}: model={model.get("provider")}/{model.get("default")} active_provider={auth.get("active_provider")} access_token_len={len(toks.get("access_token", ""))} refresh_token_present={bool(toks.get("refresh_token"))}')
PY

# Crons/logs
crontab -l
# Prefer monitor-cron-stale-logs summary: problems=0; spot-check recent logs for active monitors.
```

## 1Password env gotcha

When using `op` in a non-interactive shell, source `/root/mgs-agent/.env` with export semantics. Plain `source` may set shell variables but not export `OP_SERVICE_ACCOUNT_TOKEN` to subprocesses, causing `op` to say “No accounts configured”.

```bash
set +u
set -a
source /root/mgs-agent/.env
set +a
set -u
op item get 'Brave Search API - MGS' --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --format json >/dev/null
```

Never print token values. Report presence/length only.

## Manual npm update pattern

Use only after explicit critical confirmation because it modifies `/usr/lib`. Keep npm’s current tree as both a tarball and a moved directory for rollback.

```bash
set -euo pipefail
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP_ROOT="/root/mgs-backups/update-$TS"
WORK="/tmp/npm-manual-update-$TS"
mkdir -p "$BACKUP_ROOT" "$WORK"

node -v
npm -v
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
NEWVER="$(node -p "require('$WORK/extract/package/package.json').version")"
test -n "$NEWVER"

mv /usr/lib/node_modules/npm "/usr/lib/node_modules/npm.before-manual-$TS"
mv "$WORK/extract/package" /usr/lib/node_modules/npm
chmod -R a+rX /usr/lib/node_modules/npm
hash -r

npm -v
npm exec --yes -- node -e "console.log('npm exec ok')"
npm outdated -g --depth=0 || true
mgs-updates | sed -n '/NPM global/,+14p'
systemctl is-active zeus-gateway.service atena-gateway.service

echo "rollback_dir=/usr/lib/node_modules/npm.before-manual-$TS"
echo "backup_tar=$BACKUP_ROOT/npm-before-manual-$TS.tgz"
```

If validation fails, rollback by moving the new `/usr/lib/node_modules/npm` aside and restoring the `npm.before-manual-*` directory, then re-run `npm -v`.

## Reporting shape

Use a compact aligned table:

```text
Camada              | Status | Evidência
--------------------|--------|-----------------------------
APT                 | OK     | nenhum pacote pendente
Hermes              | OK     | HEAD=origin/main, behind=0
npm                 | OK     | 11.15.0, no global outdated
Zeus/Atena          | OK     | active, 0 restarts
Crons               | OK     | watchdog problems=0
```

End with `Próximo passo pendente:`; if all clear, say there is no immediate technical next step and only passive monitoring remains.
