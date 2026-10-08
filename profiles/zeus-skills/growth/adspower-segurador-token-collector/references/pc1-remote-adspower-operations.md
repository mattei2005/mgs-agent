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
2. Call `get-browser-list` with the exact profile-name filter and require one safe identity match.
3. Call `get-browser-active`; if the profile is already active, do not open or later close user-owned state unless the current request explicitly authorizes it.
4. Call `open-browser` for the unique profile and require a successful response with browser connection data. Do not print the WebSocket/CDP value.
5. Call `connect-browser-with-ws`, then use the allowlisted page tools for the authorized action.
6. Call `close-browser` only when closure is authorized. Poll `get-browser-active` until `Inactive`/`Closed`; close propagation is asynchronous and may briefly remain `Active`.
7. Release the lease in every exit path.

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

## Read-only proxy allocation audit

- Treat `get-browser-list` responses as secret-bearing: root `list` rows contain raw Observation, platform passwords/authenticator seeds and proxy credentials. Never print the response or a dictionary that still includes `list`; whitelist safe fields before any stdout/file write. For proxy reconciliation persist only profile ID/number/name/group, last-open timestamp and proxy host/port/type. Keep credentials only in memory when strictly needed for private matching.
- The first page may include `total_count`/`total_pages`, while later pages return only `list`, `page` and `page_size`. Preserve the first-page declared total, paginate at no more than one request per second, append sanitized batches to protected scratch and require collected unique profile IDs to equal the declared total. Missing pagination metadata on later pages is not an API failure.
- Match purchased static proxies by the configured host plus port, not the profile's cached public `ip`: that field can belong to an old connection or an ISP gateway exit. For rotating/ISP gateways, reconcile product/sub-user and endpoint mapping before claiming a purchased IP is unused.
- Report allocated-to-profile separately from actual traffic. An unallocated endpoint in AdsPower does not prove it is unused elsewhere, and a configured profile does not prove recent successful proxy use. Provider contract/list readback is mandatory before declaring purchased-but-unallocated totals; do not infer purchased ports from a numeric sequence.
- Refresh and repaginate the AdsPower inventory after a human-authentication pause before final reconciliation; allocations can change while the provider session is blocked. Supersede the earlier allocation result explicitly rather than carrying old unallocated ports into the final report.
- On paginated provider lists, an empty immediate capture may be a loading transition. Wait and reread the same page until its rows and pagination are stable before using Next; persist sanitized host/port batches and require unique endpoint counts to equal each product's contracted quantity.
- Human CAPTCHA or an unresolved Cloudflare verification blocks provider account reads. Preserve the AdsPower inventory and request an authenticated provider session on PC1 or a credential-free proxy-list export; do not loop login submission, use archives for private/current account data, or bypass the challenge.
- When Rodolfo supplies an authenticated PC1 Chrome session, verify the actual provider account email through Settings before treating missing paid plans as a subscription fact. A Webshare session can show only Free Proxy because it belongs to a different email from the exact 1Password item; preserve that session and ask Rodolfo to switch accounts rather than logging out or declaring the purchased proxies absent.
- Native AX captures can enumerate rows whose values are inaccessible or clipped inside an internally scrollable table. Count declared rows separately from visibly verified endpoints; never invent the hidden tail from a port sequence. If a screenshot is necessary, crop to host/port only before saving, excluding username/password columns and authentication examples.
- A read-only capture through a second Cua transport can invalidate the first transport's element tokens. Re-capture through the action-owning backend immediately before every indexed click; never reuse its pre-external-capture indices.
- An existing 1Password save suggestion can intercept otherwise valid page controls. Verify that overlay in the current capture and dismiss it with Escape; do not save an item or change credentials as a navigation repair.

## Read-only Facebook profile batch audit

