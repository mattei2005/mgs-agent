# Hermes update 2026-06-04 — all-agent restart + live-shell pytest pitfalls

Session context: Hermes was 158 commits behind (`39fee4f3b` → `30412a977`) while MGS local patches were present. Update completed with backup, patch guard, gateway validation, targeted tests, and cleanup of the previous backup.

## Durable lessons

### 1. Treat Zeus/Atena/Ares as the affected service set

Older controlled update script restarted only:

```bash
systemctl restart zeus-gateway.service atena-gateway.service
```

That leaves Ares on the old process after the repo/dependencies update. Future Hermes updates should either update the script or explicitly restart/validate all active MGS gateway services:

```bash
systemctl restart zeus-gateway.service atena-gateway.service ares-gateway.service
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service mgs-autocommit.service
systemctl show zeus-gateway.service atena-gateway.service ares-gateway.service \
  -p Id -p ActiveState -p MainPID -p NRestarts -p ExecMainStatus --no-pager
```

If Zeus restarts mid-tool and interrupts the session, resume by validating live state before reporting failure.

### 2. Run pytest from the Hermes repo, not `/root/mgs-agent`

A targeted pytest call failed with:

```text
ERROR: file or directory not found: tests/gateway/test_gateway_shutdown.py
```

Root cause: command executed from `/root/mgs-agent`; paths were relative to `/root/.hermes/hermes-agent`.

Use:

```bash
cd /root/.hermes/hermes-agent
venv/bin/python -m pytest -q tests/gateway/test_gateway_shutdown.py tests/gateway/test_restart_resume_pending.py
```

or pass `workdir=/root/.hermes/hermes-agent` in terminal tools.

### 3. Live Discord env can pollute upstream-ish tests

The live Zeus shell had production Discord env vars, e.g. `DISCORD_ALLOWED_CHANNELS`, `DISCORD_THREAD_REQUIRE_MENTION`, `DISCORD_ALLOW_BOTS`, and history backfill settings. These can make isolated Discord adapter tests fail even when production behavior is correct.

For MGS-local test fixtures, clear relevant `DISCORD_*` env vars or set explicit expected behavior before asserting auto-thread/mention behavior. Distinguish:

- **Production invariant tests**: validate MGS behavior (deterministic thread names, auto-add users, non-actionable backfill, planned restart resume).
- **Upstream default tests**: may need local fixture isolation if production env vars are present.

### 4. MGS local behavior intentionally diverges from some upstream default expectations

Validated MGS-local behavior after update:

- Free-response channel means “no mention required”; it does **not** necessarily mean “force inline.” Use `DISCORD_NO_THREAD_CHANNELS` to suppress auto-threading.
- Backfilled Discord context should use a strong read-only/non-actionable header, not the old generic `[Recent channel messages]` header.
- Deterministic auto-thread titles may normalize punctuation/case/truncation differently from older upstream tests.

Patch local tests to assert MGS invariants, not stale upstream assumptions.

## Evidence shape that worked

```text
Hermes: v0.15.1, Up to date
HEAD: 30412a977
origin/main: 30412a977
behind: 0
patch guard: OK
py_compile critical: OK
targeted pytest: 152 passed
Zeus/Atena/Ares: active with fresh PIDs
backup cleanup: previous backup deleted only after validation
```
