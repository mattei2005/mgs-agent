# Interactive Browser Authentication on Remote Windows

Use this recipe when an authorized task must run in the logged-in user's real Chrome profile because a server or clean automation browser is rejected by site risk controls, or because the credential is available only through the user's browser password-manager extension.

## Procedure

### 1. Acquire and prove the interactive desktop

Acquire the environment's shared Windows-computer lease before the first input. Then run `list_windows` and require the intended logged-in desktop and browser identity. Do not infer GUI access from SSH reachability; OpenSSH commands normally execute in Session 0.

If Chrome is already open, reuse the existing user-owned window and create only the requested tab. Do not close the browser or unrelated tabs unless that cleanup was explicitly authorized.

### 2. Launch Chrome in the interactive session when absent

Do not rely on `Start-Process`, `cmd /c start`, or `explorer.exe <url>` from SSH as proof of a visible launch; they can run or hang in Session 0 while `list_windows` remains unchanged.

Use an ephemeral interactive scheduled task, run it immediately, delete the task in the same control path, and validate the result with cua-driver `list_windows`:

```powershell
$task = "HermesTempBrowser-$PID"
$exe  = "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
$url  = "<AUTHORIZED_URL>"
$time = (Get-Date).AddMinutes(5).ToString("HH:mm")
$action = '"{0}" "{1}"' -f $exe, $url

schtasks.exe /Create /TN $task /TR $action /SC ONCE /ST $time /RU $env:USERNAME /IT /F
if ($LASTEXITCODE -ne 0) { throw "interactive browser task creation failed" }
try {
    schtasks.exe /Run /TN $task
    if ($LASTEXITCODE -ne 0) { throw "interactive browser task launch failed" }
} finally {
    schtasks.exe /Delete /TN $task /F | Out-Null
}
```

Require all three gates before continuing:

```text
task creation succeeded
immediate run succeeded and the task was deleted
list_windows shows a visible, responsive Chrome window with the expected safe page title
```

Resolve the executable path first instead of assuming Chrome is on `PATH`. Keep the task name unique and credential-free.

### 3. Navigate and submit only non-secret identity data

Capture the exact Chrome window by fresh PID/window ID. For each indexed action, resolve the exact semantic label and role again from that capture and require a unique match; never reuse the previous capture's ordinal. Prefer the index over translating its native AX bounds into a coordinate click. For a pixel-only control through Hermes Computer Use, pass the position measured in the returned screenshot directly: the wrapper maps screenshot-relative coordinates to native input coordinates. Do not multiply by the AX/native bounds scale or pass native bounds as screenshot pixels, even if a capture summary suggests doing so; this can scale twice and click outside the control. Verify the delivered coordinates and actual UI after the first pixel action.

Type only the non-secret account identifier through CUA. If Chromium returns `background_unavailable`, retry only that text action in foreground mode, then recapture and require the expected identifier in the field before clicking Continue.

### 4. Fill the password through the browser password manager

At the password page:

1. Confirm the page origin is the intended site. Let the login form finish loading, then recapture immediately before any authentication-related click: a passkey chooser can appear asynchronously and change the active window or element mapping.
2. Inspect the current authentication surface before opening the extension. If Windows Security shows **Choose a passkey** for the intended domain, report it as a passkey-provider selection, not proof that the vault is locked, credentials were rejected, or the bank blocked automation. Preserve the prompt, release the lease, and ask the user to complete authentication directly on the target machine; resume with step 5 after acknowledgement. Otherwise, open the password-manager extension.
3. If it is already unlocked, select the exact site/identifier item and let the extension fill the page; never reveal the password field.
4. If the manager asks for its master password or Windows Security asks for a Windows Hello PIN to unlock it, stop. Leave the site and popup open, release the shared desktop lease, and ask the user to unlock it directly through their Remote Desktop session. Never ask for either secret in chat, reveal a saved unlock item, or relay the secret through CUA. Explain this as the protected human-unlock workflow, not an untested claim that the field is technically undrivable.
5. Treat the user's completion acknowledgement as the trigger for immediate read-only validation, not proof of recovery. Reacquire the lease, rediscover the Chrome PID/window ID, and inspect the current target page first. If the requested account area is already authenticated, proceed to its readback without reopening the extension or provoking another challenge. Validate manager unlock, website authentication and any device-security hold separately; completing one does not prove the others cleared.

A server-side 1Password Service Account may safely confirm item metadata, but it does not authorize or justify carrying the resolved password into a different remote browser through SSH, shell variables, clipboard injection, MCP arguments, or synthetic typing. The fill must remain inside the password manager's protected browser path.