- Resolve the requested AdsPower group by name, preserve the exact returned group ID/name, paginate profile inventory, and reconcile unique `profile_id` count against `total_count`. AdsPower profile names are historical labels, not live health evidence.
- Record each profile's initial active state before opening. For a large batch, obtain explicit authorization to close only audit-opened instances before proceeding sequentially; preserve all pre-existing active browsers. Opening permission alone never authorizes closure.
- Verify browser responsiveness and the authenticated Facebook identity through visible page content. Login, checkpoint, CAPTCHA, selfie and 2FA remain blockers; do not reset credentials or bypass challenges.
- `https://www.facebook.com/accountquality/` may show **no problems in the last 30 days** even when the Facebook account is restricted. Follow the live **Ver minhas contas** link to the all-account overview and read the **Facebook account** status separately from business portfolios/ad accounts. Never classify advertising as unrestricted from the 30-day summary or a working Facebook feed.
- Read `https://accountscenter.facebook.com/personal_info/contact_points/` and the actual **Informações de contato / Contact info** panel. Match a standalone heading, not a substring inside **Add new contact info**; accept **Adicionar novas informações de contato** as the add-contact control. Count unique email contacts inside that panel, including contacts marked pending/unconfirmed while reporting that flag; do not double-count summary repetitions, count phone numbers as emails, or infer contact count from AdsPower login/Observation. Persist only the count and safe status, not credential-bearing fields.
- Detect extra authentication from the actual challenge/login surface, never keywords in an authenticated feed. A feed post mentioning selfie or code is not a challenge; an optional Messenger PIN prompt does not block Facebook/advertising inspection. Report CAPTCHA, ownership confirmation, recovery, login-required and forced-account-switch separately, leaving advertising status unverified when those gates prevent inspection.
- Treat MCP text such as **Browser not connected** or **Failed to get visible text content / Execution context was destroyed** as an operation failure even if `isError` is absent. Reconcile the active profile, allow browser startup to settle, reconnect using its current endpoint, and reread after navigation before classifying the profile. Never mark an automation attach failure as a Facebook account failure.
- Wait and reread if the all-account overview loads the identity without its status badge. If needed, inspect only the matching account link text from DOM HTML; never print raw HTML, hidden form fields or scripts. A safe link explicitly showing **No advertising issues** is evidence for that Facebook account, not all its business portfolios/pages.
- For Central de Contas `ERR_TOO_MANY_REDIRECTS`, retry through the live official Facebook settings link. If both routes fail, preserve the session/cookies, report email count as unverified and escalate any proposed destructive/session reset separately; a redirect loop is not an advertising restriction.
- Batch opening/closure follows the user's authorized batch size. Close the exact batch profile IDs (never bulk-close unrelated profiles), then poll for **Inactive/Closed** with a bounded validation window of up to 40 seconds; a 10-second window can falsely flag normal asynchronous close propagation.
- Save a sanitized inventory, per-profile results and resumable checkpoint in protected scratch/cache. Distinguish verified success, restriction, access blocker and not yet inspected; never promote stored profile-name warnings to confirmed current restrictions.

## Explicitly authorized Facebook feed actions

- Separate a read-only/open-profile request from permission to react: apply reactions only when the current user request explicitly authorizes them, and preserve the requested quantity.
- In the compact Facebook feed, `aria-label="Curtir"` with numeric text can be the reaction-count control, not the action. Open the observed `aria-label="Reagir"` control with focused `press-key` + `Enter` when pointer hover is intercepted, then choose the menu button whose label AND visible text are `Curtir`. Read back `Remover Curtir` / `Alterar reação Curtir` on the exact post before any next write; do not blindly retry a like toggle.
- AdsPower `scroll-element` uses DOM `querySelector`, so pass a standard CSS selector, not Playwright `>> nth=` syntax. Inspect fresh DOM after failed navigation/click and use the actual observed Reels link with `navigate` if the click does not change the page.
- Validate Reels playback through successive observed `role="slider"` / `aria-valuenow` values against `aria-valuemax`; opening the page alone is not proof of watching. Preserve pre-existing browser state and leave the profile open unless closure was explicitly authorized.

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