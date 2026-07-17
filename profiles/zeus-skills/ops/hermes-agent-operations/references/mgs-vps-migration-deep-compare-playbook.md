# MGS VPS migration — deep old-vs-new comparison playbook

Use this reference when Rodolfo challenges a VPS migration with “olha de novo”, “TUDO”, “seja mais detalhista”, or similar. The goal is not a quick health check; it is a forensic comparison between the old standby VPS and the new production VPS, followed by correction of any non-runtime drift.

## Trigger

After a full VPS migration/cutover, especially Hetzner → Hostinger, Rodolfo may ask for repeated validation. Treat this as a real audit request, not as annoyance or duplicate work. Re-run the comparison from fresh manifests; do not reuse prior conclusions.

## Safety rule after restart recovery

If the gateway restarts mid-audit and Hermes injects an internal restart recovery checkpoint, do **not** immediately re-run rsync, restart, deploy, update, or other side-effecting steps. First inspect current state and send a concise recovery/status message. Continue only after Rodolfo explicitly says to continue.

## What to compare

Generate fresh manifests on both servers with SHA256/size/mode for stable files across:

- `/root/mgs-agent`
- `/root/.hermes/profiles/{zeus,atena,ares,legacy-agent}`
- `/root/.hermes/hermes-agent`
- `/etc/systemd/system/{zeus,atena,ares,legacy-agent,mgs-autocommit}.service`
- root crontab hash/line count
- service active/enabled status
- failed systemd units
- profile config/auth facts sanitized, never token values
- package/runtime basics: Hermes version, node, npm, python3, uv, op
- Git branch, HEAD, origin/main, dirty count

Skip or classify as runtime rather than failure:

- logs, sessions, caches, image/audio caches
- `gateway.pid`, `gateway.lock`, `gateway_state.json`
- SQLite runtime files: `state.db`, `state.db-wal`, `state.db-shm`
- `channel_directory.json` when it differs due to live Discord state
- PulseAudio runtime under profile home
- crontab differences where production has active crons and standby intentionally has zero

## Critical files that must match

These should be exact matches after final stable sync unless there is a documented intentional reason:

- profile `config.yaml` for Zeus/Atena/Ares/agente legado
- profile `auth.json` for Zeus/Atena/Ares/agente legado, but report only sanitized facts
- `/root/mgs-agent/AGENT.md`
- `/root/mgs-agent/context/mgs-os-map.md`
- `/root/mgs-agent/context/company-os.md`
- `/root/mgs-agent/context/agent-map.md`
- `/root/mgs-agent/context/routes.md`
- `/root/mgs-agent/context/permissions-matrix.md`
- `/root/mgs-agent/data/authorized-users.json`
- `/root/mgs-agent/data/sites.json`
- gateway systemd units for Zeus/Atena/Ares/agente legado

`auth.json` raw hash can differ due to provider metadata or token refresh. Do not print or diff token contents. Compare sanitized facts: `active_provider`, presence of `openai-codex`, access-token length, refresh-token presence, and config provider/model. If sanitized facts differ in a way that affects policy, fix it.

## Correction pattern for non-runtime drift

If old standby is missing stable files, sync from production to standby, not the reverse:

1. Mirror stable `/root/mgs-agent` from production to standby, excluding logs, `.git`, browser profiles, generated media, caches and live runtime directories.
2. Mirror stable profile surfaces: `config.yaml`, `auth.json`, `SOUL.md`, `skills/`, `discord_threads.json`, `.skills_prompt_snapshot.json` when useful.
3. Keep old standby operationally disabled after syncing:
   - `systemctl disable --now zeus-gateway atena-gateway ares-gateway legacy-agent-gateway mgs-autocommit`
   - `systemctl reset-failed`
   - root crontab should remain empty on standby.
4. Re-run manifests after correction.
5. Accept only runtime-only drift after correction.

If old standby has archival backups/tmp/data not present on production and Rodolfo said “TUDO”, pull them into production for preservation. Keep sensitive/debug artifacts ignored by Git if they are not meant to be versioned.

## Git/runtime state pitfall

Runtime state files can keep production Git dirty forever if they are tracked. If a state file is already covered by `.gitignore` but remains tracked, remove it from Git tracking while keeping the local file:

```bash
git rm --cached -- data/<runtime-state>.json
git commit -m "chore(ops): untrack <runtime> state"
```

Validate `HEAD == origin/main` and `dirty=0` after auto-push.

## Evidence shape for final report

Use a compact but detailed executive matrix:

```text
Métrica                       Resultado
----------------------------- ---------
Arquivos Hostinger no escopo  N
Arquivos Hetzner no escopo    N
Arquivos comuns               N
Arquivos idênticos            N
Diferenças para revisão       0
Só Hostinger para revisão     only runtime/cache if any
Só Hetzner para revisão       0
Critical not match            0
Erros de leitura              0 / 0
```

Then list:

- what was found before correction;
- what was fixed;
- exact remaining differences and why each is runtime/expected;
- production vs standby service state;
- Git HEAD/origin/dirty;
- disk and failed unit count;
- audit log and REPORT-INFRA status.

## REPORT-INFRA

If the comparison causes changes to systemd units, scripts, profile skills, data files, `.gitignore`, or mirrored infra state, send REPORT-INFRA and update/ack inventory as usual before calling the task complete.
