---
name: secure-remote-windows-automation
description: "Use when securing remote Windows GUI automation."
version: 1.2.2
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [windows, remote-access, computer-use, tailscale, openssh, cua-driver]
    related_skills: [computer-use, hermes-agent-operations, adspower-segurador-token-collector]
---

# Secure Remote Windows Automation

## When to Use

Use this skill when a Hermes host must securely control GUI software on a separate, logged-in Windows machine, including first-time setup, transport repair, post-update revalidation, or safe retirement. Do not use it for the application's business workflow after connectivity is proven; route that work to the application-specific skill.

## Scope

The transport is:

```text
Hermes host
→ SSH over Tailscale
→ cua-driver MCP proxy
→ named pipe on the Windows interactive session
→ target GUI application
```

Keep application-specific operations in their own skill. This skill owns only machine setup, transport, validation, persistence, and rollback.

For an authorized account task that needs the user's real Windows Chrome session, a browser password-manager extension, or a human unlock handoff, load `references/interactive-browser-authentication.md`.

## Always-on rules

- Use a private overlay network. Never publish OpenSSH, the cua-driver named pipe, an application's local API, CDP/WebSocket endpoint, or MCP listener to the public internet.
- When an official application MCP depends on `localhost`, run it on Windows beside the application and carry only stdio over key-only SSH; do not solve loopback addressing by exposing the application's port.
- Keep `cua-driver serve` in the logged-in user's interactive session. An SSH service process runs outside that visual session and must proxy to the existing named pipe rather than launch the GUI driver itself.
- Start with read-only probes: network reachability, `doctor`, daemon status, `list_apps`, `list_windows`, and capture. Do not click or type until the transport is proven and the application operation is separately authorized.
- Use a dedicated SSH key, strict host-key checking, password authentication disabled, and a firewall rule restricted to the exact Tailscale source IP.
- Treat persistent Hermes configuration and gateway restart as a separate activation phase. Validate the temporary wrapper first, then obtain any required critical confirmation before config or restart.
- Never print private keys, application API keys, browser cookies, tokens, or secrets in diagnostics or reports.
- For browser authentication on remote Windows, let the browser password manager fill secrets. Never relay a password through SSH, shell arguments, clipboard automation, CUA typing, logs, or chat; if the manager is locked, release the shared desktop lease and require the user to unlock it locally before resuming.
- Treat window titles, accessibility labels, and application notes as potentially secret-bearing. Some applications concatenate profile notes into a browser title; match locally and report only sanitized identity fields, booleans, and PIDs.
- After a cua-driver or Hermes update, re-resolve the versioned Windows binary path and rerun the entire read-only canary; a wrapper pinned to an old version directory can silently become stale.

## Procedure

### 1. Prove the private network first

Record the two Tailscale identities and verify the Windows host is reachable from the Hermes host:

```bash
tailscale ping --timeout=5s --c=1 <WINDOWS_TAILSCALE_IP>
```

A DERP relay is acceptable for correctness; it only affects latency. Do not open application or SSH ports on the router.

### 2. Install and validate cua-driver in the interactive Windows session

Use the current official Hermes Windows installer and current documented non-interactive option; do not reuse remembered installer flags without checking the current script/docs.

Then run in the logged-in Windows user's PowerShell:

```powershell
hermes computer-use install
hermes computer-use doctor
$cua = Get-ChildItem "$env:LOCALAPPDATA\hermes\tools\cua-driver-*-win32-x64\cua-driver.exe" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 -ExpandProperty FullName
& $cua status
```

Enable the canonical interactive-logon autostart and validate both registration and runtime:

```powershell
& $cua autostart enable
& $cua autostart kick
& $cua autostart status
& $cua status
```

If the task reports success but the daemon is absent, prove the binary independently before changing anything:

```powershell
Start-Process -FilePath $cua -ArgumentList 'serve' -WindowStyle Hidden -WorkingDirectory $env:USERPROFILE
Start-Sleep -Seconds 3
& $cua status
```

When direct launch works, inspect the scheduled task's `Execute`, `Arguments`, `WorkingDirectory`, principal, and last result. Repair quoting or interactive-logon context; do not reinstall a healthy driver. A known-good action shape is a PowerShell task whose command calls `Start-Process -FilePath '<resolved exe>' -ArgumentList 'serve'` without wrapping the entire argument string in an extra literal quote pair.

