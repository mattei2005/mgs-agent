---
name: adspower-segurador-token-collector
description: "Use when Zeus or Ares operates MGS AdsPower on PC1."
version: 1.2.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, adspower, meta, facebook, token, segurador, graph-api, access-token, proxy, computer-use, remote-windows, zeus, ares]
    related_skills: [segurador-page-health-monitor, meta-app-rate-limit-monitor, computer-use]
---

# AdsPower Segurador Token Collector — MGS

## When to Use

This skill is for collecting and validating **Meta user tokens for seguradores** through AdsPower profiles/proxies.

Use it when Rodolfo asks to:

- open seguradores in AdsPower;
- generate Meta user tokens;
- extend/debug tokens;
- validate token permissions/pages;
- save tokens for the page/segurador monitor.

This is separate from the B001–B010 app/rate-limit monitor. The goal here is **segurador profile operation and token collection**, not app role/rate-limit monitoring.

## Zeus and Ares — shared PC1 route

For routine remote AdsPower operation—locating a profile, opening it, verifying the SunBrowser instance, or listing visible tabs—load and follow:

```text
references/pc1-remote-adspower-operations.md
```

The same private PC1 transport is used by Zeus and Ares. Deterministic profile and browser-page operations use the official AdsPower Local API/MCP route first; Computer Use remains the fallback for native GUI, CAPTCHA, 2FA, checkpoints, or visual recovery. Both routes share the same cross-agent lease, because they can conflict on the same AdsPower profile and interactive browser state. Zeus owns technical governance; Ares owns routine Growth/Media Buying execution within the requesting user's current authority.

Token generation remains a separate, higher-sensitivity stage. Opening a profile never authorizes generating, copying, exposing, replacing, or storing a token.

## Required URLs

```text
Graph API Explorer:       https://developers.facebook.com/tools/explorer/
Access Token Debugger:    https://developers.facebook.com/tools/debug/accesstoken/
```

## Approved Permission Set — 18 permissions

Use exactly these permissions for the first production collector flow:

```text
email
read_insights
pages_show_list
business_management
pages_messaging
instagram_basic
instagram_manage_comments
instagram_manage_insights
instagram_content_publish
leads_retrieval
instagram_manage_messages
pages_read_engagement
pages_manage_metadata
pages_read_user_content
pages_manage_ads
pages_manage_posts
pages_manage_engagement
pages_utility_messaging
```

## Manual Flow After Opening AdsPower Profile

Once the segurador's AdsPower instance/profile is open:

```text
1. Open https://developers.facebook.com/tools/explorer/
2. Insert/select all 18 approved permissions.
3. In Meta App, confirm the correct Bxxx app for that segurador.
4. Keep User or Page = User Token.
5. Click Generate Access Token.
6. Copy the generated token locally only.
7. Open a new tab: https://developers.facebook.com/tools/debug/accesstoken/
8. Paste token into "Enter an access token to debug".
9. Click Debug.
10. Scroll to the bottom.
11. Click the debug/extend action.
12. Copy the new/extended token.
13. Validate token.
14. Save token.
```

## Validation Checks

A token is not considered usable until these checks pass:

```text
GET /me?fields=id,name
GET /debug_token?input_token={token}
GET /me/accounts?fields=id,name,category,tasks,access_token
```

Minimum OK criteria:

```text
Check                 Expected
--------------------  --------------------------------------------------
/me                   returns segurador profile id/name
/debug_token          is_valid=true, correct app_id, expected scopes
/me/accounts          returns pages visible to the segurador
permissions/scopes    includes the approved operational scopes
```

Also capture safe metadata only:

```text
segurador_name
segurador_profile_id
app_code B001–B010
app_id
expires_at
page_count
page_ids/page_names if needed
validation timestamp
```

Never print or store raw tokens outside the secure destination.

## Save Destination

Preferred destination: 1Password.

Item naming pattern:

```text
Segurador {Nome} ({Bxxx}) Token
```

Expected fields:

