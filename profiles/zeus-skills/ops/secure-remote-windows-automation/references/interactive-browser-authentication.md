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

Capture the exact Chrome window by fresh PID/window ID. Prefer fresh accessibility elements for page controls. When a page is rendered as an image and exposes no control nodes, use a visual capture to locate the target and pass the screenshot-relative coordinate directly; do not pre-scale it before calling `computer_use`, because the driver maps it to native screen coordinates.

Type only the non-secret account identifier through CUA. If Chromium returns `background_unavailable`, retry only that text action in foreground mode, then recapture and require the expected identifier in the field before clicking Continue.

### 4. Fill the password through the browser password manager

At the password page:

1. Confirm the page origin is the intended site.
2. Open the password-manager extension.
3. If it is already unlocked, select the exact site/identifier item and let the extension fill the page; never reveal the password field.
4. If it asks for the manager's master password, stop. Leave the site and popup open, release the shared desktop lease, and ask the user to unlock the extension through their Remote Desktop session. Never ask for the master password in chat or type it through CUA.
5. After the user confirms the unlock, reacquire the lease, rediscover the Chrome PID/window ID, recapture, and continue from the current page.

A server-side 1Password Service Account may safely confirm item metadata, but it does not authorize or justify carrying the resolved password into a different remote browser through SSH, shell variables, clipboard injection, MCP arguments, or synthetic typing. The fill must remain inside the password manager's protected browser path.

### 5. Validate the authenticated target

Do not declare success from a click or from a filled password field. Require the site to show an authenticated state, then navigate to the requested account area and read back the exact artifact (for example, the account-level referral link rather than a product deep link). If 2FA, passkey approval, or a site checkpoint appears, use the approved human handoff and keep verification pending.

### 6. Cleanup

- Confirm the ephemeral scheduled task no longer exists.
- Preserve the user's Chrome window and unrelated tabs unless closure was authorized.
- Release the shared desktop lease on success, failure, or human handoff.
- Report only the requested non-secret result plus the exact blocker when human action remains.