# Hermes/MGS maintenance notes — 2026-06-09

Use this as session-specific support for full maintenance runs where Hermes itself is already at upstream HEAD, but surrounding system/tooling updates are available.

## What happened

- Hermes repo was already up-to-date: `v0.16.0`, `HEAD == origin/main`, `behind 0`.
- System/userland updates were still available and were applied separately:
  - `nodejs` 22.22.2 → 22.22.3
  - `npm` 11.15.0 → 11.16.0
  - `@openai/codex` 0.133.0 → 0.138.0
  - `corepack` 0.34.6 → 0.35.0
  - Ubuntu packages including apparmor/cloud-init/systemd/poppler/rsync/etc.
- `hermes update` was blocked by the safety guard because it restarts gateways/kills running agents. Correct action: do **not** retry/bypass; continue with non-Hermes updates and validate Hermes state directly.
- A reboot was required after package upgrades due to kernel/linux-base/apparmor. Treat reboot as separate Critical Subset authorization.

## Validation pattern used

1. Backup profiles first:
   - `/root/hermes-profiles-backup-YYYYMMDD-HHMMSS.tar.gz`
   - record size and checksum, but do not print secrets.
2. Validate Hermes is still at upstream HEAD:
   - `hermes --version`
   - `git fetch origin main`
   - `rev-parse HEAD/origin/main`, `rev-list HEAD..origin/main`, `git status --short`
3. Validate runtime/tooling:
   - `node -v`, `npm -v`, `npx --yes @openai/codex --version`, `corepack --version`
   - `apt list --upgradable` and `npm outdated -g --depth=0`
4. Validate services:
   - `systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service legacy-agent-gateway.service mgs-autocommit.service`
   - `systemctl show ... -p Id -p ActiveState -p MainPID -p NRestarts -p ExecMainStatus`
5. Validate MGS local patches:
   - `/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh`
   - `py_compile` on critical files.
6. Validate auth sanitized:
   - root + Zeus/Atena/Ares/agente legado `auth.json`
   - report `active_provider`, `auth_mode`, token length, refresh-token presence only.

## Test drift pitfall

The old named test `tests/gateway/test_gateway_shutdown.py::test_planned_restart_keeps_resume_pending_after_graceful_drain` no longer existed. Do not treat this as product failure; collect tests first or run the whole relevant files:

```bash
cd /root/.hermes/hermes-agent
py=/root/.hermes/hermes-agent/venv/bin/python
"$py" -m pytest --collect-only -q tests/gateway/test_gateway_shutdown.py tests/gateway/test_restart_resume_pending.py
"$py" -m pytest -q tests/gateway/test_gateway_shutdown.py tests/gateway/test_restart_resume_pending.py tests/gateway/test_discord_free_response.py
```

If local MGS patches intentionally change behavior, update local MGS tests to match the MGS policy before declaring failure. In this run the test file was aligned with two MGS invariants:

- `discord.free_response_channels` only bypasses mention gating; it does **not** force inline replies. Use `DISCORD_NO_THREAD_CHANNELS` for explicit inline behavior.
- Channel backfill context should be labeled as read-only/non-actionable:
  `[READ-ONLY RECENT CHANNEL CONTEXT — NON-ACTIONABLE]` plus instruction that only `[New message]` is actionable.

After aligning tests with the MGS policy, targeted gateway tests passed: `119 passed`.

## Reporting shape

Final report should include, without being asked:

- Hermes version/commit and whether behind upstream.
- System/tooling versions changed.
- Gateways and autocommit live status.
- Backup path, size, and disk remaining.
- Codex auth status sanitized for all MGS profiles.
- Reboot-required status and packages that triggered it.
- Explicit note that Claude/Anthropic tooling was not updated unless Rodolfo authorized it.