```text
field         purpose
------------ -------------------------------------------------------
segurador    Human segurador/profile name
app_code     B001–B010
app_id       Meta app ID used
access_token Extended user token
expires_at   Token expiry timestamp if returned
profile_id   /me id
page_count   Number of pages visible in /me/accounts
validated_at Last validation timestamp
```

Do not save raw tokens to Google Sheets, Discord, plain CSV, screenshots, logs, or audit messages.

## Profile 2FA setup from an existing Observação seed

- Require Rodolfo's explicit request and Critical Subset double-confirmation before registering an existing authenticator seed in AdsPower. Scope by immutable profile ID plus profile number/name; never infer standing permission for passkey creation.
- Read only the exact profile through the authenticated PC1 localhost API under the shared lease. Keep raw Observação and seed inside process memory; stdout, audit, inventory and transport scripts contain only safe metadata. Require a single standalone valid Base32 seed; authenticator seeds may be grouped with spaces. Preserve the original value when writing; do not replace or generate a seed and do not alter the remote account's 2FA.
- Prefer the documented minimal `POST /api/v1/user/update` payload containing only `user_id` and `fakey`. The V2 update documentation declares additional fingerprint/proxy inputs, so do not use it for a key-only change or resend unrelated profile settings. If `fakey` already exists and differs, stop instead of overwriting.
- Requery the exact profile after writing. Require `fakey` to equal the source and every other returned field, including `remark`, to remain unchanged. A successful POST alone is not validation.
- For account-wide work, paginate all profiles and require the collected unique profile IDs to equal the first-page declared total before writing. Keep a sanitized per-batch ledger, renew the shared lease before each batch, canary a few profiles first, and repaginate the complete account after the last write. Reconcile the final profile-ID set with the initial set and every successful write with its final source match.
- Scan for legacy inline/pipe-delimited uppercase 32-character Base32 tokens as well as standalone, grouped, explicitly labeled and authenticator-URL formats. Deduplicate candidates in memory. Invalid Base32 lengths, unlabeled lowercase password-like strings, multiple possible seeds and existing-key conflicts are not permission to guess; list unresolved profiles separately from confirmed missing keys. Do not treat a populated `fakey` as absent just because the same source token is embedded in a legacy import line.
- Force UTF-8 for safe PowerShell stdout on PC1. Long Windows encoded command lines can exceed the native command limit: pass the public script through SSH stdin to a short PowerShell ScriptBlock loader rather than placing oversized encoded code in arguments. Never send credential literals as argv or save raw Observação locally.
- Keep execute_code batches comfortably below its five-minute cell limit. A cell timeout can leave a foreground terminal subprocess running: inspect the ledger and the exact process, wait for it to finish, and reconcile target state before any retry. Never launch a duplicate batch or infer failure from a lost caller response.
- Verify local six-digit TOTP generation without printing codes. Distinguish configured/generating from visible in the native AdsPower UI and from accepted by Facebook; do not claim visual display or end-to-end login unless those separate checks actually passed. Do not log out or provoke a challenge merely for a smoke test.
- Treat read-only inventory and native capture responses as secret-bearing. Reduce them in process before any tool stdout. When calling the Hermes Computer Use handler programmatically for safe output reduction, use the normal PM `activate_dependencies(repo_root())` boot path; an interpreter path alone does not activate the selected dependency generation. Do not enable lazy installs or modify runtime dependencies as a workaround.

## Bulk AdsPower Observação archival to 1Password

When Rodolfo asks to archive AdsPower profile Observação data securely:

