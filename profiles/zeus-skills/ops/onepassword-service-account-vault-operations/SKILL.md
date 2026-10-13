---
name: onepassword-service-account-vault-operations
description: "Use when managing 1Password vaults via Service Accounts."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [onepassword, service-account, vault, permissions, credentials, bulk-import, security]
---

# 1Password Service Account Vault Operations

## When to Use

Use this skill when an authorized MGS request requires creating a 1Password vault through a Service Account, granting a known operator access, validating vault permissions, or importing a credential-bearing inventory without exposing it to Sheets, Discord, logs, argv, or plaintext files.

For large exact-data imports, load `references/bulk-sensitive-import.md` after the vault and access gates pass.

## Always-on security gates

- Treat vault creation, user permission changes, and bulk secret writes as separate state changes. Bind each to Rodolfo's explicit target and requested access level, then audit the actual result.
- Never print a Service Account token, item JSON, Secure Note body, password, authenticator seed, recovery material, cookie, proxy credential, or raw free-text credential field.
- Do not copy raw credential-bearing fields to Google Sheets even when 2FA is enabled. A record can contain both the password and authenticator seed, and Sheets adds broader access plus version history.
- Pass secret payloads through stdin or in-memory subprocess input. Do not put them in command arguments, shell history, local CSV/JSON files, debug output, or exception messages. Export the canonical Service Account environment to subprocesses before CLI capability checks. Resolve template names from `op item template list`: the CLI template name is `API Credential`, while the returned JSON category is `API_CREDENTIAL`; do not pass the JSON enum as a template name.
- A successful create response is not closure. Read back the vault, permissions, and every aggregate artifact before reporting success.

## Procedure

### 1. Discover live capability

Load the authorized environment without printing it, then inspect the deployed CLI rather than relying on remembered subcommands:

```bash
op --version
op service-account --help
op vault --help
op vault create --help
op vault list --format json
```

Separate these facts:

```text
Service Account token works
Service Account can see the target vault
Service Account can create vaults
An existing operator can manage or view the new vault
The deployed CLI exposes an edit path for existing Service Account vault membership
```

Do not rotate or revoke the token merely to make a vault visible; token lifecycle and vault membership are independent operations.

### 1A. Bridge an authorized login into Hermes without exposing it

Use this only when the current task explicitly authorizes a browser sign-in, `browser_vault_list` reports 1Password as `unavailable_in_this_session`, and the canonical Service Account can read the exact Login item.

1. Resolve candidates through the canonical MGS wrapper `/root/mgs-agent/scripts/mgs-op-with-service-account.sh item list --format json`, filtering before printing. For same-title entries, fetch each exact item ID with `item get <id> --vault <vault-id> --format json` inside one process and emit only ID, username, and secret presence. Select by the requested username, not list order; identical titles can belong to admin and ordinary-user accounts. Keep revealed passwords and raw item JSON in process memory only.
2. Discover the active Hermes installation with `readlink -f "$(command -v hermes)"` and use its interpreter/modules rather than a guessed checkout or backup. Inspect `VaultStore.add_item` before calling it. Construct `VaultStore(Path(<active-profile-home>) / 'vault')`; create the temporary item with `add_item(kind='login', label=<deterministic TEMP relay label>, origin=<exact origin>, secret={'identifier_type': 'username', 'identifier': <requested username>, 'password': <in-memory password>})`. Require no existing matching relay label before creating a new item. The exact origin includes scheme, hostname, and any non-default port; mobile and desktop hosts are not interchangeable.
3. Call `browser_vault(action='list')` again and use the returned handle for `browser_vault(action='fill', handle=...)`. Fill at the password stage of a multi-step login, then submit and verify the authenticated account. Never type or paste the password with DOM automation, Computer Use, Playwright, shell arguments, or the clipboard.
4. Guarantee cleanup on both successful and failed login paths. If creation and supervised fill span separate tool calls, remove the owned relay in a dedicated cleanup call before any final response; a `finally` around creation alone cannot cover a later fill. Use `remove_item(<returned item ID>)`, then `list_items()` and require zero matching temporary labels. Preserve unrelated vault entries and report a cleanup blocker honestly.

This is a one-operation relay, not a persistent vault import. Do not use it for payment cards, do not leave a second credential copy behind, and do not weaken exact-origin enforcement to make a fill succeed.

### 2. Create a distinct vault when that is the authorized route

If the current Service Account is allowed to create vaults and the requested manually created vault remains outside its visible scope, create a distinctly named vault instead of producing an indistinguishable duplicate:

```bash
op vault create '<distinct name>' \
  --description '<credential-safe purpose>' \
  --icon vault-door \
  --allow-admins-to-manage=true \
  --format json
```

Capture the vault ID privately, then run `op vault get <id> --format json` and require exact name, description, type, and visibility. `--allow-admins-to-manage=true` is a management gate; it does not prove the intended operator can view items.

### 3. Resolve and grant the correct operator

Display names are not stable identifiers. If `op user list` returns multiple active users with the same name:

1. List that operator's access on established MGS vaults.
2. Select the user ID consistently present on those vaults.
3. Read the established permission set.
4. Grant the new vault the same set unless Rodolfo requested a narrower level.
5. Read back `op vault user list <vault>` and compare exact user ID and permissions.

Example shape:

```bash
op vault user grant \
  --vault '<vault-id>' \
  --user '<resolved-user-id>' \
  --permissions '<explicit-comma-separated-set>' \
  --no-input
```

Never choose the first same-name user or infer identity from display order.

### 4. Import sensitive data

Choose the artifact based on the operational need:

```text
Complete bounded snapshot, quota-sensitive  -> encrypted 1Password Document
Search/edit one profile at a time            -> one Secure Note per profile
Both                                          -> master Document first, then optional notes
```

Create the complete master artifact first whenever item-per-record writes may exceed the current write budget. Use `op service-account ratelimit --format json` and budget by observed write units, not by item count; one item creation can consume several units.

The detailed no-plaintext workflow, Document `uuid` handling, per-item schema, reconciliation, and readback gates are in `references/bulk-sensitive-import.md`.

### 5. Reconcile failures before retry

After any failed or timed-out mutating command:

1. List the exact vault.
2. Reconcile by returned ID or a unique deterministic title.
3. Treat an existing exact item as a completed side effect and continue with readback.
4. Retry creation only when readback proves no item exists.
5. Never delete duplicates or partial items without the required destructive-operation confirmation.

Concurrency failures are a signal to lower write concurrency and inspect rate-limit counters, not to replay the whole batch.

### 6. Close with audit evidence

Record only credential-safe evidence:

```text
authorization source
vault ID and name
Service Account identity label
resolved operator ID/access level
item/document counts
readback status
secrets_emitted=false
```

The final report distinguishes the complete master artifact from any optional individual-item count and names every unresolved quota or cleanup condition.

## Acceptance checklist

- [ ] Live CLI capability and target vault visibility were checked.
- [ ] Vault create/get readback matches.
- [ ] Intended operator ID was resolved unambiguously.
- [ ] Exact permissions were granted and read back.
- [ ] Persistent credential storage remains in 1Password only; any authorized temporary encrypted browser relay was removed and read back as zero remaining items.
- [ ] Master artifact was downloaded and compared exactly.
- [ ] Individual items, if requested, have unique titles and field readback.
- [ ] Failed creates were reconciled before retry.
- [ ] No secrets entered Sheets, Discord, logs, argv, or local plaintext.
- [ ] Authorization and validation were appended to the audit trail.
