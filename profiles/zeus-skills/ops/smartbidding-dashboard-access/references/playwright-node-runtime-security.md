# Playwright Node security in the persistent SB runtime

## Scope and canonical artifacts

Use for a security correction of the Node interpreter used by `/root/.local/share/mgs/sb-venv`, without upgrading Playwright or changing Chromium, profiles, session identity, cron schedules or business rules.

- Versioned hook source: `/root/mgs-agent/scripts/sb-playwright-node-sitecustomize.py`.
- Versioned bootstrap: `/root/mgs-agent/runtime/sb-venv/mgs-playwright-node.pth`.
- Installed hook: `sb-venv/lib/python3.12/site-packages/sitecustomize.py`.
- Installed bootstrap: `sb-venv/lib/python3.12/site-packages/mgs-playwright-node.pth`.
- Effective supported selector: `PLAYWRIGHT_NODEJS_PATH=/usr/bin/node`.

## Procedure and safety gates

1. Confirm the exact installed system Node version against the current official security release for that branch. A newer major number alone does not establish a fixed build. Do not install a new system package under this procedure without its separate authorization gate.
2. Freeze the shared interpreter, Playwright driver path, browser executable and hashes, authenticated state metadata, gateway PIDs/start times, and stable cron definitions. Exclude scheduler-owned counters and timestamps from schedule equality checks. Back up credential-bearing state only in a private directory with0600 files; never serialize its contents into logs, inventory or Git.
3. Stage the selector by explicitly executing the canonical scoped hook in a disposable canary process. Require actual driver `/proc/<pid>/exe` and `--version`, a local browser launch/DOM interaction and authenticated read-only SB capture. Transport-only success is not functional acceptance.
4. Preserve the canonical headed launch flags, viewport, user agent, browser-budget admission and session lease. Wait for the SPA's network readiness before capturing headers. A header timeout alone does not prove a Node incompatibility or an expired credential. If the Auth0 wall is reached, use the existing approved login route, validate `/company` HTTP200 and authorized-company projection before atomically saving refreshed storage state with0600. Save successful rotating session state before reusing it in another process; never change the password or discard the protected profile.
5. Install only the scoped hook and `.pth` bootstrap after the candidate passes. Ubuntu may import `/usr/lib/python3.12/sitecustomize.py` before a virtualenv's same-named module; a venv-local sitecustomize file alone therefore does not prove activation. The `.pth` explicitly executes the venv-local hook while leaving distro Python untouched. Never edit the distro hook to solve this shadowing.
6. Verify ordinary and `-I` interpreter startup select the approved Node automatically, without a shell export. Test missing approved Node fails closed, an inherited stale override cannot select the old driver, and unrelated interpreters remain unchanged. Standard startup is the supported contract; `python -S` deliberately bypasses site initialization and is not a compliant consumer entrypoint.
7. Validate another fresh authenticated browser process after installation. Capture only allowlisted MGS company identities or counts; `/company` can contain secrets and unrelated accounts. Explicitly prevent business API writes during the canary.
8. Inventory existing old-driver PIDs separately from new consumers. A startup policy does not replace an already-running Node process. Let authorized concurrent work drain naturally; never kill another session's writer or restart gateways merely to make the old-PID count zero. Keep full closure pending until the old drivers have exited or report the exact owner/timing blocker.
9. Recheck browser and embedded-package binary hashes, protected-session continuity/mode, stable schedules and gateway PIDs. The old embedded binary may remain preserved on disk for package integrity/rollback; report the active execution path, not a fictional package upgrade or deletion.
10. If this virtualenv is rebuilt, restore both versioned artifacts and repeat the gates; copying only the Python hook recreates the shadowing failure. Record source/installed hash parity, audit, inventory, checkpoint and REPORT-INFRA.

## Rollback

Restore the previously absent startup policy by moving only the two installed hook/bootstrap files to a private rollback evidence directory. Preserve the embedded Node, system Node, browsers, profiles and scheduler state. Revalidate the prior runtime before reporting rollback. Any destructive cleanup or unrelated system-file change retains its independent Critical Subset gate.