1. Treat `profile_id` as the immutable identity key and preserve `profile_no`, profile name, group ID, group name, and the exact raw Observação only inside 1Password.
2. Create **one Secure Note per AdsPower profile, including profiles whose Observação is empty**. A master JSON/CSV document is a backup/export surface, never a substitute for the one-profile-per-item acceptance criterion.
3. Require exact reconciliation: AdsPower profile count = unique Secure Note count = unique stored `profile_id` count, with zero missing and zero duplicates. A Sheet row count includes its header and must not be compared directly to item count without separating header from profiles.
4. Read back every created item. 1Password may normalize an empty string field to `null`; accept `null` only when the expected source value is exactly empty, while requiring every non-empty field byte-for-byte.
5. Create items serially. Concurrent `op item create` calls can consume write budget and fail transactionally; after any failure, run `op item list` and reconcile unique titles/IDs before retrying. Inspect `op service-account ratelimit`, respect the reported reset window, and resume only missing profiles after the quota resets.
6. Never write raw Observação values to Google Sheets, Discord, logs, command arguments, or local plaintext files. Stream bulk backup documents through stdin and validate by encrypted 1Password document readback.

## AdsPower Official CLI / Skill

Rodolfo also provided the official AdsPower GitHub resources:

```text
https://github.com/AdsPower/adspower-browser/blob/main/skills/adspower-browser/SKILL.md
https://github.com/AdsPower/adspower-browser/blob/main/packages/adspower-browser/README.MD
```

Useful package:

```bash
npm install -g adspower-browser
```

Equivalent commands:

```text
adspower-browser
adspower
ads
```

Essential CLI commands for our collector:

```bash
ads status
ads check-status
ads get-browser-list '{}'
ads open-browser <profile_id>
ads close-browser <profile_id>
ads get-opened-browser
ads get-browser-active <profile_id>
ads get-profile-cookies <profile_id>
ads get-profile-ua <profile_id>
ads close-all-profiles
```

Start/stop runtime if needed:

```bash
ads start -k <KEY>
ads stop
ads restart
```

Notes:

```text
- `ads get-browser-list '{}'` defaults to page=1, limit=200.
- If total_pages > 1, paginate before processing batch.
- Profile commands accept shorthand profile_id or JSON args.
- Numeric shorthand may be treated as profile_no for some commands.
- Use `ADS_API_KEY` env var or `--api-key`/`-k` when API verification is enabled.
```

## Production route — PC1

The validated production route is:

```text
Zeus/Ares
→ /root/mgs-agent/scripts/mgs-pc1-adspower-mcp-ssh.sh
→ key-only SSH over Tailscale
→ official AdsPower MCP running on PC1
→ authenticated Local API on localhost:50325
→ AdsPower / SunBrowser / Playwright-CDP
```

Rules:

- Do not call `100.85.69.58:50325` directly. Windows Firewall blocks remote access to the Local API; only PC1 localhost remains valid.
- API Verification stays enabled. The MCP launcher reads the key from the protected PC1 secret file; never pass or print it in arguments, logs, Discord, screenshots, or shell output.
- The credential source of truth is the authorized 1Password item `AdsPower Local API - PC1`; the PC1 copy is the minimum runtime material.
- Hermes server name is `adspower-pc1` for Zeus and Ares. Its allowlist excludes profile creation/update/deletion, cookies, bulk-close, proxy mutation, sharing, kernel changes, and arbitrary script evaluation.
- `/root/mgs-agent/scripts/mgs-pc1-adspower-mcp-ssh.sh` starts `/root/mgs-agent/scripts/mgs-pc1-adspower-mcp-proxy.py`. The proxy lets both gateways keep an idle MCP connection, acquires the shared PC1 lease on a tool call, holds it across a multi-call browser operation, releases it after `close-browser` or an idle timeout, and releases read-only inventory/status probes immediately. Never restore a process-lifetime lease: that lets the first gateway monopolize AdsPower and prevents the other agent from connecting.
- `get-browser-list` is limited to one request per second; preserve documented endpoint limits.
- `close-browser` is asynchronous. After a successful close response, poll `get-browser-active` until `Inactive`/`Closed` with a bounded timeout. A transient `Active → Active → Inactive` sequence is normal; do not report failure or issue duplicate closes before polling.
- Use Computer Use only when the official MCP cannot complete the authorized operation or the flow requires visual/native interaction.

## AdsPower Local API

Rodolfo found the AdsPower API/MCP page and Postman documentation. This is the correct integration path.

