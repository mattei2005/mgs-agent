# MGS Migration and Agent Bootstrap

> Extracted from the former monolithic `SKILL.md` on 2026-07-10. Load this file only when its branch is relevant.

## 7. Full MGS VPS migration / restore

Use `references/mgs-full-vps-migration-hostinger-2026-06-18.md` when Rodolfo asks to move the MGS/Hermes operation to a new VPS or asks whether to use `hermes backup/import` for migration. Core rule: `hermes backup/import` is the fast path for Hermes state, but a complete MGS migration also requires `/root/mgs-agent`, systemd gateway units, root crontab, OS packages/base tools, 1Password/uv/Node/Python, validation, REPORT-INFRA and updated infra inventory.

Preferred workflow: prepare target VPS → backup Hermes + `/root/mgs-agent` + units + crontab → transfer full runtime → restore Hermes/import → validate offline with gateways disabled → detached cutover finalizer stops old crons/gateways, final-syncs, installs crontab on target, then starts Ares/agente legado/Atena before Zeus → validate live host/IP/services/logs. If copied Hermes venv fails with `cannot execute: required file not found`, check uv-managed Python symlinks and run `uv python install <missing-version>` on the target before retrying `hermes --version`.

## 7. Full VPS migration / Hostinger cutover

When Rodolfo wants to migrate the whole MGS/Hermes operation to a new VPS, use `references/mgs-full-vps-migration-hostinger-2026-06-18.md`. Core rule: `hermes backup/import` is the backbone for Hermes state, but full MGS migration also requires `/root/mgs-agent`, systemd units, crontab, local Hermes checkout/patches, 1Password validation, final delta sync, target startup validation, and old-VPS standby audit. Prefer **full mirror + controlled cutover** over piecemeal agent migration when Rodolfo's concern is future drift.

Do not call the cutover complete until the target has Zeus/Atena/Ares/agente legado `active` + `enabled`, crons active, Codex auth present, patch guard OK, and the old VPS has gateways inactive/disabled, crontab empty, and zero Hermes/gateway processes. Validate `mgs-autocommit.service` separately; post-commit auto-push existing is not enough if the watcher service is missing.

When Rodolfo asks to “look again”, “compare everything”, or says he is being persistent, run a fresh deep comparison instead of repeating the prior conclusion. Use `references/mgs-vps-migration-deep-file-comparison.md`: generate new SHA256 manifests on both hosts, classify runtime drift separately from stable-file drift, pull missing historical archives if needed, sync stable profile/MGS surfaces to the standby host, keep old-host services disabled, and report `critical_not_match`, `review_diff`, `review_only_hostinger`, and `review_only_hetzner` explicitly.

When Rodolfo challenges the result with “olha de novo”, “TUDO”, “seja mais detalhista” or similar, run the deeper old-vs-new comparison in `references/mgs-vps-migration-deep-compare-playbook.md`: fresh SHA256 manifests on both VPSs, critical file matching, stable production→standby sync for non-runtime drift, failed-unit cleanup on standby, runtime-drift classification, Git clean verification, and REPORT-INFRA for any infra/data/script changes. If a restart recovery checkpoint interrupts the audit, first inspect state and send a short recovery/status message; continue only after Rodolfo confirms.

When Rodolfo asks for a persistent “compare TUDO” verification after migration, run the deep manifest workflow in `references/mgs-vps-migration-deep-file-comparison.md`: compare `/root/mgs-agent`, Hermes profiles, Hermes checkout, systemd units and crontabs by SHA256/size; copy any historical old-VPS-only `backups/`, `tmp/` or `data/backups/` artifacts to production; disable **all** old-VPS services including `mgs-autocommit`; then classify remaining differences as runtime-only vs. risky before final reporting.

Post-migration finalization must also close the Git/runtime loop: install `inotify-tools` if needed, recreate/enable `/etc/systemd/system/mgs-autocommit.service`, secret-scan dirty files before staging, commit/push controlled migration state, clean or ignore runtime artifacts, and prove end-to-end with a create/delete auto-commit + auto-push smoke test. Detailed playbook: `references/mgs-hostinger-post-migration-autocommit-finalization-2026-06-18.md`.

