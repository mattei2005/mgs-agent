---
name: cloudflare-operations
description: "Use when Rodolfo asks Zeus to operate Cloudflare for MGS domains: purge cache, inspect zones/DNS/settings, or prepare DNS/SSL/WAF/rules changes. Covers 1Password token handling, zone resolution including subdomains, confirmation rules, API calls, audit logging, and reporting."
version: 1.1.1
author: Zeus MGS
license: Proprietary
metadata:
  hermes:
    tags: [mgs, cloudflare, cache, dns, infra, audit]
    related_skills: [discord-ops, log-monitor-discord-alert]
---

# Cloudflare Operations — MGS

## Overview

Zeus can operate Cloudflare for MGS using an API token stored in 1Password. The normal high-frequency action is cache purge. Broader Cloudflare changes such as DNS, SSL/TLS, WAF, Page Rules, Rulesets, Workers routes, or Zone Settings are allowed only when Rodolfo asks for the specific action, and require an explicit pre-apply confirmation with the exact change.

Never expose Cloudflare tokens or 1Password secret values in Discord, logs, reports, code blocks, or error excerpts. Only report item names, field names, token verification status, zone names, HTTP status, and Cloudflare result IDs/prefixes.

## When to Use

Use this skill when Rodolfo asks to:

- clear/limpar/purge Cloudflare cache for one or more MGS domains;
- test or validate Zeus Cloudflare access;
- list or resolve Cloudflare zones for MGS domains;
- inspect DNS/settings/rules before a change;
- prepare or apply specific Cloudflare changes after approval.

Do not use this skill for WordPress application cache, RunCloud cache, plugin cache, browser cache, or CDN providers other than Cloudflare unless Rodolfo explicitly says Cloudflare is involved.

## Routine Cache Purge Fast Path

For a direct cache-purge request from Rodolfo, loading this skill completes the procedural lookup. Execute from this documented procedure immediately; do **not** search the repository for Cloudflare scripts, reopen `AGENT.md`, or run broad confirmation-rule searches when the request and zone scope are already clear.

Limit prerequisite work to the required live checks: validate the token, resolve the requested hostname to its Cloudflare zone, purge, append the audit event, and validate the audit readback. Search other files only when this skill is missing or broken, the hostname-to-parent-zone scope is ambiguous, the API path fails, or Rodolfo explicitly asks for an audit/investigation. This keeps routine purges fast and avoids unnecessary visible `Searching...` churn in Discord.

## Credential Source

Canonical 1Password item currently used by Zeus:

- Vault: `MGS Conteúdo` via `OP_DEFAULT_VAULT`
- Item: `Cloudflare MGS Admin Token - mattei2005`
- Preferred field: `token`

An alternate item, `Cloudflare MGS Admin Token - mattei20052`, may validate as active but has a different zone scope. Never select a token only because `/user/tokens/verify` succeeds: query the exact target zone and use the item that returns it. Live read-only validation on 2026-08-26 confirmed that `pdllifestyle.com` is visible through `mattei2005` and not through `mattei20052`.

Load credentials with `.env` exported for subprocesses:

```bash
cd /root/mgs-agent
set -a
source .env 2>/dev/null || true
set +a
```

Then resolve the item through `op`. Do not print the token. If multiple token-like fields exist, prefer the exact field label `token`; validate with `/user/tokens/verify` before using it.

## Authorization and Confirmation Rules

1. **Read-only checks** — token verify, zone list, DNS list, settings read — may run immediately when Rodolfo asks to test/inspect.
2. **Cache purge** — destructive but low-risk. If Rodolfo says “confirma antes”, do a read-only precheck and wait for explicit confirmation. If Rodolfo directly asks to purge and does not ask for confirmation, purge may proceed, but for multi-site purge prefer one concise precheck confirmation.
3. **DNS/SSL/WAF/rules/settings changes** — always show the exact intended diff/action and ask for explicit confirmation before applying.
4. **Account-wide or cross-zone changes** — confirm scope clearly, especially when a requested hostname is a subdomain whose Cloudflare zone is the parent domain.
5. **Billing, ownership, account members, token creation/deletion, or global security settings** — treat as sensitive; require explicit instruction and confirmation.

### Creating Additional API Tokens

Cloudflare's current official flow requires the initial token to be generated from the dashboard template **Create additional tokens**. The `User → API Tokens → Edit` permission (API name: `API Tokens Write`) is not available in other templates or in the Custom Token builder.

For a safe capability smoke test after Rodolfo's Critical Subset confirmation:

1. Verify the initial token is active.
2. Resolve its exact `com.cloudflare.api.user.<USER_TAG>` resource from the current token policy; do not expose the user tag or token IDs in Discord.
3. Create a short-lived temporary token with the smallest useful permission (for example, `User Details Read`) and a near-term expiration as a cleanup fallback.
4. Verify the temporary token through `/user/tokens/verify`.
5. Delete it immediately with the initial token.
6. Validate deletion by readback (`GET /user/tokens/{id}` returning not found) and append a secret-free audit event.