### 3. Prove the daemon sees the visual session

Run read-only calls against the named pipe:

```powershell
& $cua call list_apps --socket '\\.\pipe\cua-driver'
& $cua call list_windows --socket '\\.\pipe\cua-driver'
```

`list_apps` proving the target process is running is useful, but its per-app `windows` array may be empty. Use `list_windows` as the authoritative window-discovery probe before concluding that the application has no controllable window.

### 4. Add private, key-only OpenSSH access

Install Windows OpenSSH Server, create a dedicated Ed25519 key on the Hermes host, and place only its public key in the correct Windows authorized-keys file. For an administrator account, use:

```text
C:\ProgramData\ssh\administrators_authorized_keys
```

Set language-neutral ACLs with SIDs so localized Windows group names do not break setup:

```powershell
icacls.exe $auth /inheritance:r /grant '*S-1-5-32-544:F' /grant '*S-1-5-18:F'
```

Disable the broad default inbound SSH rule and create a replacement limited to:

```text
Local address:  Windows Tailscale IP
Remote address: Hermes host Tailscale IP
Protocol/port:  TCP 22
```

Harden `sshd_config` before restarting the service:

```text
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
AllowUsers <WINDOWS_USER>
```

Always preserve a rollback copy, run `sshd.exe -t -f <config>`, and only then restart `sshd`. Validate effective settings with `sshd.exe -T`; service status or numeric enum values alone do not prove key-only authentication.

From the Hermes host, prove the exact path with no password prompt:

```bash
ssh -i <DEDICATED_KEY> \
  -o BatchMode=yes \
  -o StrictHostKeyChecking=accept-new \
  -o ConnectTimeout=10 \
  <WINDOWS_USER>@<WINDOWS_TAILSCALE_IP> 'hostname & whoami'
```

After the first trusted connection, switch the durable wrapper to `StrictHostKeyChecking=yes`.

### 5. Build the SSH-to-MCP wrapper

Copy and fill `templates/cua-driver-ssh-wrapper.sh`, then make it executable. The wrapper has three contracts:

1. Forward `manifest` and other read-only CLI subcommands to the remote binary.
2. When Hermes invokes `mcp`, strip caller-supplied transport flags and insert `--socket \\.\pipe\cua-driver` so the proxy always attaches to the already-running interactive daemon.
3. When global `approvals.mode: off` makes Hermes request an unrestricted private embedded daemon, fail closed instead of launching that daemon from Windows OpenSSH Session 0: keep only a local placeholder lifecycle, route `status` and `mcp` to the existing standard-mode interactive daemon, and make the private-socket `stop` a no-op so one Hermes session cannot stop the shared daemon. This deliberately narrows the requested permission mode; never forward unrestricted/bypass environment into Windows.

Use `BatchMode=yes`, strict host-key checking, no TTY, and `ClearAllForwardings=yes`. Do not implement this as a TCP bridge for the named pipe.

### 6. Bridge an application-local MCP without exposing its API

When the Windows application ships an official MCP or CLI whose API/CDP addresses resolve to `localhost`, execute that server on Windows and bridge only its stdin/stdout over SSH:

```text
Hermes profile → local wrapper → SSH stdio → Windows launcher → application MCP → localhost API
```

Apply these contracts:

