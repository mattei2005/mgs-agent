# MGS full VPS migration — Hostinger cutover lessons (2026-06-18)

Use this reference when Rodolfo wants to move the full MGS/Hermes stack from one VPS to another, not just one agent.

## Decision pattern

When the target is operational continuity, prefer **full mirror + controlled cutover** over migrating a single agent piecemeal:

1. Prepare target VPS base packages and SSH access.
2. Create Hermes full backup with `hermes backup`.
3. Also copy the non-Hermes stack: `/root/mgs-agent`, systemd units, root crontab, local Hermes checkout/venv if it carries MGS patches.
4. Restore/import on target with services disabled first.
5. Validate offline before cutover.
6. Run a finalizer/detached script for cutover so Zeus can be stopped without dumping raw logs into Discord.
7. Disable old VPS crons/gateways, final rsync delta, enable target crons/gateways.
8. Validate target live and old VPS standby.

`hermes backup/import` is the right backbone for profiles/config/skills/sessions/data, but it is **not** a whole-VPS clone. It does not cover `/root/mgs-agent`, systemd services, OS packages, custom scripts outside Hermes, or machine-specific SSH access.

## Recommended cutover order

For full migration:

1. Backup current state and crontab.
2. Restore target with all gateways disabled.
3. Validate target `hermes --version`, profile config checks, Codex auth presence, patch guard, systemd unit syntax, 1Password CLI, Git remote, disk.
4. During cutover, stop/disable old crons first.
5. Stop old gateways: Ares/agente legado/Atena, then Zeus.
6. Final delta sync `/root/.hermes` and `/root/mgs-agent`.
7. Install target crontab.
8. Enable/start target gateways: Ares/agente legado/Atena first, Zeus last.
9. Validate target after startup.
10. Audit old VPS via its own credential; do not assume root on the new VPS can inspect the old VPS.

## Post-migration validation checklist

Do not call the migration complete until these are checked with real commands:

- Target identity: hostname, public IP, OS, timezone, disk/memory/load.
- Hermes: `hermes --version`, binary path, repo HEAD, local dirty count.
- Gateways: Zeus/Atena/Ares/agente legado `active` and `enabled`, PIDs, `NRestarts=0` after cutover.
- Logs: no new traceback/OOM/crash-loop after target start. Treat `Opus codec not found` as text-safe/voice-only.
- Profiles: config exists for all agents; `model.provider=openai-codex`, `model.default=gpt-5.5`; auth has Codex access token length and refresh token present without printing tokens.
- `hermes config check` for each profile.
- MGS repo: HEAD, remote, dirty count, size.
- Crons: root crontab line count, cron service active, frequent cron logs updated after cutover.
- 1Password: CLI version and a harmless item lookup without exposing secrets.
- Patch guard: `/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh` passes.
- Systemd failed units: `systemctl --failed` empty.
- Disk breakdown: `/root/.hermes`, `/root/mgs-agent`, migration backups.
- Old VPS: gateways inactive/disabled, crontab empty, `pgrep -af 'hermes|gateway'` count 0.

## Pitfalls observed

- A target root shell does **not** grant access to the old VPS. For old-host audit, retrieve the old VPS credential from 1Password and SSH explicitly.
- After stopping old gateways, units may remain `enabled` and `failed`; run `systemctl disable ...` and `systemctl reset-failed ...` so a reboot cannot resurrect old agents.
- `hermes import` can restore a venv with broken symlinks if the source used a uv-managed Python version not installed on the target. Fix by installing the matching Python with `uv python install <version>` before validating the Hermes binary.
- A successful gateway cutover does not prove Git automation is complete. Validate `mgs-autocommit.service` separately; in the Hostinger cutover it was missing/inactive while the post-commit auto-push hook existed.
- Large rsync progress output can flood Discord/tool context. For future runs, log full rsync output to file and print only step markers plus final stats.
- Keep old VPS in standby 48–72h before cleanup/cancellation. Clean migration backups only after target has been stable.

## Reporting shape

Final report should clearly separate:

- Production target status.
- Old VPS standby status.
- Runtime OK items.
- Real pendências with priority.
- Evidence paths/logs.

Example concise status line:

```text
Hostinger 2.25.165.171 = produção ativa; Hetzner mgs-agent-01 = desativada, endereço anterior reatribuído a terceiros, nunca conectar.
```