Local API base observed in AdsPower UI:

```text
http://local.adspower.net:50325
http://localhost:50325
```

Connection check:

```text
GET /status
```

Useful confirmed endpoints from AdsPower Postman docs:

```text
GET  /api/v1/browser/start              Open profile by user_id/profile ID or serial_number
POST /api/v2/browser-profile/start      Open profile v2 by profile_id or profile_no
GET  /api/v1/browser/stop               Close profile by user_id/profile ID or serial_number
POST /api/v2/browser-profile/list       Query/list profiles, fixed 1 req/sec limit
GET  /api/v2/browser-profile/cookies    Query cookies, fixed 1 req/sec limit
GET  /api/v1/user/list                  Query users, fixed 1 req/sec limit
GET  /api/v1/group/list                 Query groups, fixed 1 req/sec limit
```

Open profile v2 body pattern:

```json
{
  "profile_id": "abcdefg",
  "launch_args": ["--window-position=400,0", "--disable-notifications"],
  "headless": "0",
  "last_opened_tabs": "1",
  "proxy_detection": "1",
  "password_filling": "0",
  "password_saving": "0",
  "cdp_mask": "1",
  "delete_cache": "0",
  "device_scale": "1"
}
```

Authentication:

```text
If API Verification is OFF: local calls may work without API key.
If API Verification is ON or CLI mode is used: use Authorization: Bearer <API_KEY>.
Never print the API key.
```

Rate limits from docs:

```text
0–200 profiles      2 requests/sec
200–5000 profiles   5 requests/sec
5000+ profiles      10 requests/sec
Special endpoints   1 request/sec where documented
```

## AdsPower Automation Design

Target operating model:

```text
Google Sheet / queue
→ segurador name + NO APP/Bxxx + AdsPower profile ID/name
→ AdsPower Local API opens profile with proxy
→ Local API returns browser automation connection info
→ Playwright/Selenium connects to that browser
→ automation navigates Meta Explorer
→ user token generated/extended
→ validation via Meta Graph
→ token saved to 1Password
→ profile closed through AdsPower Local API
→ next segurador
```

Expected human intervention cases:

```text
- Meta checkpoint
- 2FA
- CAPTCHA
- profile not logged into Facebook
- missing developer/app access
- wrong app selected or app unavailable
- permission consent blocked
```

When any of these happen, stop that profile, record safe status, and continue/ask Rodolfo depending on batch mode.

## Security Rules

```text
- Never expose access_token, page token, app secret, cookie, Auth0 token, or bearer token.
- Never paste raw token into Discord.
- Never include token in terminal stdout if stdout may be reported.
- Redact tokens as [REDACTED] in any logs/reports.
- Confirm Meta App Bxxx matches the planilha NO APP before generating.
- Keep User Token mode; do not switch to Page Token for the collector.
- Treat screenshots containing token strings as sensitive.
```

## Reporting Format

For batch progress, report only safe summary:

```text
Segurador              App   Status       Pages  Reason
---------------------  ----  -----------  -----  ------------------------
Dân Kbang              B005  OK           20     token valid + accounts OK
Nome Exemplo           B003  BLOCKED      -      checkpoint/2FA
Outro Nome             B007  FAILED       -      app mismatch or no pages
```

Do not include tokens or token prefixes.

## Common Pitfalls

1. Selecting the wrong Meta App before generating the token.
2. Forgetting to extend/debug the token after Graph API Explorer generation.
3. Treating a token as valid before `/me/accounts` confirms page access.
4. Saving short-lived Explorer token instead of the extended Debugger token.
5. Printing token to stdout/logs during automation.
6. Confusing user token collection with app role/rate-limit monitoring.

## Open Configuration Items

These will be filled as the AdsPower automation is configured:

```text
AdsPower Local API host/port
Auth method/API key if required
Profile ID field/source in the sheet
Exact queue sheet/tab
Bxxx → app_id mapping source
1Password vault/item template
Retry/checkpoint handling policy
```
