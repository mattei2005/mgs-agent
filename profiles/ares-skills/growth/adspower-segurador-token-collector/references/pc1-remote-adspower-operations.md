# PC1 Remote AdsPower Operations — Zeus + Ares

## Purpose

Use this runbook when Zeus or Ares must operate the MGS AdsPower desktop on PC1: find and open an authorized profile, confirm the resulting SunBrowser window, or inspect visible browser tabs. It does not by itself authorize Meta writes, budget changes, token extraction, cookie extraction, profile edits, profile closure, or destructive AdsPower actions.

## Verified architecture

Primary deterministic route:

```text
Zeus or Ares gateway on MGS VPS
→ Hermes MCP server `adspower-pc1`
→ /root/mgs-agent/scripts/mgs-pc1-adspower-mcp-ssh.sh
→ key-only SSH over private Tailscale
→ official AdsPower MCP on PC1
→ authenticated Local API on localhost:50325
→ AdsPower / SunBrowser / Playwright-CDP
```

Visual fallback:

```text
Zeus or Ares gateway on MGS VPS
→ Hermes `computer_use`
→ HERMES_CUA_DRIVER_CMD=/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh
→ key-only SSH over private Tailscale
→ PC1 interactive Windows session (`matte`)
→ local cua-driver named pipe
→ AdsPower / SunBrowser
```

Known private endpoints:

```text
MGS VPS Tailscale: 100.88.187.55
PC1 Tailscale:     100.85.69.58
```

The named pipe, SSH, AdsPower MCP, CDP/WebSocket endpoints, and Local API must not be published to the internet. Remote TCP access to `50325` is blocked; the MCP runs on PC1 beside `localhost:50325`. API Verification remains enabled and the key is never printed or passed in command-line arguments. The Windows user must remain logged into the interactive graphical session for Computer Use. AdsPower and `cua-driver serve` must be running there.

## Ownership and authorization

- **Zeus:** technical governance, access validation, incident recovery, and operations explicitly requested by Rodolfo.
- **Ares:** routine AdsPower actions needed for authorized Creative Operations, Growth, Media Buying, Meta, and segurador work.
- Opening a profile authorizes only the visible operation requested. Do not infer authorization to close profiles, edit profile configuration, extract cookies, generate tokens, change Meta assets, or alter campaign state.
- A request from a user is still limited by that user's active Ares permission scope and the MGS Critical Subset.

## AdsPower request queue — single active task

For every AdsPower operation, including inventory, opening, inspection and GUI input, check the shared PC1 lease and the live/resumable AdsPower requests before starting. A browser being open alone does not prove another agent task is running; conversely a gap between tool calls does not mean a running task has finished.

If an earlier authorized request is running or already queued for the resource, preserve the new request in `data/agent-checkpoints.json` with `state=waiting_resource`, its original source/thread, exact scope, queue dependency and next action. Do not start a second AdsPower task, bypass a live lease, spawn parallel profile workers, or retry the contested action. Resume the next queued request only after readback confirms the predecessor finished or was explicitly released/cancelled and the shared lease is free. Future scheduled tasks outside their execution window and historical completed checkpoints are not active resource owners.

Process multi-profile audits sequentially and preserve profile IDs plus partial results for resume. After an uncertain open, re-read active state before any second launch. Never close user-owned or audit-opened profiles unless closure is explicitly authorized. Opening successfully and reaching Facebook are separate checks; verify Account Status before claiming absence of visible restrictions, and do not interpret notifications being disabled as an account restriction. Identify the entity shown in Account Status: `Page has no issues` certifies only that Page's displayed status, not the personal profile or ad account. Generic warnings such as `can cause restrictions` are not active restrictions. Corroborate every suspected restriction with a profile-specific notice before classifying the profile as blocked.

On shared host memory pressure, `Page Unresponsive`, Local API connection refusal, or widespread CDP timeouts, reconcile existing instances and record a host/runtime failure separately from individual Facebook restrictions. Do not keep retrying a dead MCP connection, mark unreadable profiles clean, or relaunch an uncertain open blindly. Recover through the approved route without closing profiles or restarting the gateway; if recovery needs an unapproved closure/restart, preserve the request as waiting for scoped recovery and hand off to Zeus.

The existing cross-agent lease prevents simultaneous inputs; the request checkpoint queue preserves whole-task ordering. Do not claim a new automatic global scheduler was installed merely because this operating rule was persisted. If enforcement requires shared infrastructure changes, route that separately to Zeus instead of altering production transport/config during an audit.

## Batch lifecycle — maximum five simultaneous profiles

