# MGS VPS migration — deep file comparison / standby audit

Use this reference when Rodolfo asks to re-check a VPS migration, especially with wording like “olha de novo”, “TUDO”, “seja detalhista”, or when he is worried about drift between old and new VPS.

## Lesson from Hostinger cutover review — 2026-06-18

A normal post-cutover health check is not enough for Rodolfo when he asks for “TUDO”. Do a fresh comparison, not a recap of the previous validation.

The useful pattern was:

1. Generate new manifests on both hosts.
2. Compare SHA256/size/mode for stable surfaces.
3. Classify expected runtime drift vs real missing files.
4. Pull/restore missing historical archive files when safe.
5. Keep the old VPS in standby: gateways/crons/autocommit inactive + disabled.
6. Re-run manifests after corrections.
7. Report remaining differences explicitly.

## Manifest scope

Compare at least:

```text
/root/mgs-agent
/root/.hermes/profiles/zeus
/root/.hermes/profiles/atena
/root/.hermes/profiles/ares
/root/.hermes/profiles/legacy-agent
/root/.hermes/hermes-agent
/etc/systemd/system/{zeus,atena,ares,legacy-agent,mgs-autocommit}.service
root crontab
```

Also capture non-secret runtime facts:

```text
hostname, public IP, OS, timezone, disk, memory
hermes --version
mgs-agent git HEAD/branch/dirty
hermes-agent git HEAD/dirty
service active/enabled/PID/restarts
failed units count
profile model/provider/auth presence with token lengths only
package versions: node, npm, python3, uv, op
```

## Expected differences — do not treat as migration failure

These are normal when comparing active production Hostinger to standby Hetzner:

```text
gateway.pid / gateway.lock          active host only
state.db / state.db-wal / state.db-shm runtime SQLite state
gateway_state.json                  live gateway state
channel_directory.json              Discord runtime/cache
crontab 36 vs 0                     production active vs standby disabled
.clean_shutdown / restart flags     old-host shutdown residue
Pulse runtime under profile home    local audio/session cache
logs, sessions, image/audio cache   volatile runtime
```

## Real findings worth correcting

From the 2026-06-18 review, the second detailed pass found issues a first pass missed:

- `/root/mgs-agent/backups`, `/root/mgs-agent/tmp`, and some historical `data/backups` existed only on Hetzner. Pull them to Hostinger if keeping rollback/history matters.
- `mgs-autocommit.service` on the old VPS can be `inactive` but still `enabled`; disable it too.
- A failed transient systemd unit on old VPS can remain after migration; run `systemctl reset-failed` after verifying it is historical.
- Stable profile surfaces may drift after production resumes. If using Hetzner as rollback standby, sync stable files from Hostinger to Hetzner: `config.yaml`, `auth.json`, `SOUL.md`, `skills/`, `discord_threads.json`, `.skills_prompt_snapshot.json`.
- Runtime state files like `data/hermes-mgs-patch-watchdog-state.json` should not keep Git dirty. If already tracked and purely runtime, remove from tracking with `git rm --cached` while keeping the local file.

## Safe old-host standby contract

After any mirror/sync to old VPS, immediately enforce:

```bash
systemctl disable --now zeus-gateway atena-gateway ares-gateway legacy-agent-gateway mgs-autocommit
systemctl reset-failed
crontab -l  # should be empty / 0 lines for standby
pgrep -af 'hermes|gateway'  # should show 0 relevant old-agent processes
```

The old VPS may keep files for rollback, but must not run agents, crons, or autocommit.

## Reporting shape Rodolfo expects

Report in this structure:

```text
Escopo checado
Achados reais e ações tomadas
Comparação final: counts + critical_not_match + review_diff
Arquivos críticos que matcham
Diferenças restantes e why expected
Estado operacional Hostinger vs Hetzner
Conclusão direta
```

Use explicit language: “critical_not_match=0”, “review_diff=0”, “review_only_hetzner=0”. If anything remains, name the exact path and why it is safe or not safe.