1. Keep the application API authenticated and block its TCP port on remote interfaces; validate that the Hermes host cannot connect directly while authenticated localhost succeeds on Windows.
2. Keep secrets on Windows in a protected file or approved local secret store. The launcher reads them locally; never put them in SSH arguments, MCP YAML, process listings, stdout, or reports.
3. Reserve wrapper stdout exclusively for MCP JSON-RPC. Send diagnostics to stderr or suppress them.
4. If multiple long-lived gateways share the application, do not hold the shared lease merely because an idle MCP transport is connected. Put a transaction-aware proxy in front of the application MCP: acquire the lease at the first active tool call, keep it across the related multi-call browser operation, release it after the terminal close action or a bounded idle-recovery timeout, and return a structured busy error without killing the MCP session when another authorized agent owns the lease. A process-lifetime lease is acceptable only for short-lived, single-operator batch clients; on long-lived gateways it lets the first connection monopolize the application indefinitely.
5. Install cleanup traps before launching SSH, but do not replace the shell with `exec ssh`; replacing it prevents the wrapper's EXIT trap from releasing the lease. Capture the SSH exit code, return normally, then release in the trap.
8. Validate in layers: raw MCP initialize + `tools/list`, Hermes `mcp test`, resolved least-privilege allowlist readback, then one non-destructive real application canary. Raw `tools/list` and `mcp test` may enumerate the server's full catalog; the resolved profile config and `hermes tools list` prove what Hermes actually exposes. Report those counts separately instead of calling every discovered tool enabled.
9. Install every remote validation script at a durable inventoried path before the finalizer, verify its hash by remote readback, and execute it once. Never let a closure gate assume that a setup-time scratch probe still exists on the remote host.
7. Treat profile/process close operations as potentially asynchronous; poll the authoritative status endpoint to a bounded terminal state before declaring cleanup complete.
8. If setup or rotation creates temporary credential artifacts, keep them only until vault readback, Windows installation, authenticated localhost probing, and the application canary all pass. Then search protected caches for the exact secret bytes without printing them, securely remove only matched temporary artifacts, and require zero remaining matches; preserve the approved vault item and protected Windows runtime copy.

### 7. Run canaries before persistent activation

Validate syntax and the driver's manifest:

```bash
bash -n <WRAPPER>
<WRAPPER> manifest
```

Prove Hermes can establish MCP and reach Windows capabilities:

```bash
HERMES_CUA_DRIVER_CMD=<WRAPPER> \
  hermes -p <PROFILE> computer-use doctor
```

Then discover the target window through the wrapper:

```bash
<WRAPPER> call list_windows
```

For a minimized Windows target, `get_window_state` correctly refuses an all-black capture. Restore it with `bring_to_front` using both required `pid` and optional exact `window_id`, then recapture:

```powershell
'{"pid":1234,"window_id":5678}' |
  & $cua call bring_to_front --socket '\\.\pipe\cua-driver'

'{"pid":1234,"window_id":5678,"max_elements":20}' |
  & $cua call get_window_state --socket '\\.\pipe\cua-driver'
```

On Windows PowerShell 5.1, pipe multi-field JSON through stdin. Passing it as a positional argument strips the field-name quotes before cua-driver parses it. Also parse the returned JSON's logical error/degraded fields; a process exit code alone is not sufficient acceptance evidence.

A successful read-only capture must prove at least:

```text
correct pid/window_id
nonzero screenshot dimensions
nonempty screenshot payload
expected application/window identity
no screenshot_error
```

Accessibility trees for Chromium/Electron shells may contain only a root pane or document. That is not a transport failure when pixels are valid; use the visual/pixel path later under the application's own authorization rules.

### 8. Activate Hermes only after the canary passes

Set `HERMES_CUA_DRIVER_CMD` to the validated executable wrapper and enable the `computer_use` toolset for the intended platform/profile using Hermes' native config writer. Inspect the deployed config parser before choosing the writer: when `hermes config set` supports JSON arrays, this is the preferred narrow sequence:

```bash
hermes -p <PROFILE> config set platform_toolsets.<PLATFORM> '["<PLATFORM_TOOLSET>","computer_use"]'
hermes -p <PROFILE> config get platform_toolsets.<PLATFORM>
```

Do not trust the printed shape alone. Load the resolved config and confirm the value is a real list containing the existing platform toolset plus `computer_use`; if that version stores JSON-looking text as a scalar, use Hermes' native atomic YAML writer instead. Preserve all existing platform toolsets.

If activation requires a gateway restart, use the environment's safe detached restart flow, restart the initiating agent last, and run the post-restart validation outside the active tool chain. When the active gateway's lifecycle guard refuses to invoke the canonical restart helper, do not disguise the command or keep retrying nested wrappers. Prepare a one-shot launcher for the host scheduler that:

1. posts the user-facing pre-restart status **before** scheduling;
2. removes its own temporary cron entry immediately on start;
3. invokes the canonical detached restart helper from outside the gateway process;
4. waits with a bounded timeout for the finalizer's explicit success/failure marker;
5. reruns `hermes computer-use doctor` and a read-only target-window lookup after readiness;
6. posts the validated result or exact blocker back to the source thread.