Rodolfo's active rule applies to every kind of AdsPower request that requires opening more than five profiles, not just SHEIN audits. Process sequential batches of at most **five** profiles. Five is a concurrency ceiling, not five concurrent workers: keep profile actions sequential under the single-task resource queue.

Before opening a batch, read current active instances and reconcile ownership. Do not open a sixth instance for the task. Account for pre-existing open profiles in the PC1 capacity ceiling; preserve user-owned or another task's instances and queue/coordinate instead of closing them without authority. Opening fewer than five is allowed when memory or responsiveness requires it.

Inspect every profile in the batch, persist safe per-profile results, then close the task-owned batch as part of this explicitly approved batch lifecycle. Verify each closure with `get-browser-active` until `Inactive`/`Closed`, and require the previous batch drained before opening the next. Do not clear cache, reset sessions, change proxies/fingerprints/credentials, or force-kill uncertain instances as a substitute for verified closure. A failed closure blocks progression to the next batch and requires scoped recovery.

An explicit request to close **all** current AdsPower instances authorizes that cleanup for that request after confirming no other agent task is operating them; it is not permission to close unrelated Chrome windows or to restart a gateway. If another authorized task is using PC1, queue the cleanup and send the new closure authority to that task's owner; do not bypass the lease. Start a fresh audit pass after cleanup, preserve prior results as historical, and derive the final problems-only report from the new pass with all targets accounted for.

## Mandatory cross-agent lease

Zeus and Ares share one physical desktop. Concurrent inputs can click or type into the wrong window. Acquire the PC1 lease before the first `computer_use` input and release it after the last validation.

```bash
LOCK=/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py

python3 "$LOCK" acquire \
  --agent zeus \
  --session-id '<current Hermes session id>' \
  --thread-id '<current Discord thread id>' \
  --ttl 900

python3 "$LOCK" status
python3 "$LOCK" renew --agent zeus --session-id '<current Hermes session id>' --ttl 900
python3 "$LOCK" release --agent zeus --session-id '<current Hermes session id>'
```

Ares substitutes `--agent ares`. Use the real current session/thread identifiers. Do not invent identifiers. The lease is idempotent for the same agent/session, expires automatically, and fails closed when another live session owns PC1. Never bypass a live lease. If the work exceeds the TTL, renew it before expiry. Release it in the cleanup path even after a blocked or failed operation.

## Preflight

1. Acquire the lease.
2. Confirm the profile has the remote driver configured:

   ```bash
   hermes -p <zeus|ares> computer-use doctor
   ```

3. Call `computer_use` with `action=list_windows`.
4. Require a visible `AdsPower Global.exe` window. Rediscover its PID and window ID every operation; never reuse historical identifiers.
5. If AdsPower, PC1, SSH, Tailscale, or the interactive daemon is unavailable, investigate and recover within the authorized scope. Do not guess or retry a click blindly.

## Preferred MCP flow

1. Connect through `mgs-pc1-adspower-mcp-ssh.sh`, which delegates to the transaction-aware proxy. Idle Zeus and Ares MCP connections do not own PC1. The first active tool sequence acquires the shared lease; the proxy holds it through the browser operation and releases it after `close-browser` or bounded idle recovery. Never use a process-lifetime MCP lease, because the first gateway would monopolize PC1 and starve the other.
2. Call `get-browser-list` with the requested profile-name filter and the known group ID when available; require one match for the combined profile/group identity, not one name across the entire inventory. Retain only safe identity fields and never inspect or reproduce credential-bearing fields returned alongside them.
3. Call `get-browser-active`; if the profile is already active, do not open or later close user-owned state unless the current request explicitly authorizes it.
4. Call `open-browser` for the unique profile and require a successful response with browser connection data. Do not print the WebSocket/CDP value.
5. Call `connect-browser-with-ws`, then use the allowlisted page tools for the authorized action.
6. Call `close-browser` only when closure is authorized. Poll `get-browser-active` until `Inactive`/`Closed`; close propagation is asynchronous and may briefly remain `Active`.
7. Release the lease in every exit path.

## Recover a stopped AdsPower application

1. After an MCP transport failure, inspect the shared lease, current desktop windows, AdsPower/SunBrowser process presence, and the PC1-local API listener before retrying; an uncertain write must still be reconciled at its exact target.
2. If AdsPower is confirmed absent and the request authorizes opening a profile, acquire the GUI lease, capture `app="desktop"`, and double-click the fresh **AdsPower Browser** shortcut element. Verify the resulting windows before any second launch; starting an absent application is not permission to restart or kill a running one.
3. Allow a bounded startup wait and re-check the windows and PC1-local listener. A blank **Starting** window alone neither proves readiness nor proves failure. Once the API is available, release the GUI lease before returning to the MCP route so its transaction proxy can acquire its own lease. Re-run the read-only lookup, then reconcile active state before opening the exact profile.
4. If startup does not recover within the bounded checks, preserve the request and escalate the exact missing prerequisite; do not restart the gateway, alter the transport, or force-close profiles.

