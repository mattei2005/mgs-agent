# MGS VPS migration — deep file comparison and standby audit

Use this reference after a full VPS migration/cutover when Rodolfo asks to prove that the old VPS and new VPS really match, especially with language like “compara TUDO”, “arquivo por arquivo”, or “sou chato e persistente”.

## Goal

Prove that the production VPS has all operationally relevant state from the old VPS, while preserving the intended difference between:

- **New VPS / production**: gateways, crons, autocommit and monitors active.
- **Old VPS / standby**: gateways, crons and autocommit disabled/inactive, zero Hermes/gateway processes.

Do not require byte-identical runtime state for active vs standby. Runtime files such as PIDs, locks, SQLite WAL/SHM, channel caches and monitor state will diverge by design.

## Scope to compare

Minimum roots:

```text
/root/mgs-agent
/root/.hermes/profiles/zeus
/root/.hermes/profiles/atena
/root/.hermes/profiles/ares
/root/.hermes/profiles/hera
/root/.hermes/hermes-agent
/etc/systemd/system/{zeus,atena,ares,hera}-gateway.service
/etc/systemd/system/mgs-autocommit.service
root crontab
```

Critical files that should normally match exactly unless intentionally changed after cutover:

```text
/root/.hermes/profiles/{zeus,atena,ares,hera}/config.yaml
/root/.hermes/profiles/{zeus,atena,ares,hera}/auth.json
/root/mgs-agent/AGENT.md
/root/mgs-agent/context/mgs-os-map.md
/root/mgs-agent/context/company-os.md
/root/mgs-agent/data/authorized-users.json
/root/mgs-agent/data/sites.json
systemd gateway unit files for Zeus/Atena/Ares/Hera
```

## Manifest pattern

Generate JSON manifests on both hosts with path, type, size and SHA256. Exclude volatile/cache-heavy paths from equality scoring, not from operational reasoning:

```text
.git/
logs/
sessions/
audio_cache/
image_cache/
cron/output/
__pycache__/
.pytest_cache/
node_modules/
venv/
.venv/
data/browser-profiles/
data/generated/
```

For large files, either hash if practical or record `LARGE:<size>` consistently. Never print secrets. It is acceptable to compare `auth.json` by SHA256/size only, not content.

## Interpreting differences

Expected differences after successful cutover:

```text
Hostinger-only gateway.pid / state.db-wal / state.db-shm — active production runtime.
Hostinger-vs-Hetzner gateway.lock / gateway_state.json — per-host runtime state.
channel_directory.json — Discord cache/runtime may differ.
crontab: production has active crons, standby should have 0 lines.
.clean_shutdown / .restart_pending / .restart_failure_counts on old VPS — stale shutdown/restart markers.
data/*-state.json — monitor state changes on the live production host.
skill usage files / USER.md — may change during active session after cutover.
```

Potentially important differences that should be resolved or explicitly classified:

```text
Old VPS has backups/tmp/data-backups not present on production.
Old VPS service is inactive but still enabled.
Core configs/auth/context differ unexpectedly.
Git HEAD differs and production has dirty tree.
Systemd unit hash differs without an intentional production-only change.
```

## Corrective actions that proved useful

If the old VPS contains historical artifacts not present on production, copy them to the new host before declaring the comparison complete, especially:

```text
/root/mgs-agent/backups/
/root/mgs-agent/tmp/
/root/mgs-agent/data/backups/
/root/mgs-agent/data/mgs-gateway-restart-finalizer-*.sh
```

Use `rsync -a` over SSH with credentials pulled from 1Password into environment/stdin only; never print the password. After copying, regenerate the production manifest and compare again.

If the old VPS has any MGS service `enabled`, disable it for standby:

```bash
systemctl stop zeus-gateway atena-gateway ares-gateway hera-gateway mgs-autocommit 2>/dev/null || true
systemctl disable zeus-gateway atena-gateway ares-gateway hera-gateway mgs-autocommit >/dev/null 2>&1 || true
systemctl reset-failed zeus-gateway atena-gateway ares-gateway hera-gateway mgs-autocommit 2>/dev/null || true
```

## Final evidence shape

Report with counts and classification:

```text
Files compared: hostinger=N, hetzner=N, common=N, identical=N, different=N, only_hostinger=N, only_hetzner=N.
Critical configs/auth/context: match.
Production services: active/enabled.
Standby services: inactive/disabled, crontab=0, process_count=0.
Remaining differences: runtime-only / expected, with examples.
Actions taken: copied missing historical artifacts, disabled old autocommit, updated audit/report-infra if applicable.
```

Important: if artifacts are copied or services disabled, update audit log and send REPORT-INFRA before claiming final completion.