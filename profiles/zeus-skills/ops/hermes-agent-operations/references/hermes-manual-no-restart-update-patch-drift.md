# Hermes manual update without gateway restart — patch drift playbook

Context: MGS sometimes needs to update `/root/.hermes/hermes-agent` while keeping Zeus/Atena/Ares gateways online until Rodolfo explicitly authorizes restart. The official `hermes update` path auto-restarts gateways at the end, so a manual controlled path is safer when the instruction is “update without restart”.

## Pattern

1. Pre-check live state:
   - `hermes --version`
   - `git -C /root/.hermes/hermes-agent fetch origin main`
   - `git rev-parse HEAD origin/main`, `git rev-list --count HEAD..origin/main`
   - `git status --short`
   - `systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service`
   - disk space and MGS patch guard.
2. Backup before mutation:
   - tar profiles/config/auth, excluding volatile caches/logs if needed;
   - save `git diff` to `/root/mgs-agent/patches/hermes/local-pre-manual-update-<stamp>.patch`;
   - save pre-update HEAD/origin/behind metadata.
3. Validate canonical patches against `origin/main` in a temporary worktree before touching the live checkout:
   - `git worktree add --detach /tmp/... origin/main`
   - `git apply --check` for canonical MGS patch files.
4. Manual no-restart update:
   - `git reset --hard HEAD` to clear tracked local patch state after backup;
   - `git pull --ff-only origin main`;
   - apply canonical MGS patches / run `ensure-hermes-mgs-patches.sh`;
   - reinstall Python deps with `uv pip install --python "$repo/venv/bin/python" -e "$repo[all]"`;
   - run npm install/build for `web` and `ui-tui` if package.json exists;
   - clear stale `.update_check` files.
   - for any detached finalizer launched with `systemd-run`, export `HOME=/root` and `PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin` before calling `hermes`; transient units do not inherit `/root/.local/bin` and otherwise fail with exit 127 before the restart starts.
   - size the post-restart readiness timeout above the service's `TimeoutStopSec` plus `RestartSec` (MGS gateways currently need at least 360s; use 420s). A Zeus restart during an active Discord turn can spend close to 300s in graceful shutdown; a 120s finalizer timeout creates a false failure even though systemd later starts the new process successfully. Final authority is the new active PID + fresh gateway readiness marker + smoke, not the early timeout.
5. Validate before reporting success:
   - HEAD equals origin/main and behind=0;
   - patch guard OK;
   - py_compile critical files;
   - targeted tests for restart/session and Discord MGS behavior;
   - services still active.
6. Ask Rodolfo separately before graceful restart.

## Patch drift lessons

- `git apply --reverse --check` can false-fail when a composite/superset local patch is already present but context drifted. The durable check is invariants + compile, not reverse-check alone.
- For MGS Discord patch guard, invariant-positive states should be accepted with a log such as “patch invariants already present despite context drift”. Required invariants include deterministic thread naming helper, `DISCORD_THREAD_AUTO_ADD_USERS`, auto-thread member sync marker, and planned restart resume marker.
- Applying a full saved local patch after update can fail if canonical patches already applied a subset. If needed, apply only cleanly portable files with `git apply --3way --include=<path>` and then port conflicted code manually from invariants/tests.
- Environment variables from the live Zeus process can contaminate pytest, especially `DISCORD_ALLOWED_CHANNELS`. For isolated Discord tests, run with explicit test env like `DISCORD_ALLOWED_CHANNELS='*'` or unset the production channel allowlist.
- Some pytest target names are brittle across upstream updates; if a specific node id no longer exists, run the owning file or collect tests rather than assuming update failure.

## Reporting shape

Report as: repo rev/behind, backup path+size, patch guard, py_compile, targeted test counts, services active, and whether restart was executed. Do not claim gateways are running new code until restart is authorized and completed.