## Ads Manager campaign screenshot

1. Resolve and open the unique authorized profile/group through the preferred MCP flow. Attach with `connect-browser-with-ws` using the current open response; do not disclose the connection endpoint.
2. Navigate with `navigate` to `https://adsmanager.facebook.com/adsmanager/manage/campaigns`, then read `get-page-visible-text`. Do not assume the default selected ad account is the intended business account: an empty personal account can show **Get set up to run ads** while the business campaign account is available in the selector.
3. If the account differs, click the currently displayed account selector using its observed text. Read the menu, select the relevant business portfolio, read its account entries, then click the exact authorized account name. Use `click-element` with observed `text=...` selectors; never pick a row by position or invent an account from historical context. If multiple accounts remain materially ambiguous, ask which account to capture.
4. Re-read rendered text and require the intended account name/ID plus the campaign rows and displayed date range. Preserve the UI status literally in meaning: **Preparing** is not proof of delivery. Account switching and inspection do not authorize **Create**, **Edit**, **Review and publish**, or campaign toggles.
5. Capture the page with `screenshot(isFullPage=false)`, then inspect the returned local image. Confirm campaign rows are visible and no credentials appear. A screenshot can truncate labels: ground the full account/campaign identity in the preceding rendered-text readback rather than claiming the image proves every character. Improve the view only when needed for the requested legibility.
6. Return the image using `MEDIA:<returned-local-path>` with a concise PT-BR profile/account summary and the observed campaign status. Do not substitute a desktop screenshot of AdsPower startup or a Facebook feed for the requested Ads Manager image. Leave the requested profile open, and release only the lease owned by this operation.

## Ad editor configuration and preview screenshot

- Require an explicit request to open **Edit**; a campaigns-only screenshot request does not authorize it. Opening the editor for inspection does not authorize field changes, toggles, drafts, publication or discarding pre-existing edits.
- Reconfirm the selected account, campaign, ad set and exact ad name from rendered UI. Select the requested ad and open the toolbar **Edit**. If a name click is intercepted, read back state before another action; do not repeat the same blocked locator.
- When current, exact IDs are evidenced by the page, selecting with `/adsmanager/manage/ads?act=<account>&selected_campaign_ids=<campaign>&selected_adset_ids=<adset>&selected_ad_ids=<ad>` is a verified navigation-only fallback. Read back **Ads — 1 selected** and the exact intended ad before opening the toolbar **Edit**.
- Require the editor breadcrumb and selected ad, visible configuration fields, and a loaded **Ad preview**. Capture and inspect the actual image; thumbnails/players being rendered do not prove complete video playback. Leave all fields untouched and report inspection only.
- The MCP `scroll-element` implementation uses native `querySelector`, so pass only a CSS selector grounded in current DOM; Playwright `text=...` is invalid there even though `click-element` supports it. Do not fetch the full HTML repeatedly when the tool has already persisted its output, and do not infer missing DOM elements from a truncated HTML response.

## Read a current ad field without editing

1. Reattach to the active authorized profile and read `get-page-visible-text` to confirm the same account and exact selected ad. Apply the canonical domain-scope check before returning an operational destination URL; do not visit the destination just to read the field.
2. If **Website URL** appears as a label but its value is absent, obtain `get-page-html` through the same MCP route before switching to desktop control. Visible text commonly omits form values; the current input's `value` attribute can contain the complete URL even when the screenshot truncates it.
3. If HTML is persisted as oversized output, parse that local file once with the standard library. Match the actual input by its observed label/placeholder or label association, require one match, and emit only its value. Do not regex-search the whole document for a familiar URL: scripts may contain other ads, stale state or credentials. Do not treat the oversized-output notice alone as proof the saved HTML was truncated; check whether the target input is present.

For a DOM-confirmed Website URL input using the placeholder below, this extraction was exercised successfully. Pass the tool-returned HTML path as the script argument; re-discover the field association if the placeholder changes:

```python
from html.parser import HTMLParser
from pathlib import Path
import sys

class WebsiteField(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if (tag == "input" and attrs.get("placeholder") ==
                "Enter the URL people visit after your ad"):
            self.values.append(attrs.get("value"))

parser = WebsiteField()
parser.feed(Path(sys.argv[1]).read_text(encoding="utf-8"))
if len(parser.values) != 1 or not parser.values[0]:
    raise SystemExit("Exact Website URL field not uniquely resolved")
print(parser.values[0])
```