After cutover, use `references/post-migration-host-hardening.md` to independently audit OOM versus shutdown cleanup, swap posture, protected credential scrubbing versus genuinely missing service credentials, retired IP/domain references, hashed SSH known-host entries, and downstream firewall/Fail2Ban allowlists. Keep each state-changing remediation behind its own approval gate.

When Rodolfo asks whether the old VPS can be deleted, validate old-host inactivity with `hostname`, root `crontab -l`, gateway service states, `pgrep -af 'hermes|gateway'`, and current-production health. If docs need cleanup, update only current-state operational docs/backlog/inventory; preserve audit logs, changelogs, Discord imports and migration logs as historical evidence. Detailed playbook: `references/mgs-vps-decommission-documentation-cleanup-2026-06-19.md`.

## 8. New MGS agent bootstrap

When Rodolfo asks to start a new MGS agent/profile (Ares, agente legado or future agents), use `references/mgs-new-agent-bootstrap.md`. Core rule: clone profile/config as needed, but immediately blank any inherited Discord bot token; do not create/enable the systemd gateway until the agent has its own dedicated bot token and Rodolfo confirms the Critical Subset system-file write.

When Rodolfo provisions a fresh Hostinger VPS for migration, use `references/hostinger-vps-agent-migration-bootstrap.md`. Default recommendation is Ares as the canary, Zeus last, Atena only after the new host is proven. First do read-only inventory; then get explicit confirmation before installing packages or changing system config. Initial bootstrap should avoid firewall/SSH hardening unless Rodolfo explicitly requests it.

After the profile/SOUL/config exist and Rodolfo has created the Discord application/bot, use `references/mgs-new-agent-discord-activation.md` for the live activation path: Discord OAuth permissions, 1Password token retrieval via MGS service-account env, token/API validation without leaking secrets, channel `403 Missing Access` diagnosis, Message Content Intent pitfall, systemd service creation, and end-to-end Discord validation.

Additional validated agente legado bootstrap notes live in `references/mgs-legacy-agent-discord-bootstrap-2026-06-06.md`: 1Password token retrieval with project service-account env, channel `403 Missing Access` validation/fix, Discord Developer Portal `Message Content Intent` requirement, and stopping/disabling the service to avoid restart loops until privileged intents are enabled.

Critical pitfalls for new Discord agent gateways:

- Do **not** blindly sync inherited bundled/vendor skill categories into `/root/mgs-agent/profiles/<agent>-skills/`; add the new profile to SOUL/config sync first, and only add selective MGS-specific skill sync after deciding the category is genuinely custom/operational.
- Validate bot token internally without printing it: token length, decoded bot/application ID, and Discord API `/users/@me`.
- A bot can be valid and in the guild but still fail `GET /channels/<channel_id>` with `403 Missing Access`; fix channel/category permissions before starting the gateway.
- Hermes Discord gateway needs Discord Developer Portal → Bot → Privileged Gateway Intents → **Message Content Intent = ON**. If absent, logs show `discord.errors.PrivilegedIntentsRequired`; stop/disable/reset-failed the service until Rodolfo enables it, then start again.
- Only report end-to-end success after a real Discord mention test in the new agent channel produces an agent response, not just because systemd is `active`.

After the Discord application/bot exists and the token is stored securely, use `references/mgs-new-agent-discord-activation.md` for the phase-2 workflow: record app/bot IDs and permissions integer, fetch the token via 1Password service-account env without printing it, validate `/users/@me`, validate guild/channel access, handle `403 Missing Access`, then request explicit Critical Subset confirmation before creating systemd.

Session-specific agente legado bootstrap notes live in `references/mgs-new-agent-bootstrap-legacy-agent-2026-06-06.md`, including the confirmed agente legado channel ID, bot IDs, safe Phase 1 validation shape, and the pitfall that broad inherited skill sync can accidentally version hundreds of bundled creative skills.