#### Windows Hello configuration guidance

When the user asks how to avoid a Hello prompt, identify its purpose before giving instructions:

- **1Password vault unlock:** the user can open and unlock the desktop app, select their account/collection → **Settings → Security**, then turn off **Unlock using Windows Hello** to use their 1Password account password instead. Alternatively, turn off only **Show Windows Hello prompt automatically** to retain Hello as an optional unlock method. Both alternatives still require the user to perform protected unlocks; neither grants the agent permission to enter the master password.
- **Website passkey held by Windows:** changing 1Password's unlock preference does not remove the passkey's device-verification requirement. Preserve it for human completion, or use the site's existing username/password option through an unlocked password-manager extension if the site offers that option. Do not delete or replace a passkey as a login repair.
- **Unclear prompt:** ask which app/domain the dialog names or inspect the exact dialog read-only; a generic Windows Security title alone does not establish which gate is active.

Use the current official instructions at `https://support.1password.com/windows-hello/` and `https://support.1password.com/unlock-auto-lock/?windows` when explaining these settings; recheck labels before changing them. Do not remove device-wide Windows Hello or disable auto-lock merely to make an account-reading task unattended. After any user-performed change, validate the exact browser/manager/site state again and report only the gate actually cleared; absence of a visible Hello dialog does not prove an unlocked vault or successful login.

### 4a. Recover a missing browser-extension suggestion

- If an authorized site's login page loads but the password-manager toolbar button produces no verified popup, reload the exact login tab once and inspect a fresh screenshot for the small inline 1Password button inside the username field. Clicking the field itself may not open the suggestion; click the inline button, then select the exact approved item through the manager. Do not infer that the vault is locked or unavailable merely from a missing toolbar popup.
- The inline suggestion may be visible only in pixels, not in the browser accessibility tree. Ground its position on a fresh capture and pass screenshot-relative coordinates directly to Hermes Computer Use; do not multiply by the reported AX/native bounds scale. Verify the driver's delivered coordinates and resulting UI before retrying.
- Selecting the saved item can both fill and submit login automatically. Read the resulting page before clicking the site's Log In button; never duplicate the submission. If a bank sends a device push, preserve that challenge and request approval directly on the user's device without resending notifications or switching verification methods automatically.

### 5. Validate the authenticated target

Do not declare success from a click or from a filled password field. Require the site to show an authenticated state, then navigate to the requested account area and read back the exact artifact (for example, the account-level referral link rather than a product deep link). If 2FA, passkey approval, or a site checkpoint appears, use the approved human handoff and keep verification pending.

### 6. Temporary device-security block is not a vault unlock

- Classify a real Meta Business `/security/block/` page saying `We are running additional checks on this new device. Please retry in 5 minutes` as a device/session security hold, not as missing password, OTP or passkey. Do not open/reveal vault entries when the page offers no authentication control. Respect the displayed cooldown for one bounded read-only navigation retry; if the same gate remains, preserve the user's logged-in session, release the desktop lease and report the exact persistent blocker. Never replay a previously ambiguous account-creation mutation from the alternate computer.
- When the active Hermes Computer Use call cannot load an already-installed dependency generation, use the canonical `pm.environments.activate_dependencies(repo_root)` boot path in a scoped subprocess before importing the handler; do not install packages, enable lazy installs or restart the gateway as a shortcut. `execute_code` may replace stdout/stderr with streams lacking `fileno`, making Cua session startup fail even after dependency activation; use normal subprocess file descriptors and reduce its output in process. Keep indexed captures and actions in the same worker/session and terminate the worker at the end.
- If the native tool reports that its MCP session has ended, preserve the shared desktop lease and browser state, then establish a fresh scoped client rather than replaying the stale action. A foreground subprocess can activate the current repository's dependencies, import `handle_computer_use` and `release_computer_use_session`, recapture the exact window, resolve the intended control by semantic identity, execute and read back the bounded action, and release only its own client in `finally`. Derive the repository/interpreter from the live Hermes launcher rather than pinning a versioned checkout. Never stop the shared Windows daemon, restart the gateway, transfer secrets or change approval policy to recover a client.
- Reduce capture results before stdout: retain safe control labels, evidence paths and action verdicts. When the inline response truncates the accessibility tree, read the returned `elements_file` inside the same worker to locate controls beyond the cap; absence from the truncated response is not absence from the page.

### 7. Cleanup

- Confirm the ephemeral scheduled task no longer exists.
- Preserve the user's Chrome window and unrelated tabs unless closure was authorized.
- Release the shared desktop lease on success, failure, or human handoff.
- Report only the requested non-secret result plus the exact blocker when human action remains.