4. Preserve the extracted string without URL normalization or query reordering. HTML entity decoding restores the field value; do not additionally URL-decode it. Keep **Website URL** separate from **Tracking → URL parameters** and do not silently combine them when the operator asked for one field.
5. Return the field/ad label plus the complete value in a text code block. State direct field verification only when the input was actually read, and leave the editor unchanged. Use GUI fallback only if the DOM route cannot resolve the field; a browser-chrome-only accessibility tree is not evidence that the field is empty.

## Computer Use fallback — find and open one profile

1. Capture the current AdsPower window by its fresh PID and window ID.
2. Click **Perfis**.
3. Capture again. Element indices belong only to that snapshot.
4. Focus **Pesquisa ou novos critérios de pesquisa** and type the requested profile name exactly.
5. If background text input returns `background_unavailable`, recapture and retry once with `delivery_mode="foreground"` only when the user's request already authorizes visible AdsPower interaction. Otherwise ask first.
6. Choose **Nome contém** for a human name fragment, or an exact ID/number criterion only when the user supplied that identifier.
7. Wait for the filtered result and recapture. Require a unique identity match using the visible profile name and, when needed, its safe group/app code. `Total: 1` is the expected gate for opening by name.
8. If zero or multiple rows match, stop and report the ambiguity. Never select by row position alone.
9. Do not inspect or repeat the **Observação** field. It may contain an email, password-like material, profile URL, or other credential-bearing data.
10. Click the **Abrir** button inside the matched row—not the toolbar's bulk **Abrir** button.
11. Recapture before any retry. `effect=unverifiable` means verify state; it does not authorize repeating the click.

## Validate the opened profile

1. Call `list_windows` again.
2. Require a new or existing visible `SunBrowser.exe` window whose title contains the exact safe AdsPower profile name.
3. Do not quote the raw window title: AdsPower can concatenate the profile's Observation field into it.
4. Validate the process/window remains present and responsive. Do not declare success from the click response alone.
5. If the exact profile is already open, treat it as an idempotent success and do not open a duplicate instance.

## List visible tabs safely

1. Capture the matched main SunBrowser window, not a translation popup or helper window.
2. Read top-level browser `TabItem` elements from the tab strip.
3. Exclude translator-language controls such as `inglês` and `português`; they belong to the translation popup, not the browser tab strip.
4. Strip memory-use suffixes such as `: 307 MB` from tab labels.
5. Sanitize any profile tab to a safe label such as **Página inicial do perfil <nome>**. Never repeat a raw title containing Observation data.
6. Count tabs programmatically before declaring a total.
7. Do not click tabs unless the user requested inspection of their contents.

## Verified example — Pready AS

The validated safe route is:

```text
AdsPower
→ Perfis
→ search `Pready AS`
→ Nome contém
→ unique result `03 - PERFIL SEGURADOR - Pready AS - NEWSOUN - B004-7`
→ row action Abrir
→ `SunBrowser.exe` exact-profile window readback
```

Observed safe tab labels after opening:

```text
Página inicial do perfil Pready AS
Mail - asaro mapa - Outlook
5SMail.Email - Temporary Email Service
Facebook
Digital TR Chat | Login
Todos os apps - Meta for Developers
Configurações do desenvolvedor - Meta for Developers
```

This example proves the route, not standing authorization to reopen or manipulate that profile later.

## Computer Use failure discipline

- Re-capture after every navigation, filter, popup, or window change.
- Never reuse an element index across captures.
- Prefer element-index clicks from a fresh semantic snapshot; use coordinates only as the documented escalation when the element route fails.
- On `background_unavailable`, follow the returned escalation exactly. Do not predict foreground mode merely because AdsPower uses Chromium.
- After a nonzero or ambiguous action result, inspect the real UI/window state before retrying.
- Stop after five consecutive failures of the same tool, or earlier on any loop signal.

## Security rules

- Never expose passwords, tokens, keys, cookies, bearer values, 2FA secrets, or raw Observation text.
- Never paste a credential-bearing window title into Discord, logs, reports, skill examples, or audit events.
- Screenshots and semantic trees can contain credentials even when no secret field was intentionally opened. Keep them in the protected Hermes cache and report only sanitized facts.
- The shared wrapper and SSH key are infrastructure; agents use the configured route and never print, copy, rotate, or replace key material during routine operation.
- Token collection must continue through the token-specific sections of the parent skill and save only to the approved secure destination.

## Reporting

Report only:

```text
result: opened / already open / blocked / ambiguous
safe profile name
safe route taken
validation: SunBrowser exact-profile window present and responsive
pending blocker, if any
```

Never include raw titles, Observation content, credentials, or token prefixes.