`API Tokens Read` alone does not authorize `POST /user/tokens`; creation requires `API Tokens Write`.

A token created through the API is a sub-token and cannot itself receive permission to manage other tokens. Cloudflare rejects that recovery-token pattern with error `1001: sub-token is not allowed to have permissions to manage other tokens`. Do not rely on an API-created token as rollback authority for editing the only token-management credential. Require either an independently dashboard-created management credential or a new Critical Subset confirmation for an atomic self-update with manual dashboard rollback if access is lost.

## Zone Resolution

Cloudflare zones are usually apex domains. For a requested hostname:

1. Try exact zone name first, e.g. `openzed.com`.
2. If not found and the request is a subdomain, progressively try parent zones, e.g. `finance.topfeed.fun` → `topfeed.fun`.
3. Report the mapping before purge when confirmation is requested.
4. If a subdomain maps to parent zone, state that purge applies to the whole parent zone when using `purge_everything`.

Known observed mappings from validated purges:

```text
finance.topfeed.fun  -> topfeed.fun
finanzas.topfeed.fun -> topfeed.fun
```

For either subdomain, `purge_everything` clears the complete `topfeed.fun` zone, including cache for sibling hostnames. State that actual scope explicitly in the final report even when the user asked only for one subdomain.

## Cache Purge Procedure

Use Cloudflare endpoint:

```text
POST /client/v4/zones/{zone_id}/purge_cache
Body: {"purge_everything": true}
```

Operational steps:

1. Verify token:
   - `GET /user/tokens/verify`
   - Completion: HTTP 200, `success=true`, token status `active`.
2. Resolve each requested site to a Cloudflare zone:
   - `GET /zones?name=<candidate>&per_page=5`
   - Completion: every requested site has a zone or is explicitly reported missing.
3. If confirmation was requested, stop and show a short mapping table:
   - requested hostname;
   - matched Cloudflare zone;
   - zone status;
   - warning for parent-zone purge.
4. After confirmation, call purge endpoint once per zone.
   - Completion: every call returns HTTP 200 and `success=true`.
5. Append audit event to `/root/mgs-agent/logs/events-audit.jsonl`.
   - Include timestamp, actor, agent, mode, requested sites, zones, HTTP statuses, success flags, Cloudflare result IDs/prefixes, and token item name.
   - Exclude secrets and full token values.
6. Report concise final status in Discord.

## Minimal Python Pattern

Use this as the base pattern when no wrapper script exists yet. Keep output small.

```python
import json, os, subprocess, urllib.parse, urllib.request, urllib.error

ITEM = 'Cloudflare MGS Admin Token - mattei2005'
VAULT = os.environ.get('OP_DEFAULT_VAULT', 'MGS Conteúdo')
obj = json.loads(subprocess.check_output(['op','item','get',ITEM,'--vault',VAULT,'--format','json'], text=True))
token = next(f['value'] for f in obj['fields'] if (f.get('label') or '').lower() == 'token')

def cf(method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        'https://api.cloudflare.com/client/v4' + path,
        data=data,
        method=method,
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {'success': False, 'errors': [{'message': body[:300]}]}
        return e.code, parsed
```

## Reporting Format

For final purge reports, use compact aligned rows:

```text
Site                 Zona Cloudflare      HTTP  Status
-------------------  -------------------  ----  ------
eggbev.com           eggbev.com           200   OK
finance.topfeed.fun  topfeed.fun          200   OK
```

Mention whether audit logging happened. Do not include raw JSON unless Rodolfo asks.

## Common Pitfalls

1. **Token verifies but purge fails.** Token status `active` only proves token validity. Purge can still fail if `Zone → Cache Purge → Edit` is missing for the target zones. Fix Cloudflare token permissions and retry.
2. **Subdomain purge scope confusion.** `finance.topfeed.fun` maps to zone `topfeed.fun`; `purge_everything` clears the parent zone cache, not only that subdomain.
3. **Leaking secrets through debug output.** Avoid printing 1Password item JSON, field values, headers, env vars, or request objects.
4. **Assuming result ID is separate from zone ID.** Cloudflare purge responses may echo an ID that resembles the zone ID. Treat it as an API result handle; do not overinterpret.
5. **Skipping audit log.** Every write operation must append to `events-audit.jsonl` before reporting completion.

## Verification Checklist

- [ ] Correct 1Password item and field used without printing secrets.
- [ ] Token verify returned `success=true` and status `active`.
- [ ] Requested hostnames resolved to expected Cloudflare zones.
- [ ] Confirmation obtained when required.
- [ ] Every write call returned HTTP 2xx and `success=true`.
- [ ] Audit event appended with no secrets.
- [ ] Discord report is concise and includes any partial failures.