For a self-removing one-shot scheduler entry, first apply the canonical global cron policy: inventory root/system crons, timers, every Hermes profile, and application schedulers; normalize timezones; choose an exact future minute with zero non-baseline operational collisions; and record unavoidable dense-baseline overlap, lock, and resource isolation. Freeze and validate the launcher before calculating the slot, then leave enough lead time for the remaining write/readback turns so the minute cannot expire. The launcher must delete its scheduler entry before doing any restart work, use its own `flock`, and have no repeating fallback; do not use `* * * * *` merely to compensate for tool-call latency.

Size the external validator deadline from the full lifecycle budget, not only the helper readiness window: `restart_drain_timeout + per-agent readiness timeout + safety margin`. With Zeus defaults this is at least `240s + 180s + margin`; use 600s unless the live config proves a different larger requirement. A 240s total deadline races the normal drain and can publish a false failure seconds before the helper reports `gateway_restart_agent_ready` and `gateway_restart_finalizer_finished`. Before alerting on timeout, reconcile the finalizer log, audit events, service state, and Discord readiness; explicit late success wins over the earlier local timeout.

When a finalizer calls Hermes, use the absolute deployed `hermes` binary because cron/system schedulers may omit the user-local bin directory. If an inline validator imports Hermes runtime modules such as `utils`, derive the Python interpreter from that executable's shebang and validate it before scheduling; system `python3` may not have the deployed module path.

After writing the one-shot entry, require two readbacks: the exact scheduler file/line and a fresh global collision audit. If the normal control-plane inventory omits a newly created `/etc/cron.d` entry, do not treat an empty result as absence; directly enumerate enabled `/etc/cron.d` and `/etc/crontab` lines for the target minute, reconcile that result with the broader audit, and record the fallback.

When the launcher posts Discord Markdown, build the JSON with `jq` or Python and keep Markdown backticks out of double-quoted shell literals; backticks inside double quotes execute command substitution before the message is sent.

### 9. Validate and preserve rollback

After activation, verify:

- SSH key login still works with `BatchMode=yes`.
- `sshd -T` remains key-only and restricted to the intended user.
- The firewall's local and remote address filters are exact.
- cua-driver is `registered (running)` in the interactive session.
- `hermes computer-use doctor` reaches the remote Windows host.
- A read-only window capture succeeds from the activated profile.

Rollback in reverse order: disable the Hermes binding, restore prior Hermes config, restart safely if required, remove only the narrow SSH firewall rule, restore the backed-up `sshd_config`, and stop/disable services only when the authorized rollback scope includes them.

## Pitfalls

- Do not mistake a reachable Windows SSH shell for access to the interactive desktop; Session 0 isolation is why the named-pipe proxy is required.
- Do not trust `LastTaskResult=0` when the daemon is absent; malformed PowerShell quoting can exit successfully without launching the child process.
- Do not infer window absence from `list_apps.windows=[]`; query `list_windows` directly.
- Do not use `Get-Process.MainWindowTitle` from an OpenSSH session as sole proof of a GUI launch; Session 0 can return an empty title while the interactive window exists. Use cua-driver `list_windows` for window identity, then pair it with a sanitized `Get-Process -Id` probe for `Exists`/`Responding` when process health is needed.
- When Chromium/Electron returns `background_unavailable` for text input, recapture and retry only the text action with foreground delivery under the existing application authorization; do not replay the preceding click, and verify the resulting field value before continuing.
- Do not call `bring_to_front` with only `window_id`; the tool schema requires `pid`.
- Do not accept a capture that merely returned JSON; inspect screenshot presence, dimensions, degraded reason, and screenshot error.
- Do not stream a multi-command diagnostic to `powershell.exe -Command -` when it launches external programs that inherit stdin; a child can consume the remaining script before PowerShell parses it. Upload a temporary `.ps1` over SCP, execute it with `powershell.exe -File`, and emit only reduced readback.
- Do not expose an application's localhost API to make remote control easier. Run its official CLI/MCP on Windows and bridge stdio over SSH; add a separately authenticated private proxy only when that API workflow is explicitly approved.
- Do not use `exec ssh` in a wrapper that directly owns a renewable lease; shell replacement bypasses the wrapper's EXIT cleanup and leaves a stale lock after the transport exits. For long-lived shared gateways, prefer a transaction-aware proxy instead of a process-lifetime lease.
